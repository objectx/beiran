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

"""
Container packaging plugin
"""
import os
import re
import base64
import json
import tarfile
import uuid
import gzip
import hashlib
from typing import Tuple
import aiohttp

from peewee import SQL

from beiran.config import config
from beiran.plugin import BasePackagePlugin, History
from beiran.models import Node
from beiran.lib import async_write_file_stream, async_req
from beiran.daemon.peer import Peer

from beiran_package_container.image_ref import is_tag, is_digest, add_default_tag, del_idpref
from beiran_package_container.models import ContainerImage, ContainerLayer
from beiran_package_container.models import MODEL_LIST
from beiran_package_container.util import ContainerUtil


PLUGIN_NAME = 'container'
PLUGIN_TYPE = 'package'


# pylint: disable=attribute-defined-outside-init
class ContainerPackaging(BasePackagePlugin):  # pylint: disable=too-many-instance-attributes
    """Container support for Beiran"""
    DEFAULTS = {
        'cache_dir': config.cache_dir + '/container'
    }

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

    # consts related with timeout
    TIMEOUT = 10 # second
    TIMEOUT_DL_MANIFEST = 10
    TIMEOUT_DL_CONFIG = 10
    TIMEOUT_DL_LAYER = 30
    RETRY = 2

    async def init(self):
        self.cache_dir = self.config["cache_dir"]
        self.layer_tar_path = self.cache_dir + '/layers/tar/sha256' # for storing archives of layers
        self.layer_gz_path = self.cache_dir + '/layers/gz/sha256' # for storing compressed archives
        self.tmp_path = self.cache_dir + '/tmp'

        if not os.path.isdir(self.layer_tar_path):
            os.makedirs(self.layer_tar_path)
        if not os.path.isdir(self.layer_gz_path):
            os.makedirs(self.layer_gz_path)
        if not os.path.isdir(self.tmp_path):
            os.makedirs(self.tmp_path)

        self.model_list = MODEL_LIST
        self.history = History() # type: History
        self.queues: dict = {}

        # TODO: Persist this mapping cache to disk or database
        self.diffid_mapping: dict = {}
        self.layerdb_mapping: dict = {}

    async def save_image_at_node(self, image: ContainerImage, node: Node):
        """Save an image from a node into db"""
        try:
            image_ = ContainerImage.get(ContainerImage.hash_id == image.hash_id)
            image_.set_available_at(node.uuid.hex)
            image_.save()
            self.log.debug("update existing image %s, now available on new node: %s",
                           image.hash_id, node.uuid.hex)
        except ContainerImage.DoesNotExist:
            image.available_at = [node.uuid.hex] # type: ignore
            image.save(force_insert=True)
            self.log.debug("new image from remote %s", str(image))

    async def fetch_images_from_peer(self, peer: Peer):
        """fetch image list from the node and update local db"""

        images = await peer.client.get_images()
        self.log.debug("received image list from peer")

        for image_data in images:
            # discard `id` sent from remote
            image_data.pop('id', None)
            image = ContainerImage.from_dict(image_data)
            await self.save_image_at_node(image, peer.node)

    @staticmethod
    async def delete_layers(diff_id_list: list)-> None:
        """
        Unset available layer, delete it if no image refers it
        """
        layers = ContainerLayer.select() \
                            .where(ContainerLayer.diff_id.in_(diff_id_list))
        for layer in layers:
            if not layer.available_at:
                layer.delete_instance()

    @staticmethod
    async def tag_image(image_id: str, tag: str):
        """
        Tag an image existing in database. If already same tag exists,
        move it from old one to new one.
        """
        target = ContainerImage.get_image_data(image_id)
        if tag not in target.tags:
            target.tags = [tag] # type: ignore
            target.save()

        images = ContainerImage.select().where((SQL('tags LIKE \'%%"%s"%%\'' % tag)))

        for image in images:
            if image.hash_id == target.hash_id:
                continue

            image.tags.remove(tag)
            image.save()

    def get_diffid_by_digest(self, digest: str)-> str:
        """Return diff id of a layer by digest from mapping."""
        return list(self.diffid_mapping.keys())[list(self.diffid_mapping.values()).index(digest)]

    async def fetch_image_manifest(self, host, repository, tag_or_digest, schema_v2_header,
                                   **kwargs) -> dict:
        """
        Fetch image manifest specified repository.
        """
        url = 'https://{}/v2/{}/manifests/{}'.format(host, repository, tag_or_digest)
        requirements = ''

        self.log.debug("fetch manifest from %s", url)

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
            raise self.FetchManifestFailed("Failed to fetch manifest. code: %d"
                                           % resp.status)
        return manifest

    async def get_bearer_token(self, realm, service, scope):
        """
        Get Bearer token
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
                token = await self.get_bearer_token(
                    val_dict['realm'],
                    val_dict['service'],
                    val_dict['scope']
                )
            except Exception:
                raise self.AuthenticationFailed("Failed to get Bearer token")

            return 'Bearer ' + token

        if headers['Www-Authenticate'].startswith('Basic'):
            try:
                login_str = kwargs.pop('user') + ":" + kwargs.pop('passwd')
                login_str = base64.b64encode(login_str.encode('utf-8')).decode('utf-8')
            except KeyError:
                raise self.AuthenticationFailed("Basic auth required but " \
                                                      "'user' and 'passwd' wasn't passed")

            return 'Basic ' + login_str

        raise self.AuthenticationFailed("Unsupported type of authentication (%s)"
                                        % headers['Www-Authenticate'])

    def get_layer_tar_file(self, diff_id: str):
        """Get local path of layer tarball"""
        return os.path.join(self.layer_tar_path, del_idpref(diff_id) + '.tar')

    def get_layer_gz_file(self, digest: str):
        """Get local path of layer compressed tarball"""
        return os.path.join(self.layer_gz_path, del_idpref(digest) + '.tar.gz')


    async def download_config_from_origin(self, host: str, repository: str,
                                          image_id: str, **kwargs) -> str:
        """
        Download a config file of image and save it to database.
        """
        url = 'https://{}/v2/{}/blobs/{}'.format(host, repository, image_id)
        requirements = ''

        self.log.debug("downloading config from %s", url)

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
            raise self.ConfigDownloadFailed("Failed to download config. code: %d"
                                            % resp.status)
        return await resp.text(encoding='utf-8')

    async def download_layer_from_origin(self, ref: dict, digest: str, jobid: str, **kwargs):
        """
        Download layer from registry.
        """
        save_path = self.get_layer_gz_file(digest)
        url = 'https://{}/v2/{}/blobs/{}'.format(ref['domain'], ref['repo'], digest)
        requirements = ''

        self.log.debug("downloading layer from %s", url)

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
                                                 ContainerUtil.get_additional_time_downlaod(
                                                     layer_size),
                                                 retry=self.RETRY,
                                                 queue=self.queues[jobid][digest]['queue'],
                                                 Authorization=requirements)

        if resp.status != 200:
            raise self.LayerDownloadFailed("Failed to download layer. code: %d"
                                           % resp.status)

        self.log.debug("downloaded layer %s to %s", digest, save_path)
        self.queues[jobid][digest]['status'] = self.DL_FINISH

    async def download_layer_from_node(self, digest: str, jobid: str,
                                       url: str)-> aiohttp.client_reqrep.ClientResponse:
        """
        Download layer from other node.
        """
        diff_id = self.get_diffid_by_digest(digest)
        save_path = self.get_layer_tar_file(diff_id)
        self.log.debug("downloading layer from %s", url)

        # HEAD request to get size
        resp, _ = await async_req(url=url, return_json=False, timeout=self.TIMEOUT,
                                  retry=self.RETRY, method='HEAD')
        layer_size = int(resp.headers.get('content-length'))

        self.queues[jobid][digest]['size'] = layer_size
        self.queues[jobid][digest]['status'] = self.DL_TAR_DOWNLOADING

        resp = await async_write_file_stream(url, save_path, timeout=self.TIMEOUT_DL_LAYER + \
                                             ContainerUtil.get_additional_time_downlaod(layer_size),
                                             retry=self.RETRY,
                                             queue=self.queues[jobid][digest]['queue'])
        self.log.debug("downloaded layer %s to %s", digest, save_path)
        self.queues[jobid][digest]['status'] = self.DL_FINISH
        return resp

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
            raise self.ConfigError(
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
                    raise self.LayerNotFound("Layer doesn't exist in cache directory")
                tar.add(layer_tar_file, arcname=arc_tar_names[i])

        return tar_path
