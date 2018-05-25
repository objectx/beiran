"""Docker API endpoints"""
import os
import random
import re
import json
import asyncio
import aiohttp
from tornado import web
from tornado.web import HTTPError
from peewee import SQL
import aiodocker
from beiran.util import create_tar_archive
from beiran.client import Client
from beiran.models import Node
from .models import DockerImage, DockerLayer


class Services:
    """These needs to be injected from the plugin init code"""
    local_node = None
    logger = None
    aiodocker = None
    docker_util = None
    tar_cache_dir = "tar_cache"
    loop = None
    daemon = None


class ImagesTarHandler(web.RequestHandler):
    """ Images export handler """

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    async def get(self, image_id_or_sha):
        """
            Get image as a tarball
        """
        try:
            # pylint: disable=no-member
            content = await Services.aiodocker.images.export_image(image_id_or_sha)
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
            Services.logger.error("Image Stream failed: %s", str(error))
            raise HTTPError(status_code=500, log_message=str(error))

    async def head(self, image_id_or_sha):
        """
            HEAD endpoint
        """
        try:
            if image_id_or_sha.startswith("sha256:"):
                image = DockerImage.get(DockerImage.hash_id == image_id_or_sha)
            else:
                if not ":" in image_id_or_sha:
                    image_id_or_sha += ":latest"
                query = DockerImage.select()
                query = query.where(SQL('tags LIKE \'%%"%s"%%\'' % image_id_or_sha))
                image = query.first()
                if not image:
                    raise HTTPError(status_code=404, log_message="Image Not Found")

            self.set_header("Docker-Image-HashID", image.hash_id)
            self.set_header("Docker-Image-CreatedAt", image.created_at)
            self.set_header("Docker-Image-Size", image.size)

            self.finish()

        except DockerImage.DoesNotExist as error:
            raise HTTPError(status_code=404, log_message=str(error))


class LayerDownload(web.RequestHandler):
    """ Container image layer downloading handler """

    def data_received(self, chunk):
        pass

    def _set_headers(self, layer_id):
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
    def prepare_tar_archive(layer_id):
        """
        Finds docker layer path and prepare a tar archive for `layer_id`.

        Args:
            layer_id (str): uuid str of layer

        Returns:
            (str) tar path

        Raises:
            404 if layer not found

        """
        layer_path = Services.docker_util.docker_find_layer_dir_by_sha(layer_id)
        if not layer_path:
            raise HTTPError(status_code=404, log_message="Layer Not Found")

        tar_path = "{cache_dir}/{cache_tar_name}" \
            .format(cache_dir=Services.tar_cache_dir,
                    cache_tar_name=Services.docker_util.docker_sha_summary(layer_id))

        if not os.path.isdir(Services.tar_cache_dir):
            os.makedirs(Services.tar_cache_dir)

        if not os.path.isfile(tar_path):
            create_tar_archive(layer_path, tar_path)

        return tar_path

    # pylint: disable=arguments-differ
    def head(self, layer_id):
        """Head response with actual Content-Lenght of layer"""
        self._set_headers(layer_id)
        tar_path = self.prepare_tar_archive(layer_id)
        self.set_header("Content-Length", os.path.getsize(tar_path))
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


class ImagePullHandler(web.RequestHandler):
    """Docker image pull"""
    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ

    @web.asynchronous
    async def get(self, image):
        """

        Pull images

        Args:
            image (str): image name

        Returns:
            streams image pulling progress

        """
        self.set_header("Content-Type", "application/json")

        tag = self.get_argument('tag', 'latest')

        Services.logger.info("pulling image %s:%s", image, tag)

        result = await Services.aiodocker.images.pull(from_image=image, tag=tag, stream=True)
        self.write('{"statuses": [')

        comma = ""
        async for data in result:
            data = json.dumps(data)
            self.write("{comma}{status_data}".format(comma=comma, status_data=data))
            comma = ", "
            self.flush()

        self.write(']}')
        self.finish()

    # pylint: enable=arguments-differ


class ImageList(web.RequestHandler):
    """List images"""

    def data_received(self, chunk):
        pass

    # pylint: disable=too-many-locals
    async def pull(self):
        """
            Pulling image in cluster
        """
        body = json.loads(self.request.body)

        image_identifier = body['image']
        if not image_identifier:
            raise HTTPError(status_code=400, log_message='Image name is not given')

        node_identifier = body['node']
        if not node_identifier:
            available_nodes = await DockerImage.get_available_nodes_by_tag(image_identifier)

        if not node_identifier:
            raise HTTPError(status_code=404, log_message='Image is not available in cluster')

        wait = True if 'wait' in body and body['wait'] else False
        force = True if 'force' in body and body['force'] else False

        if not wait:
            self.write({'started':True})
            self.finish()

        uuid_pattern = re.compile(r'^([a-f0-9]+)$', re.IGNORECASE)
        Services.logger.debug("Will fetch %s from >>%s<<",
                              image_identifier, node_identifier)
        if uuid_pattern.match(node_identifier):
            node = await Services.daemon.nodes.get_node_by_uuid(node_identifier)
        else:
            try:
                node = await Services.daemon.nodes.get_node_by_url(node_identifier)
            except Node.DoesNotExist as err:
                if not force:
                    raise err
                node = await Services.daemon.nodes.fetch_node_info(node_identifier)

        client = Client(node=node)

        chunks = asyncio.Queue()
        @aiohttp.streamer
        async def sender(writer, chunks):
            """ async generator data sender for aiodocker """
            chunk = await chunks.get()
            while chunk:
                await writer.write(chunk)
                chunk = await chunks.get()

        try:
            # pylint: disable=no-value-for-parameter,no-member
            docker_future = Services.aiodocker.images.import_image(data=sender(chunks))
            # pylint: enable=no-value-for-parameter,no-member
            docker_result = asyncio.ensure_future(docker_future)

            image_response = await client.stream_image(image_identifier)
            async for data in image_response.content.iter_chunked(64*1024):
                # Services.logger.debug("Pull: Chunk received with length: %s", len(data))
                chunks.put_nowait(data)

            chunks.put_nowait(None)
            await docker_result
        except Client.Error as error:
            Services.logger.error(error)
            if wait:
                raise HTTPError(status_code=500, log_message=str(error))
        if wait:
            self.write({'finished':True})
            self.finish()
    # pylint: enable=too-many-locals

    # pylint: disable=arguments-differ
    @web.asynchronous
    async def post(self):
        cmd = self.get_argument('cmd')
        if cmd:
            Services.logger.debug("Image endpoint is invoked with command `%s`", cmd)
            method = None
            try:
                method = getattr(self, cmd)
            except AttributeError:
                raise NotImplementedError("Endpoint `/images` does not implement `{}`"
                                          .format(cmd))

            return await method()
        raise NotImplementedError()

    def get(self):
        """
        Return list of nodes, if specified `all`from database or discovered ones from memory.

        Returns:
            (dict) list of nodes, it is a dict, since tornado does not write list for security
                   reasons; see:
                   http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write

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
    # pylint: enable=arguments-differ


class LayerList(web.RequestHandler):
    """List images"""

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    def get(self):
        """
        Return list of nodes, if specified `all`from database or discovered ones from memory.

        Returns:
            (dict) list of nodes, it is a dict, since tornado does not write list for security
                   reasons; see:
                   http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write

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
    (r'/docker/images/(.*)', ImagesTarHandler),
    (r'/docker/layers/([0-9a-fsh:]+)', LayerDownload),
    (r'/docker/image/pull/([0-9a-zA-Z:\\\-]+)', ImagePullHandler),
]
