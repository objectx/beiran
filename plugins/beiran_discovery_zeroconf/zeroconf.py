"""
Zeroconf multicast discovery service implementation
"""

import asyncio
import socket

from typing import Optional, Coroutine

from aiozeroconf import Zeroconf, ZeroconfServiceTypes, ServiceInfo, ServiceBrowser
import netifaces

from beiran.plugin import BaseDiscoveryPlugin

# Beiran plugin variables
PLUGIN_NAME = 'zeroconf'
PLUGIN_TYPE = 'discovery'

# Constants
DEFAULT_DOMAIN = "_beiran._tcp.local."


class ZeroconfDiscovery(BaseDiscoveryPlugin):
    """Beiran Implementation of Zeroconf Multicast DNS Service Discovery
    """

    def __init__(self, config: dict) -> None:
        """ Creates an instance of Zeroconf Discovery Service
        """
        super().__init__(config)
        self.info = None
        self.domain = config['domain'] if 'domain' in config else DEFAULT_DOMAIN
        self.version = config['version']
        self.zeroconf = Zeroconf(self.loop,
                                 address_family=[netifaces.AF_INET],
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
    def advertise_name(self) -> str:
        """Return concatenated string as advertise name"""
        return "{}-{}.{}".format(self.hostname, str(self.port), self.domain)

    async def init(self):
        """ Initialization of discovery service with all information and starts service browser
        """
        self.log.debug("hostname = %s", self.hostname)
        self.log.debug("interface = %s", self.network_interface)
        self.log.debug("ip = %s", self.address)
        desc = {'name': self.hostname, 'version': self.version}
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

    def __init__(self, discovery: "ZeroconfDiscovery") -> None:
        self.discovery = discovery
        self.log = discovery.log
        self.services = {} # type: dict

    def remove_service(self, zeroconf: Zeroconf, typeos: str, name: str):
        """Service removed change receives
        """
        asyncio.ensure_future(self.removed_service(zeroconf, typeos, name))
        self.log.debug("Service %s removed" % (name,))

    def add_service(self, zeroconf: Zeroconf, typeos: str, name: str):
        """Service added change receives
        """
        asyncio.ensure_future(self.found_service(zeroconf, typeos, name))

    async def found_service(self, zeroconf: Zeroconf, typeos: str, name: str,
                            retries: int = 5) -> Optional[Coroutine]:
        """
        Service Info for newly added node
        Args:
            zeroconf: Zeroconf instance
            typeos: Type of the service
            name: Name of the service
        """
        service_info = await zeroconf.get_service_info(typeos, name)
        if not service_info:
            self.log.warning("could not fetch info of discovered service: %s", name)
            if retries == 0:
                # give up
                return None
            retries -= 1
            await asyncio.sleep(5)
            return self.found_service(zeroconf, typeos, name, retries)

        is_itself = all(
            [
                socket.inet_ntoa(service_info.address) == self.discovery.address,
                service_info.port == self.discovery.port
            ]
        )
        if is_itself:
            return None # return here if we discovered ourselves

        self.services[name] = service_info
        if service_info:
            self.log.debug("  Address: %s:%d" %
                           (socket.inet_ntoa(service_info.address),
                            service_info.port))
            self.log.debug("  Weight: %d, priority: %d" %
                           (service_info.weight, service_info.priority))
            self.log.debug("  Server: %s" % service_info.server)
            self.discovery.emit('discovered',
                                ip_address=socket.inet_ntoa(service_info.address),
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

        return None

    async def removed_service(self, zeroconf: Zeroconf, typeos: str, name: str):
        """
        Service Info for removed node
        Args:
            zeroconf: Zeroconf instance
            typeos: Type of the service
            name: Name of the service
        """
        service_info = await zeroconf.get_service_info(typeos, name)
        if not service_info:
            service_info = self.services[name]

        if not service_info:
            self.log.warning("We undiscovered a service that we did not discover; name: %s", name)
            return

        self.log.debug("Service is removed. Name: %s", name)
        self.discovery.emit('undiscovered',
                            ip_address=socket.inet_ntoa(self.services[name].address),
                            service_port=self.services[name].port)
        del self.services[name]
