"""Docker Plugin Utility Module"""
import asyncio
import os
import json

import logging
import aiofiles
from peewee import SQL

from aiodocker import Docker

from beiran.log import build_logger
from beiran.lib import async_req
from beiran.models import Node
from .models import DockerImage, DockerLayer


LOGGER = build_logger()


async def aio_dirlist(path: str):
    """async proxy method for os.listdir"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, os.listdir, path)


async def aio_isdir(path: str):
    """async proxy method for os.isdir"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, os.path.isdir, path)


class DockerUtil:
    """Docker Utilities"""

    class CannotFindLayerMappingError(Exception):
        """..."""
        pass

    def __init__(self, storage: str = "/var/lib/docker", aiodocker: Docker = None,
                 logger: logging.Logger = None) -> None:
        self.storage = storage
        self.diffid_mapping = {} # type: dict
        self.layerdb_mapping = {} # type: dict
        self.aiodocker = aiodocker
        self.logger = logger if logger else LOGGER

    @staticmethod
    def docker_sha_summary(sha: str) -> str:
        """
        shorten sha to 12 bytes length str as docker uses

        e.g "sha256:53478ce18e19304e6e57c37c86ec0e7aa0abfe56dff7c6886ebd71684df7da25"
        to "53478ce18e19"

        Args:
            sha (string): sha string

        Returns:
            string

        """
        return sha.split(":")[1][0:12]

    def docker_find_layer_dir_by_sha(self, sha: str):
        """
        try to find local layer directory containing tar archive
        contents pulled from remote repository

        Args:
            sha (string): sha string

        Returns:
            string directory path or None

        """

        local_diff_dir = self.storage + '/image/overlay2/distribution/v2metadata-by-diffid/sha256'
        local_cache_id = self.storage + '/image/overlay2/layerdb/sha256/{diff_file_name}/cache-id'
        local_layer_dir = self.storage + '/overlay2/{layer_dir_name}/diff/'

        for file_name in os.listdir(local_diff_dir):
            f_path = '{}/{}'.format(local_diff_dir, file_name)
            file = open(f_path)
            try:
                content = json.load(file)
                if not content[0].get('Digest', None) == sha:
                    continue  # next file

                file.close()

                with open(local_cache_id.format(diff_file_name=file_name)) as file:
                    return local_layer_dir.format(layer_dir_name=file.read())

            except ValueError:
                pass

    @staticmethod
    async def reset_docker_info_of_node(uuid_hex: str):
        """ Delete all (local) layers and images from database """
        for image in list(DockerImage.select(DockerImage.hash_id,
                                             DockerImage.available_at)):
            if uuid_hex in image.available_at:
                image.unset_available_at(uuid_hex)
                image.save()

        for layer in list(DockerLayer.select(DockerLayer.id,
                                             DockerLayer.digest,
                                             DockerLayer.available_at)):
            if uuid_hex in layer.available_at:
                layer.unset_available_at(uuid_hex)
                layer.save()

        await DockerUtil.delete_unavailable_objects()

    @staticmethod
    async def delete_unavailable_objects():
        """Delete unavailable layers and images"""
        DockerImage.delete().where(SQL('available_at = \'[]\'')).execute()
        DockerLayer.delete().where(SQL('available_at = \'[]\'')).execute()


    async def fetch_docker_info(self) -> dict:
        """
        Fetch async docker daemon information

        Returns:
            (dict): docker status and information

        """

        try:
            info = await self.aiodocker.system.info() # type: ignore
            return {
                "status": True,
                "daemon_info": info
            }
        except Exception as error:  # pylint: disable=broad-except
            self.logger.error("Error while connecting local docker daemon %s", error)
            return {
                "status": False,
                "error": str(error)
            }

    async def update_docker_info(self, node: Node):
        """
        Makes an async call to docker `client` and get info for `node`

        Args:
            node (Node):

        Returns:
            (None): updates `node` object
        """
        self.logger.debug("Updating local docker info")
        retry_after = 0

        while True:
            docker_info = await self.fetch_docker_info()
            if docker_info["status"]:
                self.logger.debug(" *** Found local docker daemon *** ")
                node.docker = docker_info['daemon_info']
                break
            else:
                self.logger.debug("Cannot fetch docker info," +
                                  " retrying after %d seconds",
                                  retry_after)
                await asyncio.sleep(retry_after)
            if retry_after < 30:
                retry_after += 5

    async def get_diffid_mappings(self) -> dict:
        """..."""

        self.logger.debug("Getting diff-id digest mappings..")
        diffid_mapping = {}
        mapping_dir = self.storage + "/image/overlay2/distribution/diffid-by-digest/sha256"

        try:
            for filename in await aio_dirlist(mapping_dir):
                if await aio_isdir(mapping_dir + '/' + filename):
                    continue

                async with aiofiles.open(mapping_dir + '/' + filename, mode='r') as mapping_file:
                    contents = await mapping_file.read()
                contents = contents.strip()
                diffid_mapping[contents] = 'sha256:' + filename
            self.diffid_mapping = diffid_mapping
            return diffid_mapping
        except FileNotFoundError:
            return {}

    async def get_layerdb_mappings(self) -> dict:
        """..."""

        self.logger.debug("Getting layerdb digest mappings..")
        layerdb_mapping = {}
        layerdb_path = self.storage + "/image/overlay2/layerdb/sha256"

        try:
            for filename in await aio_dirlist(layerdb_path):
                if not await aio_isdir(layerdb_path + '/' + filename):
                    continue

                async with aiofiles.open(layerdb_path + '/' +
                                         filename + '/diff',
                                         mode='r') as mapping_file:
                    contents = await mapping_file.read()
                contents = contents.strip()
                layerdb_mapping[contents] = 'sha256:' + filename

            self.layerdb_mapping = layerdb_mapping
            return layerdb_mapping
        except FileNotFoundError:
            return {}

    async def get_image_layers(self, diffid_list: list) -> list:
        """Returns an array of DockerLayer objects given diffid array"""
        layers = []
        for idx, diffid in enumerate(diffid_list):
            try:
                layer = await self.get_layer_by_diffid(diffid, idx)
                # handle DockerUtil.CannotFindLayerMappingError?
                layers.append(layer)
            except FileNotFoundError:
                self.logger.error("attempted to access to a non-existent layer by diff id: %s",
                                  diffid)
        return layers

    async def get_layer_by_diffid(self, diffid: str, idx: int) -> DockerLayer:
        """
        Makes an DockerLayer objects using diffid of layer

        Args:
            diffid (string)
            idx (integer): order of layer in docker image

        Returns:
            (DockerLayer): `layer` object
        """

        layer_storage_path = self.storage + "/image/overlay2/layerdb"
        if diffid not in self.diffid_mapping:
            raise DockerUtil.CannotFindLayerMappingError()
            # image.has_unknown_layers = True
            # # This layer is not pulled from a registry
            # # It's built on this machine and we're **currently** not interested
            # # in local-only layers
            # print("cannot find digest mapping layer", idx, diffid, image_data['RepoTags'])
            # print(" -- Result: Cannot even find mapping")
            # continue

        digest = self.diffid_mapping[diffid]
        try:
            layer = DockerLayer.get(DockerLayer.digest == digest)
        except DockerLayer.DoesNotExist:
            layer = DockerLayer()
            layer.digest = digest

        layer.local_diff_id = diffid
        # print("--- Processing layer", idx, "of", image_details['RepoTags'])
        # print("Diffid: ", diffid)
        # print("Digest: ", layer.digest)

        if idx == 0:
            layer.layerdb_diff_id = diffid
        else:
            layer.layerdb_diff_id = self.layerdb_mapping[diffid]
        # print("layerdb: ", layer.layerdb_diff_id)

        # try:
        layer_meta_folder = layer_storage_path + '/' + layer.layerdb_diff_id.replace(':', '/')
        async with aiofiles.open(layer_meta_folder + '/size', mode='r') as layer_size_file:
            size_str = await layer_size_file.read()

        layer.size = int(size_str.strip())

        # except FileNotFoundError as e:
        #     # Actually some other layers refers to this layer
        #     # (grep in /var/lib/docker/image/overlay2/layerdb/sha256/
        #     # shows some results)
        #     image.has_not_found_layers = True
        #     print(" -- Result: Cannot find layer folder")
        #     image.layers.append("<not-found>")
        return layer

    async def fetch_docker_image_info(self, name: str):
        """
        Fetch Docker Image manifest specified repository.
        Args:
            name (str): image name (e.g. dkr.rsnc.io/beiran/beirand:v0.1, beirand:latest)
        """

        default_elem = {
            "host": "index.docker.io",
            "repository": "library",
            "tag": "latest"
        }

        url_elem = {
            "host": "",
            "port": "",
            "repository": "",
            "image": "",
            "tag": ""
        }

        # 'name' --- 5 patterns
        # # - beirand
        # # - beirand:v0.1
        # # - beiran/beirand:v0.1
        # # - dkr.rsnc.io/beirand:v0.1
        # # - dkr.rsnc.io/beiran/beirand:v0.1
        #

        #
        # # divide into Domain and Repository and Image
        #
        name_list = name.split("/")

        # nginx:latest
        url_elem['host'] = default_elem['host']
        url_elem['repository'] = default_elem['repository'] + "/"
        img_tag = name_list[0]

        if len(name_list) == 2:
            # openshift/origin:latest, dkr.rsnc.io/nginx:latest
            # determine host name and repository name with "."
            url_elem['host'] = default_elem['host']
            url_elem['repository'] = name_list[0] + "/"
            if "." in name_list[0]:
                url_elem['host'] = name_list[0]
                url_elem['repository'] = ""
            img_tag = name_list[1]

        elif len(name_list) == 3:
            # dkr.rsnc.io/beiran/beirand:v0.1
            url_elem['host'] = name_list[0]
            url_elem['repository'] = name_list[1] + "/"
            img_tag = name_list[2]

        #
        # # divide into Host and Port
        #
        host_list = url_elem['host'].split(":")
        url_elem['host'] = host_list[0]
        url_elem['port'] = ""
        if len(host_list) == 2:
            url_elem['host'], url_elem['port'] = host_list
            url_elem['host'] += ":"

        #
        # # divide into Host and Port
        #
        url_elem['image'] = img_tag
        url_elem['tag'] = default_elem['tag']
        if ":" in img_tag:
            url_elem['image'], url_elem['tag'] = img_tag.split(":")

        url = 'https://{}{}/v2/{}{}/manifests/{}'.format(
            url_elem['host'], url_elem['port'],
            url_elem['repository'], url_elem['image'],
            url_elem['tag']
        )

        if url_elem['host'] == default_elem['host']:
            resp, token = await async_req(
                "https://auth.docker.io/" + \
                "token?service=registry.docker.io&scope=repository:{}{}:pull" \
                .format(url_elem['repository'], url_elem['image'])
            )
            if resp.status != 200:
                raise Exception("Failed to get token")

            resp, manifest = await async_req(url, Authorization="Bearer " + token["token"])
            self.logger.debug("fetching Docker Image manifest: %s", url)
            if resp.status != 200:
                raise Exception("Cannnot fetch Docker image")

            self.logger.debug("fetched Docker Image %s", str(manifest))

        else:
            resp, manifest = await async_req(url)
            self.logger.debug("fetching Docker Image manifest: %s", url)

            if resp.status != 200:
                raise Exception("Cannot fetch Docker Image")

            self.logger.debug("fetched Docker Image %s", str(manifest))

        manifest['hashid'] = resp.headers['Docker-Content-Digest'] # type: ignore

        DockerImage.from_dict(manifest, dialect="manifest").save()
