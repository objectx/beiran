"""
Module for in memory node tracking object `Nodes`
"""

from playhouse.shortcuts import model_to_dict

from beiran.models import Node


class Nodes(object):
    """Nodes is in memory data model, composed of members of Beiran Cluster"""

    def __init__(self):
        self.all_nodes = self.get_from_db() or {}

    @staticmethod
    def get_from_db():
        """
        Get all nodes from database and dumps them into a dict.

        Returns:
            dict: key value list of nodes as in form {'uuid': {'ip': '10.0.0.2', 'hostname':'web1'}}


        """
        return {n.uuid.hex: model_to_dict(n) for n in Node.select()}

    @staticmethod
    def get_node_by_uuid_from_db(uuid):
        """
        Get node from database
        Args:
            uuid (str): node uuid

        Returns:
            (dict): serialized node object

        """
        return model_to_dict(Node.get(uuid == uuid))

    def get_node_by_uuid(self, uuid=None, from_db=False):
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
        node = None

        if not from_db:
            node = self.all_nodes.get(uuid)

        if not node:
            node = self.get_node_by_uuid_from_db(uuid=uuid)

        return node

    def add_new(self, node):
        """
        Appends the new node into nodes dict or updates if exists

        Args:
            node (Node): node model object

        """

        node_dict = model_to_dict(node)

        self.all_nodes.update({node.uuid: node_dict})
        node_from_db, new = Node.get_or_create(**node_dict)
        if not new:
            node_from_db.update(**node_dict)

    def remove_node(self, node):
        """
        Remove node from nodes dict

        Args:
            node (Node): node model object

        """

        self.all_nodes.pop(node.uuid)

    def list_of_nodes(self, from_db=True):
        """
        List all nodes from database or nodes dict

        Args:
            from_db: db lookup for nodes or not

        Returns:
            list: list of uuid of nodes

        """
        if from_db:
            return [n for n in Node.select()]

        return self.all_nodes.keys()

    def list_all_by_ip4(self):
        """List nodes by IP v4 Address"""
        # todo: will be implemented
        pass
