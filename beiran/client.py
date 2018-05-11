"""
Common client for beiran project
"""

import socket
import json
import sys
import re
# from tornado.platform.asyncio import AsyncIOMainLoop
from tornado import httpclient, gen
from tornado.httpclient import AsyncHTTPClient
from tornado.netutil import Resolver
from tornado.platform.asyncio import to_asyncio_future

class UnixResolver(Resolver):

    """
    Resolver for unix socket implementation
    """
    def initialize(self, socket_path=None): #pylint: disable=arguments-differ
        """
        Class initialization method
        Args:
            socket_path: Path for unix socket
        """
        self.socket_path = socket_path #pylint: disable=attribute-defined-outside-init
        Resolver.initialize(self)

    def close(self):
        """Closing resolver"""
        self.close()

    @gen.coroutine
    def resolve(self, host, port, family=socket.AF_UNSPEC, callback=None):
        """
        Unix Socket resolve
        Args:
            host: host ip
            port: host port
            family: socket family default socket.AF_UNSPEC
            callback: function to call after resolve
        """
        if host == 'unixsocket':
            raise gen.Return([(socket.AF_UNIX, self.socket_path)])
        result = yield self.resolve(host, port, family, callback)
        raise gen.Return(result)


class Client:
    """ Beiran Client class
    """
    def __init__(self, url, node=None, version=None):
        """
        Initialization method for client
        Args:
            url: beirand url
            node: Node (optional)
            version: string (optional)
        """
        self.node = node
        self.version = node.beiran_version if node else version

        url_pattern = re.compile(r'^(https?)(?:\+(unix))?://(.+)$', re.IGNORECASE)
        matched = url_pattern.match(url)
        if not matched:
            raise ValueError("URL is broken: %s" % url)

        proto = matched.groups()[0]
        is_unix_socket = matched.groups()[1]
        location = matched.groups()[2]

        if is_unix_socket:
            self.socket_path = location

            resolver = UnixResolver(self.socket_path)
            self.http_client = AsyncHTTPClient(force_instance=True,
                                               resolver=resolver)
            self.url = proto + "://unixsocket"
        else:
            self.http_client = AsyncHTTPClient(force_instance=True)
            self.url = url

    async def request(self, path="/", parse_json=True, return_response=False, data=None, method="GET", **kwargs):
        """
        Request call to daemon
        Args:
            path: http path to request from daemon
            parse_json: if return value is JSON from daemon,
            it returns parsed JSON

        Returns: Response from daemon

        """
        headers = kwargs['headers'] if 'headers' in kwargs else {}
        data_options = {}
        if data:
            headers['Content-Type'] = 'application/json'
            kwargs['body'] = json.dumps(data)

        if return_response and 'raise_error' not in kwargs:
            kwargs['raise_error'] = False

        if 'timeout' in kwargs:
            # this is not good, we want a total timeout..
            # but will do for now..
            kwargs['connect_timeout'] = kwargs['timeout']
            kwargs['request_timeout'] = kwargs['timeout']
            del kwargs['timeout']

        response = await to_asyncio_future(self.http_client.fetch(self.url + path, method=method, **kwargs))

        if return_response:
            return response

        if parse_json:
            return json.loads(response.body)

        return response.body

    async def get_server_info(self):
        """
        Gets root path from daemon for server information
        Returns:
            object: parsed from JSON

        """
        return await self.request(path="/", parse_json=True)

    async def get_server_version(self):
        """
        Daemon version retrieve
        Returns:
            str: semantic version
        """
        return await self.get_server_info()['version']

    async def get_node_info(self, uuid=None):
        """
        Retrieve information about node
        Returns:
            object: info of node
        """
        path = "/info" if not uuid else "/info/{}".format(uuid)
        return await self.request(path=path, parse_json=True)

    async def ping(self, timeout=10):
        """
        Pings the node
        """
        response = await self.request("/ping", return_response=True, timeout=timeout)
        if not response or response.code != 200:
            raise Exception("Failed to receive ping response from node")

        # TODO: Return ping time
        return True

    async def probe_node(self, address):
        """
        Connect to a new node
        Returns:
            object: info of node if successful
        """
        path = "/nodes"
        new_node = {
            "address": address
        }
        return await self.request(path=path, data=new_node, parse_json=True, method="POST")

    async def get_nodes(self, all_nodes=False):
        """
        Daemon get nodes
        Returns:
            list: list of nodes
        """
        path = '/nodes{}'.format('?all=true' if all_nodes else '')

        resp = await self.request(path=path)

        return resp.get('nodes', [])

    async def get_images(self, all_nodes=False, node_uuid=None):
        """
        Get Image list from beiran API
        Returns:
            list: list of images

        """
        if node_uuid and all_nodes:
            raise Exception("node_uuid and all_nodes cannot be defined at the same time")

        if self.version == '0.0.5':
            path = '/images'
        else:
            path = '/docker/images'

        if node_uuid:
            path = path + '?node={}'.format(node_uuid)
        elif all_nodes:
            path = path + '?all=true'

        resp = await self.request(path=path)
        return resp.get('images', [])

    async def get_layers(self, all_nodes=False, node_uuid=None):
        """
        Get Layer list from beiran API
        Returns:
            list: list of layers
        """
        if node_uuid and all_nodes:
            raise Exception("node_uuid and all_nodes cannot be defined at the same time")

        if self.version == '0.0.5':
            path = '/layers'
        else:
            path = '/docker/layers'

        if node_uuid:
            path = path + '?node={}'.format(node_uuid)
        elif all_nodes:
            path = path + '?all=true'

        resp = await self.request(path=path)

        return resp.get('layers', [])
