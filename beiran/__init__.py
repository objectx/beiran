import socket
import json
# from tornado.platform.asyncio import AsyncIOMainLoop
from tornado import httpclient, gen
from tornado.httpclient import AsyncHTTPClient
from tornado.netutil import Resolver

VERSION = "0.0.1"

class UnixResolver(Resolver):
    def initialize(self, socket_path):
        self.resolver = Resolver()
        self.socket_path = socket_path

    def close(self):
        self.resolver.close()

    @gen.coroutine
    def resolve(self, host, port, *args, **kwargs):
        if host == 'unixsocket':
            raise gen.Return([(socket.AF_UNIX, self.socket_path)])
        result = yield self.resolver.resolve(host, port, *args, **kwargs)
        raise gen.Return(result)

class Client:
    def __init__(self, socket_path):
        self.socket_path = socket_path

        resolver = UnixResolver(socket_path=self.socket_path)
        AsyncHTTPClient.configure(None, resolver=resolver)
        # self.http_client = httpclient.HTTPClient()
        self.http_client = httpclient.HTTPClient(async_client_class = AsyncHTTPClient)

    def request(self, method = "GET", path = "/", parse_json = True, async = False):
        try:
            response = self.http_client.fetch("http://unixsocket" + path)
            # TODO: Parse JSON
        except httpclient.HTTPError as e:
            print("Error: " + str(e))
            raise e
        except Exception as e:
            # Other errors are possible, such as IOError.
            print("Error: " + str(e))
            raise e

        if parse_json:
            return json.loads(response.body)

        return response.body

    def GetServerInfo(self):
        return self.request(path = "/", parse_json = True)

    def GetServerVersion(self):
        return self.GetServerInfo()['version']
