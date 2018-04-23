"""
Module for in memory node tracking object `Nodes`
"""
import logging
from beiran.models import Node

from beirand.lib import async_fetch

class Nodes(object):
    """Nodes is in memory data model, composed of members of Beiran Cluster"""

    def __init__(self):
        self.all_nodes = {}
        self.logger = logging.getLogger(__package__)
        self.local_node = None

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
        if not from_db:
            return self.all_nodes.get(uuid, None)

        elif uuid is not None:
            return self.get_node_by_uuid_from_db(uuid=uuid)

        else:
            node = self.get_node_by_uuid_from_db(uuid=uuid)

        return node

    def set_online(self, node):
        """Append node to online nodes collection
        """
        self.all_nodes.update({node.uuid.hex: node})

    def set_offline(self, node):
        """Remove node from online nodes collection
        """
        del self.all_nodes[node.uuid.hex]

    def add_or_update(self, node):
        """
        Appends the new node into nodes dict or updates if exists

        Args:
            node (Node): node object

        """

        try:
            node_ = Node.get(Node.uuid == node.uuid)
            node_.update_using_obj(node)
            node_.save()

        except Node.DoesNotExist:
            node_ = node
            # https://github.com/coleifer/peewee/blob/0ed129baf1d6a0855afa1fa27cde5614eb9b2e57/peewee.py#L5103
            node_.save(force_insert=True)

        self.set_online(node_)

        return node_

    def remove_node(self, node):
        """
        Remove node from nodes dict

        Args:
            node (Node): node model object

        Returns:
            (bool): true if node removed, else false

        """

        removed = self.all_nodes.pop(node.uuid.hex, None)
        return bool(removed)

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

    def list_all_by_ip4(self):
        """List nodes by IP v4 Address"""
        # todo: will be implemented
        pass

    async def add_or_update_new_remote_node(self, node_ip, node_port):
        """
        Get information of the node on IP `node_ip` at port `node_port` via info endpoint.

        Args:
            node_ip (str): node ipv4 address
            node_port (str): node port

        Returns:

        """
        self.logger.debug("getting remote node info: %s %s", node_ip, node_port)
        status, response = await async_fetch('http://{}:{}/info'.format(node_ip, node_port))
        if status != 200:
            raise Exception("Cannot fetch node information")

        self.logger.debug("received node information %s", str(response))
        return self.add_or_update(Node.from_dict(response))

    def get_node_by_ip(self, ip_address):
        """
        Returns the node specified by `ip` address.

        Args:
            ip_address (str): ip address

        Returns:
            (Node) found node object

        """
        for _, node in self.all_nodes.items():
            if node.ip_address == ip_address:
                return node

        return None
