"""
    Beiran daemon execution script to create server and schedule
    tasks by observing nodes and communication each other.
"""
import os
import sys
import asyncio
import logging
import docker
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options, define
from tornado.netutil import bind_unix_socket
from tornado import websocket, web, httpserver
from tornado.web import HTTPError

from beirand.discovery.zeroconf import ZeroconfDiscovery
from beirand.lib import docker_find_layer_dir_by_sha, create_tar_archive, docker_sha_summary

from beiran.version import get_version

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'DEBUG'))
FILE_HANDLER = logging.FileHandler(filename='tmp.log')
STDOUT_HANDLER = logging.StreamHandler(sys.stdout)
HANDLERS = [FILE_HANDLER, STDOUT_HANDLER]
logging.getLogger('asyncio').level = logging.WARNING
logging.basicConfig(
    level=LOG_LEVEL,
    format='[%(asctime)s] [%(name)s] %(levelname)s - %(message)s',
    handlers=HANDLERS
)

LOGGER = logging.getLogger('daemon')

VERSION = get_version('short', 'daemon')

AsyncIOMainLoop().install()

# Initialize docker client
CLIENT = docker.from_env()

# docker low level api client to get image data
DOCKER_LC = docker.APIClient()

# we may have a settings file later, create this dir while init wherever it would be
DOCKER_TAR_CACHE_DIR = "tar_cache"

define('listen_address',
       group='webserver',
       default='0.0.0.0',
       help='Listen address')
define('listen_port',
       group='webserver',
       default=8888,
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
        LOGGER.info("WebSocket opened")

    def on_message(self, message):
        """ Received message from websocket
        """
        self.write_message(u"You said: " + message)

    def on_close(self):
        """ Monitor if websocket is closed
        """
        LOGGER.info("WebSocket closed")


class ApiRootHandler(web.RequestHandler):
    """ API Root endpoint `/` handling"""

    def data_received(self, chunk):
        pass

    def get(self, *args, **kwargs):
        self.write('{"version":"' + VERSION + '"}')
        self.finish()


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
        self.set_header("X-Content-Type-Options", "nosniff")  # only nosniff, what else could it be?
        self.set_header("accept-ranges", "bytes")
        self.set_header("cache-control", "max-age=31536000")  # how is 31536000 calculated?

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


APP = web.Application([
    (r'/', ApiRootHandler),
    (r'/layers/([0-9a-fsh:]+)', LayerDownload),
    # (r'/layers', LayersHandler),
    # (r'/images', ImagesHandler),
    (r'/ws', EchoWebSocket),
])


async def new_node(node):
    """
    Discovered new node on beiran network
    Args:
        node: Node object
    """
    LOGGER.info('new node has reached %s', str(node))

async def removed_node(node):
    """
    Node on beiran network is down
    Args:
        node: Node object
    """
    LOGGER.info('node has been removed %s', str(node))


def main():
    """ Main function wrapper """
    LOGGER.info("Starting Daemon HTTP Server...")
    # Listen on Unix Socket
    server = httpserver.HTTPServer(APP)
    LOGGER.info("Listening on unix socket: %s", options.unix_socket)
    socket = bind_unix_socket(options.unix_socket)
    server.add_socket(socket)

    # Also Listen on TCP
    APP.listen(options.listen_port, address=options.listen_address)
    LOGGER.info("Listening on tcp socket: " +
                options.listen_address + ":" +
                str(options.listen_port))

    loop = asyncio.get_event_loop()
    discovery = ZeroconfDiscovery(loop)
    discovery.set_log_level(LOG_LEVEL)
    discovery.on('discovered', new_node)
    discovery.on('undiscovered', removed_node)
    discovery.start()
    loop.set_debug(True)
    loop.run_forever()

if __name__ == '__main__':
    main()
