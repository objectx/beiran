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
Module for in memory node tracking object `Nodes`
"""
import asyncio
import logging
import urllib

from typing import Optional

from beiran.models import Node

class Nodes:
    """Nodes is in memory data model, composed of members of Beiran Cluster"""

    def __init__(self):
        self.all_nodes = {}
        self.logger = logging.getLogger('beiran.nodes')
        self.local_node = None
        self.__probe_lock = asyncio.Lock()

    @staticmethod
    def get_from_db() -> dict:
        """
        Get all nodes with docker information from database and dumps them into a dict.

        Returns:
            dict: key value list of nodes as in form {'uuid': {'ip': '10.0.0.2', 'hostname':'web1'}}


        """
        nodes_query = Node.select()
        return {n.uuid.hex: n for n in nodes_query}

    @staticmethod
    def get_node_by_uuid_from_db(uuid: Optional[str]) -> Node:
        """
        Get node from database
        Args:
            uuid (Optional[str]): node uuid

        Returns:
            node (Node): node object

        """
        return Node.get(uuid == uuid)  # pylint: disable=comparison-with-itself

    async def get_node_by_uuid(self, uuid: str = None, from_db: bool = False) -> Node:
        """
        Unless from_db is True, get node dict from self.all_nodes memory
        object, if available.

        If from_db is True or node is not in memory, try to get from db.

        Args:
            uuid (str): node uuid
            from_db (bool): ask for db if True, else get from memory if available

        Returns:
            node (Node): node object

        """
        if uuid is None:
            uuid = self.local_node.uuid.hex  # pylint: disable=no-member

        if not from_db:
            return self.all_nodes.get(uuid, None)

        return self.get_node_by_uuid_from_db(uuid=uuid)

    def update_node(self, node: Node):
        """Append node to online nodes collection
        """
        self.all_nodes.update({node.uuid.hex: node})

    def set_offline(self, node: Node):
        """Remove node from online nodes collection
        """
        node.status = Node.STATUS_OFFLINE
        node.save()

        # why should we delete node from both all_nodes and connections?
        if node.uuid.hex in self.all_nodes:
            del self.all_nodes[node.uuid.hex]
        # if node.uuid.hex in self.connections:
        #     del self.connections[node.uuid.hex]

    def add_or_update(self, node: Node) -> Node:
        """
        Appends the new node into nodes dict or updates if exists

        Args:
            node (Node): node object

        Returns:
            node (Node): node object
        """
        node = Node.add_or_update(node)
        self.update_node(node)
        return node

    def remove_node(self, node: Node):
        """
        Remove node from nodes dict

        Args:
            node (Node): node model object

        Returns:

        """
        self.set_offline(node)

    def list_of_nodes(self, from_db: bool = True) -> list:
        """
        List all nodes from database or nodes dict

        Args:
            from_db (bool): db lookup for nodes or not

        Returns:
            list: list of node objects

        """
        if from_db:
            return [*self.get_from_db().values()]

        return [*self.all_nodes.values()]

    async def get_node_by_ip_and_port(self, ip_address: str, service_port: int,
                                      from_db: bool = False) -> Node:
        """
        Returns the node specified by `ip` address.

        Args:
            ip_address (str): ip address
            service_port (int): port of node
            from_db (bool): indicate search scope

        Returns:
            (Node) found node object

        """
        if from_db:
            return Node.select().where(
                (Node.ip_address == ip_address) &
                (Node.port == service_port)
            ).get()

        for _, node in self.all_nodes.items():
            if node.ip_address == ip_address and node.port == int(service_port):
                return node

        raise Node.DoesNotExist()

    async def get_node_by_url(self, url: str, from_db: bool = False) -> Node:
        """..."""
        parsed = urllib.parse.urlparse(url)
        if parsed.fragment:
            return await self.get_node_by_uuid(parsed.fragment, from_db)

        return await self.get_node_by_ip_and_port(parsed.hostname, parsed.port, from_db)
