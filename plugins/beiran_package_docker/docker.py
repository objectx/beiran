"""
Docker packaging plugin
"""

import asyncio
import logging
import socket
import os
import docker

from aiodocker import Docker

from .models import DockerImage, DockerLayer
from .models import MODEL_LIST
from beiran.plugin import BasePackagePlugin

from .util import DockerUtil
from .api import ROUTES
from .api import Services as ApiDependencies


PLUGIN_NAME = 'docker'
PLUGIN_TYPE = 'package'


class DockerPackaging(BasePackagePlugin):
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
        self.api_routes = ROUTES
        self.model_list = MODEL_LIST

        ApiDependencies.aiodocker = self.aiodocker
        ApiDependencies.logger = self.log
        ApiDependencies.docker_util = self.util
        ApiDependencies.local_node = self.node
        ApiDependencies.loop = self.loop

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

        images = await peer.client.get_images()
        self.log.debug("received image list from peer")

        for image in images:
            try:
                image_ = DockerImage.get(DockerImage.hash_id == image['hash_id'])
                image_.set_available_at(peer.node.uuid.hex)
                image_.save()
                self.log.debug("update existing image %s, now available on new node: %s",
                             image['hash_id'], peer.node.uuid.hex)
            except DockerImage.DoesNotExist:
                new_image = DockerImage.from_dict(image)
                new_image.save(force_insert=True)
                self.log.debug("new image from remote %s", str(image))

    async def fetch_layers_from_peer(self, peer):
        """fetch layer list from the node and update local db"""

        layers = await peer.client.get_layers()
        self.log.debug("received layer list from peer")

        for layer in layers:
            try:
                layer_ = DockerLayer.get(DockerLayer.digest == layer['digest'])
                layer_.set_available_at(peer.node.uuid.hex)
                layer_.save()
                self.log.debug("update existing layer %s, now available on new node: %s",
                             layer['digest'], peer.node.uuid.hex)
            except DockerLayer.DoesNotExist:
                new_layer = DockerLayer.from_dict(layer)
                new_layer.save(force_insert=True)
                self.log.debug("new layer from remote %s", str(layer))

    async def daemon_error(self, error):
        # This will be converted to something like
        #   daemon.plugins['docker'].setReady(false)
        # in the future; will we in docker plugin code.
        self.log.error("docker connection error: %s", error, exc_info=True)
        self.emit('error', error)
        self.emit('down')

        # re-schedule
        await asyncio.sleep(30)
        self.probe_task = self.loop.create_task(self.probe_daemon())

    async def daemon_lost(self):
        # This will be converted to something like
        #   daemon.plugins['docker'].setReady(false)
        # in the future; will we in docker plugin code.
        self.emit('down')
        self.log.warning("docker connection lost")

        # re-schedule
        await asyncio.sleep(30)
        self.probe_task = self.loop.create_task(self.probe_daemon())

    async def probe_daemon(self):
        """Deal with local docker daemon states"""

        try:
            self.log.debug("Probing docker daemon")

            # Delete all data regarding our node
            await DockerUtil.reset_docker_info_of_node(self.node.uuid.hex)

            # wait until we can update our docker info
            await self.util.update_docker_info(self.node)

            # connected to docker daemon
            self.emit('up')
            self.node.save()

            try:
                # Get mapping of diff-id and digest mappings of docker daemon
                await self.util.get_diffid_mappings()
                # Get layerdb mapping
                await self.util.get_layerdb_mappings()
            except PermissionError as err:
                self.log.error("Cannot access docker storage, please run as sudo for now")
                raise err

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
                image_exists_in_db = False
                try:
                    image_ = DockerImage.get(DockerImage.hash_id == image_data['Id'])
                    old_available_at = image_.available_at
                    image_.update_using_obj(image)
                    image = image_
                    image.available_at = old_available_at
                    image_exists_in_db = True

                except DockerImage.DoesNotExist:
                    pass

                try:
                    image_details = await self.aiodocker.images.get(name=image_data['Id'])

                    layers = await self.util.get_image_layers(image_details['RootFS']['Layers'])
                except DockerUtil.CannotFindLayerMappingError as err:
                    continue

                image.layers = [layer.digest for layer in layers]

                for layer in layers:
                    layer.set_available_at(self.node.uuid.hex)
                    layer.save()

                image.set_available_at(self.node.uuid.hex)
                image.save(force_insert=not image_exists_in_db)

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

            await self.daemon_lost()

        except Exception as err:
            await self.daemon_error(err)
