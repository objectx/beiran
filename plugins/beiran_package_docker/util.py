"""Docker Plugin Utility Module"""
import asyncio
import os
import logging
import re
import base64
import aiohttp
import aiofiles

from peewee import SQL
from aiodocker import Docker

from beirand.common import CACHE_DIR
from beiran.log import build_logger
from beiran.lib import async_write_file_stream, async_req
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

    class AuthenticationFailed(Exception):
        """..."""
        pass

    class LayerDownloadFailed(Exception):
        """..."""
        pass

    def __init__(self, storage: str = "/var/lib/docker", aiodocker: Docker = None,
                 logger: logging.Logger = None) -> None:
        self.storage = storage

        # TODO: Persist this mapping cache to disk or database
        self.diffid_mapping: dict = {}
        self.layerdb_mapping: dict = {}

        self.aiodocker = aiodocker or Docker()
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
        diff_file_name = ""

        local_digest_dir = self.storage + '/image/overlay2/distribution/diffid-by-digest/sha256'
        local_layer_db = self.storage + '/image/overlay2/layerdb/sha256'
        local_cache_id = local_layer_db + '/{diff_file_name}/cache-id'
        local_layer_dir = self.storage + '/overlay2/{layer_dir_name}/diff'

        f_path = local_digest_dir + "/{}".format(sha.replace('sha256:', '', 1))

        file = open(f_path, 'r')
        diff_1 = file.read()
        file.close()

        for layer_dir_name in os.listdir(local_layer_db):
            f_path = '{}/{}/diff'.format(local_layer_db, layer_dir_name)

            with open(f_path, 'r') as file:
                diff_2 = file.read()
                if diff_2 == diff_1:
                    diff_file_name = layer_dir_name
                    break

        with open(local_cache_id.format(diff_file_name=diff_file_name)) as file:
            return local_layer_dir.format(layer_dir_name=file.read())

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
            info = await self.aiodocker.system.info()
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
        """
        Returns a mapping dict for layers;
         - keys => diff-id
         - values => digest (being used for downloading layers!?)
        """

        # TODO:
        # - to be able to find digests FOR SPECIFIC diff-id,
        # see here => /var/lib/docker/image/overlay2/distribution/v2metadata-by-diffid/sha256
        # Note that these are JSON files, pointing to multiple (POSSIBLY DIFFERENT)
        # digests (per remote repository)

        # FIXME! There are multiple digests for diff-ids, per remote repository
        # sometimes they are same, sometimes they are not.

        self.logger.debug("Getting diff-id digest mappings..")
        mapping_dir = self.storage + "/image/overlay2/distribution/diffid-by-digest/sha256"

        cached_digests = self.diffid_mapping.values()

        try:
            for filename in await aio_dirlist(mapping_dir):
                digest = 'sha256:' + filename
                if digest in cached_digests:
                    continue

                if await aio_isdir(mapping_dir + '/' + filename):
                    continue

                async with aiofiles.open(mapping_dir + '/' + filename, mode='r') as mapping_file:
                    contents = await mapping_file.read()

                contents = contents.strip()
                self.diffid_mapping[contents] = digest
            return self.diffid_mapping
        except FileNotFoundError:
            return {}

    async def get_layerdb_mappings(self) -> dict:
        """
        Returns a mapping dict for layers;
         - keys => diff-id
         - values => chain-id
        """

        # TODO:
        # - to be able to find digests FOR SPECIFIC diff-id,
        # we have to enumerate all {chain-in}/diff files in layerdb
        # since there are no mappings outside...

        self.logger.debug("Getting layerdb digest mappings..")
        layerdb_path = self.storage + "/image/overlay2/layerdb/sha256"

        cached_chain_ids = self.layerdb_mapping.values()

        try:
            for filename in await aio_dirlist(layerdb_path):
                chain_id = 'sha256:' + filename
                if chain_id in cached_chain_ids:
                    continue

                if not await aio_isdir(layerdb_path + '/' + filename):
                    continue

                async with aiofiles.open(layerdb_path + '/' +
                                         filename + '/diff',
                                         mode='r') as mapping_file:
                    contents = await mapping_file.read()

                contents = contents.strip()
                self.layerdb_mapping[contents] = chain_id

            return self.layerdb_mapping
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

        manifest['hashid'] = resp.headers['Docker-Content-Digest']

        DockerImage.from_dict(manifest, dialect="manifest").save()

    async def get_docker_bearer_token(self, realm, service, scope):
        """
        Get Bearer token from auth.docker.io
        """
        _, data = await async_req(
            "{}?service={}&scope={}".format(realm, service, scope)
        )
        token = data['token']
        return token

    async def get_auth_requirements(self, headers, **kwargs):
        """
        Get requirements for registry authentication.
        Supporting -> Basic, Bearer token

        Args:
            headers: async client response header
        """

        if headers['Www-Authenticate'].startswith('Bearer'):
            # parse 'Bearer realm="https://auth.docker.io/token",
            # service="registry.docker.io",scope="repository:google/cadvisor:pull"'
            values = re.findall('(\w+(?==)|(?<=")[\w.:/]+)',  # pylint: disable=anomalous-backslash-in-string
                                headers['Www-Authenticate'])
            val_dict = dict(zip(values[0::2], values[1::2]))

            try:
                token = await self.get_docker_bearer_token(
                    val_dict['realm'],
                    val_dict['service'],
                    val_dict['scope']
                )
            except Exception:
                raise DockerUtil.AuthenticationFailed("Failed to get Bearer token")

            return 'Bearer ' + token

        if headers['Www-Authenticate'].startswith('Basic'):
            try:
                login_str = kwargs.pop('user') + ":" + kwargs.pop('passwd')
                login_str = base64.b64encode(login_str.encode('utf-8')).decode('utf-8')
            except KeyError:
                raise DockerUtil.AuthenticationFailed("Basic auth required but " \
                                                      "'user' and 'passwd' wasn't passed")

            return 'Basic ' + login_str

        raise DockerUtil.AuthenticationFailed("Unsupported type of authentication (%s)"
                                              % headers['Www-Authenticate'])

    async def download_layer_from_origin(self, host, repository, layer_hash, **kwargs):
        """
        Download layer from registry.
        Args:
            host (str): registry domain (e.g. index.docker.io)
            repository (str): path of repository (e.g. library/centos)
            layer_hash (str): SHA-256 hash of a blob
        """
        save_path = CACHE_DIR + '/layers/sha256/' + layer_hash.lstrip("sha256:") + ".tar.gz"
        url = 'https://{}/v2/{}/blobs/{}'.format(host, repository, layer_hash)
        requirements = None

        self.logger.debug("downloading layer from %s", url)

        # try to access the server with HTTP HEAD requests
        # there is also a purpose to check the type of authentication
        try:
            resp, _ = await async_req(url=url, return_json=False, method='HEAD')

        except aiohttp.client_exceptions.ClientConnectorSSLError:
            self.logger.debug("the server %s may not support HTTPS. retry with HTTP", host)
            url = 'http://{}/v2/{}/blobs/{}'.format(host, repository, layer_hash)
            resp, _ = await async_req(url=url, return_json=False, method='HEAD')

        if resp.status == 401 or resp.status == 200:
            if resp.status == 401:
                requirements = await self.get_auth_requirements(resp.headers, **kwargs)

            resp = await async_write_file_stream(url, save_path, Authorization=requirements)

        if resp.status != 200:
            raise DockerUtil.LayerDownloadFailed("Failed to download layer. code: %d" % resp.status)

        self.logger.debug("downloaded layer %s to %s", layer_hash, save_path)
