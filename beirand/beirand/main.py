from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.options import options, define
from tornado.netutil import bind_unix_socket
from tornado import websocket, web, httpserver
import asyncio
import docker

AsyncIOMainLoop().install()

# Initialize docker client
client = docker.from_env()

define('listen_address', group='webserver', default='0.0.0.0', help='Listen address')
define('listen_port', group='webserver', default=8888, help='Listen port')
define('unix_socket', group='webserver', default="/var/run/beirand.sock", help='Path to unix socket to bind')

class EchoWebSocket(websocket.WebSocketHandler):
	def open(self):
		print("WebSocket opened")

	def on_message(self, message):
		self.write_message(u"You said: " + message)

	def on_close(self):
		print("WebSocket closed")

class ApiRootHandler(web.RequestHandler):
	def get(self):
		self.write("Hello!")
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
	socket = bind_unix_socket(options.unix_socket)
	server.add_socket(socket)

	# Also Listen on TCP
	app.listen(options.listen_port, address=options.listen_address)

	asyncio.get_event_loop().run_forever()
