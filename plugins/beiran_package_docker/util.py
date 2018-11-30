"""Docker Plugin Utility Module"""
import asyncio
import os
import logging
import re
import base64
import json
import hashlib
import platform
from typing import Tuple
from collections import OrderedDict

import aiofiles

from peewee import SQL
from aiodocker import Docker

from beiran.log import build_logger
from beiran.lib import async_write_file_stream, async_req
from beiran.models import Node
from beiran.config import config
from beiran.util import gunzip, clean_keys

from .models import DockerImage, DockerLayer
from .image_ref import normalize_ref


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

    class ConfigDownloadFailed(Exception):
        """..."""
        pass

    class FetchManifestFailed(Exception):
        """..."""
        pass

    class ManifestError(Exception):
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
        DockerImage.delete().where(SQL('available_at = \'[]\' AND' \
            ' download_progress = NULL')).execute()
        DockerLayer.delete().where(SQL('available_at = \'[]\' AND ' \
            'download_progress = NULL')).execute()

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
            self.diffid_mapping[diffid] = None
            # image.has_unknown_layers = True
            # # This layer is not pulled from a registry
            # # It's built on this machine and we're **currently** not interested
            # # in local-only layers
            # print("cannot find digest mapping layer", idx, diffid, image_data['RepoTags'])
            # print(" -- Result: Cannot even find mapping")
            # continue

        digest = self.diffid_mapping[diffid]
        try:
            layer = DockerLayer.get(DockerLayer.diff_id == diffid)
        except DockerLayer.DoesNotExist:
            layer = DockerLayer()
            layer.digest = digest

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
        layer_meta_folder = layer_storage_path + '/' + layer.chain_id.replace(':', '/')
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
        resp, _ = await async_req(url=url, return_json=False, method='HEAD')

        if resp.status == 401 or resp.status == 200:
            if resp.status == 401:
                requirements = await self.get_auth_requirements(resp.headers, **kwargs)

            resp, data = await async_req(url=url, return_json=True, Authorization=requirements,
                                         Accept=schema_v2_header)

        if resp.status != 200:
            raise DockerUtil.FetchManifestFailed("Failed to fetch manifest. code: %d"
                                                 % resp.status)
        return data


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

    def layer_storage_path(self, layer_hash: str)-> str:
        """Where to storage layer downloads (temporarily)"""
        return config.cache_dir + '/layers/sha256/' + layer_hash.replace("sha256:", '') + ".tar.gz"

    async def download_layer_from_origin(self, host: str, repository: str,
                                         layer_hash: str, **kwargs):
        """
        Download layer from registry.
        Args:
            host (str): registry domain (e.g. index.docker.io)
            repository (str): path of repository (e.g. library/centos)
            layer_hash (str): SHA-256 hash of a blob
        """
        save_path = self.layer_storage_path(layer_hash)
        url = 'https://{}/v2/{}/blobs/{}'.format(host, repository, layer_hash)
        requirements = ''

        self.logger.debug("downloading layer from %s", url)

        # try to access the server with HEAD requests
        # there is a purpose to check the type of authentication
        resp, _ = await async_req(url=url, return_json=False, method='HEAD')

        if resp.status == 401 or resp.status == 200:
            if resp.status == 401:
                requirements = await self.get_auth_requirements(resp.headers, **kwargs)

            resp = await async_write_file_stream(url, save_path, timeout=60,
                                                 Authorization=requirements)

        if resp.status != 200:
            raise DockerUtil.LayerDownloadFailed("Failed to download layer. code: %d" % resp.status)

        self.logger.debug("downloaded layer %s to %s", layer_hash, save_path)

    async def download_layer_from_node(self, host: str, diff_id: str):
        """
        Download layer from other node.
        """
        save_path = self.layer_storage_path(diff_id)
        save_path = save_path.rstrip('.gz') # beiran node give a layer as  tar archive
        url = host + '/docker/layers/' + diff_id

        self.logger.debug("downloading layer from %s", url)
        await async_write_file_stream(url, save_path, timeout=60)
        self.logger.debug("downloaded layer %s to %s", diff_id, save_path)

    async def ensure_having_layer(self, host: str, repository: str, layer_hash: str, **kwargs):
        """Download a layer if it doesnt exist locally
        This function returns the path of .tar.gz file, .tar file file or the layer directory
        """

        # beiran cache directory
        gs_layer_path = self.layer_storage_path(layer_hash)
        tar_layer_path = gs_layer_path.rstrip('.gz')

        if os.path.exists(tar_layer_path):
            return 'cache', tar_layer_path # .tar file exists

        if os.path.exists(gs_layer_path):
            return 'cache-gz', gs_layer_path # .tar.gz file exists

        # docker library or other node
        try:
            layer = DockerLayer.get(DockerLayer.digest == layer_hash)

            # check local storage
            layerdb_path = self.storage + "/image/overlay2/layerdb/sha256/" \
                                        + layer.chain_id.replace('sha256:', '')
            if os.path.exists(layerdb_path):
                cache_id = ""
                with open(layerdb_path + '/cache-id')as file:
                    cache_id = file.read()

                return 'docker', self.storage + "/overlay2/" + cache_id + "/diff"

            node_id = layer.available_at[0]
            node = Node.get(Node.uuid == node_id)

            await self.download_layer_from_node(node.url_without_uuid, layer.digest)
            return 'cache', tar_layer_path

        except (DockerLayer.DoesNotExist, IndexError):
            # TODO: Wait for finish if another beiran is currently downloading it
            # TODO:  -- or ask for simultaneous streaming download
            await self.download_layer_from_origin(host, repository, layer_hash, **kwargs)
            return 'cache-gz', gs_layer_path

    async def get_layer_diffid(self, host: str, repository: str, layer_hash: str, **kwargs)-> str:
        """Calculate layer's diffid, using it's tar file"""
        storage, layer_path = await self.ensure_having_layer(host, repository,
                                                             layer_hash, **kwargs)

        if storage == 'docker':
            # TODO: do something using path of the layer directory ?
            layer = DockerLayer.get(DockerLayer.digest == layer_hash)
            return layer.diff_id

        if storage == 'cache-gz':
            # decompress .tar.gz
            gunzip(layer_path)

        with open(layer_path, 'rb') as tarfile:
            diff_id = hashlib.sha256(tarfile.read()).hexdigest()

        return 'sha256:' + diff_id

    async def download_config_from_origin(self, host: str, repository: str,
                                          image_id: str, **kwargs) -> dict:
        """
        Download config file of docker image and save it to database.
        """
        url = 'https://{}/v2/{}/blobs/{}'.format(host, repository, image_id)
        requirements = ''

        self.logger.debug("downloading config from %s", url)

        # try to access the server with HEAD requests
        # there is a purpose to check the type of authentication
        resp, _ = await async_req(url=url, return_json=False, method='HEAD')

        if resp.status == 401 or resp.status == 200:
            if resp.status == 401:
                requirements = await self.get_auth_requirements(resp.headers, **kwargs)

            resp, data = await async_req(url=url, return_json=True, Authorization=requirements)

        if resp.status != 200:
            raise DockerUtil.ConfigDownloadFailed("Failed to download config. code: %d"
                                                  % resp.status)

        return data

    async def fetch_config_schema_v1(self, host: str, repository: str, # pylint: disable=too-many-locals, too-many-branches
                                     manifest: dict) -> Tuple[dict, str, str]:
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


        rootfs = await self.get_layer_diffids_of_image(host, repository, descriptors)

        config_json = OrderedDict(json.loads(manifest['history'][0]['v1Compatibility']))
        clean_keys(config_json, ['id', 'parent', 'Size', 'parent_id', 'layer_id', 'throwaway'])

        config_json['rootfs'] = rootfs
        config_json['history'] = history

        # calc RepoDigest
        del manifest['signatures']
        manifest_str = json.dumps(manifest, indent=3)
        repo_digest = 'sha256:' + hashlib.sha256(manifest_str.encode('utf-8')).hexdigest()

        # replace, shape, then calc digest
        config_json = OrderedDict(sorted(config_json.items(), key=lambda x: x[0]))
        config_json_str = json.dumps(config_json, separators=(',', ':'))
        config_json_str = config_json_str.replace('&', r'\u0026') \
                                         .replace('<', r'\u003c') \
                                         .replace('>', r'\u003e')

        config_digest = 'sha256:' + hashlib.sha256(config_json_str.encode('utf-8')).hexdigest()

        return config_json, config_digest, repo_digest


    async def fetch_config_schema_v2(self, host: str, repository: str,
                                     manifest: dict)-> Tuple[dict, str, str]:
        """
        Pull image using image manifest version 2
        """
        config_digest = manifest['config']['digest']
        config_json = await self.download_config_from_origin(
            host, repository, config_digest
        )

        manifest_str = json.dumps(manifest, indent=3)
        repo_digest = 'sha256:' + hashlib.sha256(manifest_str.encode('utf-8')).hexdigest()

        return config_json, config_digest, repo_digest


    async def fetch_config_manifest_list(self, host: str, repository: str,
                                         manifestlist: dict)-> Tuple[dict, str, str]:
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
        manifest = await self.fetch_docker_image_manifest(host, repository, manifest_digest)
        schema_v = manifest['schemaVersion']

        if schema_v == 1:
            # pull layers and create config from version 1 manifest
            config_json, config_digest, _ = await self.fetch_config_schema_v1(
                host, repository, manifest
            )

        elif schema_v == 2:
            if manifest['mediaType'] == 'application/vnd.docker.distribution.manifest.v2+json':
                # pull layers using version 2 manifest
                config_json, config_digest, _ = await self.fetch_config_schema_v2(
                    host, repository, manifest
                )
            else:
                raise DockerUtil.ManifestError('Invalid media type: %d' % manifest['mediaType'])
        else:
            raise DockerUtil.ManifestError('Invalid schema version: %d' % schema_v)

        manifestlist_str = json.dumps(manifestlist, indent=3)
        repo_digest = 'sha256:' + hashlib.sha256(manifestlist_str.encode('utf-8')).hexdigest()

        return config_json, config_digest, repo_digest



    async def get_layer_diffids_of_image(self, host: str, repository: str,
                                         descriptors: list)-> dict:
        """Download and allocate layers included in an image."""
        tasks = [
            self.get_layer_diffid(host, repository, layer_d['digest'])
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

    async def create_or_download_config(self, tag: str):
        """
        Create or download image config.

        Depend on manifest version;
            - schema v1: create config
            - schema v2: download config
            - manifest list: v1 or v2
        """

        try:
            image = DockerImage.get_image_data(tag)
            config_path = self.storage + '/image/overlay2/imagedb/content/sha256/' \
                                       + image.hash_id.replace('sha256:', '')
            content = ""
            with open(config_path)as file:
                content = file.read()

            return json.loads(content), image.hash_id, image.repo_digests[0].split('@')[1]

        except (DockerImage.DoesNotExist, FileNotFoundError):
            pass


        ref = normalize_ref(tag, index=True)

        # get manifest
        manifest = await self.fetch_docker_image_manifest(
            ref['domain'], ref['repo'], ref['suffix'])

        schema_v = manifest['schemaVersion']

        if schema_v == 1:

            # pull layers and create config from version 1 manifest
            config_json, config_digest, repo_digest = await self.fetch_config_schema_v1(
                ref['domain'], ref['repo'], manifest
            )

        elif schema_v == 2:
            media_type = manifest['mediaType']

            if media_type == 'application/vnd.docker.distribution.manifest.v2+json':

                # pull layers using version 2 manifest
                config_json, config_digest, repo_digest = await self.fetch_config_schema_v2(
                    ref['domain'], ref['repo'], manifest
                )

            elif media_type == 'application/vnd.docker.distribution.manifest.list.v2+json':

                # pull_schema_list
                config_json, config_digest, repo_digest = await self.fetch_config_manifest_list(
                    ref['domain'], ref['repo'], manifest
                )

            else:
                raise DockerUtil.ManifestError('Invalid media type: %d' % media_type)
        else:
            raise DockerUtil.ManifestError('Invalid schema version: %d' % schema_v)

        #FIXME! acutually, config must be saved before downloading image
        # image = DockerImage.get(DockerImage.hash_id == config_digest)
        # image.config = config_json
        # image.save()

        return config_json, config_digest, repo_digest
