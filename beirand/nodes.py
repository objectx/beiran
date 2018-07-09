"""
Module for in memory node tracking object `Nodes`
"""
import asyncio
import logging
import urllib

from beiran.models import Node

class Nodes(object):
    """Nodes is in memory data model, composed of members of Beiran Cluster"""

    def __init__(self):
        self.all_nodes = {}
        self.logger = logging.getLogger('beiran.nodes')
        self.local_node = None
        self.__probe_lock = asyncio.Lock()

    @staticmethod
    def get_from_db():
        """
        Get all nodes with docker information from database and dumps them into a dict.

        Returns:
            dict: key value list of nodes as in form {'uuid': {'ip': '10.0.0.2', 'hostname':'web1'}}


        """
        nodes_query = Node.select()
        return {n.uuid.hex: n for n in nodes_query}

    @staticmethod
    def get_node_by_uuid_from_db(uuid):
        """
        Get node from database
        Args:
            uuid (str): node uuid

        Returns:
            (dict): serialized node object

        """
        return Node.get(uuid == uuid)

    async def get_node_by_uuid(self, uuid=None, from_db=False):
        """
        Unless from_db is True, get node dict from self.all_nodes memory
        object, if available.

        If from_db is True or node is not in memory, try to get from db.

        Args:
            uuid (str): node uuid
            from_db (bool): ask for db if True, else get from memory if available

        Returns:
            (dict): serialized node object

        """
        if uuid is None:
            uuid = self.local_node.uuid.hex

        if not from_db:
            return self.all_nodes.get(uuid, None)

        return self.get_node_by_uuid_from_db(uuid=uuid)

    def update_node(self, node):
        """Append node to online nodes collection
        """
        self.all_nodes.update({node.uuid.hex: node})

    def set_offline(self, node):
        """Remove node from online nodes collection
        """
        node.status = Node.STATUS_OFFLINE
        node.save()

        # why should we delete node from both all_nodes and connections?
        if node.uuid.hex in self.all_nodes:
            del self.all_nodes[node.uuid.hex]
        # if node.uuid.hex in self.connections:
        #     del self.connections[node.uuid.hex]

    def add_or_update(self, node):
        """
        Appends the new node into nodes dict or updates if exists

        Args:
            node (Node): node object

        """
        node = Node.add_or_update(node)
        self.update_node(node)
        return node

    def remove_node(self, node):
        """
        Remove node from nodes dict

        Args:
            node (Node): node model object

        Returns:
            (bool): true if node removed, else false

        """
        self.set_offline(node)

    def list_of_nodes(self, from_db=True):
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

    async def get_node_by_ip_and_port(self, ip_address, service_port, from_db=False):
        """
        Returns the node specified by `ip` address.

        Args:
            ip_address (str): ip address
            service_port (str): port of node
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

    async def get_node_by_url(self, url, from_db=False):
        """..."""
        parsed = urllib.parse.urlparse(url)
        if parsed.fragment:
            return await self.get_node_by_uuid(parsed.fragment, from_db)

        return await self.get_node_by_ip_and_port(parsed.hostname, parsed.port, from_db)
