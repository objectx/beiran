"""
    Peer class for handling;
     - beirand-beirand communications
     - status changes
     - information updates
"""

import asyncio
import logging
import time
from pyee import EventEmitter

from beirand.common import Services

from beiran.client import Client

from beiran.models import PeerAddress

PEER_REGISTRY = dict()

logger = logging.getLogger('beiran.peer')
class PeerMeta(type):
    def __new__(mcs, name, bases, dct):
        klass = super().__new__(mcs, name, bases, dct)
        klass.peers = PEER_REGISTRY
        return klass

    def __iter__(cls):
        return iter(cls.peers.items())


class Peer(EventEmitter, metaclass=PeerMeta):
    """Peer class"""
    def __new__(cls, node=None, url=None, loop=None, local=False):
        if node:
            cls.node = node
            cls.uuid = node.uuid.hex
            try:
                return cls.peers[node.uuid]
            except KeyError:
                new_obj = object.__new__(cls)
                cls.peers[node.uuid] = new_obj
                return cls

    def __init__(self, node=None, url=None, loop=None, local=False):
        """

        Args:
            node:
            url:
            loop:
            local:
        """
        super().__init__(loop=loop)
        self.ping = -1
        self.last_sync_state_version = 0  # self.node.last_sync_version
        self.logger = logging.getLogger('beiran.peer')
        self.__probe_lock = asyncio.Lock()
        if not node and url and not isinstance(url, PeerAddress):
            self.peer_address = PeerAddress(address=url)
        else:
            self.peer_address = node.address
        if not local:
            self.client = Client(url=self.node.url)
            self.loop = loop if loop else asyncio.get_event_loop()
            self.start_loop()

    def start_loop(self):
        """schedule handling of peer in the asyncio loop"""
        # TODO: Figure out handling errors when scheduling like this
        while not self.node:
            self.node = self.probe_node(self.peer_address)

        if not self.node:
            return

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


    async def probe_node(self, peer_address):
        async def try_probe_remote_node(node=None, peer_address=None, retries=3):
            remote_addresses = []
            if not (node or peer_address):
                self.logger.error("cannot call this method with lack of both node and url")

            if node:
                remote_addresses.append(node.address)
                remote_addresses.append(node.get_connections())
            if peer_address:
                remote_addresses.append(peer_address)

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

            if uuid in self.peers:
                # TODO: If node status is "lost", then trigger reconnect here
                # self.connections[node.uuid.hex].reconnect()
                self.logger.error(
                    "Inconsistency error, already connected node is being added AGAIN")
                return self.peers[uuid]  # todo: self.connections[uuid]?

            if node:
                node.set_get_address(peer_address.address)  # update address of uuid, it may differ
                self.add_or_update(node)

                node.status = 'connecting'
                node.save()

                self.peers.update({node.uuid.hex: Peer(node=node, loop=self.loop)})

                self.logger.info(
                    'Probed node, uuid: %s, %s:%s',
                    node.uuid.hex, node.ip_address, node.port)

                return node
            else:
                self.logger.info(
                    'Can not probed given info: %s', peer_address)


