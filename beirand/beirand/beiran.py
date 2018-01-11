import asyncio
import logging
import signal
import socket
import sys

import netifaces
from aiozeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ZeroconfServiceTypes

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if log.level == logging.NOTSET:
    log.setLevel(logging.WARN)

info: ServiceInfo = None
zc: Zeroconf = None
hostname = socket.gethostname()
domain = "_beiran._tcp.local."


async def do_close(zeroconf: Zeroconf) -> None:
    """ Unregister service and close zeroconf
    Args:
        zeroconf (Zeroconf): 

    Returns:
        None:
    """
    print("Unregistering...")
    await zeroconf.unregister_service(info)
    await zeroconf.close()


def signal_term_handler():
    print('got SIGTERM')
    if info:
        zc.unregister_service(info)
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_term_handler)


class ZeroconfListener(object):

    def on_connect(self):
        print('connect')

    def on_disconnect(self):
        print('disconnect')

    def on_reconnect(self):
        print('reconnect')

    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))

    def add_service(self, zeroconf, type, name):
        asyncio.ensure_future(self.found_service(zeroconf, type, name))

    async def found_service(self, zeroconf, type, name):
        service_info = await zeroconf.get_service_info(type, name)
        # print("Adding {}".format(service_info))
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


async def register_self():
    print("Registering " + hostname + "...")
    await zc.register_service(info)


async def init(async_loop):
    global info, zc
    logging.getLogger('zeroconf').setLevel(logging.DEBUG)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('google.com', 0))
    host_ip = s.getsockname()[0]
    print("hostname = " + hostname)
    print("ip = " + host_ip)
    # FIXME: with real daemon version
    desc = {'name': hostname, 'version': '0.1.0'}
    info = ServiceInfo(domain,
                       hostname + "." + domain,
                       socket.inet_aton(host_ip), 3000, 0, 0,
                       desc, hostname + ".local.")
    zc = Zeroconf(async_loop, address_family=[netifaces.AF_INET], iface="eth0")
    print("\nBrowsing services, press Ctrl-C to exit...\n")
    listener = ZeroconfListener()
    ServiceBrowser(zc, domain, listener=listener)


async def list_service(zeroconf):
    los = await ZeroconfServiceTypes.find(zeroconf, timeout=0.5)
    print("Found {}".format(los))


if __name__ == '__main__':
    print('Number of arguments:', len(sys.argv), 'arguments.')
    print('Argument List:', str(sys.argv))
    if len(sys.argv) > 1:
        assert sys.argv[1:] == ['--debug']
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init(loop))
        # loop.run_until_complete(list_service(zc))
        asyncio.ensure_future(register_self(), loop=loop)
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(do_close(zc))
    finally:
        loop.close()
