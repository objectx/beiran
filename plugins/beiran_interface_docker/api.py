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

"""Docker API endpoints"""
import os
import random
import re
import json
import asyncio
import uuid
import aiohttp
from tornado import web
from tornado.web import HTTPError
from tornado.web import Application
from tornado.httputil import HTTPServerRequest
from peewee import SQL
import aiodocker
# from beiran.util import create_tar_archive
from beiran.client import Client
from beiran.models import Node
from beiran.cmd_req_handler import RPCEndpoint, rpc
from beiran.util import until_event
from beiran_package_container.models import ContainerImage, ContainerLayer

class Services:
    """These needs to be injected from the plugin init code"""
    local_node = None
    logger = None
    aiodocker = None
    docker_util = None
    loop = None
    daemon = None


class ImagesTarHandler(web.RequestHandler):
    """ Images export handler """

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    async def get(self, image_identifier: str):
        """
            Get image as a tarball
        """
        try:
            # pylint: disable=no-member
            content = await Services.aiodocker.images.export_image(image_identifier) # type: ignore
            # pylint: enable=no-member
            self.set_header("Content-Type", "application/x-tar")

            while True:
                chunk = await content.read(65536)
                if not chunk:
                    break
                self.write(chunk)
                await self.flush()
            self.finish()
        except aiodocker.exceptions.DockerError as error:
            raise HTTPError(status_code=404, log_message=error.message)
        except Exception as error:
            Services.logger.error("Image Stream failed: %s", str(error)) # type: ignore
            raise HTTPError(status_code=500, log_message=str(error))

    async def head(self, image_identifier: str):
        """
            HEAD endpoint
        """
        try:
            image = ContainerImage.get_image_data(image_identifier)
        except ContainerImage.DoesNotExist:
            raise HTTPError(status_code=404, log_message='Image Not Found')

        self.set_header("Docker-Image-HashID", image.hash_id)
        self.set_header("Docker-Image-CreatedAt", image.created_at)
        self.set_header("Docker-Image-Size", image.size)

        self.finish()


class ImageInfoHandler(web.RequestHandler):
    """ Image info handler """

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    async def get(self, image_identifier):
        """
            Get image information
        """
        self.set_header("Content-Type", "application/json")

        image_identifier = image_identifier.rstrip('/info')
        try:
            image = ContainerImage.get_image_data(image_identifier)
        except ContainerImage.DoesNotExist:
            raise HTTPError(status_code=404, log_message='Image Not Found')

        self.write(json.dumps(image.to_dict(dialect="api")))
        self.finish()

class ImageConfigHandler(web.RequestHandler):
    """ Image config handler (for testing)"""

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    async def get(self, image_identifier):
        """
            Create or download config (this endpoint for test)
        """
        self.set_header("Content-Type", "application/json")

        image_identifier = image_identifier.rstrip('/config')
        config_str, image_id, repo_digest = \
            await Services.docker_util.docker_create_download_config(image_identifier)

        dict_ = {
            'config': json.loads(config_str),
            'image_id': image_id,
            'repo_digest': repo_digest
        }

        self.write(json.dumps(dict_))
        self.finish()


class LayerDownload(web.RequestHandler):
    """ Container image layer downloading handler """

    def data_received(self, chunk):
        pass

    def _set_headers(self, layer_id: str):
        # modify headers to pretend like docker registry if we decide to be proxy
        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Docker-Content-Digest", layer_id)
        self.set_header("Docker-Distribution-Api-Version", "registry/2.0")
        self.set_header("Etag", layer_id)
        # only nosniff, what else could it be?
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("accept-ranges", "bytes")
        # how is 31536000 calculated?
        self.set_header("cache-control", "max-age=31536000")

    @staticmethod
    async def prepare_tar_archive(layer_id: str) -> str:
        """
        Finds docker layer path and prepare a tar archive for `layer_id`.

        Args:
            layer_id (str): uuid str of layer

        Returns:
            (str) tar path

        Raises:
            404 if layer not found

        """
        try:
            layer = ContainerLayer.select().where(ContainerLayer.digest == layer_id).get()
        except ContainerLayer.DoesNotExist:
            raise HTTPError(status_code=404, log_message="Layer Not Found")

        if not layer.cache_path and not layer.cache_gz_path and not layer.docker_path:
            raise HTTPError(status_code=404, log_message="Layer Not Found")

        # not deal with .tar.gz in cache directory now
        if not layer.cache_path:
            if layer.cache_gz_path:
                _, layer.cache_path = \
                    await Services.docker_util.container.decompress_gz_layer(layer.cache_gz_path) # type: ignore # pylint: disable=line-too-long

            elif layer.docker_path:
                layer.cache_path = \
                    await Services.docker_util.assemble_layer_tar(layer.diff_id) # type: ignore
            layer.save()

        return layer.cache_path

    # pylint: disable=arguments-differ
    async def head(self, layer_id: str):
        """Head response with actual Content-Lenght of layer"""
        self._set_headers(layer_id)
        tar_path = await self.prepare_tar_archive(layer_id)
        self.set_header("Content-Length", str(os.path.getsize(tar_path)))
        self.finish()

    # pylint: enable=arguments-differ

    # pylint: disable=arguments-differ
    async def get(self, layer_id):
        """
        Get layer info by given layer_id
        """
        self._set_headers(layer_id)
        tar_path = await self.prepare_tar_archive(layer_id)

        with open(tar_path, 'rb') as file:
            while True:
                data = file.read(51200)
                if not data:
                    break
                self.write(data)

        self.finish()

    # pylint: enable=arguments-differ


