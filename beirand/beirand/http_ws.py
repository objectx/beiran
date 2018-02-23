import os

from beirand.common import logger, VERSION, DOCKER_CLIENT, DOCKER_TAR_CACHE_DIR, NODES
from beirand.lib import docker_find_layer_dir_by_sha, create_tar_archive, docker_sha_summary
from beirand.lib import get_listen_address, get_listen_port
from beirand.lib import local_node_uuid, get_plugin_list
from tornado import websocket, web
from tornado.options import options, define
from tornado.web import HTTPError

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

        if not uuid:
            uuid = local_node_uuid()
        else:
            uuid = uuid.lstrip('/')

        node_info = NODES.all_nodes.get(uuid)
        if not node_info:
            raise HTTPError(status_code=404, log_message="Node Not Found")

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
    (r'/info(/[0-9a-fsh:]+)?', NodeInfo),
    # (r'/layers', LayersHandler),
    # (r'/images', ImagesHandler),
    (r'/ws', EchoWebSocket),
])
