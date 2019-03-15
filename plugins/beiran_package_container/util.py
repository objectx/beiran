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
"""Container Plugin Utility Module"""
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
import gzip
from typing import Tuple
from pyee import EventEmitter
import aiohttp

from peewee import SQL

from beiran.log import build_logger
from beiran.lib import async_write_file_stream, async_req
from beiran.models import Node

from .models import ContainerImage, ContainerLayer
from .image_ref import is_tag, is_digest, add_idpref, del_idpref, \
                       add_default_tag


LOGGER = build_logger()


async def aio_dirlist(path: str):
    """async proxy method for os.listdir"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, os.listdir, path)


async def aio_isdir(path: str):
    """async proxy method for os.isdir"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, os.path.isdir, path)


class ContainerUtil: # pylint: disable=too-many-instance-attributes
    """Container Utilities"""

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

    class ConfigError(Exception):
        """..."""
        pass

    class LayerNotFound(Exception):
        """..."""
        pass

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

    def __init__(self, cache_dir: str,  # pylint: disable=too-many-arguments
                 logger: logging.Logger = None,
                 local_node: Node = None) -> None:
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

        self.local_node = local_node

        # TODO: Persist this mapping cache to disk or database
        self.diffid_mapping: dict = {}
        self.layerdb_mapping: dict = {}

        self.logger = logger if logger else LOGGER
        self.queues: dict = {}
        self.emitters: dict = {}


    @staticmethod
    def get_additional_time_downlaod(size: int) -> int:
        """Get additional time to downlload something"""
        return size // 5000000

    @staticmethod
    async def delete_unavailable_objects():
        """Delete unavailable layers and images"""
        ContainerImage.delete().where(SQL('available_at = \'[]\' AND' \
            ' download_progress = \'null\'')).execute()
        ContainerLayer.delete().where(SQL('available_at = \'[]\' AND ' \
            'download_progress = \'null\'')).execute()

    def get_diffid_by_digest(self, digest: str)-> str:
        """Return diff id of a layer by digest from mapping."""
        return list(self.diffid_mapping.keys())[list(self.diffid_mapping.values()).index(digest)]

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
            raise ContainerUtil.FetchManifestFailed("Failed to fetch manifest. code: %d"
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
                raise ContainerUtil.AuthenticationFailed("Failed to get Bearer token")

            return 'Bearer ' + token

        if headers['Www-Authenticate'].startswith('Basic'):
            try:
                login_str = kwargs.pop('user') + ":" + kwargs.pop('passwd')
                login_str = base64.b64encode(login_str.encode('utf-8')).decode('utf-8')
            except KeyError:
                raise ContainerUtil.AuthenticationFailed("Basic auth required but " \
                                                      "'user' and 'passwd' wasn't passed")

            return 'Basic ' + login_str

        raise ContainerUtil.AuthenticationFailed("Unsupported type of authentication (%s)"
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
            raise ContainerUtil.LayerDownloadFailed("Failed to download layer. code: %d"
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
            raise ContainerUtil.ConfigDownloadFailed("Failed to download config. code: %d"
                                                     % resp.status)
        return await resp.text(encoding='utf-8')

    def create_emitter(self, jobid):
        """Create a new emitter and add it to a emitter dictionary"""
        self.emitters[jobid] = EventEmitter()

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
            raise ContainerUtil.ConfigError(
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
                    raise ContainerUtil.LayerNotFound("Layer doesn't exist in cache directory")
                    # Do not create tarball from storage of docker!!!
                    # The digest of the tarball varies depending on mtime of the file to be added
                    # with tarfile.open(self.layer_tar_path + '/' + f_name, "w") as layer_tar:
                    #     chain_id = self.layerdb_mapping[diff_id_list[i]]
                    #     layer_tar.add(
                    #         self.layerdir_path'.format(
                    #             layer_dir_name=self.get_cache_id_from_chain_id(chain_id)))
                tar.add(layer_tar_file, arcname=arc_tar_names[i])

        return tar_path
