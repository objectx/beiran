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


class Peer(EventEmitter):
    """Peer class"""

    def __init__(self, node, loop=None):
        super().__init__()
        self.node = node
        self.ping = -1
        self.loop = loop if loop else asyncio.get_event_loop()
        self.logger = logging.getLogger('beiran.peer')
        self.start_loop()

        url = "http://{}:{}".format(self.node.ip_address, self.node.port)
        self.client = Client(url, node=self.node)
        self.last_sync_state_version = 0

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

        if self.last_sync_state_version == 0 or sync_version < self.last_sync_state_version:
            self.node.status = 'online'
            self.node.save()

        self.last_sync_state_version = sync_version

        self.logger.info("node(%s) synced(v:%d) on %s at port %s",
                         self.node.uuid.hex,
                         sync_version,
                         self.node.ip_address,
                         self.node.port)
        self.emit('sync')

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
                if new_status['sync_state_version'] > self.last_sync_state_version:
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
