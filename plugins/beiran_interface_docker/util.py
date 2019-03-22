# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=too-many-lines
"""Docker Plugin Utility Module"""
import asyncio
import os
import logging
import json
import uuid
import subprocess
from typing import Tuple, Optional
import aiohttp

import aiofiles

from aiodocker import Docker

from beiran.log import build_logger
from beiran.models import Node

from beiran_package_container.models import ContainerLayer
from beiran_package_container.image_ref import add_idpref, del_idpref


LOGGER = build_logger()


async def aio_dirlist(path: str):
    """async proxy method for os.listdir"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, os.listdir, path)


async def aio_isdir(path: str):
    """async proxy method for os.isdir"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, os.path.isdir, path)


class DockerUtil: # pylint: disable=too-many-instance-attributes
    """Docker Utilities"""

    class CannotFindLayerMappingError(Exception):
        """..."""
        pass

    class LayerNotFound(Exception):
        """..."""
        pass

    class LayerMetadataNotFound(Exception):
        """..."""
        pass

    def __init__(self, storage: str, # pylint: disable=too-many-arguments
                 aiodocker: Docker = None, logger: logging.Logger = None,
                 local_node: Node = None, tar_split_path=None) -> None:

        self.storage = storage
        self.local_node = local_node

        self.aiodocker = aiodocker or Docker()
        self.logger = logger if logger else LOGGER
        self.tar_split_path = tar_split_path
        self.container = None

    @property
    def digest_path(self)-> str:
        """Get digest path in docker storage"""
        return self.storage + '/image/overlay2/distribution/diffid-by-digest/sha256'

    @property
    def v2metadata_path(self)-> str:
        """Get v2metadata path in docker storage"""
        return self.storage + '/image/overlay2/distribution/v2metadata-by-diffid/sha256'

    @property
    def layerdb_path(self)-> str:
        """Get layerdb path in docker storage"""
        return self.storage + '/image/overlay2/layerdb/sha256'

    @property
    def layerdir_path(self)-> str:
        """Get directory of layer path in docker storage"""
        return self.storage + '/overlay2/{layer_dir_name}/diff'

    @property
    def config_path(self)-> str:
        """Get path of image config in docker storage"""
        return self.storage + '/image/overlay2/imagedb/content/sha256'

    def save_local_paths(self, layer: ContainerLayer):
        """Update 'cache_path' and 'cache_gz_path' and 'docker_path' with paths of local node"""
        try:
            docker_path = self.layerdir_path.format(
                layer_dir_name=self.get_cache_id_from_chain_id(layer.chain_id))

            if os.path.exists(docker_path):
                layer.docker_path = docker_path
            else:
                layer.docker_path = None

        except FileNotFoundError:
            layer.docker_path = None

        cache_path = self.container.get_layer_tar_file(layer.diff_id) # type: ignore
        if os.path.exists(cache_path):
            layer.cache_path = cache_path
        else:
            layer.cache_path = None

        if layer.digest:
            cache_gz_path = self.container.get_layer_gz_file(layer.digest) # type: ignore
            if os.path.exists(cache_gz_path):
                layer.cache_gz_path = cache_gz_path
            else:
                layer.cache_gz_path = None

    def docker_find_layer_dir_by_digest(self, digest: str):
        """
        try to find local layer directory containing tar archive
        contents pulled from remote repository

        Args:
            digest (string): digest of layer

        Returns:
            string directory path or None

        """
        diff_file_name = ""

        local_digest_dir = self.digest_path
        local_layer_db = self.layerdb_path
        local_cache_id = local_layer_db + '/{diff_file_name}/cache-id'
        local_layer_dir = self.layerdir_path
        f_path = local_digest_dir + "/{}".format(del_idpref(digest))

        try:
            file = open(f_path, 'r')
        except FileNotFoundError:
            return None

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

    async def get_digest_by_diffid(self, diffid: str)-> Optional[str]:
        """Return digest of a layer by diff id."""
        try:
            with open(os.path.join(self.v2metadata_path, del_idpref(diffid)))as file:
                content = json.load(file)
                return content[0]['Digest']
        except FileNotFoundError:
            return None

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
        mapping_dir = self.digest_path

        cached_digests = self.container.diffid_mapping.values() # type: ignore

        try:
            for filename in await aio_dirlist(mapping_dir):
                digest = add_idpref(filename)
                if digest in cached_digests:
                    continue

                if await aio_isdir(mapping_dir + '/' + filename):
                    continue

                async with aiofiles.open(mapping_dir + '/' + filename, mode='r') as mapping_file:
                    contents = await mapping_file.read()

                contents = contents.strip()
                self.container.diffid_mapping[contents] = digest # type: ignore
            return self.container.diffid_mapping # type: ignore
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
        layerdb_path = self.layerdb_path

        cached_chain_ids = self.container.layerdb_mapping.values() # type: ignore

        try:
            for filename in await aio_dirlist(layerdb_path):
                chain_id = add_idpref(filename)
                if chain_id in cached_chain_ids:
                    continue

                if not await aio_isdir(layerdb_path + '/' + filename):
                    continue

                async with aiofiles.open(layerdb_path + '/' +
                                         filename + '/diff',
                                         mode='r') as mapping_file:
                    contents = await mapping_file.read()

                contents = contents.strip()
                self.container.layerdb_mapping[contents] = chain_id # type: ignore

            return self.container.layerdb_mapping # type: ignore
        except FileNotFoundError:
            return {}

    async def get_image_layers(self, diffid_list: list, image_id: str) -> list:
        """Returns an array of ContainerLayer objects given diffid array"""
        layers = []
        for idx, diffid in enumerate(diffid_list):
            try:
                layer = await self.get_layer_by_diffid(diffid, idx, image_id)
                # handle DockerUtil.CannotFindLayerMappingError?
                layers.append(layer)
            except FileNotFoundError:
                self.logger.error("attempted to access to a non-existent layer by diff id: %s",
                                  diffid)
        return layers

    async def get_layer_by_diffid(self, diffid: str, idx: int, image_id: str) -> ContainerLayer:
        """
        Makes an ContainerLayer objects using diffid of layer

        Args:
            diffid (string)
            idx (integer): order of layer in docker image

        Returns:
            (ContainerLayer): `layer` object
        """

        layerdb_path = self.storage + "/image/overlay2/layerdb"
        if diffid not in self.container.diffid_mapping: # type: ignore
            self.container.diffid_mapping[diffid] = await self.get_digest_by_diffid(diffid) # type: ignore # pylint: disable=line-too-long
            # image.has_unknown_layers = True
            # # This layer is not pulled from a registry
            # # It's built on this machine and we're **currently** not interested
            # # in local-only layers
            # print("cannot find digest mapping layer", idx, diffid, image_data['RepoTags'])
            # print(" -- Result: Cannot even find mapping")
            # continue

        digest = self.container.diffid_mapping[diffid] # type: ignore
        try:
            layer = ContainerLayer.get(ContainerLayer.diff_id == diffid)
        except ContainerLayer.DoesNotExist:
            layer = ContainerLayer()
            layer.digest = digest
        layer.set_local_image_refs(image_id)

        layer.diff_id = diffid
        # print("--- Processing layer", idx, "of", image_details['RepoTags'])
        # print("Diffid: ", diffid)
        # print("Digest: ", layer.digest)

        if idx == 0:
            layer.chain_id = diffid
        else:
            if diffid not in self.container.layerdb_mapping: # type: ignore
                await self.get_layerdb_mappings()
            layer.chain_id = self.container.layerdb_mapping[diffid] # type: ignore
        # print("layerdb: ", layer.chain_id)

        # try:
        layer_meta_folder = layerdb_path + '/' + layer.chain_id.replace(':', '/')
        async with aiofiles.open(layer_meta_folder + '/size', mode='r') as layer_size_file:
            size_str = await layer_size_file.read()

        layer.size = int(size_str.strip())

        local_layer_dir = self.layerdir_path
        layer.docker_path = local_layer_dir.format(
            layer_dir_name=self.get_cache_id_from_chain_id(layer.chain_id))

        # set cachae_path
        cache_path = self.container.get_layer_tar_file(diffid) # type: ignore
        if os.path.exists(cache_path):
            layer.cache_path = cache_path

        if digest:
            cache_gz_path = self.container.get_layer_gz_file(digest) # type: ignore
            if os.path.exists(cache_gz_path):
                layer.cache_gz_path = cache_gz_path

        # except FileNotFoundError as e:
        #     # Actually some other layers refers to this layer
        #     # (grep in /var/lib/docker/image/overlay2/layerdb/sha256/
        #     # shows some results)
        #     image.has_not_found_layers = True
        #     print(" -- Result: Cannot find layer folder")
        #     image.layers.append("<not-found>")
        return layer

    def get_cache_id_from_chain_id(self, chain_id: str)-> str:
        """Read cache id file and return the content (cache id)"""
        with open(self.storage + '/image/overlay2/layerdb/' + \
                  chain_id.replace(':', '/') + '/cache-id') as file:
            return file.read()

    async def ensure_docker_having_layer(self, digest: str, jobid: str) -> Tuple[str, str]:
        """Download a layer if it doesnt exist locally
        This function returns the path of .tar.gz file, .tar file file or the layer directory

        Args:
            digest(str): digest of layer
        """
        diff_id = self.container.get_diffid_by_digest(digest) # type: ignore
        tar_layer_path = self.container.get_layer_tar_file(diff_id) # type: ignore

        try:
            layer = ContainerLayer.get(ContainerLayer.digest == digest)

            # check docker storage
            try:
                if layer.docker_path:
                    layer.cache_path = await self.assemble_layer_tar(layer.diff_id)
                    self.logger.debug("Found layer %s in Docker's storage", layer.diff_id)
                    layer.save()
                    return 'cache', layer.cache_path
            # this exception handling may be needless if 'dockerlayer' in datbase is
            # initialized when daemon start
            except DockerUtil.LayerMetadataNotFound:
                pass

            # try to download layer from node that has tarball in own cache directory
            for node_id in layer.available_at:
                if node_id == self.local_node.uuid.hex: # type: ignore
                    continue

                node = Node.get(Node.uuid == node_id)
                resp = await self.container.download_docker_layer_from_node( # type: ignore
                    node.url_without_uuid, layer.digest, jobid)

                if resp.status == 200:
                    if not os.path.exists(tar_layer_path):
                        raise self.container.LayerNotFound( # type: ignore
                            "Layer doesn't exist in cache directory")
                    return 'cache', tar_layer_path

        except (ContainerLayer.DoesNotExist, IndexError):
            pass

        return '', ''

    async def docker_create_download_config(self, tag: str, jobid: str = uuid.uuid4().hex):
        """
        Create or download image config.

        Depend on manifest version;
            - schema v1: create config
            - schema v2: download config
            - manifest list: v1 or v2
        """
        return await self.container.create_or_download_config( # type: ignore
            tag, jobid,
            {
                "manifest": "application/vnd.docker.distribution.manifest.v2+json",
                "manifest-list": "application/vnd.docker.distribution.manifest.list.v2+json",
                "signed-manifest": "application/vnd.docker.distribution.manifest.v1+prettyjws",
                "type": "application/json"
            },
            self.ensure_docker_having_layer
        )

    async def download_docker_layer_from_node(self, host: str, digest: str,
                                              jobid: str)-> aiohttp.client_reqrep.ClientResponse:
        """
        Download layer from other node.
        """
        # if get a taball of layer, it is preferable to use diff_id
        return await self.container.download_layer_from_node( # type: ignore
            digest, jobid,
            host + '/docker/layers/' + digest
        )

    async def load_image(self, tar_path: str):
        """
        Load image tarball.
        """
        self.logger.debug("loading image...")

        @aiohttp.streamer
        async def file_sender(writer, file_name=None):
            with open(file_name, "rb") as file:
                chunk = file.read(1024 * 64)
                while chunk:
                    await writer.write(chunk)
                    chunk = file.read(1024 * 64)

        await self.aiodocker.images.import_image(data=file_sender(file_name=tar_path)) # pylint: disable=no-value-for-parameter

    async def assemble_layer_tar(self, diff_id: str)-> str:
        """
        Assemble layer tarball from Docker's storage. Now we need 'tar-split'.
        """
        input_file = os.path.join(
            self.layerdb_path, del_idpref(
                self.container.layerdb_mapping[diff_id]), "tar-split.json.gz") # type: ignore
        if not os.path.exists(input_file):
            raise DockerUtil.LayerMetadataNotFound(
                "Docker doesn't have metadata of the layer %s" % input_file)

        relative_path = self.docker_find_layer_dir_by_digest(
            self.container.diffid_mapping[diff_id]) # type: ignore
        if not relative_path:
            raise DockerUtil.LayerNotFound("Layer doesn't exist in %s" % relative_path)

        output_file = os.path.join(
            self.container.layer_tar_path, del_idpref(diff_id) + '.tar') # type: ignore

        cmd = self.tar_split_path + " asm --input " + input_file + "  --path " + \
              relative_path + " --output " + output_file

        with open('/dev/null', 'w') as devnull:
            subprocess.run(cmd.split(), env=os.environ, stdout=devnull, stderr=devnull)

        return output_file
