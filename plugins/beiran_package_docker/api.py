"""Docker API endpoints"""
import os
import random
import re
import json
import asyncio
import aiohttp
from tornado import web
from tornado.web import HTTPError
from tornado.web import Application
from tornado.httputil import HTTPServerRequest
from peewee import SQL
import aiodocker
from beiran.util import create_tar_archive
from beiran.client import Client
from beiran.models import Node
from beiran.cmd_req_handler import RPCEndpoint, rpc
from .models import DockerImage, DockerLayer

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
            image = DockerImage.get_image_data(image_identifier)
        except DockerImage.DoesNotExist:
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
            image = DockerImage.get_image_data(image_identifier)
        except DockerImage.DoesNotExist:
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
            await Services.docker_util.create_or_download_config(image_identifier)

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
    def prepare_tar_archive(layer_id: str) -> str:
        """
        Finds docker layer path and prepare a tar archive for `layer_id`.

        Args:
            layer_id (str): uuid str of layer

        Returns:
            (str) tar path

        Raises:
            404 if layer not found

        """
        # layer_path = Services.docker_util.docker_find_layer_dir_by_sha(layer_id) # type: ignore

        try:
            layer = DockerLayer.select().where(DockerLayer.digest == layer_id).get()
        except DockerLayer.DoesNotExist:
            raise HTTPError(status_code=404, log_message="Layer Not Found")

        if not layer.cache_path:
            layer.cache_path = Services.docker_util.layer_storage_path(layer_id).split('.gz')[0] # type: ignore # pylint: disable=line-too-long
            if not os.path.isfile(layer.cache_path):
                create_tar_archive(layer.docker_path, layer.cache_path)
            layer.save()

        return layer.cache_path

    # pylint: disable=arguments-differ
    def head(self, layer_id: str):
        """Head response with actual Content-Lenght of layer"""
        self._set_headers(layer_id)
        tar_path = self.prepare_tar_archive(layer_id)
        self.set_header("Content-Length", str(os.path.getsize(tar_path)))
        self.finish()

    # pylint: enable=arguments-differ

    # pylint: disable=arguments-differ
    def get(self, layer_id):
        """
        Get layer info by given layer_id
        """
        self._set_headers(layer_id)
        tar_path = self.prepare_tar_archive(layer_id)

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

        wait = True if 'wait' in body and body['wait'] else False
        force = True if 'force' in body and body['force'] else False
        show_progress = True if 'progress' in body and body['progress'] else False

        await self.pull_routine(image_identifier, node_identifier, self, wait, show_progress, force)


    @staticmethod
    async def pull_routine(image_identifier: str, node_identifier: str = None, # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
                           rpc_endpoint: "RPCEndpoint" = None, wait: bool = False,
                           show_progress: bool = False, force: bool = False) -> str:
        """Coroutine to pull image in cluster
        """
        if not node_identifier:
            available_nodes = await DockerImage.get_available_nodes(image_identifier)
            online_nodes = Services.daemon.nodes.all_nodes.keys() # type: ignore
            online_availables = [n for n in available_nodes if n in online_nodes]
            if online_availables:
                node_identifier = random.choice(online_availables)

        if not node_identifier:
            raise HTTPError(status_code=404, log_message='Image is not available in cluster')

        try:
            image = DockerImage.get_image_data(image_identifier)
        except DockerImage.DoesNotExist:
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
            rpc_endpoint.write('{"image":"%s","progress":[' % image_identifier) # type: ignore
            rpc_endpoint.flush() # type: ignore

        if not wait and not show_progress and rpc_endpoint is not None:
            rpc_endpoint.write({'started':True})
            rpc_endpoint.finish()

        @aiohttp.streamer
        async def sender(writer, chunks: asyncio.queues.Queue):
            """ async generator data sender for aiodocker """
            nonlocal real_size
            progress = 0.0
            last_progress = 0.0

            while True:
                chunk = await chunks.get()
                await writer.write(chunk)

                if chunk:
                    real_size += len(chunk)
                    if show_progress and real_size/float(image.size) - last_progress > 0.05:
                        progress = real_size/float(image.size)
                        rpc_endpoint.write( # type: ignore
                            '{"progress": %.2f, "done": false},' % progress
                        )
                        rpc_endpoint.flush() # type: ignore
                        last_progress = progress
                else:
                    if show_progress:
                        rpc_endpoint.write('{"progress": %.2f, "done": true}' % # type: ignore
                                           (real_size / float(image.size)))
                        rpc_endpoint.write(']}') # type: ignore
                        rpc_endpoint.finish() # type: ignore

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
            rpc_endpoint.write({'finished':True}) # type: ignore
            rpc_endpoint.finish() # type: ignore

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

        query = DockerImage.select()

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

        query = DockerLayer.select()

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
