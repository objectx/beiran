"""
Module for in memory node tracking object `Nodes`
"""
import json

from playhouse.shortcuts import model_to_dict
from tornado.httpclient import AsyncHTTPClient

from beiran.models import Node


class Nodes(object):
    """Nodes is in memory data model, composed of members of Beiran Cluster"""

    def __init__(self):
        from beirand.common import logger
        self.all_nodes = self.get_from_db() or {}
        self.logger = logger

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

    def add_or_update(self, node):
        """
        Appends the new node into nodes dict or updates if exists

        Args:
            node (Node): node model object

        """

        node_dict = model_to_dict(node)

        self.all_nodes.update({node.uuid: node_dict})

        try:
            node_from_db = Node.get(Node.uuid == node.uuid)
            node_from_db.update(**node_dict)

        except Node.DoesNotExist:
            Node.create(**node_dict)

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
            from_db (bool): db lookup for nodes or not

        Returns:
            list: list of uuid of nodes

        """
        if from_db:
            return [n.uuid.hex for n in Node.select()]

        return [*self.all_nodes.keys()]

    def list_all_by_ip4(self):
        """List nodes by IP v4 Address"""
        # todo: will be implemented
        pass

    def get_remote_node_info(self, node_ip, node_port):
        """
        Get information of the node on IP `node_ip` at port `node_port` via info endpoint.

        Args:
            node_ip (str): node ipv4 address
            node_port (str): node port

        Returns:
            (dict): detailed information of the node.

        """

    def add_or_update_new_remote_node(self, node_ip, node_port):
        """
        Get information of the node on IP `node_ip` at port `node_port` via info endpoint.

        Args:
            node_ip (str): node ipv4 address
            node_port (str): node port

        Returns:

        """
        self.logger.debug("getting remote node info: %s %s", node_ip, node_port)
        http_client = AsyncHTTPClient()
        http_client.fetch('http://{}:{}/info'.format(node_ip, node_port),
                          self.on_new_remote_node)  # todo: https?

    def on_new_remote_node(self, response):
        """
        Add or update local db record of the new remote node with information
        gathered from the remote node over http info endpoint

        Args:
            response: tornado async http client response object

        """

        if response.error:
            # which means node is not accessible, mark it offline.
            self.logger.error(
                "An error occured while trying to reach remote node at port %s",
                response.error)
        else:
            node_info = json.loads(response.body)  # todo: remove unnecessary details
            self.add_or_update(Node(**node_info))
            self.logger.debug("Nodes: {}".format(self.all_nodes))
