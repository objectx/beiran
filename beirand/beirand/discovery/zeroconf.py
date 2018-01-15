"""
Zeroconf multicast discovery service implementation
"""

import asyncio
import logging
import socket

from aiozeroconf import Zeroconf, ZeroconfServiceTypes, ServiceInfo, ServiceBrowser

import netifaces

from discovery.discovery import Discovery

_DOMAIN = "_beiran._tcp.local."


class ZeroconfDiscovery(Discovery):
    """Beiran Implementation of Zeroconf Multicast DNS Service Discovery
    """

    def __init__(self, aioloop):
        """ Creates an instance of Zeroconf Discovery Service

        Args:
            aioloop: AsyncIO Loop
        """
        super().__init__(aioloop)
        self.info = None
        self.zero_conf = Zeroconf(self.loop, address_family=[netifaces.AF_INET], iface="eth0")

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
        list_of_services = await ZeroconfServiceTypes.find(self.zero_conf, timeout=0.5)
        print("Found {}".format(list_of_services))
        return list_of_services

    def init(self):
        """ Initialization of discovery service with all information and starts service browser
        """
        socket_for_host = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_for_host.connect(('google.com', 0))
        host_ip = socket_for_host.getsockname()[0]
        print("hostname = " + self.hostname)
        print("ip = " + host_ip)
        desc = {'name': self.hostname, 'version': '0.1.0'}
        self.info = ServiceInfo(_DOMAIN,
                                self.hostname + "." + _DOMAIN,
                                socket.inet_aton(host_ip), 3000, 0, 0,
                                desc, self.hostname + ".local.")

    def start_browse(self):
        """ Start browsing changes on discovery
        """
        print("\nBrowsing services, press Ctrl-C to exit...\n")

        listener = ZeroconfListener(self)
        ServiceBrowser(self.zero_conf, _DOMAIN, listener=listener)

    async def register(self):
        """ Registering own service to zeroconf
        """
        print("Registering " + self.hostname + "...")
        await self.zero_conf.register_service(self.info)


class Node(object):
    def __init__(self, hostname=None, ip_address=None):
        self.hostname = hostname
        self.ip_address = ip_address


class ZeroconfListener(object):
    """Listener instance for zeroconf discovery to monitor changes
    """

    def __init__(self, discovery=None):
        self.discovery = discovery

    def remove_service(self, zeroconf, typeos, name):
        """Service removed change receives
        """
        asyncio.ensure_future(self.removed_service(zeroconf, typeos, name))
        print("Service %s removed" % (name,))

    def add_service(self, zeroconf, typeos, name):
        """Service added change receives
        """
        asyncio.ensure_future(self.found_service(zeroconf, typeos, name))

    async def found_service(self, zeroconf, typeos, name):
        """
        Service Info for newly added node
        Args:
            zeroconf: Zeroconf instance
            typeos: Type of the service
            name: Name of the service
        """
        service_info = await zeroconf.get_service_info(typeos, name)
        # print("Adding {}".format(service_info))
        if service_info:
            print("  Address: %s:%d" % (socket.inet_ntoa(service_info.address), service_info.port))
            print("  Weight: %d, priority: %d" % (service_info.weight, service_info.priority))
            print("  Server: %s" % service_info.server)
            self.discovery.emit('discovered',
                                Node(hostname=service_info.name,
                                     ip_address=socket.inet_ntoa(service_info.address)))
            if service_info.properties:
                print("  Properties are:")
                for key, value in service_info.properties.items():
                    print("    %s: %s" % (key, value))
            else:
                print("  No properties")
        else:
            print("  No info")
        print('\n')

    async def removed_service(self, zeroconf, typeos, name):
        """
        Service Info for removed node
        Args:
            zeroconf: Zeroconf instance
            typeos: Type of the service
            name: Name of the service
        """
        service_info = await zeroconf.get_service_info(typeos, name)
        print("Service is removed. Name: ", service_info.server)
        self.discovery.emit('undiscovered',
                            Node(hostname=service_info.name,
                                 ip_address=socket.inet_ntoa(service_info.address)))