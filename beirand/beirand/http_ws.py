"""HTTP and WS API implementation of beiran daemon"""
import os
import re
import json
import asyncio
import urllib
import aiohttp

from tornado import websocket, web
from tornado.options import options, define
from tornado.web import HTTPError

from peewee import SQL

import aiodocker

from beirand.common import logger, VERSION, AIO_DOCKER_CLIENT, DOCKER_TAR_CACHE_DIR, NODES, EVENTS
from beirand.lib import docker_find_layer_dir_by_sha, create_tar_archive, docker_sha_summary
from beirand.lib import get_listen_address, get_listen_port

from beiran.models import DockerImage, DockerLayer

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


class JsonHandler(web.RequestHandler):
    """Request handler where requests and responses speak JSON."""

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.json_data = dict()
        self.response = dict()

    def data_received(self, chunk):
        pass

    def prepare(self):
        # Incorporate request JSON into arguments dictionary.
        if self.request.body:
            try:
                self.json_data = json.loads(self.request.body)
            except ValueError:
                message = 'Unable to parse JSON.'
                self.send_error(400, message=message) # Bad Request

        # Set up response dictionary.
        self.response = dict()

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    def write_error(self, status_code, **kwargs):
        if 'message' not in kwargs:
            if status_code == 405:
                kwargs['message'] = 'Invalid HTTP method.'
            else:
                kwargs['message'] = 'Unknown error.'

        self.response = kwargs
        self.write_json()

    def write_json(self):
        """Write json output"""
        output = json.dumps(self.response)
        self.write(output)

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
                chunk = await content.read(65536)
                if not chunk:
                    break
                self.write(chunk)
                await self.flush()
            self.finish()
        except aiodocker.exceptions.DockerError as error:
            raise HTTPError(status_code=404, log_message=error.message)
        except Exception as error:
            logger.error("Image Stream failed: %s", str(error))
            raise HTTPError(status_code=500, log_message=str(error))

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
        if not node:
            raise HTTPError(status_code=404, log_message="Node Not Found")
        self.write(node.to_dict())
        self.finish()

    # pylint: enable=arguments-differ


@web.stream_request_body
class ImagesHandler(web.RequestHandler):
    """Endpoint to list docker images"""

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
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
        logger.debug("image: streaming image directly from docker daemon")

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
        if self.request.method != 'POST':
            return

        logger.debug("image: preparing for receiving upload")
        self.chunks = asyncio.Queue()

        @aiohttp.streamer
        async def sender(writer, chunks):
            """ async generator data sender for aiodocker """
            chunk = await chunks.get()
            while chunk:
                await writer.write(chunk)
                chunk = await chunks.get()

        self.future_response = APP.docker.images.import_image(data=sender(self.chunks))  # pylint: disable=no-value-for-parameter

    # pylint: disable=arguments-differ
    async def data_received(self, chunk):
        self.chunks.put_nowait(chunk)

    async def post(self):
        """
            Loads tarball to docker
        """
        logger.debug("image: upload done")
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


class ImageList(web.RequestHandler):
    """List images"""

    def data_received(self, chunk):
        pass

    async def pull(self):
        """
            Pulling image in cluster
        """
        body = json.loads(self.request.body)
        if not body['node']:
            raise NotImplementedError('Clusterwise image pull is not implemented yet')

        if not body['image']:
            raise HTTPError(status_code=400, log_message='Image name is not given')

        wait = True if 'wait' in body and body['wait'] else False

        if not wait:
            self.write({'started':True})
            self.finish()

        # TODO: Replacing protocols should be reconsidered
        url = '{}/images/{}'.format(body['node'].replace('beiran', 'http'), body['image'])
        logger.debug("Requesting image from %s", url)

        chunks = asyncio.Queue()

        @aiohttp.streamer
        async def sender(writer, chunks):
            """ async generator data sender for aiodocker """
            chunk = await chunks.get()
            while chunk:
                await writer.write(chunk)
                chunk = await chunks.get()

        try:
            docker_future = APP.docker.images.import_image(data=sender(chunks)) # pylint: disable=no-value-for-parameter
            docker_result = asyncio.ensure_future(docker_future)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    async for data in resp.content.iter_chunked(64*1024):
                        # logger.debug("Pull: Chunk received with length: %s", len(data))
                        chunks.put_nowait(data)
            chunks.put_nowait(None)
            await docker_result
        except aiohttp.ClientError as error:
            logger.error(error)
            if wait:
                raise HTTPError(status_code=500, log_message=str(error))
        if wait:
            self.write({'finished':True})
            self.finish()


    # pylint: disable=arguments-differ
    @web.asynchronous
    async def post(self):
        cmd = self.get_argument('cmd')
        if cmd:
            logger.debug("Image endpoint is invoked with command `%s`", cmd)
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
        node = self.get_argument('node', NODES.local_node.uuid.hex)
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
        node = self.get_argument('node', NODES.local_node.uuid.hex)
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


class NodesHandler(JsonHandler):
    """List nodes by arguments specified in uri all, online, offline, etc."""

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    def post(self):
        if 'address' not in self.json_data:
            raise Exception("Unacceptable data")

        address = self.json_data['address']
        parsed = urllib.parse.urlparse(address)

        # loop = asyncio.get_event_loop()
        # task = loop.create_task(NODES.add_or_update_new_remote_node(parsed.hostname, parsed.port))
        EVENTS.emit('probe', ip_address=parsed.hostname, service_port=parsed.port) # TEMP

        self.write({"status": "OK"})
        self.finish()
    # pylint: enable=arguments-differ

    # pylint: disable=arguments-differ
    def get(self):
        """
        Return list of nodes, if specified `all`from database or discovered ones from memory.

        Returns:
            (dict) list of nodes, it is a dict, since tornado does not write list for security
                   reasons; see:
                   http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write

        """
        all_nodes = self.get_argument('all', False) == 'true'

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
        """Just return a PONG response"""
        self.write({"ping":"pong"})
        self.finish()
    # pylint: enable=arguments-differ


APP = web.Application([
    (r'/', ApiRootHandler),
    (r'/images', ImageList),
    (r'/layers', LayerList),
    (r'/images/(.*)', ImagesTarHandler),
    (r'/layers/([0-9a-fsh:]+)', LayerDownload),
    (r'/info(?:/([0-9a-fsh:]+))?', NodeInfo),
    (r'/nodes', NodesHandler),
    (r'/ping', Ping),
    # (r'/layers', LayersHandler),
    (r'/image/pull/([0-9a-zA-Z:\\\-]+)', ImagePullHandler),
    (r'/ws', EchoWebSocket),
])

APP.docker = AIO_DOCKER_CLIENT
