"""
Module for in memory node tracking object `Nodes`
"""
import asyncio
import logging
import urllib
import socket

from beiran.models import Node, PeerConnection
from beiran.client import Client as BeiranClient

import beiran.defaults as defaults

from beirand.peer import Peer


class Nodes(object):
    """Nodes is in memory data model, composed of members of Beiran Cluster"""

    def __init__(self):
        self.all_nodes = {}
        self.connections = {}
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

    def set_online(self, node):
        """Append node to online nodes collection
        """
        self.all_nodes.update({node.uuid.hex: node})

    def set_offline(self, node):
        """Remove node from online nodes collection
        """
        node.status = 'offline'
        node.save()
        if node.uuid.hex in self.all_nodes:
            del self.all_nodes[node.uuid.hex]
        if node.uuid.hex in self.connections:
            del self.connections[node.uuid.hex]

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

    def list_all_by_ip4(self):
        """List nodes by IP v4 Address"""
        # todo: will be implemented
        pass

    async def fetch_node_info(self, url):
        """Fetches node information using url"""

        # todo: after client refactor which make it accept beiran url
        # remove lines below
        transport, protocol, hostname, port, uuid = PeerConnection.parse_address(url)
        url = "{}://{}:{}".format(protocol, hostname, port)
        self.logger.debug("getting remote node info: %s", url)

        client = BeiranClient(url)
        info = await client.get_node_info()

        # self.logger.debug("received node information %s", str(info))
        node_ = Node.from_dict(info)
        try:
            node = Node.get(Node.uuid == node_.uuid)
            node.update_using_obj(node_)
        except Node.DoesNotExist:
            node = node_

        # but for us, addresses might be different than what that node thinks of herself
        # todo: remove after peerconnection implementation
        # parsed = urllib.parse.urlparse(url)
        # node.ip_address = socket.gethostbyname(parsed.hostname)
        # node.port = parsed.port or defaults.LISTEN_PORT
        return node

    async def add_or_update_new_remote_node(self, url):
        """
        Get information of the node on IP `node_ip` at port `node_port` via info endpoint.

        Args:
            node_ip (str): node ipv4 address
            node_port (str): node port

        Returns:

        """

        node = await self.fetch_node_info(url)

        return self.add_or_update(node)

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

    async def probe_node_bidirectional(self, url):
        """
        Probe remote node at `ip_address`:`port` and ask probe back local node

        Args:
            url (str): beiran node url to be probed

        Returns:

        """

        # first, we probe remote
        remote_node = await self.probe_node(url)
        try:
            await self.request_probe_from(node=remote_node)
        except BeiranClient.Error:
            self.logger.error("Cannot make remote node %s probe us", url)

    async def request_probe_from(self, url=None, node=None):
        """Request probe from a remote node"""
        if not url and not node:
            raise Exception("url or node must be provided")
        client = BeiranClient(url=url, node=node)
        return await client.probe_node(self.local_node.url)

    async def probe_node(self, url):
        """
        Probe remote node, get info and save.

        - if url has uuid
            - if uuid in self.connections
                node already connected, return
                # todo: add address change and status

            - if uuid in self.all_nodes
                although it is not a connection, we already know the node, update address in any case

            - finally try to get from db by uuid,
                - if found update address

            - if a node found then try probe with `node` which has its all peer_connection addresses

        - if no node then it is a brand new one, then try with url.

        Args:
            url (str): beiran node url to be probed

        Returns:

        """

        async def try_probe_remote_node(node=None, url=None, retries=3):
            remote_addresses = []
            if not (node and url):
                self.logger.error("cannot call this method with lack of both node and url")

            if node:
                remote_addresses.append(node.address)
                remote_addresses.append(node.get_connections())
            if url:
                remote_addresses.append(url)

            _node = None
            counter = retries

            while counter and not _node and remote_addresses:
                url = remote_addresses[0]
                self.logger.info(
                    'Detected not is not accesible, trying again: %s', url)
                _node = await self.add_or_update_new_remote_node(url)
                await asyncio.sleep(3)  # no need to rush, take your time!

                # decrease counter
                counter -= 1
                # after `retries` times, pop first element
                # of `remote_addresses` and reset counter, so loop goes on with next url.
                if not counter:
                    remote_addresses.pop(0)
                    if remote_addresses:
                        counter = retries
            return _node

        async with self.__probe_lock:
            transport, protocol, hostname, port, uuid = PeerConnection.parse_address(url)

            if uuid:
                if uuid in self.connections:
                    # TODO: If node status is "lost", then trigger reconnect here
                    # TODO: check if address is same?
                    # self.connections[node.uuid.hex].reconnect()

                    node = self.connections.get(uuid)
                    if node.address == url:
                        # Inconsistency error, but we can handle
                        self.logger.error(
                            "Inconsistency error, already connected node is being added AGAIN")
                        return self.connections[uuid].node  # todo: self.connections[uuid]?

                elif uuid in self.all_nodes:  # from memory
                    node = self.all_nodes.get(uuid)
                else:  # from db
                    node = Node.get(Node.uuid==uuid)

                if node:
                    node.set_get_address(url)  # update address of uuid, it may differ
                    node = try_probe_remote_node(node=node)

            else:  # a new node, probably from discovery service
                node = await try_probe_remote_node(url=url)

            if not node:
                self.logger.warning(
                    'Cannot fetch node information, %s',
                )
                return

            node.status = 'connecting'
            node.save()

            peer = Peer(node)
            self.connections.update({node.uuid.hex: peer})

            self.logger.info(
                'Probed node, uuid: %s, %s:%s',
                node.uuid.hex, node.ip_address, node.port)

            return node