@web.stream_request_body
class ImagesHandler(web.RequestHandler):
    """Endpoint to list docker images"""

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.chunks = None
        self.future_response = None

    def prepare(self):
        if self.request.method != 'POST':
            return

        Services.logger.debug("image: preparing for receiving upload")
        self.chunks = asyncio.Queue()

        @aiohttp.streamer
        async def sender(writer, chunks):
            """ async generator data sender for aiodocker """
            chunk = await chunks.get()
            while chunk:
                await writer.write(chunk)
                chunk = await chunks.get()

        # pylint: disable=no-value-for-parameter,no-member
        self.future_response = Services.aiodocker.images.import_image(data=sender(self.chunks))
        # pylint: enable=no-value-for-parameter,no-member

    # pylint: disable=arguments-differ
    async def data_received(self, chunk):
        self.chunks.put_nowait(chunk)

    async def post(self):
        """
            Loads tarball to docker
        """
        Services.logger.debug("image: upload done")
        try:
            await self.chunks.put(None)
            response = await self.future_response
            for state in response:
                if 'error' in state:
                    if 'archive/tar' in state['error']:
                        raise HTTPError(status_code=400, log_message=state['error'])
                    raise HTTPError(status_code=500, log_message=state['error'])
            self.write("OK")
            self.finish()
        except aiodocker.exceptions.DockerError as error:
            raise HTTPError(status_code=404, log_message=error.message)
    # pylint: enable=arguments-differ


