"""
    Peer class for handling;
     - beirand-beirand communications
     - status changes
     - information updates
"""

import asyncio
from pyee import EventEmitter

from beirand.common import logger, PLUGINS
from beirand.lib import async_fetch

from beiran.client import Client


class Peer(EventEmitter):
    """Peer class"""

    def __init__(self, node, loop=None):
        super().__init__()
        self.node = node
        self.loop = loop if loop else asyncio.get_event_loop()
        self.start_loop()

        url = "http://{}:{}".format(self.node.ip_address, self.node.port)
        self.client = Client(url, node=self.node)

    def start_loop(self):
        """schedule handling of peer in the asyncio loop"""
        # TODO: Figure out handling errors when scheduling like this
        self.loop.create_task(self.peerloop())

    async def peerloop(self):
        """lifecycle of a beiran-node connection"""
        logger.info("getting new nodes' images and layers from %s at port %s\n\n ",
                    self.node.ip_address, self.node.port)
        self.node.status = 'syncing'
        self.node.save()

        sync_futures = []
        for plugin_name, plugin in PLUGINS.items():
            sync_futures.append(plugin.sync(self))

        await asyncio.gather(*sync_futures)

        self.node.status = 'online'
        self.node.save()

        logger.info("node(%s) synced on %s at port %s",
                    self.node.uuid.hex,
                    self.node.ip_address,
                    self.node.port)

        # In future this part will be replaced with a websocket or gRPC connection
        # Check node availability every x second, drop online status if it fails
        check_interval = 30
        retry_interval = 5
        timeout = 4
        fails = 0
        while True:
            await asyncio.sleep(check_interval)
            try:
                await self.client.ping(timeout=timeout)

                # TODO: Track ping duration
                # that can be utilized in download priorities etc. in future
                fails = 0
                check_interval = 15
            except Exception as err:  # pylint: disable=unused-variable,broad-except
                logger.debug("pinging node failed, because %s", str(err))
                check_interval = retry_interval
                fails += 1
                if fails >= 2:
                    break

        logger.info("lost connection to node %s(%s:%d)",
                    self.node.uuid.hex, self.node.ip_address, self.node.port)
        self.node.status = 'lost'
        self.node.save()
        # TODO: Communicate this to the discovery plugin
        # so it can allow re-discovery of this node when found again
