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
        'cache_dir': config.cache_dir + '/container'
    }

    async def init(self):
        self.util = ContainerUtil(cache_dir=self.config["cache_dir"],
                                  logger=self.log, local_node=self.node)
        self.model_list = MODEL_LIST
        self.history = History() # type: History

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

    async def fetch_images_from_peer(self, peer: Peer):
        """fetch image list from the node and update local db"""

        images = await peer.client.get_images()
        self.log.debug("received image list from peer")

        for image_data in images:
            # discard `id` sent from remote
            image_data.pop('id', None)
            image = ContainerImage.from_dict(image_data)
            await self.save_image_at_node(image, peer.node)

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

    @staticmethod
    async def delete_layers(diff_id_list: list)-> None:
        """
        Unset available layer, delete it if no image refers it
        """
        layers = ContainerLayer.select() \
                            .where(ContainerLayer.diff_id.in_(diff_id_list))
        for layer in layers:
            if not layer.available_at:
                layer.delete_instance()

    @staticmethod
    async def tag_image(image_id: str, tag: str):
        """
        Tag an image existing in database. If already same tag exists,
        move it from old one to new one.
        """
        target = ContainerImage.get_image_data(image_id)
        if tag not in target.tags:
            target.tags = [tag] # type: ignore
            target.save()

        images = ContainerImage.select().where((SQL('tags LIKE \'%%"%s"%%\'' % tag)))

        for image in images:
            if image.hash_id == target.hash_id:
                continue

            image.tags.remove(tag)
            image.save()
