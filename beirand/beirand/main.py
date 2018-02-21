"""
    Beiran daemon execution script to create server and schedule
    tasks by observing nodes and communication each other.
"""
import os
import sys
import asyncio
import logging
import importlib
import docker
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options, define
from tornado.netutil import bind_unix_socket
from tornado import websocket, web, httpserver
from tornado.web import HTTPError
from peewee import SqliteDatabase
from playhouse.shortcuts import model_to_dict

from beirand.lib import docker_find_layer_dir_by_sha, create_tar_archive, docker_sha_summary
from beirand.lib import local_node_uuid
from beirand.lib import get_plugin_list, get_listen_address, get_listen_port, collect_node_info
from beirand.nodes import Nodes

from beiran.models import Node
from beiran.version import get_version
from beiran.log import build_logger
from beiran.models.base import DB_PROXY

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'DEBUG'))
LOG_FILE = os.getenv('LOG_FILE', '/var/log/beirand.log')
logger = build_logger(LOG_FILE, LOG_LEVEL) # pylint: disable=invalid-name

VERSION = get_version('short', 'daemon')

AsyncIOMainLoop().install()

# Initialize docker client
DOCKER_CLIENT = docker.from_env()

# docker low level api client to get image data
DOCKER_LC = docker.APIClient()

# we may have a settings file later, create this dir while init wherever it would be
DOCKER_TAR_CACHE_DIR = "tar_cache"

NODES = {}

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

    def data_received(self, chunk):
        pass

    def get(self, uuid=None):
        """Retrieve info of the node by `uuid` or the local node"""
        global NODES

        if not uuid:
            uuid = local_node_uuid()
        node_info = NODES.all_nodes.get(uuid)
        node_info.update(get_plugin_list())
        node_info.update(
            {
                "docker": {
                    "daemon_info": DOCKER_CLIENT.info(),
                    "version": DOCKER_CLIENT.version()
                }
            }
        )
        self.write(node_info)


APP = web.Application([
    (r'/', ApiRootHandler),
    (r'/layers/([0-9a-fsh:]+)', LayerDownload),
    (r'/info/(?:[0-9a-fsh:]+)?', NodeInfo),
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
    logger.info('new node has reached %s', str(node))


async def removed_node(node):
    """
    Node on beiran network is down
    Args:
        node: Node object
    """
    logger.info('node has been removed %s', str(node))


def main():
    """ Main function wrapper """
    logger.info("Starting Daemon HTTP Server...")
    # Listen on Unix Socket
    server = httpserver.HTTPServer(APP)
    logger.info("Listening on unix socket: %s", options.unix_socket)
    socket = bind_unix_socket(options.unix_socket)
    server.add_socket(socket)

    # Also Listen on TCP
    APP.listen(options.listen_port, address=options.listen_address)
    logger.info("Listening on tcp socket: " +
                options.listen_address + ":" +
                str(options.listen_port))

    # check database file exists
    beiran_db_path = os.getenv("BEIRAN_DB_PATH", '/var/lib/beiran/beiran.db')
    db_file_exists = os.path.exists(beiran_db_path)

    if not db_file_exists:
        logger.info("sqlite file does not exist, creating file %s!..", beiran_db_path)
        open(beiran_db_path, 'a').close()

    # init database object
    database = SqliteDatabase(beiran_db_path)
    DB_PROXY.initialize(database)

    if not db_file_exists:
        logger.info("db hasn't initialized yet, creating tables!..")
        from beiran.models import create_tables

        create_tables(database)

    node_info = collect_node_info()
    node = Node(**node_info)
    logger.info("local node created: %s", model_to_dict(node))

    global NODES
    NODES = Nodes()
    NODES.add_new(node)
    logger.info("local node added, known nodes are: %s", NODES.all_nodes)

    loop = asyncio.get_event_loop()
    discovery_mode = os.getenv('DISCOVERY_METHOD') or 'zeroconf'

    try:
        module = importlib.import_module("beirand.discovery." + discovery_mode)
        discovery_class = getattr(module, discovery_mode.title() + "Discovery")
    except ModuleNotFoundError as error:
        logger.error(error)
        logger.error("Unsupported discovery mode: %s", discovery_mode)
        sys.exit(1)

    discovery = discovery_class(loop)
    discovery.on('discovered', new_node)
    discovery.on('undiscovered', removed_node)
    discovery.start()
    loop.set_debug(True)
    loop.run_forever()


if __name__ == '__main__':
    main()