class ImageList(RPCEndpoint):
    """List images"""

    def __init__(self, application: Application, request: HTTPServerRequest, **kwargs) -> None:
        super().__init__(application, request, **kwargs)

    def data_received(self, chunk):
        pass

    @rpc
    async def pull(self):
        """
            Pulling image in cluster

        """
        body = json.loads(self.request.body)

        image_identifier = body['image']
        if not image_identifier:
            raise HTTPError(status_code=400, log_message='Image name is not given')

        node_identifier = body['node']

        wait = bool('wait' in body and body['wait'])
        force = bool('force' in body and body['force'])
        show_progress = bool('progress' in body and body['progress'])
        whole_image_only = bool('whole_image_only' in body and body['whole_image_only'])

        if whole_image_only:
            await self.pull_routine(image_identifier, node_identifier,
                                    self, wait, show_progress, force)

        else:
            # distributed layer-by-layer download
            await self.pull_routine_distributed(image_identifier, self, wait, show_progress)


    @staticmethod
    async def pull_routine_distributed(tag_or_digest: str, rpc_endpoint: "RPCEndpoint" = None, # pylint: disable=too-many-locals,too-many-branches, too-many-statements
                                       wait: bool = False, show_progress: bool = False) -> None:
        """Coroutine to pull image (download distributed layers)
        """
        Services.logger.debug("Will fetch %s", tag_or_digest) # type: ignore

        if not wait and not show_progress and rpc_endpoint is not None:
            rpc_endpoint.write({'started':True})
            rpc_endpoint.finish()

        if show_progress:
            rpc_endpoint.write('{"image":"%s","progress":[' % tag_or_digest) # type: ignore
            rpc_endpoint.flush() # type: ignore

        jobid = uuid.uuid4().hex
        Services.docker_util.container.create_emitter(jobid) # type: ignore

        config_future = asyncio.ensure_future(
            Services.docker_util.docker_create_download_config( # type: ignore
                tag_or_digest, jobid)
        )
        await until_event(
            Services.docker_util.container.emitters[jobid], # type: ignore
            Services.docker_util.container.EVENT_START_LAYER_DOWNLOAD # type: ignore
        )

        def format_progress(digest: str, status: str, progress: int = 100):
            """generate json dictionary for sending progress of layer downloading"""
            return '{"digest": "%s", "status": "%s", "progress": %d},' % (digest, status, progress)

        async def send_progress(digest):
            """send progress of layer downloading"""
            progress = 0
            last_size = 0

            # if layer already exist
            status = Services.docker_util.container.queues[jobid][digest]['status']
            if status == Services.docker_util.container.DL_ALREADY:
                if show_progress:
                    rpc_endpoint.write( # type: ignore
                        format_progress(digest, status)
                    )
                    rpc_endpoint.flush() # type: ignore
                return

            while True:
                status = Services.docker_util.container.queues[jobid][digest]['status']

                # calc progress
                chunk = await Services.docker_util.container.queues[jobid][digest]['queue'] \
                                      .get()
                if chunk:
                    last_size += len(chunk)
                    progress = int(
                        last_size /
                        Services.docker_util.container.queues[jobid][digest]['size'] * 100
                    )
                    if show_progress:
                        rpc_endpoint.write( # type: ignore
                            format_progress(digest, status, progress)
                        )
                        rpc_endpoint.flush() # type: ignore
                else:
                    return

        pro_tasks = [
            send_progress(digest)
            for digest in Services.docker_util.container.queues[jobid].keys() # type: ignore
        ]
        pro_future = asyncio.gather(*pro_tasks)

        await pro_future
        config_json_str, image_id, _ = await config_future
        del Services.docker_util.container.queues[jobid] # type: ignore

        if show_progress:
            rpc_endpoint.write(format_progress('done', 'done')[:-1]) # type: ignore
            rpc_endpoint.flush() # type: ignore

        # Do we need to save repo_digest to database?
        # config_json_str, image_id, _ = \
        #     await Services.docker_util.docker_create_download_config(
        #         tag_or_digest) # type: ignore

        tarball_path = await Services.docker_util.container.create_image_from_tar( # type: ignore
            tag_or_digest, config_json_str, image_id)

        await Services.docker_util.load_image(tarball_path) # type: ignore

        # # save repo_digest ?
        # image = ContainerImage.get().where(...)
        # image.repo_digests.add(repo_digest)
        # image.save()

        if wait and not show_progress:
            rpc_endpoint.write({'finished':True}) # type: ignore
            rpc_endpoint.finish() # type: ignore

        if show_progress:
            rpc_endpoint.write(']}') # type: ignore
            rpc_endpoint.finish() # type: ignore

    @staticmethod
    async def pull_routine(image_identifier: str, node_identifier: str = None, # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
                           rpc_call: "RPCEndpoint" = None, wait: bool = False,
                           show_progress: bool = False, force: bool = False) -> str:
        """Coroutine to pull image in cluster
        """
        if not node_identifier:
            available_nodes = await ContainerImage.get_available_nodes(image_identifier)
            online_nodes = Services.daemon.nodes.all_nodes.keys() # type: ignore
            online_availables = [n for n in available_nodes if n in online_nodes]
            if online_availables:
                node_identifier = random.choice(online_availables)

        if not node_identifier:
            raise HTTPError(status_code=404, log_message='Image is not available in cluster')

        try:
            image = ContainerImage.get_image_data(image_identifier)
        except ContainerImage.DoesNotExist:
            raise HTTPError(status_code=404, log_message='Image Not Found')

        uuid_pattern = re.compile(r'^([a-f0-9]+)$', re.IGNORECASE)
        Services.logger.debug("Will fetch %s from >>%s<<", # type: ignore
                              image_identifier, node_identifier)
        if uuid_pattern.match(node_identifier):
            node = await Services.daemon.nodes.get_node_by_uuid(node_identifier) # type: ignore
        else:
            try:
                node = await Services.daemon.nodes.get_node_by_url(node_identifier) # type: ignore
            except Node.DoesNotExist as err:
                if not force:
                    raise err
                node = await Services.daemon.nodes.fetch_node_info(node_identifier) # type: ignore

        client = Client(node=node)
        chunks = asyncio.Queue() # type: asyncio.queues.Queue

        real_size = 0

        if show_progress:
            rpc_call.write('{"image":"%s","progress":[' % image_identifier) # type: ignore
            rpc_call.flush() # type: ignore

        if not wait and not show_progress and rpc_call is not None:
            rpc_call.write({'started':True})
            rpc_call.finish()

        @aiohttp.streamer
        async def sender(writer, chunks: asyncio.queues.Queue):
            """ async generator data sender for aiodocker """
            nonlocal real_size
            progress = 0
            last_progress = 0

            while True:
                chunk = await chunks.get()
                await writer.write(chunk)

                if chunk:
                    real_size += len(chunk)
                    progress = int(real_size / float(image.size) * 100)

                    # if over real size
                    if progress > 100:
                        progress = 100

                    if show_progress and progress - last_progress > 5:
                        rpc_call.write( # type: ignore
                            '{"progress": %d, "done": false},' % progress
                        )
                        rpc_call.flush() # type: ignore
                        last_progress = progress
                else:
                    if show_progress:
                        rpc_call.write('{"progress": %d, "done": true}' % progress) # type: ignore
                        rpc_call.write(']}') # type: ignore
                        rpc_call.finish() # type: ignore

                        # FIXME!
                        if real_size != image.size:
                            Services.logger.debug( # type: ignore
                                "WARNING: size of image != sum of chunks length. [%d, %d]",
                                real_size, image.size)
                    break

        try:
            # pylint: disable=no-value-for-parameter,no-member
            docker_future = Services.aiodocker.images.import_image( # type: ignore
                data=sender(chunks)
            )
            # pylint: enable=no-value-for-parameter,no-member
            docker_result = asyncio.ensure_future(docker_future)

            image_response = await client.stream_image(image_identifier)
            async for data in image_response.content.iter_chunked(64*1024):
                # Services.logger.debug("Pull: Chunk received with length: %s", len(data))
                chunks.put_nowait(data)

            chunks.put_nowait(None)

            await docker_result
        except Client.Error as error:
            Services.logger.error(error) # type: ignore
            if wait:
                raise HTTPError(status_code=500, log_message=str(error))
        if wait and not show_progress:
            rpc_call.write({'finished':True}) # type: ignore
            rpc_call.finish() # type: ignore

        return image.hash_id

    def get(self):  # pylint: disable=arguments-differ
        """
        Return list of docker images.

        Returns:
            (dict): list of images, it is a dict, since
            tornado does not write list for security reasons; see:
            ``http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write``


        """
        self.set_header("Content-Type", "application/json")

        all_images = self.get_argument('all', False) == 'true'

        # todo: validate `node` argument if it is valid UUID
        node = self.get_argument('node', Services.local_node.uuid.hex)
        node_pattern = re.compile("^([A-Fa-f0-9-]+)$")
        if node and not node_pattern.match(node):
            raise HTTPError(status_code=400,
                            log_message="invalid node uuid")

        query = ContainerImage.select()

        if not all_images:
            query = query.where(SQL('available_at LIKE \'%%"%s"%%\'' % node))

        # Sorry for hand-typed json, this is for streaming.
        self.write('{"images": [')
        is_first = True
        for image in query:
            if is_first:
                is_first = False
            else:
                self.write(',')
            self.write(json.dumps(image.to_dict(dialect="api")))
            self.flush()

        self.write(']}')
        self.finish()


