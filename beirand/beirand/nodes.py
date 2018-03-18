"""
Module for in memory node tracking object `Nodes`
"""
import json
import logging

from playhouse.shortcuts import model_to_dict, JOIN
from tornado.httpclient import AsyncHTTPClient

from beiran.models import Node, DockerDaemon


class Nodes(object):
    """Nodes is in memory data model, composed of members of Beiran Cluster"""

    def __init__(self):
        self.all_nodes = {}
        self.logger = logging.getLogger(__package__)

    @staticmethod
    def get_from_db():
        """
        Get all nodes with docker information from database and dumps them into a dict.

        Returns:
            dict: key value list of nodes as in form {'uuid': {'ip': '10.0.0.2', 'hostname':'web1'}}


        """
        nodes_with_docker = Node.select(DockerDaemon, Node).join(
            DockerDaemon, JOIN.LEFT_OUTER, on=(DockerDaemon.node == Node.uuid).alias('docker')
        )

        result = {}
        for node in nodes_with_docker:
            node_info = model_to_dict(node)
            node_info.update({'docker': model_to_dict(node.docker)})
            result[node.uuid.hex] = node_info

        return result

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

    def add_or_update(self, node_info):
        """
        Appends the new node into nodes dict or updates if exists

        Args:
            node_info (dict): node information

        """

        # node_dict = model_to_dict(node)

        try:
            node_ = Node.get(Node.uuid == node_info['uuid'])
            node_.update(**node_info)

        except Node.DoesNotExist:
            node_ = Node.create(**node_info)

        if 'docker' in node_info and node_info['docker']['status']:
            daemon = node_info['docker']['daemon_info']
            docker_dict = {
                'docker_version': daemon['ServerVersion'],
                'storage_driver': daemon['Driver'],
                'docker_root_dir': daemon['DockerRootDir'],
                'details': daemon
            }
            try:
                docker_ = DockerDaemon.get(DockerDaemon.node == node_info['uuid'])
                docker_.update(**docker_dict)
            except DockerDaemon.DoesNotExist:
                DockerDaemon.create(
                    node=node_,
                    **docker_dict
                )

        self.all_nodes.update({node_info['uuid']: node_info})

        return node_

    def remove_node(self, node):
        """
        Remove node from nodes dict

        Args:
            node (Node): node model object

        Returns:
            (bool): true if node removed, else false

        """

        removed = self.all_nodes.pop(node.uuid, None)
        return bool(removed)

    def list_of_nodes(self, from_db=True):
        """
        List all nodes from database or nodes dict

        Args:
            from_db (bool): db lookup for nodes or not

        Returns:
            list: list of uuid of nodes

        """
        if from_db:
            self.get_from_db()

        return [*self.all_nodes.values()]

    def list_all_by_ip4(self):
        """List nodes by IP v4 Address"""
        # todo: will be implemented
        pass

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
            return None

        node_info = json.loads(response.body)  # todo: remove unnecessary details
        node = self.add_or_update(node_info)
        return node
