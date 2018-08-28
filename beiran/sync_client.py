"""
Common client for beiran project
"""
# pylint: disable=duplicate-code


import socket
import json
from typing import Any

from tornado import httpclient, gen
from tornado.httpclient import AsyncHTTPClient
from tornado.netutil import Resolver
from beiran.models import PeerAddress

class UnixResolver(Resolver):

    """
    Resolver for unix socket implementation
    """
    def initialize(self, socket_path: str = None): #pylint: disable=arguments-differ
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
    def resolve(self, host: str, port: int, family: int = socket.AF_UNSPEC, callback=None):
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
    def __init__(self, peer_address: PeerAddress):
        """
        Initialization method for client

        Args:
            peer_address (PeerAddress, str): beirand address
        """

        if not isinstance(peer_address, PeerAddress):
            address = PeerAddress(address=peer_address)
        else:
            address = peer_address

        if address.unix_socket:
            resolver = UnixResolver(address.path)
            # AsyncHTTPClient.configure(None, resolver=resolver)
            # self.http_client = httpclient.HTTPClient()
            self.http_client = httpclient.HTTPClient(force_instance=True,
                                                     async_client_class=AsyncHTTPClient,
                                                     resolver=resolver)
            self.url = address.protocol + "://unixsocket"
        else:
            self.http_client = httpclient.HTTPClient(force_instance=True)
            self.url = address.location

    def request(self, path: str = "/", **kwargs) -> Any:
        """
        Request call to daemon
        Args:
            path: http path to request from daemon
            parse_json: if return value is JSON from daemon,
            it returns parsed JSON

        Returns: Response from daemon
        """

        headers = kwargs['headers'] if 'headers' in kwargs else {}
        data = kwargs.pop('data', None)
        if data:
            kwargs['body'] = json.dumps(data)
            headers['Content-Type'] = 'application/json'

        method = kwargs.pop('method', "GET")
        parse_json = kwargs.pop('parse_json', True)
        return_response = kwargs.pop('return_response', False)
        if return_response and 'raise_error' not in kwargs:
            kwargs['raise_error'] = False

        if 'timeout' in kwargs:
            # this is not good, we want a total timeout
            # but will do for now..
            kwargs['connect_timeout'] = kwargs['timeout']
            kwargs['request_timeout'] = kwargs['timeout']
            del kwargs['timeout']

        try:
            response = self.http_client.fetch(self.url + path, method=method, **kwargs)
        except httpclient.HTTPError as error:
            print("Error: " + str(error))
            raise error
        except Exception as error:
            print("Cannot connect to beiran daemon at %s" % self.url)
            print("Error: " + str(error))

            # Other errors are possible, such as IOError.
            raise error

        if return_response:
            return response

        if parse_json:
            return json.loads(response.body)

        return response.body

    def get_server_info(self, **kwargs) -> dict:
        """
        Gets root path from daemon for server information
        Returns:
            object: parsed from JSON

        """
        return self.request(path="/", parse_json=True, **kwargs)

    def get_server_version(self, **kwargs) -> str:
        """
        Daemon version retrieve
        Returns:
            str: semantic version
        """
        return self.get_server_info(**kwargs)['version']

    def get_node_info(self, uuid: str = None, **kwargs) -> dict:
        """
        Retrieve information about node
        Returns:
            object: info of node
        """
        path = "/info" if not uuid else "/info/{}".format(uuid)
        return self.request(path=path, parse_json=True, **kwargs)

    def get_status(self, plugin: str = None, **kwargs) -> dict:
        """
        Retrieve status information about node or one of it's plugins
        Returns:
            object: status of node or plugin
        """
        path = "/status" if not plugin else "/status/plugins/{}".format(plugin)
        return self.request(path=path, parse_json=True, **kwargs)

    def probe_node(self, address: str, **kwargs) -> dict:
        """
        Connect to a new node
        Returns:
            object: info of node if successful
        """
        path = "/nodes?cmd=probe"
        new_node = {
            "address": address,
            "probe_back": True
        }
        return self.request(path=path, data=new_node, parse_json=True, method="POST", **kwargs)

    def get_nodes(self, all_nodes: bool = False, **kwargs) -> list:
        """
        Daemon get nodes
        Returns:
            list: list of nodes
        """
        path = '/nodes{}'.format('?all=true' if all_nodes else '')

        resp = self.request(path=path, **kwargs)

        return resp.get('nodes', [])

    def get_images(self, all_nodes: bool = False, node_uuid: str = None, **kwargs) -> list:
        """
        Get Image list from beiran API
        Returns:
            list: list of images

        """
        if node_uuid and all_nodes:
            raise Exception("node_uuid and all_nodes cannot be defined at the same time")

        path = '/docker/images'

        if node_uuid:
            path = path + '?node={}'.format(node_uuid)
        elif all_nodes:
            path = path + '?all=true'

        resp = self.request(path=path, **kwargs)
        return resp.get('images', [])

    def pull_image(self, imagename: str, **kwargs) -> dict:
        """
        Pull image accross cluster with spesific node support
        Returns:
            result: Pulling process result
        """

        progress = kwargs.pop('progress', False)
        force = kwargs.pop('force', False)
        wait = kwargs.pop('wait', False)
        node = kwargs.pop('node', None)

        path = '/docker/images?cmd=pull'
        data = {
            'image': imagename,
            'node': node,
            'wait': wait,
            'force': force,
            'progress':progress
        }

        resp = self.request(path,
                            data=data,
                            method='POST',
                            timeout=600,
                            **kwargs)
        return resp
    #pylint: enable-msg=too-many-arguments

    def get_layers(self, all_nodes: bool = False, node_uuid: str = None, **kwargs) -> list:
        """
        Get Layer list from beiran API
        Returns:
            list: list of layers
        """
        if node_uuid and all_nodes:
            raise Exception("node_uuid and all_nodes cannot be defined at the same time")

        path = '/docker/layers'

        if node_uuid:
            path = path + '?node={}'.format(node_uuid)
        elif all_nodes:
            path = path + '?all=true'

        resp = self.request(path=path, **kwargs)

        return resp.get('layers', [])
