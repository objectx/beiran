"""Beiran Implementation of DNS Service Discovery
"""
import os
import asyncio
import aiodns
from beirand.discovery.discovery import Discovery, Node


class DnsDiscovery(Discovery):
    """Beiran Implementation of DNS Service Discovery
    """

    def __init__(self, aioloop):
        """ Creates an instance of Dns Discovery Service

        Args:
            aioloop: AsyncIO Loop
        """
        super().__init__(aioloop)
        self.loop = aioloop
        self.resolver = aiodns.DNSResolver(loop=self.loop)
        self.nodes = {}

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
            for result_node in new_comers:
                node = Node(hostname=result_node, ip_address=result_node)
                self.nodes[result_node] = node
                self.emit('discovered', node)
            for node in sadly_goodbyers:
                self.emit('undiscovered', self.nodes.get(node))
                self.nodes.pop(node, None)
            await asyncio.sleep(1.0)
