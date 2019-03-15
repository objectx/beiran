# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Container packaging plugin
"""

import os
from peewee import SQL

from beiran.config import config
from beiran.plugin import BasePackagePlugin, History
from beiran.models import Node
from beiran.daemon.peer import Peer

from beiran_package_container.models import ContainerImage, ContainerLayer
from beiran_package_container.models import MODEL_LIST
from beiran_package_container.util import ContainerUtil


PLUGIN_NAME = 'container'
PLUGIN_TYPE = 'package'


# pylint: disable=attribute-defined-outside-init
class ContainerPackaging(BasePackagePlugin):  # pylint: disable=too-many-instance-attributes
    """Container support for Beiran"""
    DEFAULTS = {
        'storage': '/var/lib/docker'
    }

    # def __init__(self, plugin_config: dict) -> None:
    #     super().__init__(plugin_config)

    def set_dynamic_defaults(self):
        """Set dynamic configuration value like using ``run_dir``"""
        self.config.setdefault('cache_dir', config.cache_dir + '/docker')
        self.config.setdefault('tar_split_path', os.path.dirname(__file__) + '/tar-split')

    async def init(self):
        self.util = ContainerUtil(cache_dir=self.config["cache_dir"],
                                  storage=self.config["storage"],
                                  logger=self.log, local_node=self.node,
                                  tar_split_path=self.config['tar_split_path'])
        self.probe_task = None
        self.model_list = MODEL_LIST
        self.history = History() # type: History
        self.last_error = None

    async def sync(self, peer: Peer):
        await ContainerUtil.reset_docker_info_of_node(peer.node.uuid.hex)

        await self.fetch_images_from_peer(peer)
        await self.fetch_layers_from_peer(peer)

    async def save_image_at_node(self, image: ContainerImage, node: Node):
        """Save an image from a node into db"""
        try:
            image_ = ContainerImage.get(ContainerImage.hash_id == image.hash_id)
            image_.set_available_at(node.uuid.hex)
            image_.save()
            self.log.debug("update existing image %s, now available on new node: %s",
                           image.hash_id, node.uuid.hex)
        except ContainerImage.DoesNotExist:
            image.available_at = [node.uuid.hex] # type: ignore
            image.save(force_insert=True)
            self.log.debug("new image from remote %s", str(image))

    async def save_layer_at_node(self, layer: ContainerLayer, node: Node):
        """Save a layer from a node into db"""
        try:
            layer_ = ContainerLayer.get(ContainerLayer.diff_id == layer.diff_id)
            layer_.set_available_at(node.uuid.hex)
            self.save_local_paths(layer_)
            layer_.save()
            self.log.debug("update existing layer %s, now available on new node: %s",
                           layer.digest, node.uuid.hex)
        except ContainerLayer.DoesNotExist:
            layer.available_at = [node.uuid.hex] # type: ignore
            layer.local_image_refs = [] # type: ignore
            self.save_local_paths(layer)
            layer.save(force_insert=True)
            self.log.debug("new layer from remote %s", str(layer))

    def save_local_paths(self, layer: ContainerLayer):
        """Update 'cache_path' and 'cache_gz_path' and 'docker_path' with paths of local node"""
        try:
            docker_path = self.util.layerdir_path.format(
                layer_dir_name=self.util.get_cache_id_from_chain_id(layer.chain_id))

            if os.path.exists(docker_path):
                layer.docker_path = docker_path
            else:
                layer.docker_path = None

        except FileNotFoundError:
            layer.docker_path = None

        cache_path = self.util.get_layer_tar_file(layer.diff_id)
        if os.path.exists(cache_path):
            layer.cache_path = cache_path
        else:
            layer.cache_path = None

        if layer.digest:
            cache_gz_path = self.util.get_layer_gz_file(layer.digest)
            if os.path.exists(cache_gz_path):
                layer.cache_gz_path = cache_gz_path
            else:
                layer.cache_gz_path = None

    async def fetch_images_from_peer(self, peer: Peer):
        """fetch image list from the node and update local db"""

        images = await peer.client.get_images()
        self.log.debug("received image list from peer")

        for image_data in images:
            # discard `id` sent from remote
            image_data.pop('id', None)
            image = ContainerImage.from_dict(image_data)
            await self.save_image_at_node(image, peer.node)

    async def fetch_layers_from_peer(self, peer: Peer):
        """fetch layer list from the node and update local db"""

        layers = await peer.client.get_layers()
        self.log.debug("received layer list from peer")

        for layer_data in layers:
            # discard `id` sent from remote
            layer_data.pop('id', None)
            layer = ContainerLayer.from_dict(layer_data)
            await self.save_layer_at_node(layer, peer.node)

    async def unset_local_layers(self, diff_id_list: list, image_id: str)-> None:
        """
        Unset image_id from local_image_refs of layers
        """
        layers = ContainerLayer.select() \
                            .where(ContainerLayer.diff_id.in_(diff_id_list)) \
                            .where((SQL('available_at LIKE \'%%"%s"%%\'' % self.node.uuid.hex)))
        for layer in layers:
            layer.unset_local_image_refs(image_id)
            if not layer.local_image_refs:
                layer.unset_available_at(self.node.uuid.hex)
                layer.docker_path = None
            layer.save()

    async def delete_layers(self, diff_id_list: list)-> None:
        """
        Unset available layer, delete it if no image refers it
        """
        layers = ContainerLayer.select() \
                            .where(ContainerLayer.diff_id.in_(diff_id_list))
        for layer in layers:
            if not layer.available_at:
                layer.delete_instance()
