"""
    Peer class for handling;
     - beirand-beirand communications
     - status changes
     - information updates
"""

import asyncio
import logging
import time
from aiohttp import ClientConnectorError
from pyee import EventEmitter

from beiran.client import Client
from beiran.models import Node
from beiran.daemon.nodes import Nodes
from beiran.daemon.common import Services

PEER_REGISTRY: dict = dict()


class Peer(EventEmitter):
    """Peer class"""

    @classmethod
    def find_or_create(cls, node: Node = None, *args, **kwargs):
        if node and node.uuid in PEER_REGISTRY:
            return PEER_REGISTRY[node.uuid]
        return cls(node, *args, **kwargs)

    def collect(self):
        PEER_REGISTRY[self.node.uuid] = self

    def uncollect(self):
        del PEER_REGISTRY[self.node.uuid]

    def __init__(self, node=None, nodes=None, loop=None, local=False):  # pylint: disable=unused-argument
        """

        Args:
            node (Node): node object
            nodes (Nodes):
            loop (object): asyncio loop
            local (bool): local peer or not
        """
        super().__init__()
        self.node = node
        self.uuid = node.uuid.hex
        self.logger = logging.getLogger('beiran.peer')
        self.loop = loop if loop else asyncio.get_event_loop()
        self.nodes = nodes
        self.local = local
        self.ping = -1
        self.last_sync_state_version = 0  # self.node.last_sync_version
        self.__probe_lock = asyncio.Lock()
        self.peer_address = node.get_latest_connection()
        if not self.local:
            self.client = Client(peer_address=self.peer_address)
            self.start_loop()

    def start_loop(self):
        """schedule handling of peer in the asyncio loop"""
        # TODO: Figure out handling errors when scheduling like this

        self.loop.create_task(self.peerloop())

    async def sync(self, remote_status: dict = None):
        """Sync plugin states with other peers"""
        _remote_status = remote_status or await self.client.get_status(timeout=10)
        sync_version = _remote_status.get('sync_state_version')
        if sync_version == self.last_sync_state_version:
            self.logger.debug("Already in sync (v:%d) with peer, not syncing", sync_version)
            return

        # if sync_version < self.last_sync_state_version
        #    inconsistent state; reset peer info

        sync_futures = []
        for _, plugin in Services.plugins.items():
            sync_futures.append(plugin.sync(self))
        await asyncio.gather(*sync_futures)

        if self.last_sync_state_version == 0 or sync_version != self.last_sync_state_version:
            self.node.status = Node.STATUS_ONLINE
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

        while not self.node:
            self.node = await self.probe_node(self.peer_address)

        if not self.node:
            return

        self.logger.info("getting new nodes' images and layers from %s at port %s\n\n ",
                         self.node.ip_address, self.node.port)
        self.node.status = Node.STATUS_SYNCING
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
        self.node.status = Node.STATUS_LOST
        self.node.save()
        # TODO: Communicate this to the discovery plugin
        # so it can allow re-discovery of this node when found again

    async def probe_node_bidirectional(self, peer_address, extra_addr=None):
        """
        Probe remote node at peer_address and ask probe back local node

        Args:
            peer_address (peer_address): peer address to be probed
            extra_addr (list): additional addresses we should check

        Returns:
            (Node): node object

        """

        # first, we probe remote
        remote_node = await self.probe_node(peer_address, extra_addr=extra_addr)
        try:
            await self.request_probe_from(peer_address=remote_node.get_latest_connection(),
                                          probe_back=False)
        except Client.Error:
            self.logger.error("Cannot make remote node %s probe us", peer_address)

    async def request_probe_from(self, peer_address, probe_back=False):
        """
        Request probe from a remote node
        Args:
            peer_address (PeerAddress): peer address to be asked to probe back
            probe_back (bool): whether to be asked to probe back

        Returns:
            (Node): node object

        """

        client = Client(peer_address=peer_address)
        return await client.probe_node(address=self.peer_address.location,
                                       probe_back=probe_back)

    async def probe_node(self, peer_address, extra_addr=None, retries=3):
        """

        Args:
            peer_address (PeerAddress): address of peer which will be probed
            extra_addr (list): additional addresses we should check
            retries (int): retry number, -1 means forever until node found

        Returns:
            (Node): probed node

        """
        async def try_probe_remote_node(node=None, peer_address=None, retries=retries):
            """

            Args:
                node (Node): node
                peer_address (PeerAddress): peer address
                retries (int): retry number

            Returns:

            """
            remote_addresses = []
            if not (node or peer_address):
                self.logger.error("cannot call this method with lack of both node and url")

            if node:
                remote_addresses.append(node.get_connections())
            if peer_address:
                remote_addresses.append(peer_address)

            if extra_addr:
                remote_addresses.append(extra_addr)

            _node = None
            counter = retries

            while counter and not _node and remote_addresses:
                url = remote_addresses[0]
                self.logger.info(
                    'Detected not is not accesible, trying again: %s', url)
                _node = await self.fetch_node_info(url)
                await asyncio.sleep(3)  # no need to rush, take your time!

                # decrease counter
                counter -= 1
                # after `retries` times, pop first element
                # of `remote_addresses` and reset counter, so loop goes on with next url.
                if not counter:
                    remote_addresses.pop(0)
                    if remote_addresses:
                        counter = retries
            self.logger.info("found: %s", _node)
            return _node

        async with self.__probe_lock:

            if not peer_address.uuid:  # a new node, probably from discovery service
                node = await try_probe_remote_node(peer_address=peer_address)
            else:
                node = None

            uuid = node.uuid if node else peer_address.uuid

            if not uuid:
                self.logger.warning(
                    'Cannot fetch node information, %s', peer_address.address
                )
                return

            if uuid in self.peers:  # pylint: disable=no-member
                # TODO: If node status is "lost", then trigger reconnect here
                # self.connections[node.uuid.hex].reconnect()
                self.logger.error(
                    "Inconsistency error, already connected node is being added AGAIN")
                return PEER_REGISTRY[uuid].node  # pylint: disable=no-member

            if not node:
                self.logger.info(
                    'Can not probed given info: %s', peer_address)
                return None

            node.set_get_address(peer_address.address)  # update address of uuid, it may differ
            node = Node.add_or_update(node)

            node.status = Node.STATUS_CONNECTING
            node.save()
            peer = Peer.find_or_create(node=node, loop=self.loop)
            peer.collect()
            self.nodes.update_node(node)

            self.logger.info(
                'Probed node, uuid, address: %s, %s',
                node.uuid.hex, node.address)

            return node

    async def fetch_node_info(self, peer_address):
        """
        Fetches node information using url
        Args:
            peer_address (PeerAddress): peer_address object

        Returns:
            (Node) node object with fetched info

        """

        self.logger.debug("getting remote node info: %s", peer_address.location)

        client = Client(peer_address)
        try:
            info = await client.get_node_info()
        except ClientConnectorError:
            self.logger.error("can not create client, remote node is not available: %s",
                              peer_address.location)
            return None

        # self.logger.debug("received node information %s", str(info))
        node_ = Node.from_dict(info)
        try:
            node = Node.get(Node.uuid == node_.uuid)
            node.update_using_obj(node_)
        except Node.DoesNotExist:
            node = node_

        return node
