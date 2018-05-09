"""
Docker packaging plugin
"""

import asyncio
import logging
import socket
import os
import docker

from aiodocker import Docker

from beiran.models import DockerImage, DockerLayer
from beirand.plugins import BeiranPlugin

from .util import DockerUtil


PLUGIN_NAME = 'docker'
PLUGIN_TYPE = 'package'


class DockerPackaging(BeiranPlugin):
    """Docker support for Beiran"""

    # def __init__(self, config):
    #     super().__init__(config)

    async def init(self):
        self.aiodocker = Docker()
        self.util = DockerUtil(self.config["storage"], self.aiodocker)
        self.docker = docker.from_env()
        self.docker_lc = docker.APIClient()
        self.tar_cache_dir = "tar_cache"
        self.probe_task = None

    async def start(self):
        self.log.debug("starting docker plugin")

        # # this is async but we will let it run in
        # # background, we have no rush and it will run
        # # forever anyway
        self.probe_task = self.loop.create_task(self.probe_daemon())

    async def stop(self):
        if self.probe_task:
            self.probe_task.cancel()

    async def sync(self, peer):
        await DockerUtil.reset_docker_info_of_node(peer.node.uuid.hex)

        await self.fetch_images_from_peer(peer)
        await self.fetch_layers_from_peer(peer)

    async def fetch_images_from_peer(self, peer):
        """fetch image list from the node and update local db"""

        status, response = await peer.request('/images')
        if status != 200:
            # do not raise error not to interrupt process, just log. we may emit another
            # event `check.node` which marks the node offline or emits back
            # for the caller event, the `node.added` in this case.
            self.log.error("Cannot fetch images from remote node %s", str(peer.node.ip_address))

        self.log.debug("received image information %s", str(response))

        for image in response.get('images'):
            try:
                image_ = DockerImage.get(DockerImage.hash_id == image['hash_id'])
                image_.set_available_at(peer.node.uuid.hex)
                image_.save()
                self.log.debug("update existing image %s, now available on new node: %s",
                             image['hash_id'], peer.node.uuid.hex)
            except DockerImage.DoesNotExist:
                new_image = DockerImage.from_dict(image)
                new_image.save()
                self.log.debug("new image from remote %s", str(image))

    async def fetch_layers_from_peer(self, peer):
        """fetch layer list from the node and update local db"""

        status, response = await peer.request('/layers')
        if status != 200:
            # same case with above, will be handled later..
            self.log.error("Cannot fetch images from remote node %s", str(peer.node.ip_address))

        self.log.debug("received layer information %s", str(response))

        for layer in response.get('layers'):
            try:
                layer_ = DockerLayer.get(DockerLayer.digest == layer['digest'])
                layer_.set_available_at(peer.node.uuid.hex)
                layer_.save()
                self.log.debug("update existing layer %s, now available on new node: %s",
                             layer['digest'], peer.node.uuid.hex)
            except DockerLayer.DoesNotExist:
                new_layer = DockerLayer.from_dict(layer)
                new_layer.save()
                self.log.debug("new layer from remote %s", str(layer))

    async def probe_daemon(self):
        """Deal with local docker daemon states"""

        while True:
            # Delete all data regarding our node
            await DockerUtil.reset_docker_info_of_node(self.node.uuid.hex)

            # wait until we can update our docker info
            await DOCKER_UTIL.update_docker_info(self.node)

            # connected to docker daemon
            self.emit('up')
            self.node.save()

            # Get mapping of diff-id and digest mappings of docker daemon
            await DOCKER_UTIL.get_diffid_mappings()

            # Get layerdb mapping
            await DOCKER_UTIL.get_layerdb_mappings()

            # Get Images
            self.log.debug("Getting docker image list..")
            image_list = await self.aiodocker.images.list()
            for image_data in image_list:
                if not image_data['RepoTags']:
                    continue

                # remove the non-tag tag from tag list
                image_data['RepoTags'] = [t for t in image_data['RepoTags'] if t != '<none>:<none>']

                if not image_data['RepoTags']:
                    continue

                image = DockerImage.from_dict(image_data, dialect="docker")
                try:
                    image_ = DockerImage.get(DockerImage.hash_id == image_data['Id'])
                    old_available_at = image_.available_at
                    image_.update_using_obj(image)
                    image = image_
                    image.available_at = old_available_at

                except DockerImage.DoesNotExist:
                    pass

                try:
                    image_details = await self.aiodocker.images.get(name=image_data['Id'])

                    layers = await DOCKER_UTIL.get_image_layers(image_details['RootFS']['Layers'])
                except Exception as err:  # pylint: disable=unused-variable,broad-except
                    continue

                image.layers = [layer.digest for layer in layers]

                for layer in layers:
                    layer.set_available_at(self.node.uuid.hex)
                    layer.save()

                image.set_available_at(self.node.uuid.hex)
                image.save()

            # This will be converted to something like
            #   daemon.plugins['docker'].setReady(true)
            # in the future; will we in docker plugin code.
            self.emit('ready')

            # await until docker is unavailable
            self.log.debug("subscribing to docker events for further changes")
            subscriber = self.aiodocker.events.subscribe()
            while True:
                event = await subscriber.get()
                if event is None:
                    break

                if 'id' in event:
                    self.log.debug("docker event: %s[%s] %s", event['Action'], event['Type'], event['id'])
                else:
                    self.log.debug("docker event: %s[%s]", event['Action'], event['Type'])

            # This will be converted to something like
            #   daemon.plugins['docker'].setReady(false)
            # in the future; will we in docker plugin code.
            self.emit('down')
            self.log.warning("docker connection lost")
            await asyncio.sleep(100)
