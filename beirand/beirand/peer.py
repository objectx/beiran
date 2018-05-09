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


from beiran.models import DockerImage, DockerLayer


class Peer(EventEmitter):
    """Peer class"""

    def __init__(self, node, loop=None):
        super().__init__()
        self.node = node
        self.loop = loop if loop else asyncio.get_event_loop()
        self.start_loop()

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

        # Check node availability every x second, drop online status if it fails
        check_interval = 15
        retry_interval = 5
        timeout = 4
        fails = 0
        while True:
            await asyncio.sleep(check_interval)
            try:
                status, response = await self.request('/ping', timeout=timeout)
                if status != 200 or not response:
                    raise Exception("Failed to receive ping response from node")
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

    async def request(self, uri, *args, **kwargs):
        """make a request to the peer using preferred transport method"""

        protocol = 'http' # for now it's hardcoded
        host = '{}:{}'.format(self.node.ip_address, self.node.port)
        url = '{}://{}{}'.format(protocol, host, uri)
        response = await async_fetch(url, *args, **kwargs)
        return response
