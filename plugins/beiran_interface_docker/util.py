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
import re
import base64
import json
import hashlib
import platform
import tarfile
import uuid
import subprocess
import gzip
from typing import Tuple, Optional
from collections import OrderedDict
from pyee import EventEmitter
import aiohttp

import aiofiles

from peewee import SQL
from aiodocker import Docker

from beiran.log import build_logger
from beiran.lib import async_write_file_stream, async_req
from beiran.models import Node
from beiran.util import clean_keys

from beiran_package_container.models import ContainerImage, ContainerLayer
from beiran_package_container.image_ref import normalize_ref, is_tag, is_digest, add_idpref, \
                                               del_idpref, add_default_tag


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

    class AuthenticationFailed(Exception):
        """..."""
        pass

    class LayerDownloadFailed(Exception):
        """..."""
        pass

    class ConfigDownloadFailed(Exception):
        """..."""
        pass

    class FetchManifestFailed(Exception):
        """..."""
        pass

    class ManifestError(Exception):
        """..."""
        pass

    class ConfigError(Exception):
        """..."""
        pass

    class LayerNotFound(Exception):
        """..."""
        pass

    class LayerMetadataNotFound(Exception):
        """..."""

    # status for downloading layers
    DL_INIT = 'init'
    DL_ALREADY = 'already'
    DL_TAR_DOWNLOADING = 'tar_downloading'
    DL_GZ_DOWNLOADING = 'gs_downloading'
    DL_FINISH = 'finish'

    # event datas for downloading layers
    EVENT_START_LAYER_DOWNLOAD = "start_layer_download"

    # consts related with timeout
    TIMEOUT = 10 # second
    TIMEOUT_DL_MANIFEST = 10
    TIMEOUT_DL_CONFIG = 10
    TIMEOUT_DL_LAYER = 30
    RETRY = 2

    def __init__(self, cache_dir: str, storage: str, # pylint: disable=too-many-arguments
                 aiodocker: Docker = None, logger: logging.Logger = None,
                 local_node: Node = None, tar_split_path=None) -> None:
        self.cache_dir = cache_dir
        self.layer_tar_path = self.cache_dir + '/layers/tar/sha256' # for storing archives of layers
        self.layer_gz_path = self.cache_dir + '/layers/gz/sha256' # for storing compressed archives
        self.tmp_path = self.cache_dir + '/tmp'

        if not os.path.isdir(self.layer_tar_path):
            os.makedirs(self.layer_tar_path)
        if not os.path.isdir(self.layer_gz_path):
            os.makedirs(self.layer_gz_path)
        if not os.path.isdir(self.tmp_path):
            os.makedirs(self.tmp_path)

        self.storage = storage
        self.local_node = local_node

        # TODO: Persist this mapping cache to disk or database
        self.diffid_mapping: dict = {}
        self.layerdb_mapping: dict = {}

        self.aiodocker = aiodocker or Docker()
        self.logger = logger if logger else LOGGER
        self.queues: dict = {}
        self.emitters: dict = {}
        self.tar_split_path = tar_split_path

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

    @staticmethod
    def get_additional_time_downlaod(size: int) -> int:
        """Get additional time to downlload something"""
        return size // 5000000

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

    @staticmethod
    async def reset_docker_info_of_node(uuid_hex: str):
        """ Delete all (local) layers and images from database """
        for image in list(ContainerImage.select(ContainerImage.hash_id,
                                                ContainerImage.available_at)):
            if uuid_hex in image.available_at:
                image.unset_available_at(uuid_hex)
                image.save()

        for layer in list(ContainerLayer.select(ContainerLayer.id,
                                                ContainerLayer.digest,
                                                ContainerLayer.available_at)):
            if uuid_hex in layer.available_at:
                layer.unset_available_at(uuid_hex)
                layer.save()

        await DockerUtil.delete_unavailable_objects()

    @staticmethod
    async def delete_unavailable_objects():
        """Delete unavailable layers and images"""
        ContainerImage.delete().where(SQL('available_at = \'[]\' AND' \
            ' download_progress = \'null\'')).execute()
        ContainerLayer.delete().where(SQL('available_at = \'[]\' AND ' \
            'download_progress = \'null\'')).execute()

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

    def get_diffid_by_digest(self, digest: str)-> str:
        """Return diff id of a layer by digest from mapping."""
        return list(self.diffid_mapping.keys())[list(self.diffid_mapping.values()).index(digest)]

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

        cached_digests = self.diffid_mapping.values()

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
        layerdb_path = self.layerdb_path

        cached_chain_ids = self.layerdb_mapping.values()

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
                self.layerdb_mapping[contents] = chain_id

            return self.layerdb_mapping
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
        if diffid not in self.diffid_mapping:
            self.diffid_mapping[diffid] = await self.get_digest_by_diffid(diffid)
            # image.has_unknown_layers = True
            # # This layer is not pulled from a registry
            # # It's built on this machine and we're **currently** not interested
            # # in local-only layers
            # print("cannot find digest mapping layer", idx, diffid, image_data['RepoTags'])
            # print(" -- Result: Cannot even find mapping")
            # continue

        digest = self.diffid_mapping[diffid]
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
            if diffid not in self.layerdb_mapping:
                await self.get_layerdb_mappings()
            layer.chain_id = self.layerdb_mapping[diffid]
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
        cache_path = self.get_layer_tar_file(diffid)
        if os.path.exists(cache_path):
            layer.cache_path = cache_path

        if digest:
            cache_gz_path = self.get_layer_gz_file(digest)
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

    async def fetch_docker_image_manifest(self, host, repository, tag_or_digest, **kwargs) -> dict:
        """
        Fetch Docker Image manifest specified repository.
        """
        url = 'https://{}/v2/{}/manifests/{}'.format(host, repository, tag_or_digest)
        requirements = ''

        self.logger.debug("fetch manifest from %s", url)

        # about header, see below URL
        # https://github.com/docker/distribution/blob/master/docs/spec/manifest-v2-2.md#backward-compatibility
        schema_v2_header = "application/vnd.docker.distribution.manifest.v2+json, " \
                           "application/vnd.docker.distribution.manifest.list.v2+json, " \
                           "application/vnd.docker.distribution.manifest.v1+prettyjws, " \
                           "application/json"

        # try to access the server with HEAD requests
        # there is a purpose to check the type of authentication
        resp, _ = await async_req(url=url, return_json=False, timeout=self.TIMEOUT,
                                  retry=self.RETRY, method='HEAD')

        if resp.status == 401 or resp.status == 200:
            if resp.status == 401:
                requirements = await self.get_auth_requirements(resp.headers, **kwargs)

            resp, manifest = await async_req(url=url, return_json=True, Authorization=requirements,
                                             timeout=self.TIMEOUT_DL_MANIFEST, retry=self.RETRY,
                                             Accept=schema_v2_header)

        if resp.status != 200:
            raise DockerUtil.FetchManifestFailed("Failed to fetch manifest. code: %d"
                                                 % resp.status)
        return manifest


    async def get_docker_bearer_token(self, realm, service, scope):
        """
        Get Bearer token from auth.docker.io
        """
        _, data = await async_req(
            "{}?service={}&scope={}".format(realm, service, scope),
            timeout=self.TIMEOUT, retry=self.RETRY,
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
            values = re.findall('(\w+(?==)|(?<==")[^"]+(?="))',  # pylint: disable=anomalous-backslash-in-string
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

    async def download_layer_from_origin(self, ref: dict, digest: str, jobid: str, **kwargs):
        """
        Download layer from registry.
        """
        save_path = self.get_layer_gz_file(digest)
        url = 'https://{}/v2/{}/blobs/{}'.format(ref['domain'], ref['repo'], digest)
        requirements = ''

        self.logger.debug("downloading layer from %s", url)

        # try to access the server with HEAD requests
        # there is a purpose to check the type of authentication
        resp, _ = await async_req(url=url, return_json=False, timeout=self.TIMEOUT,
                                  retry=self.RETRY, method='HEAD')

        if resp.status == 401 or resp.status == 200:
            if resp.status == 401:
                requirements = await self.get_auth_requirements(resp.headers, **kwargs)

            # HEAD request for get size
            resp, _ = await async_req(url=url, return_json=False, timeout=self.TIMEOUT,
                                      retry=self.RETRY, method='HEAD', Authorization=requirements)
            layer_size = int(resp.headers.get('content-length'))

            self.queues[jobid][digest]['size'] = layer_size
            self.queues[jobid][digest]['status'] = self.DL_GZ_DOWNLOADING

            resp = await async_write_file_stream(url, save_path, timeout=self.TIMEOUT_DL_LAYER + \
                                                 self.get_additional_time_downlaod(layer_size),
                                                 retry=self.RETRY,
                                                 queue=self.queues[jobid][digest]['queue'],
                                                 Authorization=requirements)

        if resp.status != 200:
            raise DockerUtil.LayerDownloadFailed("Failed to download layer. code: %d"
                                                 % resp.status)

        self.logger.debug("downloaded layer %s to %s", digest, save_path)
        self.queues[jobid][digest]['status'] = self.DL_FINISH

    async def download_layer_from_node(self, host: str, digest: str,
                                       jobid: str)-> aiohttp.client_reqrep.ClientResponse:
        """
        Download layer from other node.
        """
        # if get a taball of layer, it is preferable to use diff_id
        url = host + '/docker/layers/' + digest

        diff_id = self.get_diffid_by_digest(digest)
        save_path = self.get_layer_tar_file(diff_id)
        self.logger.debug("downloading layer from %s", url)

        # HEAD request to get size
        resp, _ = await async_req(url=url, return_json=False, timeout=self.TIMEOUT,
                                  retry=self.RETRY, method='HEAD')
        layer_size = int(resp.headers.get('content-length'))

        self.queues[jobid][digest]['size'] = layer_size
        self.queues[jobid][digest]['status'] = self.DL_TAR_DOWNLOADING

        resp = await async_write_file_stream(url, save_path, timeout=self.TIMEOUT_DL_LAYER + \
                                             self.get_additional_time_downlaod(layer_size),
                                             retry=self.RETRY,
                                             queue=self.queues[jobid][digest]['queue'])
        self.logger.debug("downloaded layer %s to %s", digest, save_path)
        self.queues[jobid][digest]['status'] = self.DL_FINISH
        return resp

    def get_layer_tar_file(self, diff_id: str):
        """Get local path of layer tarball"""
        return os.path.join(self.layer_tar_path, del_idpref(diff_id) + '.tar')

    def get_layer_gz_file(self, digest: str):
        """Get local path of layer compressed tarball"""
        return os.path.join(self.layer_gz_path, del_idpref(digest) + '.tar.gz')


    async def ensure_having_layer(self, ref: dict, digest: str, jobid: str, **kwargs):
        """Download a layer if it doesnt exist locally
        This function returns the path of .tar.gz file, .tar file file or the layer directory

        Args:
            digest(str): digest of layer
        """
        # beiran cache directory
        diff_id = self.get_diffid_by_digest(digest)
        tar_layer_path = self.get_layer_tar_file(diff_id)
        gz_layer_path = self.get_layer_gz_file(digest)

        if os.path.exists(tar_layer_path):
            self.logger.debug("Found layer (%s)", tar_layer_path)
            return 'cache', tar_layer_path # .tar file exists

        if os.path.exists(gz_layer_path):
            self.logger.debug("Found layer (%s)", gz_layer_path)
            return 'cache-gz', gz_layer_path # .tar.gz file exists

         # docker library or other node
        try:
            layer = ContainerLayer.get(ContainerLayer.digest == digest)

            # check docker storage
            try:
                if layer.docker_path:
                    layer.cache_path = await self.assemble_layer_tar(layer.diff_id)
                    self.logger.debug("Found layer %s in Docker's storage", diff_id)
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
                resp = await self.download_layer_from_node(
                    node.url_without_uuid, layer.digest, jobid)

                if resp.status == 200:
                    if not os.path.exists(tar_layer_path):
                        raise DockerUtil.LayerNotFound("Layer doesn't exist in cache directory")
                    return 'cache', tar_layer_path

        except (ContainerLayer.DoesNotExist, IndexError):
            pass

        # TODO: Wait for finish if another beiran is currently downloading it
        # TODO:  -- or ask for simultaneous streaming download
        await self.download_layer_from_origin(ref, digest, jobid, **kwargs)
        return 'cache-gz', gz_layer_path

    async def get_layer_diffid(self, ref: dict, digest: str, jobid: str, **kwargs)-> str:
        """Calculate layer's diffid, using it's tar file"""
        storage, layer_path = await self.ensure_having_layer(ref, digest, jobid, **kwargs)

        if storage == 'cache':
            tmp_hash = hashlib.sha256()
            with open(layer_path, 'rb') as file:
                while True:
                    chunk = file.read(2048 * tmp_hash.block_size)
                    if not chunk:
                        break
                    tmp_hash.update(chunk)

            diff_id = tmp_hash.hexdigest()

        elif storage == 'cache-gz':
            diff_id, _ = await self.decompress_gz_layer(layer_path) # decompress .tar.gz

        return add_idpref(diff_id)

    async def decompress_gz_layer(self, gzip_file: str) -> Tuple[str, str]:
        """Decompress a gzip file of layer and return the diff id."""
        tmp_hash = hashlib.sha256()
        tmp_file = self.get_layer_tar_file(uuid.uuid4().hex)

        with gzip.open(gzip_file, 'rb') as gzfile:
            with open(tmp_file, "wb") as tarf:
                while True:
                    chunk = gzfile.read(2048 * tmp_hash.block_size)
                    if not chunk:
                        break

                    tmp_hash.update(chunk)
                    tarf.write(chunk)

        diff_id = tmp_hash.hexdigest()
        tar_layer_path = self.get_layer_tar_file(diff_id)
        os.rename(tmp_file, tar_layer_path)
        return diff_id, tar_layer_path

    async def download_config_from_origin(self, host: str, repository: str,
                                          image_id: str, **kwargs) -> str:
        """
        Download config file of docker image and save it to database.
        """
        url = 'https://{}/v2/{}/blobs/{}'.format(host, repository, image_id)
        requirements = ''

        self.logger.debug("downloading config from %s", url)

        # try to access the server with HEAD requests
        # there is a purpose to check the type of authentication
        resp, _ = await async_req(url=url, return_json=False, timeout=self.TIMEOUT,
                                  retry=self.RETRY, method='HEAD')

        if resp.status == 401 or resp.status == 200:
            if resp.status == 401:
                requirements = await self.get_auth_requirements(resp.headers, **kwargs)

            resp, _ = await async_req(url=url, timeout=self.TIMEOUT_DL_CONFIG,
                                      retry=self.RETRY, Authorization=requirements)

        if resp.status != 200:
            raise DockerUtil.ConfigDownloadFailed("Failed to download config. code: %d"
                                                  % resp.status)
        return await resp.text(encoding='utf-8')

    async def fetch_config_schema_v1(self, ref: dict, # pylint: disable=too-many-locals, too-many-branches
                                     manifest: dict, jobid: str) -> Tuple[str, str, str]:
        """
        Pull image using image manifest version 1
        """
        fs_layers = manifest['fsLayers']

        descriptors = []
        history = []

        for i in range(len(fs_layers) - 1, -1, -1):

            compatibility = json.loads(manifest['history'][i]['v1Compatibility'])

            # do not chenge key order
            layer_h = OrderedDict() # type: dict # history of a layer
            if 'created' in compatibility:
                layer_h['created'] = compatibility['created']
            if 'author' in compatibility:
                layer_h['author'] = compatibility['author']
            if 'container_config' in compatibility:
                if compatibility['container_config']['Cmd']:
                    layer_h['created_by'] = " ".join(compatibility['container_config']['Cmd'])

            if 'comment' in compatibility:
                layer_h['comment'] = compatibility['comment']
            if 'throwaway' in compatibility:
                layer_h['empty_layer'] = True

            history.append(layer_h)

            if 'throwaway' in compatibility:
                continue

            layer_descriptor = {
                'digest': fs_layers[i]['blobSum'],
                # 'repoinfo': manifest['name'] + ':' + manifest['tag']
                # 'repo':
                # 'v2metadataservice':
            }
            descriptors.append(layer_descriptor)


        rootfs = await self.get_layer_diffids_of_image(ref, descriptors, jobid)

        # save layer records
        chain_id = rootfs['diff_ids'][0]
        top = True
        for i, layer_d in enumerate(descriptors):
            if top:
                top = False
            else:
                chain_id = self.calc_chain_id(chain_id, rootfs['diff_ids'][i])

            # Probably following sentences are needed when saving layers that do not belong
            # to any image.

            # layer_ = ContainerLayer()
            # layer_tar_path = self.layer_storage_path(layer_d['digest']).rstrip('.gz')
            # layer_.set_available_at(self.local_node.uuid.hex) # type: ignore
            # layer_.digest = layer_d['digest']
            # layer_.diff_id = rootfs['diff_ids'][i]
            # layer_.chain_id = chain_id
            # layer_.size = self.get_diff_size(layer_tar_path)
            # layer_.cache_path = layer_tar_path

            # layer_.save()

            self.diffid_mapping[rootfs['diff_ids'][i]] = layer_d['digest']
            self.layerdb_mapping[rootfs['diff_ids'][i]] = chain_id

        # create base of image config
        config_json = OrderedDict(json.loads(manifest['history'][0]['v1Compatibility']))
        clean_keys(config_json, ['id', 'parent', 'Size', 'parent_id', 'layer_id', 'throwaway'])

        config_json['rootfs'] = rootfs
        config_json['history'] = history

        # calc RepoDigest
        del manifest['signatures']
        manifest_str = json.dumps(manifest, indent=3)
        repo_digest = add_idpref(hashlib.sha256(manifest_str.encode('utf-8')).hexdigest())

        # replace, shape, then calc digest
        config_json = OrderedDict(sorted(config_json.items(), key=lambda x: x[0]))
        config_json_str = json.dumps(config_json, separators=(',', ':'))
        config_json_str = config_json_str.replace('&', r'\u0026') \
                                         .replace('<', r'\u003c') \
                                         .replace('>', r'\u003e')

        config_digest = add_idpref(hashlib.sha256(config_json_str.encode('utf-8')).hexdigest())

        return config_json_str, config_digest, repo_digest


    async def fetch_config_schema_v2(self, ref: dict,
                                     manifest: dict, jobid: str)-> Tuple[str, str, str]:
        """
        Pull image using image manifest version 2
        """
        config_digest = manifest['config']['digest']
        config_json_str = await self.download_config_from_origin(
            ref['domain'], ref['repo'], config_digest
        )

        manifest_str = json.dumps(manifest, indent=3)
        repo_digest = add_idpref(hashlib.sha256(manifest_str.encode('utf-8')).hexdigest())

        # set mapping
        diff_id_list = json.loads(config_json_str)['rootfs']['diff_ids']

        chain_id = diff_id_list[0]
        top = True
        for i, diff_id in enumerate(diff_id_list):
            if top:
                top = False
            else:
                chain_id = self.calc_chain_id(chain_id, diff_id_list[i])
            self.diffid_mapping[diff_id] = manifest['layers'][i]['digest']
            self.layerdb_mapping[diff_id] = chain_id

        # download layers
        await self.get_layer_diffids_of_image(ref, manifest['layers'], jobid)

        return config_json_str, config_digest, repo_digest

    async def fetch_config_manifest_list(self, ref: dict,
                                         manifestlist: dict, jobid: str)-> Tuple[str, str, str]:
        """
        Read manifest list and call appropriate pulling image function for the machine.
        """
        host_arch = await self.get_go_python_arch()
        host_os = await self.get_go_python_os()
        manifest_digest = None

        for manifest in manifestlist['manifests']:
            if manifest['platform']['architecture'] == host_arch and \
               manifest['platform']['os'] == host_os:
                manifest_digest = manifest['digest']
                break

        if manifest_digest is None:
            raise DockerUtil.ManifestError('No supported platform found in manifest list')


        # get manifest
        manifest = await self.fetch_docker_image_manifest(ref['domain'], ref['repo'],
                                                          manifest_digest)
        schema_v = manifest['schemaVersion']

        if schema_v == 1:
            # pull layers and create config from version 1 manifest
            config_json_str, config_digest, _ = await self.fetch_config_schema_v1(
                ref, manifest, jobid
            )

        elif schema_v == 2:
            if manifest['mediaType'] == 'application/vnd.docker.distribution.manifest.v2+json':
                # pull layers using version 2 manifest
                config_json_str, config_digest, _ = await self.fetch_config_schema_v2(
                    ref, manifest, jobid
                )
            else:
                raise DockerUtil.ManifestError('Invalid media type: %d' % manifest['mediaType'])
        else:
            raise DockerUtil.ManifestError('Invalid schema version: %d' % schema_v)

        manifestlist_str = json.dumps(manifestlist, indent=3)
        repo_digest = add_idpref(hashlib.sha256(manifestlist_str.encode('utf-8')).hexdigest())
        return config_json_str, config_digest, repo_digest

    def create_emitter(self, jobid):
        """Create a new emitter and add it to a emitter dictionary"""
        self.emitters[jobid] = EventEmitter()

    async def get_layer_diffids_of_image(self, ref: dict, descriptors: list, jobid: str)-> dict:
        """Download and allocate layers included in an image."""
        self.queues[jobid] = dict()

        for layer_d in descriptors:
            # check layer existence, then set status
            status = self.DL_INIT
            try:
                layer = ContainerLayer.get(ContainerLayer.digest == layer_d['digest'])
                if layer.cache_path or layer.cache_gz_path or layer.docker_path:
                    status = self.DL_ALREADY
            except ContainerLayer.DoesNotExist:
                pass

            self.queues[jobid][layer_d['digest']] = {
                'queue': asyncio.Queue(),
                'status': status,
                'size': 0
            }

        # if request to /docker/images/<id>/config, emitters is empty
        if jobid in self.emitters:
            self.emitters[jobid].emit(self.EVENT_START_LAYER_DOWNLOAD)

        tasks = [
            self.get_layer_diffid(ref, layer_d['digest'], jobid)
            for layer_d in descriptors
        ]
        results = await asyncio.gather(*tasks)

        return OrderedDict(type='layers', diff_ids=results)


    async def get_go_python_arch(self)-> str:
        """
        In order to compare architecture name of the image (runtime.GOARCH), convert
        platform.machine() and return it.
        """
        arch = platform.machine()

        go_python_arch_mapping = {
            'x86_64': 'amd64',  # linux amd64
            'AMD64' : 'amd64',  # windows amd64

            # TODO
        }
        return go_python_arch_mapping[arch]


    async def get_go_python_os(self)-> str:
        """
        In order to compare OS name of the image (runtime.GOOS), convert
        platform.machine() and return it.
        """
        os_name = platform.system()

        # go_python_os_mapping = {
        #     'Linux': 'linux',
        #     'Windows' : 'windows',
        #     'Darwin' : 'darwin',
        #     # TODO
        # }
        # return go_python_os_mapping[os_name]

        return os_name.lower() # I don't know if this is the right way

    async def create_or_download_config(self, tag: str, jobid: str = uuid.uuid4().hex):
        """
        Create or download image config.

        Depend on manifest version;
            - schema v1: create config
            - schema v2: download config
            - manifest list: v1 or v2
        """

        # try:
        #     image = ContainerImage.get_image_data(tag)
        #     if image.repo_digests:
        #         return image.config, image.hash_id, image.repo_digests[0].split('@')[1]
        #     return image.config, image.hash_id, None

        # except (ContainerImage.DoesNotExist, FileNotFoundError):
        #     pass


        ref = normalize_ref(tag, index=True)

        # get manifest
        manifest = await self.fetch_docker_image_manifest(
            ref['domain'], ref['repo'], ref['suffix'])

        schema_v = manifest['schemaVersion']

        if schema_v == 1:

            # pull layers and create config from version 1 manifest
            config_json_str, config_digest, repo_digest = await self.fetch_config_schema_v1(
                ref, manifest, jobid
            )

        elif schema_v == 2:
            media_type = manifest['mediaType']

            if media_type == 'application/vnd.docker.distribution.manifest.v2+json':

                # pull layers using version 2 manifest
                config_json_str, config_digest, repo_digest = await self.fetch_config_schema_v2(
                    ref, manifest, jobid
                )

            elif media_type == 'application/vnd.docker.distribution.manifest.list.v2+json':

                # pull_schema_list
                config_json_str, config_digest, repo_digest = await self.fetch_config_manifest_list(
                    ref, manifest, jobid
                )

            else:
                raise DockerUtil.ManifestError('Invalid media type: %d' % media_type)
        else:
            raise DockerUtil.ManifestError('Invalid schema version: %d' % schema_v)

        return config_json_str, config_digest, repo_digest

    def get_diff_size(self, tar_path: str) -> int:
        """Get the total size of files in a tarball"""
        total = 0
        with tarfile.open(tar_path, 'r:') as tar:
            for tarinfo in tar:
                if tarinfo.isreg():
                    total += tarinfo.size
        return total

    def calc_chain_id(self, parent_chain_id: str, diff_id: str) -> str:
        """calculate chain id"""
        string = parent_chain_id + ' ' + diff_id
        return add_idpref(hashlib.sha256(string.encode('utf-8')).hexdigest())

    async def create_image_from_tar(self, tag_or_digest: str, config_json_str: str, # pylint: disable=too-many-locals
                                    image_id: str)-> str:
        """
        Collect layers, download or create config json, create manifest for loading image
        and create image tarball
        """
        manifest_f_name = 'manifest.json'

        # add latest tag
        if not is_digest(tag_or_digest):
            if not is_tag(tag_or_digest):
                tag_or_digest = add_default_tag(tag_or_digest)

        image_id = del_idpref(image_id)

        config_digest = hashlib.sha256(config_json_str.encode('utf-8')).hexdigest()
        if config_digest != image_id:
            raise DockerUtil.ConfigError(
                'Invalid config. The digest is wrong (expect: %s, actual: %s)'
                % (image_id, config_digest))

        # create config file
        config_file_name = image_id + '.json'
        with open(self.tmp_path + '/' + config_file_name, 'w') as file:
            file.write(config_json_str)

        # get layer files
        diff_id_list = json.loads(config_json_str)['rootfs']['diff_ids']
        arc_tar_names = [
            del_idpref(diff_id) + '.tar'
            for diff_id in diff_id_list
        ]

        # create manifest
        manifest = [
            {
                "Config": config_file_name,
                "RepoTags": [tag_or_digest] if is_tag(tag_or_digest) else None,
                "Layers": arc_tar_names,
            }
        ]
        with open(self.tmp_path + '/' + manifest_f_name, 'w') as file:
            file.write(json.dumps(manifest))

        # create tarball
        tar_path = self.tmp_path + '/' + 'image.tar'
        with tarfile.open(tar_path, 'w') as tar:
            tar.add(self.tmp_path + '/' + config_file_name, arcname=config_file_name)
            tar.add(self.tmp_path + '/' + manifest_f_name, arcname=manifest_f_name)

            for i, diff_id in enumerate(diff_id_list):
                layer_tar_file = self.get_layer_tar_file(diff_id)
                if not os.path.exists(layer_tar_file):
                    raise DockerUtil.LayerNotFound("Layer doesn't exist in cache directory")
                    # Do not create tarball from storage of docker!!!
                    # The digest of the tarball varies depending on mtime of the file to be added
                    # with tarfile.open(self.layer_tar_path + '/' + f_name, "w") as layer_tar:
                    #     chain_id = self.layerdb_mapping[diff_id_list[i]]
                    #     layer_tar.add(
                    #         self.layerdir_path'.format(
                    #             layer_dir_name=self.get_cache_id_from_chain_id(chain_id)))
                tar.add(layer_tar_file, arcname=arc_tar_names[i])

        return tar_path

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
            self.layerdb_path, del_idpref(self.layerdb_mapping[diff_id]), "tar-split.json.gz")
        if not os.path.exists(input_file):
            raise DockerUtil.LayerMetadataNotFound(
                "Docker doesn't have metadata of the layer %s" % input_file)

        relative_path = self.docker_find_layer_dir_by_digest(self.diffid_mapping[diff_id])
        if not relative_path:
            raise DockerUtil.LayerNotFound("Layer doesn't exist in %s" % relative_path)

        output_file = os.path.join(self.layer_tar_path, del_idpref(diff_id) + '.tar')

        cmd = self.tar_split_path + " asm --input " + input_file + "  --path " + \
              relative_path + " --output " + output_file

        with open('/dev/null', 'w') as devnull:
            subprocess.run(cmd.split(), env=os.environ, stdout=devnull, stderr=devnull)

        return output_file