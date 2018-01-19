"""
Zeroconf multicast discovery service implementation
"""

import asyncio
import logging
import socket
import os
import netifaces

from aiozeroconf import Zeroconf, ZeroconfServiceTypes, ServiceInfo, ServiceBrowser

from beirand.discovery.discovery import Discovery, Node

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
        self.network_interface = self.get_network_interface()
        self.zero_conf = Zeroconf(self.loop, address_family=[netifaces.AF_INET],
                                  iface=self.network_interface)

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

    def get_network_interface(self):
        """ Gets listen interface for daemon
        """
        if 'LISTEN_INTERFACE' in os.environ:
            return os.environ['LISTEN_INTERFACE']

        # TODO: Find the interface with the specified listen address
        # if 'LISTEN_ADDR' in os.environ:
        #   return netifaces...

        return netifaces.gateways()['default'][2][1]

    def get_listen_address(self):
        """ Gets listen address for daemon
        """
        if 'LISTEN_ADDR' in os.environ:
            return os.environ['LISTEN_ADDR']
        interface = self.get_network_interface()
        return netifaces.ifaddresses(interface)[2][0]['addr']

    def get_hostname(self):
        """ Gets hostname for discovery
        """
        if 'HOSTNAME' in os.environ:
            return os.environ['HOSTNAME']
        return socket.gethostname()

    def init(self):
        """ Initialization of discovery service with all information and starts service browser
        """
        host_ip = self.get_listen_address()
        print("hostname = " + self.hostname)
        print("interface = " + self.network_interface)
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