class LayerList(web.RequestHandler):
    """List images"""

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    def get(self):
        """
        Return list of docker layers.

        Returns:
            (dict): list of layers, it is a dict, since
            tornado does not write list for security reasons; see:
            ``http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write``


        """
        self.set_header("Content-Type", "application/json")

        all_images = self.get_argument('all', False) == 'true'

        # todo: validate `node` argument if it is valid UUID
        node = self.get_argument('node', Services.local_node.uuid.hex)
        node_pattern = re.compile("^([A-Fa-f0-9-]+)$")
        if node and not node_pattern.match(node):
            raise HTTPError(status_code=400,
                            log_message="invalid node uuid")

        query = ContainerLayer.select()

        if not all_images:
            query = query.where(SQL('available_at LIKE \'%%"%s"%%\'' % node))

        # Sorry for hand-typed json, this is for streaming.
        self.write('{"layers": [')
        is_first = True
        for layer in query:
            if is_first:
                is_first = False
            else:
                self.write(',')
            self.write(json.dumps(layer.to_dict(dialect="api")))
            self.flush()

        self.write(']}')
        self.finish()
    # pylint: enable=arguments-differ


ROUTES = [
    (r'/docker/images', ImageList),
    (r'/docker/layers', LayerList),
    (r'/docker/images/(.*(?<![/config|/info])$)', ImagesTarHandler),
    (r'/docker/images/(.*/info)', ImageInfoHandler),
    (r'/docker/images/(.*/config)', ImageConfigHandler),
    (r'/docker/layers/([0-9a-fsh:]+)', LayerDownload),
]
