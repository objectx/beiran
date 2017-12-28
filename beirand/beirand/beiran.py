import asyncio
import logging
import signal
import socket
import sys
import time

from zeroconf import ServiceInfo, ServiceStateChange, Zeroconf

logging.basicConfig()

info = None
zeroconf = None
hostname = socket.gethostname()
domain = "_beiran._tcp.local."


def signal_term_handler():
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


def connect_node_ws():
    pass


def on_service_state_change(zconf, service_type, name, state_change):
    """

    :param state_change: state change of service
    :param name:
    :param service_type:
    :type zconf: Zeroconf
    """
    print("Service %s of type %s state changed: %s" % (name, service_type, state_change))

    if state_change is ServiceStateChange.Added:
        service_info = zconf.get_service_info(service_type, name)
        # if name != hostname + "." + domain:
        connect_node_ws()

        if service_info:
            print("  Address: %s:%d" % (socket.inet_ntoa(service_info.address), service_info.port))
            print("  Weight: %d, priority: %d" % (service_info.weight, service_info.priority))
            print("  Server: %s" % service_info.server)
            if service_info.properties:
                print("  Properties are:")
                for key, value in service_info.properties.items():
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
    host_ip = s.getsockname()[0]
    print("hostname = " + hostname)
    print("ip = " + host_ip)
    desc = {'name': hostname}
    info = ServiceInfo(domain,
                       hostname + "." + domain,
                       socket.inet_aton(host_ip), 3000, 0, 0,
                       desc, hostname + ".local.")
    zeroconf = Zeroconf()
    print("Registration of a service, press Ctrl-C to exit...")
    try:
        print("Registering " + hostname + "...")
        zeroconf.register_service(info)
    except KeyboardInterrupt:
        pass
    print("\nBrowsing services, press Ctrl-C to exit...\n")
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
