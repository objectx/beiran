"""Beiran Implementation of DNS Service Discovery
"""
import os
import asyncio
import aiodns
from beirand.discovery.discovery import Discovery


class DnsDiscovery(Discovery):
    """Beiran Implementation of DNS Service Discovery
    """

    def __init__(self, aioloop, config):
        """ Creates an instance of Dns Discovery Service

        Args:
            aioloop: AsyncIO Loop
        """
        super().__init__(aioloop)
        self.loop = aioloop
        self.config = config
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

    def start(self):
        """ Starts discovery service
        """
        asyncio.ensure_future(self.browse(), loop=self.loop)

    async def browse(self):
        """ Browsing other nodes of beirand
        """
        while True:
            result = await self.query(self.get_query_address(), 'A')
            result = list(map(lambda x: x.host, result))
            result = list(filter(lambda x: x != self.host_ip, result))
            new_comers = list(filter(lambda x: x not in self.nodes, result))
            sadly_goodbyers = list(filter(lambda x: x not in result, self.nodes))
            for node in new_comers:
                self.log.info("New node %s", node)
                self.nodes.add(node)
                self.emit('discovered', ip_address=node)
            for node in sadly_goodbyers:
                self.log.info("Leaving node %s", node)
                self.nodes.discard(node)
                self.emit('undiscovered', node)
            await asyncio.sleep(1.0)
