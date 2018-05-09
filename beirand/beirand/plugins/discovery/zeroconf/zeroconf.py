"""
Zeroconf multicast discovery service implementation
"""

import asyncio
import logging
import socket
import os

from aiozeroconf import Zeroconf, ZeroconfServiceTypes, ServiceInfo, ServiceBrowser
import netifaces

from beirand.plugins import BeiranDiscoveryPlugin

# Beiran plugin variables
PLUGIN_NAME = 'zeroconf'
PLUGIN_TYPE = 'discovery'

# Constants
DEFAULT_DOMAIN = "_beiran._tcp.local."


class ZeroconfDiscovery(BeiranDiscoveryPlugin):
    """Beiran Implementation of Zeroconf Multicast DNS Service Discovery
    """

    def __init__(self, config):
        """ Creates an instance of Zeroconf Discovery Service
        """
        super().__init__(config)
        self.info = None
        self.domain = config['domain'] if 'domain' in config else DEFAULT_DOMAIN
        self.version = config['version']
        self.zeroconf = Zeroconf(self.loop, address_family=[netifaces.AF_INET],
                                  iface=self.network_interface)

    async def start(self):
        """ Starts discovery service
        """
        self.start_browse()
        await self.register()

    async def stop(self):
        """ Unregister service and close zeroconf"""
        self.log.debug("Unregistering...")
        await self.zeroconf.unregister_service(self.info)
        await self.zeroconf.close()

    async def list_service(self) -> tuple:
        """ Get already registered services on zeroconf
        Returns:
            tuple: List of services
        """
        list_of_services = await ZeroconfServiceTypes.find(self.zeroconf, timeout=0.5)
        self.log.info("Found %s", format(list_of_services))
        return list_of_services

    @property
    def advertise_name(self):
        return self.hostname + '-' + str(self.port) + "." + self.domain

    async def init(self):
        """ Initialization of discovery service with all information and starts service browser
        """
        self.log.debug("hostname = %s", self.hostname)
        self.log.debug("interface = %s", self.network_interface)
        self.log.debug("ip = %s", self.address)
        desc = {'name': self.hostname, 'version': self.version }
        self.info = ServiceInfo(self.domain,
                                self.advertise_name,
                                socket.inet_aton(self.address),
                                self.port, 0, 0,
                                desc,
                                self.hostname + ".local.")
        print("INFO", self.info)

    def start_browse(self):
        """ Start browsing changes on discovery
        """
        self.log.debug("\nBrowsing services...\n")

        listener = ZeroconfListener(self)
        ServiceBrowser(self.zeroconf, self.domain, listener=listener)

    async def register(self):
        """ Registering own service to zeroconf
        """
        self.log.debug("Registering %s ...", self.hostname)
        await self.zeroconf.register_service(self.info)


class ZeroconfListener(object):
    """Listener instance for zeroconf discovery to monitor changes
    """

    def __init__(self, discovery=None):
        self.discovery = discovery
        self.log = discovery.log

    def remove_service(self, zeroconf, typeos, name):
        """Service removed change receives
        """
        asyncio.ensure_future(self.removed_service(zeroconf, typeos, name))
        self.log.debug("Service %s removed" % (name,))

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
        if socket.inet_ntoa(service_info.address) == self.discovery.address and service_info.port == self.discovery.port:
            return
        if service_info:
            self.log.debug("  Address: %s:%d" %
                           (socket.inet_ntoa(service_info.address),
                            service_info.port))
            self.log.debug("  Weight: %d, priority: %d" %
                           (service_info.weight, service_info.priority))
            self.log.debug("  Server: %s" % service_info.server)
            self.discovery.emit('discovered', ip_address=socket.inet_ntoa(service_info.address),
                                service_port=service_info.port)
            if service_info.properties:
                self.log.debug("  Properties are:")
                for key, value in service_info.properties.items():
                    self.log.debug("    %s: %s" % (key, value))
            else:
                self.log.debug("  No properties")
        else:
            self.log.debug("  No info")
        self.log.debug('\n')

    async def removed_service(self, zeroconf, typeos, name):
        """
        Service Info for removed node
        Args:
            zeroconf: Zeroconf instance
            typeos: Type of the service
            name: Name of the service
        """
        service_info = await zeroconf.get_service_info(typeos, name)
        self.log.debug("Service is removed. Name: ", service_info.server)
        self.discovery.emit('undiscovered',
                            ip_address=socket.inet_ntoa(service_info.address),
                            port=service_info.port)
