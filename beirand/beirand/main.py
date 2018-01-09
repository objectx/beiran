import os
import asyncio
import docker
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options, define
from tornado.netutil import bind_unix_socket
from tornado import websocket, web, httpserver
from tornado.web import HTTPError
from beirand.lib import docker_find_layer_dir_by_sha
from beirand.lib import create_tar_archive
from beirand.lib import docker_sha_summary

VERSION = "0.0.1"

AsyncIOMainLoop().install()

# Initialize docker client
client = docker.from_env()

# docker low level api client to get image data
docker_lc = docker.APIClient()

DOCKER_TAR_CACHE_DIR = "tar_cache"  # we may have a settings file later, create this dir while init wherever it would be

define('listen_address', group='webserver', default='0.0.0.0', help='Listen address')
define('listen_port', group='webserver', default=8888, help='Listen port')
define('unix_socket', group='webserver', default="/var/run/beirand.sock", help='Path to unix socket to bind')

if 'BEIRAN_SOCK' in os.environ:
    options.unix_socket = os.environ['BEIRAN_SOCK']

class EchoWebSocket(websocket.WebSocketHandler):
    def data_received(self, chunk):
        pass

    def open(self):
        print("WebSocket opened")

    def on_message(self, message):
        self.write_message(u"You said: " + message)

    def on_close(self):
        print("WebSocket closed")


class ApiRootHandler(web.RequestHandler):
    def data_received(self, chunk):
        pass

    def get(self):
        self.write('{"version":"' + VERSION + '"}')
        self.finish()



class LayerDownload(web.RequestHandler):

    def _set_headers(self, layer_id):
        # modify headers to pretend like docker registry if we decide to be proxy
        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Docker-Content-Digest", layer_id)
        self.set_header("Docker-Distribution-Api-Version", "registry/2.0")
        self.set_header("Etag", layer_id)
        self.set_header("X-Content-Type-Options", "nosniff")  # only nosniff, what else could it be?
        self.set_header("accept-ranges", "bytes")
        self.set_header("cache-control", "max-age=31536000")  # how is 31536000 calculated?

    def head(self, layer_id):
        self._set_headers(layer_id)

        return self.get(layer_id)

    def get(self, layer_id):
        """
        Get layer info by given layer_id
        """
        self._set_headers(layer_id)

        layer_path = docker_find_layer_dir_by_sha(layer_id)

        if not layer_path:
            raise HTTPError(status_code=404, log_message="Layer Not Found")

        tar_path = "{cache_dir}/{cache_tar_name}".format(cache_dir=DOCKER_TAR_CACHE_DIR,
                                                     cache_tar_name=docker_sha_summary(layer_id))
        if not os.path.isfile(tar_path):
            create_tar_archive(layer_path, tar_path)

        with open(tar_path, 'rb') as f:
            while True:
                data = f.read(51200)
                if not data:
                    break
                self.write(data)

        self.finish()


app = web.Application([
    (r'/', ApiRootHandler),
    (r'/layers/([0-9a-fsh:]+)', LayerDownload),
    # (r'/layers', LayersHandler),
    # (r'/images', ImagesHandler),
    (r'/ws', EchoWebSocket),
])

if __name__ == '__main__':
    # Listen on Unix Socket
    server = httpserver.HTTPServer(app)
    print("Listening on unix socket: " + options.unix_socket)
    socket = bind_unix_socket(options.unix_socket)
    server.add_socket(socket)

    # Also Listen on TCP
    app.listen(options.listen_port, address=options.listen_address)
    print("Listening on tcp socket: " + options.listen_address + ":" + str(options.listen_port))

    asyncio.get_event_loop().run_forever()
