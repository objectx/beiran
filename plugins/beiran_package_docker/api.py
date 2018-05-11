"""Docker API endpoints"""
import os
import re
import json
import asyncio
import aiohttp
import aiodocker
from tornado import web
from tornado.web import HTTPError
from peewee import SQL
from beiran.util import create_tar_archive
from .models import DockerImage, DockerLayer
from .util import DockerUtil

class Services:
    """These needs to be injected from the plugin init code"""
    local_node = None
    logger = None
    aiodocker = None
    docker_util = None
    tar_cache_dir = "tar_cache"
    loop = None

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
            content = await Services.aiodocker.images.export_image(image_id_or_sha)
            self.set_header("Content-Type", "application/x-tar")

            while True:
                chunk = await content.read(2048*1024)
                if not chunk:
                    break
                self.write(chunk)
                await self.flush()
            self.finish()
        except aiodocker.exceptions.DockerError as error:
            raise HTTPError(status_code=404, log_message=error.message)

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

    # pylint: disable=arguments-differ
    def head(self, layer_id):
        self._set_headers(layer_id)
        return self.get(layer_id)

    # pylint: enable=arguments-differ

    # pylint: disable=arguments-differ
    def get(self, layer_id):
        """
        Get layer info by given layer_id
        """
        self._set_headers(layer_id)
        layer_path = Services.docker_util.docker_find_layer_dir_by_sha(layer_id)

        if not layer_path:
            raise HTTPError(status_code=404, log_message="Layer Not Found")

        tar_path = "{cache_dir}/{cache_tar_name}" \
            .format(cache_dir=Services.tar_cache_dir,
                    cache_tar_name=Services.docker_util.docker_sha_summary(layer_id))
        if not os.path.isfile(tar_path):
            create_tar_archive(layer_path, tar_path)

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

        # pylint: disable=no-value-for-parameter
        self.future_response = Services.aiodocker.images.import_image(data=sender(self.chunks))
        # pylint: enable=no-value-for-parameter

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
    # 0.0.5 compat (TODO: delete at 0.0.6 release)
    (r'/images', ImageList),
    (r'/layers', LayerList),
    (r'/images/(.*)', ImagesTarHandler),
    (r'/layers/([0-9a-fsh:]+)', LayerDownload),
    (r'/image/pull/([0-9a-zA-Z:\\\-]+)', ImagePullHandler),
    # 0.0.6+
    (r'/docker/images', ImageList),
    (r'/docker/layers', LayerList),
    (r'/docker/images/(.*)', ImagesTarHandler),
    (r'/docker/layers/([0-9a-fsh:]+)', LayerDownload),
    (r'/docker/image/pull/([0-9a-zA-Z:\\\-]+)', ImagePullHandler),
]
