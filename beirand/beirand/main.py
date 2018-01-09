import os
import asyncio
import docker
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options, define
from tornado.netutil import bind_unix_socket
from tornado import websocket, web, httpserver

VERSION = "0.0.1"

AsyncIOMainLoop().install()

# Initialize docker client
client = docker.from_env()

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


app = web.Application([
    (r'/', ApiRootHandler),
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
