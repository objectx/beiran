"""HTTP and WS API implementation of beiran daemon"""
import os
import urllib

from tornado import websocket, web
from tornado.options import options, define
from tornado.web import HTTPError

from beiran.models import Node
from beiran.cmd_req_handler import RPCEndpoint, rpc

from beirand.common import Services
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
        Services.logger.info("WebSocket opened")

    def on_message(self, message):
        """ Received message from websocket
        """
        self.write_message(u"You said: " + message)

    def on_close(self):
        """ Monitor if websocket is closed
        """
        Services.logger.info("WebSocket closed")


class ApiRootHandler(web.RequestHandler):
    """ API Root endpoint `/` handling"""

    def data_received(self, chunk):
        pass

    def get(self, *args, **kwargs):
        self.set_header("Content-Type", "application/json")
        self.write('{"version":"' + Services.daemon.version + '"}')
        self.finish()


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
            node = Services.daemon.nodes.local_node
        else:
            node = await Services.daemon.nodes.get_node_by_uuid(uuid)

        if not node:
            raise HTTPError(status_code=404, log_message="Node Not Found")
        self.write(node.to_dict())
        self.finish()

    # pylint: enable=arguments-differ


class NodesHandler(RPCEndpoint):
    """List nodes by arguments specified in uri all, online, offline, etc."""

    def data_received(self, chunk):
        pass

    @rpc
    async def probe(self):
        """
        Probe the node on `address` specified in request body.

        Returns:
            http response

        """
        if 'address' not in self.json_data:
            raise HTTPError(400, "Unacceptable data")

        node_url = self.json_data['address']
        parsed = urllib.parse.urlparse(node_url)
        try:
            if parsed.fragment:
                existing_node = await Services.daemon.nodes.get_node_by_uuid(parsed.fragment)
            else:
                existing_node = await Services.daemon.nodes.get_node_by_ip_and_port(
                    parsed.hostname, parsed.port)
        except Node.DoesNotExist:
            existing_node = None

        if existing_node and existing_node.status != 'offline':
            self.set_status(409)
            self.write({"status": "Node is already synchronized!"})
            self.finish()
            return

        # remote_ip = self.request.remote_ip

        if self.json_data.get('probe_back', None):
            await Services.daemon.nodes.probe_node_bidirectional(url=node_url)
        else:
            await Services.daemon.nodes.probe_node(url=node_url)

        self.write({"status": "OK"})
        self.finish()

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

        node_list = Services.daemon.nodes.list_of_nodes(
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


class StatusHandler(web.RequestHandler):
    """Status endpoint"""

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    def get(self):
        status_response = {
            "status": "ok",
            "sync_state_version": Services.daemon.sync_state_version,
            "plugins": {}
        }
        for name, plugin in Services.plugins.items():
            status_response['plugins'][name] = {
                "id": name,
                "name": plugin.plugin_name,
                "type": plugin.plugin_type,
                "status": plugin.status
            }
            if plugin.history:
                status_response['plugins'][name]["@v"] = plugin.history.version
                status_response['plugins'][name]["@state"] = plugin.history.latest

        self.write(status_response)
        self.finish()
    # pylint: enable=arguments-differ


class PluginStatusHandler(web.RequestHandler):
    """Status endpoint for plugins"""

    def data_received(self, chunk):
        pass

    # pylint: disable=arguments-differ
    def get(self, plugin_id):
        if not plugin_id in Services.plugins:
            raise HTTPError(status_code=404, log_message="Plugin Not Found")

        plugin = Services.plugins[plugin_id]
        status_response = {
            "id": plugin_id,
            "name": plugin.plugin_name,
            "type": plugin.plugin_type,
            "status": plugin.status
        }
        if hasattr(plugin, 'history'):
            status_response["@v"] = plugin.history.version
            status_response["@state"] = plugin.history.latest

        self.write(status_response)
        self.finish()
    # pylint: enable=arguments-differ

ROUTES = [
    (r'/', ApiRootHandler),
    (r'/info(?:/([0-9a-fsh:]+))?', NodeInfo),
    (r'/status', StatusHandler),
    (r'/status/plugins/([0-9a-z]+(?::[0-9a-z]+))', PluginStatusHandler),
    (r'/nodes', NodesHandler),
    (r'/ping', Ping),
    # (r'/layers', LayersHandler),
    (r'/ws', EchoWebSocket),
]
