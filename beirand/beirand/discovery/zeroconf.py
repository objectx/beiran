import netifaces
import asyncio
import logging

import socket
from aiozeroconf import Zeroconf, ZeroconfServiceTypes, ServiceInfo, ServiceBrowser

from discovery import Discovery

_DOMAIN = "_beiran._tcp.local."


class ZeroconfDiscovery(Discovery):
    """Beiran Implementation of Zeroconf Multicast DNS Service Discovery
    """

    def __init__(self, aioloop):
        super().__init__(aioloop)
        """ Creates an instance of Zeroconf Discovery Service

        Args:
            aioloop: AsyncIO Loop

        Todo:
            * All prints should convert to log
            * Version code that is added to service info should come from daemon version
            * Getting host_ip should be more proper way than opening a socket to google.com
            * Network Interface name for zeroconf discovery should be a parameter to class
        """
        self.info = None
        self.zc = Zeroconf(self.loop, address_family=[netifaces.AF_INET], iface="eth0")

        logging.getLogger('zeroconf').setLevel(self.log.level)

        self.hostname = socket.gethostname()

    def start(self):
        """ Starts discovery service
        """
        self.init()
        self.start_browse()
        asyncio.ensure_future(self.register(), loop=self.loop)

    async def stop(self, zeroconf: Zeroconf):
        """ Unregister service and close zeroconf
        Args:
            zeroconf (Zeroconf):

        Returns:
            None:
        """
        print("Unregistering...")
        await zeroconf.unregister_service(self.info)
        await zeroconf.close()

    async def list_service(self) -> tuple:
        """ Get already registered services on zeroconf
        Returns:
            tuple: List of services
        """
        list_of_services = await ZeroconfServiceTypes.find(self.zc, timeout=0.5)
        print("Found {}".format(list_of_services))
        return list_of_services

    def init(self):
        """ Initialization of discovery service with all information and starts service browser
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('google.com', 0))
        host_ip = s.getsockname()[0]
        print("hostname = " + self.hostname)
        print("ip = " + host_ip)
        desc = {'name': self.hostname, 'version': '0.1.0'}
        self.info = ServiceInfo(_DOMAIN,
                                self.hostname + "." + _DOMAIN,
                                socket.inet_aton(host_ip), 3000, 0, 0,
                                desc, self.hostname + ".local.")

    def start_browse(self):
        print("\nBrowsing services, press Ctrl-C to exit...\n")

        listener = ZeroconfListener()
        ServiceBrowser(self.zc, _DOMAIN, listener=listener)

    async def register(self):
        """ Registering own service to zeroconf
        """
        print("Registering " + self.hostname + "...")
        await self.zc.register_service(self.info)


class ZeroconfListener(object):

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


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    discovery = ZeroconfDiscovery(loop)
    discovery.start()
    loop.run_forever()
