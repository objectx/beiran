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
    def __init__(self, url):
        """
        Initialization method for client
        Args:
            url: beirand url
        """
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
            # AsyncHTTPClient.configure(None, resolver=resolver)
            # self.http_client = httpclient.HTTPClient()
            self.http_client = httpclient.HTTPClient(force_instance=True,
                                                     async_client_class=AsyncHTTPClient,
                                                     resolver=resolver)
            self.url = proto + "://unixsocket"
        else:
            self.http_client = httpclient.HTTPClient(force_instance=True)
            self.url = url

    def request(self, path="/", **kwargs):
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
            # TODO: Parse JSON
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

    def get_server_info(self):
        """
        Gets root path from daemon for server information
        Returns:
            object: parsed from JSON

        """
        return self.request(path="/", parse_json=True)

    def get_server_version(self):
        """
        Daemon version retrieve
        Returns:
            str: semantic version
        """
        return self.get_server_info()['version']

    def get_node_info(self, uuid=None):
        """
        Retrieve information about node
        Returns:
            object: info of node
        """
        path = "/info" if not uuid else "/info/{}".format(uuid)
        return self.request(path=path, parse_json=True)

    def probe_node(self, address):
        """
        Connect to a new node
        Returns:
            object: info of node if successful
        """
        path = "/nodes"
        new_node = {
            "address": address
        }
        return self.request(path=path, data=new_node, parse_json=True, method="POST")

    def get_nodes(self, all_nodes=False):
        """
        Daemon get nodes
        Returns:
            list: list of nodes
        """
        path = '/nodes{}'.format('?all=true' if all_nodes else '')

        resp = self.request(path=path)

        return resp.get('nodes', [])

    def get_images(self, all_nodes=False, node_uuid=None):
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

        resp = self.request(path=path)
        return resp.get('images', [])

    def pull_image(self, imagename, node=None, wait=False):
        """
        Pull image accross cluster with spesific node support
        Returns:
            result: Pulling process result
        """
        path = '/images?cmd=pull'

        resp = self.request(path,
                            data={'image':imagename, 'node':node, 'wait':wait},
                            method='POST',
                            timeout=600)
        return resp

    def get_layers(self, all_nodes=False, node_uuid=None):
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

        resp = self.request(path=path)

        return resp.get('layers', [])

