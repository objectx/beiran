"""HTTP and WS API implementation of beiran daemon"""
import os
import json
import asyncio
import aiodocker
import aiohttp

from tornado import websocket, web
from tornado.options import options, define
from tornado.web import HTTPError

from beirand.common import logger, VERSION, AIO_DOCKER_CLIENT, DOCKER_TAR_CACHE_DIR, NODES
from beirand.lib import docker_find_layer_dir_by_sha, create_tar_archive, docker_sha_summary
from beirand.lib import get_listen_address, get_listen_port


define('listen_address',
       group='webserver',
       default=get_listen_address(),
       help='Listen address')
define('listen_port',
       group='webserver',
       default=get_listen_port(),
       help='Listen port')
define('unix_socket',
       group='webserver',
       default="/var/run/beirand.sock",
       help='Path to unix socket to bind')

if 'BEIRAN_SOCK' in os.environ:
    options.unix_socket = os.environ['BEIRAN_SOCK']


class EchoWebSocket(websocket.WebSocketHandler):
    """ Websocket implementation for test
    """

    def data_received(self, chunk):
        """
        Web socket data received in chunk
        Args:
            chunk: Current received data
        """
        pass

    def open(self, *args, **kwargs):
        """ Monitor if websocket is opened
        """
        logger.info("WebSocket opened")

    def on_message(self, message):
        """ Received message from websocket
        """
        self.write_message(u"You said: " + message)

    def on_close(self):
        """ Monitor if websocket is closed
        """
        logger.info("WebSocket closed")


class ApiRootHandler(web.RequestHandler):
    """ API Root endpoint `/` handling"""

    def data_received(self, chunk):
        pass

    def get(self, *args, **kwargs):
        self.set_header("Content-Type", "application/json")
        self.write('{"version":"' + VERSION + '"}')
        self.finish()

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
            content = await APP.docker.images.export_image(image_id_or_sha)
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
        layer_path = docker_find_layer_dir_by_sha(layer_id)

        if not layer_path:
            raise HTTPError(status_code=404, log_message="Layer Not Found")

        tar_path = "{cache_dir}/{cache_tar_name}" \
            .format(cache_dir=DOCKER_TAR_CACHE_DIR,
                    cache_tar_name=docker_sha_summary(layer_id))
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


class NodeInfo(web.RequestHandler):
    """Endpoint which reports node information"""

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.node_info = {}

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    @web.asynchronous
    async def get(self, uuid=None):
        """Retrieve info of the node by `uuid` or the local node"""

        if not uuid:
            node = NODES.local_node
        else:
            node = await NODES.get_node_by_uuid(uuid)

        # error = info = version = ""

        # try:
        #     info = await self.application.docker.system.info()
        #     version = await self.application.docker.version()
        #     status = True
        # except DockerError as error:
        #     status = False
        #     logger.error('Docker Client error %s', error)

        # node_info.update(
        #     {
        #         "docker": {
        #             "status": status,
        #             "daemon_info": info,
        #             "version": version,
        #             "error": error
        #         }
        #     }
        # )

        self.write(node.to_dict())
        self.finish()

    # pylint: enable=arguments-differ


@web.stream_request_body
class ImagesHandler(web.RequestHandler):
    """Endpoint to list docker images"""

    def __init__(self):
        super().__init__()
        self.chunks = None
        self.future_response = None

    # pylint: disable=arguments-differ
    async def get(self):
        """Retrieve image list of the node

        Available arguments are:
            - all          // all images
            - filter       // filter by name ?filter=beiran
            - dangling     // list dangling images ?dangling=true
            - label        // filter by label  ?label=

        """

        params = dict()
        params.update(
            {
                "all": self.get_argument('all', False),
                "filter": self.get_argument('filter', None),
                "dangling": self.get_argument('dangling', False),
                "label": self.get_argument('label', None),
            }
        )

        logger.debug("listing images with params: %s", params)

        image_list = await AIO_DOCKER_CLIENT.images.list(**params)

        self.write({
            "images": image_list
        })
    # pylint: enable=arguments-differ

    def prepare(self):
        self.chunks = asyncio.Queue()

        @aiohttp.streamer
        async def sender(writer, chunks):
            """ async generator data sender for aiodocker """
            chunk = await chunks.get()
            while chunk:
                await writer.write(chunk)
                chunk = await chunks.get()

        self.future_response = APP.docker.images.import_image(data=sender(self.chunks)) # pylint: disable=no-value-for-parameter

    # pylint: disable=arguments-differ
    async def data_received(self, chunk):
        self.chunks.put_nowait(chunk)

    async def post(self):
        """
            Loads tarball to docker
        """
        try:
            await self.chunks.put(None)
            await self.future_response
            self.write("OK")
            self.finish()
        except  aiodocker.exceptions.DockerError as error:
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

        logger.info("pulling image %s:%s", image, tag)

        result = await AIO_DOCKER_CLIENT.images.pull(from_image=image, tag=tag, stream=True)
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


class NodeList(web.RequestHandler):
    """List nodes by arguments specified in uri all, online, offline, etc."""

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
        all_nodes = self.get_argument('all', False)

        if all_nodes and all_nodes not in ['True', 'true', '1', 1]:
            raise HTTPError(status_code=400,
                            log_message="Bad argument please use `True` or `1` for argument `all`")

        node_list = NODES.list_of_nodes(
            from_db=all_nodes
        )

        self.write(
            {
                "nodes": [n.to_dict() for n in node_list]
            }
        )
        self.finish()

    # pylint: enable=arguments-differ


class Ping(web.RequestHandler):
    """Ping / Pong endpoint"""

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    def get(self):
        """Just write PONG string"""
        self.write("PONG")
        self.finish()
    # pylint: enable=arguments-differ


APP = web.Application([
    (r'/', ApiRootHandler),
    (r'/images/(.*)', ImagesTarHandler),
    (r'/layers/([0-9a-fsh:]+)', LayerDownload),
    (r'/info(/[0-9a-fsh:]+)?', NodeInfo),
    (r'/nodes', NodeList),
    (r'/ping', Ping),
    # (r'/layers', LayersHandler),
    (r'/images', ImagesHandler),
    (r'/image/pull/([0-9a-zA-Z:\\\-]+)', ImagePullHandler),
    (r'/ws', EchoWebSocket),
])

APP.docker = AIO_DOCKER_CLIENT
