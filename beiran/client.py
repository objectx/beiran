"""
Command line tool client for beiran project
"""

import socket
import json
# from tornado.platform.asyncio import AsyncIOMainLoop
from tornado import httpclient, gen
from tornado.httpclient import AsyncHTTPClient
from tornado.netutil import Resolver


class UnixResolver(Resolver):
    """
    Resolver for unix socket implementation
    """
    def __init__(self, socket_path=None):
        """
        Class initialization method
        Args:
            socket_path: Path for unix socket
        """
        self.socket_path = socket_path

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
    def __init__(self, socket_path):
        """
        Initialization method for client
        Args:
            socket_path: unix socket path
        """
        self.socket_path = socket_path

        resolver = UnixResolver(socket_path=self.socket_path)
        AsyncHTTPClient.configure(None, resolver=resolver)
        # self.http_client = httpclient.HTTPClient()
        self.http_client = httpclient.HTTPClient(async_client_class=AsyncHTTPClient)

    def request(self, path="/", parse_json=True):
        """
        Request call to daemon
        Args:
            path: http path to request from daemon
            parse_json: if return value is JSON from daemon,
            it returns parsed JSON

        Returns: Response from daemon

        """
        try:
            response = self.http_client.fetch("http://unixsocket" + path)
            # TODO: Parse JSON
        except httpclient.HTTPError as error:
            print("Error: " + str(error))
            raise error
        except Exception as error:
            # Other errors are possible, such as IOError.
            print("Error: " + str(error))
            raise error

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
