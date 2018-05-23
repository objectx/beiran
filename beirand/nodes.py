"""
Module for in memory node tracking object `Nodes`
"""
import asyncio
import logging

from beiran.models import Node
from beiran.client import Client as BeiranClient

import beirand.defaults as defaults


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

        self.set_online(node)

        return node

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
        url = "http://{}:{}".format(node_ip, node_port)
        client = BeiranClient(url)

        # These changes will save us from hardcoded `http` here
        info = await client.get_node_info()

        self.logger.debug("received node information %s", str(info))
        node = Node.from_dict(info)
        # but for us, addresses might be different than what that node thinks of herself
        node.ip_address = node_ip
        node.port = node_port
        return self.add_or_update(node)

    def get_node_by_ip_and_port(self, ip_address, service_port, from_db=False):
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
            try:
                return Node.select().where(
                    (Node.ip_address == ip_address) &
                    (Node.beiran_service_port == service_port)
                ).get()
            except Node.DoesNotExist:
                return None

        for _, node in self.all_nodes.items():
            if node.ip_address == ip_address and node.port == int(service_port):
                return node

        return None

    async def probe_node_bidirectional(self, ip_address, service_port):
        """
        Probe remote node at `ip_address`:`port` and ask probe back local node

        Args:
            ip_address (str): service ip address to be probed
            service_port (int): service port to be probed

        Returns:

        """

        # firstly, probe remote
        remote_node = await self.probe_node(ip_address, service_port)

        self.logger.debug("\n\nProbe remote finished\n\n")

        client = BeiranClient(node=remote_node)

        try:
            await client.probe_node(self.local_node.url)
        except BeiranClient.Error:
            self.logger.debug("Cannot make remote node %s %s to probe local node itself",
                              ip_address, service_port)

    async def probe_node(self, ip_address, service_port=None):
        """
        Probe remote node, get info and save.

        Args:
            ip_address (str): service ip address to be probed
            service_port (int): service port to be probed

        Returns:

        """
        service_port = service_port or defaults.LISTEN_PORT

        retries_left = 10

        # check if we had prior communication with this node
        node = self.get_node_by_ip_and_port(ip_address, service_port)
        # FIXME! NO! fetch that node's info, get it's uuid. and match db using that
        if node:
            # fetch up-to-date information and mark the node as online
            node = await self.add_or_update_new_remote_node(ip_address, service_port)

        # first time we met with this node, wait for information to be fetched
        # or we couldn't fetch node information at first try
        while retries_left and not node:
            self.logger.info(
                'Detected not is not accesible, trying again: %s:%s', ip_address, service_port)
            await asyncio.sleep(3)  # no need to rush, take your time!
            node = await self.add_or_update_new_remote_node(ip_address, service_port)
            retries_left -= 1

        if not node:
            self.logger.warning('Cannot fetch node information, %s:%s', ip_address, service_port)
            return

        node.status = 'connecting'
        node.save()

        self.logger.info(
            'Probed node, uuid: %s, %s:%s',
            node.uuid.hex, ip_address, service_port)

        return node
