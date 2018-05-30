"""HTTP and WS API implementation of beiran daemon"""
import os
import json
import urllib

from tornado import websocket, web
from tornado.options import options, define
from tornado.web import HTTPError

from beiran.models import Node

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

        payload = {}
        for key, value in kwargs.items():
            payload[key] = str(value)
        self.response = payload
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



class NodesHandler(JsonHandler):
    """List nodes by arguments specified in uri all, online, offline, etc."""

    def data_received(self, chunk):
        pass

    async def probe(self):
        """
        Probe the node on `address` specified in request body.

        Returns:
            http response

        """
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
    @web.asynchronous
    async def post(self):

        if 'address' not in self.json_data:
            raise Exception("Unacceptable data")

        cmd = self.get_argument('cmd')
        if cmd:
            Services.logger.debug("Node endpoint is invoked with command `%s`", cmd)
            try:
                method = getattr(self, cmd)
            except AttributeError:
                raise NotImplementedError("Endpoint `/node` does not implement `{}`"
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

    # pylint: disable=arguments-differ
    def get(self):
        status_response = {
            "status": "ok",
            "sync_state_version": Services.daemon.sync_state_version
        }

        self.write(status_response)
        self.finish()
    # pylint: enable=arguments-differ


ROUTES = [
    (r'/', ApiRootHandler),
    (r'/info(?:/([0-9a-fsh:]+))?', NodeInfo),
    (r'/status', StatusHandler),
    (r'/nodes', NodesHandler),
    (r'/ping', Ping),
    # (r'/layers', LayersHandler),
    (r'/ws', EchoWebSocket),
]
