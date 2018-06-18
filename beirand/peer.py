"""
    Peer class for handling;
     - beirand-beirand communications
     - status changes
     - information updates
"""

import asyncio
import logging
import time
import urllib
import socket
from pyee import EventEmitter

from beirand.common import Services

from beiran.client import Client
from beiran.models import Node, PeerConnection
from beiran import defaults



class Peer(EventEmitter):
    """Peer class"""

    def __init__(self, nodes, node=None, url=None, loop=None):


        self.nodes = nodes

        if node:
            connected = self.is_peer_alredy_connected(node)



        if not node:
            self.node = self.get_node(url)
        self.url = url
        self.ping = -1
        self.loop = loop if loop else asyncio.get_event_loop()
        self.logger = logging.getLogger('beiran.peer')

        url = "http://{}:{}".format(self.node.ip_address, self.node.port)
        self.client = Client(url, node=self.node)
        self.last_sync_state_version = 0 #self.node.last_sync_version
        self.start_loop()
        super().__init__()

    @classmethod
    def create(cls, nodes, node=None, url=None, loop=None):
        """
        Factory method for peer object.

        Args:
            nodes:
            node:
            url:
            loop:

        Returns:
            self class instance
        """

        def get_existing_or_new_peer(node_):
            try:
                return nodes.connections.get(node_.uuid.hex)
            except KeyError:
                new_peer = cls(nodes, node=node_, url=url, loop=loop)
                nodes.connections[node_.uuid.hex] = new_peer
                return new_peer

        if not (node or url):
            raise Exception()  # todo: figure out a more proper way.

        node = node or cls.get_node_by_url(url)
        return get_existing_or_new_peer(node)

    def is_peer_alredy_connected(self, node):
        return self.nodes.connections.get(node.uuid.hex)

    async def get_node_by_url(self, url):
        """Fetches node information and builds a Node object using url"""
        self.logger.debug("getting remote node info: %s", url)

        client = Client(url)
        info = await client.get_node_info()  # todo: what if node is not accessible

        # self.logger.debug("received node information %s", str(info))
        node_ = Node.from_dict(info)
        try:
            node = Node.get(Node.uuid == node_.uuid)
            node.update_using_obj(node_)
        except Node.DoesNotExist:
            node = node_

        # but for us, addresses might be different than what that node thinks of herself
        parsed = urllib.parse.urlparse(url)
        node.ip_address = socket.gethostbyname(parsed.hostname)
        node.port = parsed.port or defaults.LISTEN_PORT
        return node

    def start_loop(self):
        """schedule handling of peer in the asyncio loop"""
        # TODO: Figure out handling errors when scheduling like this
        self.loop.create_task(self.peerloop())

    async def sync(self, remote_status=None):
        """Sync plugin states with other peers"""
        if not remote_status:
            remote_status = await self.client.get_status(timeout=10)
        sync_version = remote_status['sync_state_version']
        if sync_version == self.last_sync_state_version:
            self.logger.debug("Already in sync (v:%d) with peer, not syncing", sync_version)
            return

        # if sync_version < self.last_sync_state_version
        #    inconsistent state; reset peer info

        sync_futures = []
        for _, plugin in Services.plugins.items():
            sync_futures.append(plugin.sync(self))
        await asyncio.gather(*sync_futures)

        # if self.last_sync_state_version == 0 or sync_version < self.last_sync_state_version:
        #     self.node.status = 'online'
        #     self.node.save()

        if self.last_sync_state_version == 0 or sync_version != self.last_sync_state_version:
            self.node.status = 'online'
            self.node.last_sync_version = sync_version
            self.node.save()

        self.last_sync_state_version = sync_version

        self.logger.info("node(%s) synced(v:%d) on %s at port %s",
                         self.node.uuid.hex,
                         sync_version,
                         self.node.ip_address,
                         self.node.port)
        self.emit('sync')

    # TODO: reconnect
    # async def reconnect(self):
    #     # ..
    #     # node.status = 'reconnecting'
    #     pass

    async def peerloop(self):
        """lifecycle of a beiran-node connection"""
        self.logger.info("getting new nodes' images and layers from %s at port %s\n\n ",
                         self.node.ip_address, self.node.port)
        self.node.status = 'syncing'
        self.node.save()

        await self.sync()

        # In future this part will be replaced with a websocket or gRPC connection
        # Check node availability every x second, drop online status if it fails
        check_interval = 30
        retry_interval = 5
        timeout = 4
        fails = 0
        while True:
            await asyncio.sleep(check_interval)
            try:
                timestamp = time.time()
                new_status = None
                new_status = await self.client.get_status(timeout=timeout)
                # self.status
                ping_duration = round((time.time()-timestamp)*1000)
                self.ping = ping_duration
                # Check if we're out of sync. resync everything if we're
                if new_status['sync_state_version'] != self.last_sync_state_version:
                    self.logger.info("Node(%s) out-of-sync, syncing", self.node.uuid.hex)
                    await self.sync(new_status)
                fails = 0
                check_interval = 15
            except Exception as err:  # pylint: disable=unused-variable,broad-except
                self.node.ping = -1
                self.logger.debug("pinging node failed, because %s", str(err))
                check_interval = retry_interval
                fails += 1
                if fails >= 2:
                    break

        self.logger.info("lost connection to node %s(%s:%d)",
                         self.node.uuid.hex, self.node.ip_address, self.node.port)
        self.node.status = 'lost'
        self.node.save()
        # TODO: Communicate this to the discovery plugin
        # so it can allow re-discovery of this node when found again

    async def probe_node(self, url):
        """
        Probe remote node, get info and save.

        Args:
            url (str): beiran node url to be probed

        Returns:

        """
        async with self.__probe_lock:

            # check if we had prior communication with this node
            try:
                node = await self.get_node_by_url(url)
                if node.uuid.hex in self.connections:
                    # TODO: If node status is "lost", then trigger reconnect here
                    # self.connections[node.uuid.hex].reconnect()

                    # Inconsistency error, but we can handle
                    self.logger.error(
                        "Inconsistency error, already connected node is being added AGAIN")
                    return self.connections[node.uuid.hex].node

                # fetch up-to-date information and mark the node as online
                node = await self.add_or_update_new_remote_node(url)
            except Node.DoesNotExist:
                node = None

            # FIXME! For some reason, this first pass above always fails

            # first time we met with this node, wait for information to be fetched
            # or we couldn't fetch node information at first try
            retries_left = 3
            while retries_left and not node:
                # TODO: Try alternative addresses of node here
                # TODO: Implement altervative addresses for nodes
                self.logger.info(
                    'Detected not is not accesible, trying again: %s', url)
                await asyncio.sleep(3)  # no need to rush, take your time!
                node = await self.add_or_update_new_remote_node(url)
                retries_left -= 1

            if not node:
                self.logger.warning('Cannot fetch node information, %s', url)
                return

            node.status = 'connecting'
            node.save()

            peer = Peer(node)
            self.connections.update({node.uuid.hex: peer})

            self.logger.info(
                'Probed node, uuid: %s, %s:%s',
                node.uuid.hex, node.ip_address, node.port)

            return node
