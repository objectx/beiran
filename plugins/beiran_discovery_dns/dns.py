"""
Zeroconf multicast discovery service implementation
"""

import os
import asyncio
import aiodns

from beiran.models import PeerAddress
from beiran.plugin import BaseDiscoveryPlugin

# Beiran plugin variables
PLUGIN_NAME = 'dns'
PLUGIN_TYPE = 'discovery'

# Constants
DEFAULT_DOMAIN = "_beiran._tcp.local."


class DNSDiscovery(BaseDiscoveryPlugin):
    """Beiran Implementation of DNS Service Discovery
    """

    def __init__(self, config):
        """ Creates an instance of Dns Discovery Service
        """
        super().__init__(config)
        self.resolver = aiodns.DNSResolver(loop=self.loop)
        self.nodes = set()

    async def query(self, name, query_type):
        """ Dns query coroutine
        Args:
            name: address to look for
            query_type: dns type

        Returns: List of dns records

        """
        return await self.resolver.query(name, query_type)

    def get_query_address(self) -> str:
        """ Query address to discover other beiran daemons
        Returns:
            str: hostname to query
        """
        return os.getenv('DISCOVERY_SERVICE_ADDRESS', 'beirand')

    async def start(self):
        """ Starts discovery service
        """
        asyncio.ensure_future(self.browse(), loop=self.loop)

    async def browse(self):
        """ Browsing other nodes of beirand
        """
        while True:
            result = await self.query(self.get_query_address(), 'A')
            result = list(map(lambda x: x.host, result))
            result = list(filter(lambda x: x != self.address, result))
            new_comers = list(filter(lambda x: x not in self.nodes, result))
            sadly_goodbyers = list(filter(lambda x: x not in result, self.nodes))
            for node in new_comers:
                self.log.info("New node %s", node)
                self.nodes.add(node)
                peer_address = PeerAddress(host=node)
                self.emit('discovered', peer_address=peer_address)
            for node in sadly_goodbyers:
                self.log.info("Leaving node %s", node)
                self.nodes.discard(node)
                self.emit('undiscovered', node)
            await asyncio.sleep(1.0)
