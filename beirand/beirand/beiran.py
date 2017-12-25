import asyncio
import logging
import signal
import socket
import sys
import time

from zeroconf import ServiceBrowser, ServiceInfo, ServiceStateChange, Zeroconf

logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

info = None
hostname = socket.gethostname()
domain = "_beiran._tcp.local."


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

def connect_node_ws(info):
    pass

def on_service_state_change(zeroconf, service_type, name, state_change):
    """

    :type zeroconf: object
    """
    print("Service %s of type %s state changed: %s" % (name, service_type, state_change))

    if state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        # if name != hostname + "." + domain:
        connect_node_ws(info)

        if info:
            print("  Address: %s:%d" % (socket.inet_ntoa(info.address), info.port))
            print("  Weight: %d, priority: %d" % (info.weight, info.priority))
            print("  Server: %s" % info.server)
            if info.properties:
                print("  Properties are:")
                for key, value in info.properties.items():
                    print("    %s: %s" % (key, value))
            else:
                print("  No properties")
        else:
            print("  No info")
        print('\n')

@asyncio.coroutine
def discover():
    global info, zeroconf
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
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print('Number of arguments:', len(sys.argv), 'arguments.')
    print('Argument List:', str(sys.argv))
    if len(sys.argv) > 1:
        assert sys.argv[1:] == ['--debug']
        logging.getLogger('zeroconf').setLevel(logging.DEBUG)

    discovery = asyncio.async(discover())
    # loop.run_until_complete(discover())
    loop = asyncio.get_event_loop()
    loop.run_forever()
    # loop.close()
