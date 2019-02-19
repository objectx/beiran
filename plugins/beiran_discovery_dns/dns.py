# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Zeroconf multicast discovery service implementation
"""

import asyncio
import aiodns

from beiran.models import PeerAddress
from beiran.plugin import BaseDiscoveryPlugin

# Beiran plugin variables
PLUGIN_NAME = 'dns'
PLUGIN_TYPE = 'discovery'


class DNSDiscovery(BaseDiscoveryPlugin):
    """Beiran Implementation of DNS Service Discovery
    """
    DEFAULTS = {
        'discovery_service_address': 'beirand',
        'domain': '_beiran._tcp.local.',
    }

    def __init__(self, config: dict) -> None:
        """ Creates an instance of Dns Discovery Service
        """
        super().__init__(config)
        self.resolver = aiodns.DNSResolver(loop=self.loop)
        self.nodes = set() # type: set

    async def query(self, name: str, query_type: str):
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
        return self.config['discovery_service_address']

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
