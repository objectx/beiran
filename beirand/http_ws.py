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

from beirand.common import logger, VERSION, NODES
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

ROUTES = [
    (r'/', ApiRootHandler),
    (r'/info(?:/([0-9a-fsh:]+))?', NodeInfo),
    (r'/nodes', NodesHandler),
    (r'/ping', Ping),
    # (r'/layers', LayersHandler),
    (r'/ws', EchoWebSocket),
]
