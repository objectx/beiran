"""
Docker packaging plugin
"""

import asyncio
import docker
from aiodocker import Docker
from aiodocker.exceptions import DockerError
from peewee import SQL

from beiran.config import config
from beiran.plugin import BasePackagePlugin, History
from beiran.models import Node
from beiran.daemon.peer import Peer

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

    def __init__(self, config: dict) -> None: # pylint: disable=redefined-outer-name
        super().__init__({
            "storage": "/var/lib/docker",
            **config
        })

    async def init(self):
        self.aiodocker = Docker()
        self.util = DockerUtil(cache_dir=config.cache_dir + '/docker',
                               storage=self.config["storage"], aiodocker=self.aiodocker,
                               local_node=self.node)
        self.docker = docker.from_env()
        self.docker_lc = docker.APIClient()
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
        await DockerUtil.reset_docker_info_of_node(peer.node.uuid.hex)

        await self.fetch_images_from_peer(peer)
        await self.fetch_layers_from_peer(peer)

    async def save_image_at_node(self, image: DockerImage, node: Node):
        """Save an image from a node into db"""
        try:
            image_ = DockerImage.get(DockerImage.hash_id == image.hash_id)
            image_.set_available_at(node.uuid.hex)
            image_.save()
            self.log.debug("update existing image %s, now available on new node: %s",
                           image.hash_id, node.uuid.hex)
        except DockerImage.DoesNotExist:
            image.available_at = [node.uuid.hex] # type: ignore
            image.save(force_insert=True)
            self.log.debug("new image from remote %s", str(image))

    async def save_layer_at_node(self, layer: DockerLayer, node: Node):
        """Save a layer from a node into db"""
        try:
            layer_ = DockerLayer.get(DockerLayer.diff_id == layer.diff_id)
            layer_.set_available_at(node.uuid.hex)
            layer_.save()
            self.log.debug("update existing layer %s, now available on new node: %s",
                           layer.digest, node.uuid.hex)
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
            image_list = await self.aiodocker.images.list(all=1)
            not_intermediates = await self.aiodocker.images.list()

            for image_data in image_list:
                self.log.debug("existing image..%s", image_data)

                if image_data in not_intermediates:
                    await self.save_image(image_data['Id'], skip_updates=True)
                else:
                    await self.save_image(image_data['Id'], skip_updates=True,
                                          skip_updating_layer=True)

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

        new_image_events = ['pull', 'load', 'tag', 'commit', 'import']
        remove_image_events = ['delete']

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

                # handle commit container (and build new image)
                if event['Type'] == 'container' and event['Action'] in new_image_events:
                    await self.save_image(event['Actor']['Attributes']['imageID'])

                # handle new image events
                if event['Type'] == 'image' and event['Action'] in new_image_events:
                    await self.save_image(event['id'])

                # handle untagging image
                if event['Type'] == 'image' and event['Action'] == 'untag':
                    await self.untag_image(event['id'])

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
        # image_data = await self.aiodocker.images.get(name=image_id)
        image = DockerImage.get(DockerImage.hash_id == image_id)
        image.unset_available_at(self.node.uuid.hex)

        # unset layers
        await self.delete_layer(image.layers)
        if image.available_at:
            image.save()
        else:
            image.delete_instance()
        self.history.update('removed_image={}'.format(image.hash_id))

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

    async def delete_layer(self, diff_id_list: list)-> None:
        """
        Unset available layer
        """
        layers = DockerLayer.select() \
                            .where(DockerLayer.diff_id.in_(diff_id_list)) \
                            .where((SQL('available_at LIKE \'%%"%s"%%\'' % self.node.uuid.hex)))

        for layer in layers:
            layer.unset_available_at(self.node.uuid.hex)
            layer.docker_path = None
            layer.save()


    async def save_image(self, image_id: str, skip_updates: bool = False,
                         skip_updating_layer: bool = False):
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

        layers = await self.util.get_image_layers(image_data['RootFS']['Layers'])
        image.layers = [layer.diff_id for layer in layers] # type: ignore

        # skip verbose updates of records
        if not skip_updating_layer:
            for layer in layers:
                layer.set_available_at(self.node.uuid.hex)
                layer.save()
                self.log.debug("image layers updated, record updated.. %s \n\n", layer.to_dict())

        self.log.debug("set availability and save image %s \n %s \n\n",
                       self.node.uuid.hex, image.to_dict(dialect="docker"))

        image.set_available_at(self.node.uuid.hex)

        # save config
        config_path = self.util.storage + '/image/overlay2/imagedb/content/sha256/' \
                                        + image.hash_id.replace('sha256:', '')
        with open(config_path)as file:
            image.config = file.read()

        image.save(force_insert=not image_exists_in_db)

        if not skip_updates:
            self.history.update('new_image={}'.format(image.hash_id))
        self.emit('docker_daemon.new_image_saved', image.hash_id)

        if image_data['RepoTags']:
            await self.tag_image(image_id, image_data['RepoTags'][0])

    async def tag_image(self, image_identifier: str, tag: str):
        """
        Tag an image existing in database. If already same tag exists,
        move it from old one to new one.
        """
        target = DockerImage.get_image_data(image_identifier)
        if tag not in target.tags:
            target.tags = [tag] # type: ignore
            target.save()

        images = DockerImage.select().where((SQL('tags LIKE \'%%"%s"%%\'' % tag)))

        for image in images:
            if image.hash_id == target.hash_id:
                continue

            image.tags.remove(tag)
            image.save()

    async def untag_image(self, image_identifier: str):
        """
        Remove a tag from an image.
        """
        # aiodocker.events.subscribe() can't get information about what tag will be removed...
        try:
            image_data = await self.aiodocker.images.get(name=image_identifier)
            image = DockerImage.get(DockerImage.hash_id == image_data['Id'])
            image.tags = image_data['RepoTags']
            image.save()
        except DockerError:
            # if the image was deleted by `docker rmi`, no image information was found
            pass
