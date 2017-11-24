import logging
import socket

import signal
import sys
import time
from threading import Lock

from zeroconf import ServiceBrowser, ServiceInfo, ServiceStateChange, Zeroconf

from flask import Flask, request
from flask_socketio import SocketIO as SocketIOServer, emit
from flask_socketio import Namespace

from socketIO_client import SocketIO, LoggingNamespace

import logging
logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

info = None
hostname = socket.gethostname()
domain = "_beiran._tcp.local."

app = Flask(__name__)
# app.config['SECRET_KEY'] = 'secret!'

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

socketio_server = SocketIOServer(app, port=5000, async_mode=async_mode)


thread = None
thread_lock = Lock()

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio_server.sleep(10)
        count += 1
        socketio_server.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/test')


def signal_term_handler(signal, frame):
    print('got SIGTERM')
    if info:
        zeroconf.unregister_service(info)
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_term_handler)


def on_connect():
    print('connect')

def on_disconnect():
    print('disconnect')

def on_reconnect():
    print('reconnect')

def connecNodeWs(info):
    socketIO = SocketIO(socket.inet_ntoa(info.address), 5000)
    socketIO.on('connect', on_connect)
    socketIO.on('disconnect', on_disconnect)
    socketIO.on('reconnect', on_reconnect)


def on_service_state_change(zeroconf, service_type, name, state_change):
    print("Service %s of type %s state changed: %s" % (name, service_type, state_change))

    if state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        # if name != hostname + "." + domain:
        connecNodeWs(info)
            
        if info:
            print("  Address: %s:%d" % (socket.inet_ntoa(info.address), info.port))
            print("  Weight: %d, priority: %d" % (info.weight, info.priority))
            print("  Server: %s" % (info.server))
            if info.properties:
                print("  Properties are:")
                for key, value in info.properties.items():
                    print("    %s: %s" % (key, value))
            else:
                print("  No properties")
        else:
            print("  No info")
        print('\n')



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print('Number of arguments:', len(sys.argv), 'arguments.')
    print('Argument List:', str(sys.argv))
    if len(sys.argv) > 1:
        assert sys.argv[1:] == ['--debug']
        logging.getLogger('zeroconf').setLevel(logging.DEBUG)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('google.com', 0))
    hostip = s.getsockname()[0]

    print("hostname = " + hostname)
    print("ip = " + hostip)

    desc = {'name': hostname}
    info = ServiceInfo(domain,
                       hostname + "." + domain,
                       socket.inet_aton(hostip), 3000, 0, 0,
                       desc, hostname + ".local.")

    zeroconf = Zeroconf()
    print("Registration of a service, press Ctrl-C to exit...")

    try:
        print("Registering " + hostname + "...")
        zeroconf.register_service(info)
    except KeyboardInterrupt:
        pass

    print("\nBrowsing services, press Ctrl-C to exit...\n")
    browser = ServiceBrowser(zeroconf, domain, handlers=[on_service_state_change])

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.close()


@socketio_server.on_error()        # Handles the default namespace
def error_handler(e):
    pass

@socketio_server.on_error_default  # handles all namespaces without an explicit error handler
def default_error_handler(e):
    pass



class BeiranNamespace(Namespace):

    def on_my_ping(self):
        emit('my_pong')

    def on_connect(self):
        global thread
        with thread_lock:
            if thread is None:
                thread = socketio_server.start_background_task(
                    target=background_thread)
        emit('my_response', {'data': 'Connected', 'count': 0})

    def on_disconnect(self):
        print('Client disconnected', request.sid)


socketio_server.on_namespace(BeiranNamespace('/beiran'))

