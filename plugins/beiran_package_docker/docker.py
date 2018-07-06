"""
Docker packaging plugin
"""

import asyncio
import docker
from aiodocker import Docker

from beiran.plugin import BasePackagePlugin, History
from beiran.models import Node
from beirand.peer import Peer

from .models import DockerImage, DockerLayer
from .models import MODEL_LIST
from .util import DockerUtil
from .api import ROUTES
from .api import Services as ApiDependencies


PLUGIN_NAME = 'docker'
PLUGIN_TYPE = 'package'

# pylint: disable=attribute-defined-outside-init
class DockerPackaging(BasePackagePlugin):  # pylint: disable=too-many-instance-attributes
    """Docker support for Beiran"""

    # def __init__(self, config):
    #     super().__init__(config)

    async def init(self):
        self.aiodocker = Docker()
        self.util = DockerUtil(self.aiodocker, self.config["storage"])
        self.docker = docker.from_env()
        self.docker_lc = docker.APIClient()
        self.tar_cache_dir = "tar_cache"
        self.probe_task = None
        self.api_routes = ROUTES
        self.model_list = MODEL_LIST
        self.history = History() # type: History
        self.last_error = None

        ApiDependencies.aiodocker = self.aiodocker
        ApiDependencies.logger = self.log
        ApiDependencies.docker_util = self.util
        ApiDependencies.local_node = self.node
        ApiDependencies.loop = self.loop
        ApiDependencies.daemon = self.daemon

    async def start(self):
        self.log.debug("starting docker plugin")

        # this is async but we will let it run in
        # background, we have no rush and it will run
        # forever anyway
        self.probe_task = self.loop.create_task(self.probe_daemon())

        self.on('docker_daemon.new_image', self.new_image_saved)
        self.on('docker_daemon.existing_image_deleted', self.existing_image_deleted)

    async def stop(self):
        if self.probe_task:
            self.probe_task.cancel()

    async def sync(self, peer: Peer):
        await DockerUtil.reset_docker_info_of_node(peer.node.uuid.hex) # type: ignore

        await self.fetch_images_from_peer(peer)
        await self.fetch_layers_from_peer(peer)

    async def save_image_at_node(self, image: DockerImage, node: Node):
        """Save an image from a node into db"""
        try:
            image_ = DockerImage.get(DockerImage.hash_id == image.hash_id)
            image_.set_available_at(node.uuid.hex) # type: ignore
            image_.save()
            self.log.debug("update existing image %s, now available on new node: %s",
                           image.hash_id, node.uuid.hex) # type: ignore
        except DockerImage.DoesNotExist:
            image.available_at = [node.uuid.hex] # type: ignore
            image.save(force_insert=True)
            self.log.debug("new image from remote %s", str(image))

    async def save_layer_at_node(self, layer: DockerLayer, node: Node):
        """Save a layer from a node into db"""
        try:
            layer_ = DockerLayer.get(DockerLayer.digest == layer.digest)
            layer_.set_available_at(node.uuid.hex) # type: ignore
            layer_.save()
            self.log.debug("update existing layer %s, now available on new node: %s",
                           layer.digest, node.uuid.hex) # type: ignore
        except DockerLayer.DoesNotExist:
            layer.available_at = [node.uuid.hex] # type: ignore
            layer.save(force_insert=True)
            self.log.debug("new layer from remote %s", str(layer))

    async def fetch_images_from_peer(self, peer: Peer):
        """fetch image list from the node and update local db"""

        images = await peer.client.get_images()
        self.log.debug("received image list from peer")

        for image_data in images:
            # discard `id` sent from remote
            image_data.pop('id', None)
            image = DockerImage.from_dict(image_data)
            await self.save_image_at_node(image, peer.node)

    async def fetch_layers_from_peer(self, peer: Peer):
        """fetch layer list from the node and update local db"""

        layers = await peer.client.get_layers()
        self.log.debug("received layer list from peer")

        for layer_data in layers:
            # discard `id` sent from remote
            layer_data.pop('id', None)
            layer = DockerLayer.from_dict(layer_data)
            await self.save_layer_at_node(layer, peer.node)

    async def daemon_error(self, error: str):
        """
        Daemon error emitter.
        Args:
            error (str): error message

        """
        # This will be converted to something like
        #   daemon.plugins['docker'].setReady(false)
        # in the future; will we in docker plugin code.
        self.log.error("docker connection error: %s", error, exc_info=True)
        self.last_error = error
        self.status = 'error'

        # re-schedule
        self.log.debug("sleeping 10 seconds before retrying")
        await asyncio.sleep(10)
        self.probe_task = self.loop.create_task(self.probe_daemon())
        self.log.debug("re-scheduled probe_daemon")

    async def daemon_lost(self):
        """
        Daemon lost emitter.
        """
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

                self.log.debug("existing image..%s", image_data)
                await self.save_image(image_data['Id'], skip_updates=True)

            # This will be converted to something like
            #   daemon.plugins['docker'].setReady(true)
            # in the future; will we in docker plugin code.
            self.history.update('init')
            self.status = 'ready'

            # Do not block on this
            self.probe_task = self.loop.create_task(self.listen_daemon_events())

        except Exception as err:  # pylint: disable=broad-except
            await self.daemon_error(err)

    async def listen_daemon_events(self):
        """
        Subscribes aiodocker events channel and logs them.
        If docker daemon is unavailable calls deamon_lost method
        to emit the lost event.
        """

        new_image_events = ['pull', 'load', 'tag']
        remove_image_events = ['untag']

        try:
            # await until docker is unavailable
            self.log.debug("subscribing to docker events for further changes")
            subscriber = self.aiodocker.events.subscribe()
            while True:
                event = await subscriber.get()
                if event is None:
                    break

                # log the event
                self.log.debug("docker event: %s[%s] %s",
                               event['Action'], event['Type'], event.get('id', 'event has no id'))

                # handle new image events
                if event['Type'] == 'image' and event['Action'] in new_image_events:
                    await self.save_image(event['id'])

                # handle delete existing image events
                if event['Type'] == 'image' and event['Action'] in remove_image_events:
                    await self.delete_image(event['id'])

            await self.daemon_lost()
        except Exception as err:  # pylint: disable=broad-except
            await self.daemon_error(str(err))

    async def new_image_saved(self, image_id: str):
        """placeholder method for new_image_saved event"""
        self.log.debug("a new image reported by docker deamon registered...: %s", image_id)

    async def existing_image_deleted(self, image_id: str):
        """placeholder method for existing_image_deleted event"""
        self.log.debug("an existing image and its layers deleted...: %s", image_id)

    async def delete_image(self, image_id: str):
        """
        Unset available image, delete it if no node remains

        Args:
            image_id (str): image identifier

        """
        image_data = await self.aiodocker.images.get(name=image_id)
        image = DockerImage.get(DockerImage.hash_id == image_data['Id'])
        image.unset_available_at(self.node.uuid.hex)
        if image.available_at:
            image.save()
        else:
            image.delete()

        # we do not handle deleting layers yet, not sure if they are
        # shared and needed by other images
        # code remains here for further interests. see PR #114 of rsnc
        #
        # try:
        #     self.log.debug("Layer list: %s", image_data['RootFS']['Layers'])
        #     layers = await self.util.get_image_layers(image_data['RootFS']['Layers'])
        #     for layer in layers:
        #         layer.unset_available_at(self.node.uuid.hex)
        #         if layer.available_at:
        #             layer.save()
        #         else:
        #             layer.delete()
        # except DockerUtil.CannotFindLayerMappingError:
        #     self.log.debug("Unexpected error, layers of image %s could not found..",
        #                    image_data['Id'])

        self.emit('docker_daemon.existing_image_deleted', image.hash_id)

    async def save_image(self, image_id: str, skip_updates: bool = False):
        """
        Save existing image and layers identified by image_id to database.

        Args:
            image_id (str): image identifier

        """

        image_data = await self.aiodocker.images.get(name=image_id)
        image = DockerImage.from_dict(image_data, dialect="docker")
        image_exists_in_db = False

        try:
            image_ = DockerImage.get(DockerImage.hash_id == image_data['Id'])
            old_available_at = image_.available_at
            image_.update_using_obj(image)
            image = image_
            image.available_at = old_available_at
            image_exists_in_db = True
            self.log.debug("image record updated.. %s \n\n", image.to_dict(dialect="docker"))

        except DockerImage.DoesNotExist:
            self.log.debug("not an existing one, creating a new record..")

        try:
            layers = await self.util.get_image_layers(image_data['RootFS']['Layers'])
            image.layers = [layer.digest for layer in layers] # type: ignore

            for layer in layers:
                layer.set_available_at(self.node.uuid.hex)
                layer.save()
                self.log.debug("image layers updated, record updated.. %s \n\n", layer.to_dict())

        except DockerUtil.CannotFindLayerMappingError:
            self.log.debug("Unexpected error, layers of image %s could not found..",
                           image_data['Id'])

        self.log.debug("set availability and save image %s \n %s \n\n",
                       self.node.uuid.hex, image.to_dict(dialect="docker"))

        image.set_available_at(self.node.uuid.hex)
        image.save(force_insert=not image_exists_in_db)

        if not skip_updates:
            self.history.update('new_image={}'.format(image.hash_id))
        self.emit('docker_daemon.new_image_saved', image.hash_id)
