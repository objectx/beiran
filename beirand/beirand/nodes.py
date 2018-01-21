from beirand.models import Node
from playhouse.shortcuts import model_to_dict

nodes = {}


class Nodes(object):
    """Nodes is in memory data model, composed of members of Beiran Cluster"""

    def __init__(self):
        self.all_nodes = self.get_from_db() or {}

    def get_from_db(self):
        """
        Get all nodes from database and dumps them into self.all_nodes dict.

        Returns:
            dict: key value list of nodes as in form {'uuid': {'ip': '10.0.0.2', 'hostname':'web1'}}


        """
        return {n.uuid: model_to_dict(n) for n in Node.select()}

    def add_new(self, node):
        """
        Appends the new node into nodes dict or updates if exists

        Args:
            node (Node): node model object

        """

        self.all_nodes.update({node.uuid: model_to_dict(node)})

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
