"""
    Peer class for handling;
     - beirand-beirand communications
     - status changes
     - information updates
"""

import asyncio
from pyee import EventEmitter

from beirand.common import logger
from beirand.lib import async_fetch, DockerUtil
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

        await DockerUtil.reset_docker_info_of_node(self.node.uuid.hex)

        await self.fetch_images()
        await self.fetch_layers()

        self.node.status = 'online'
        self.node.save()

        logger.info("new node's layer and image info added on %s at port %s",
                    self.node.ip_address, self.node.port)

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

    async def fetch_images(self):
        """fetch image list from the node and update local db"""

        status, response = await self.request('/images')
        if status != 200:
            # do not raise error not to interrupt process, just log. we may emit another
            # event `check.node` which marks the node offline or emits back
            # for the caller event, the `node.added` in this case.
            logger.error("Cannot fetch images from remote node %s", str(self.node.ip_address))

        logger.debug("received image information %s", str(response))

        for image in response.get('images'):
            try:
                image_ = DockerImage.get(DockerImage.hash_id == image['hash_id'])
                image_.set_available_at(self.node.uuid.hex)
                image_.save()
                logger.debug("update existing image %s, now available on new node: %s",
                             image['hash_id'], self.node.uuid.hex)
            except DockerImage.DoesNotExist:
                new_image = DockerImage.from_dict(image)
                new_image.save()
                logger.debug("new image from remote %s", str(image))

    async def fetch_layers(self):
        """fetch layer list from the node and update local db"""

        status, response = await self.request('/layers')
        if status != 200:
            # same case with above, will be handled later..
            logger.error("Cannot fetch images from remote node %s", str(self.node.ip_address))

        logger.debug("received layer information %s", str(response))

        for layer in response.get('layers'):
            try:
                layer_ = DockerLayer.get(DockerLayer.digest == layer['digest'])
                layer_.set_available_at(self.node.uuid.hex)
                layer_.save()
                logger.debug("update existing layer %s, now available on new node: %s",
                             layer['digest'], self.node.uuid.hex)
            except DockerLayer.DoesNotExist:
                new_layer = DockerLayer.from_dict(layer)
                new_layer.save()
                logger.debug("new layer from remote %s", str(layer))
