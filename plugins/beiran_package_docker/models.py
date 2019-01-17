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
Module for DockerLayer and DockerImage Model
"""
from datetime import datetime

from peewee import IntegerField, CharField, BooleanField, SQL
from beiran.models.base import BaseModel, JSONStringField
from beiran.daemon.common import Services

from .image_ref import add_default_tag, is_digest, add_idpref

class CommonDockerObjectFunctions:
    """..."""

    available_at = JSONStringField(default=list)

    def set_available_at(self, uuid_hex: str):
        """add uuid of node to available_at list"""
        if uuid_hex in self.available_at:
            return
        self.available_at.append(uuid_hex)

    def unset_available_at(self, uuid_hex: str):
        """remove uuid of node from available_at list"""
        if uuid_hex not in self.available_at:
            return
        self.available_at = [n for n in self.available_at if n != uuid_hex] # type: ignore


class DockerImage(BaseModel, CommonDockerObjectFunctions):
    """DockerImage"""

    created_at = IntegerField()
    hash_id = CharField(max_length=128, primary_key=True)
    parent_hash_id = CharField(max_length=128, null=True)
    size = IntegerField(null=True)
    tags = JSONStringField(default=list)
    data = JSONStringField(null=True)
    manifest = JSONStringField(null=True)
    layers = JSONStringField(default=list)
    available_at = JSONStringField(default=list)
    repo_digests = JSONStringField(default=list)
    config = JSONStringField(default=list)
    download_progress = JSONStringField(null=True)

    has_not_found_layers = BooleanField(default=False)
    has_unknown_layers = BooleanField(default=False)

    @classmethod
    def from_dict(cls, _dict: dict, **kwargs) -> "DockerImage":
        if 'availability' in _dict:
            del _dict['availability']

        if 'dialect' in kwargs and kwargs['dialect'] == "docker":
            new_dict = {}

            # be sure it is timestamp
            # aiodocker images.list returns timestamp,
            # since images.get returns something like iso 8601 with 8 digits of microseconds,
            # unfortunately python supports only 6 digits.
            if not isinstance(_dict['Created'], int):
                time_parts = _dict['Created'].split('.')
                created = datetime.strptime(time_parts[0], "%Y-%m-%dT%H:%M:%S")
                _dict['Created'] = int(created.timestamp())

            new_dict['created_at'] = _dict['Created']
            new_dict['hash_id'] = _dict['Id']
            # aiodocker images.list returns ParentId, since images.get returns Parent
            new_dict['parent_hash_id'] = _dict.get('ParentId') or _dict.get('Parent') or None
            new_dict['tags'] = _dict['RepoTags']
            new_dict['repo_digests'] = _dict['RepoDigests']
            new_dict['size'] = _dict['Size']
            new_dict['data'] = dict(_dict)

            _dict = new_dict
        elif 'dialect' in kwargs and kwargs['dialect'] == "manifest":
            new_dict = {}

            # this param is included in manifest response header as 'Docker-Content-Digest'
            # so you need to add it to the dictionary produced from manifest response body
            new_dict['hash_id'] = _dict['hashid']

            new_dict['tags'] = [_dict['tag']]
            new_dict['repo_digests'] = [_dict['repo_digests']]
            new_dict['manifest'] = dict(_dict)

            new_layer_list = []
            for layer in _dict['fsLayers']:
                new_layer_list.append(layer['blobSum'])
            new_dict['layers'] = new_layer_list

            _dict = new_dict
        return super().from_dict(_dict, **kwargs)

    def to_dict(self, **kwargs):
        _dict = super().to_dict(**kwargs)
        if 'dialect' in kwargs and kwargs['dialect'] == 'api':
            del _dict['data']
            del _dict['has_not_found_layers']
            del _dict['has_unknown_layers']

        available_at = _dict['available_at']
        local = Services.daemon.nodes.local_node.uuid.hex
        if not available_at:
            _dict['availability'] = 'unavailable'
        elif not local in available_at:
            _dict['availability'] = 'available'
        else:
            _dict['availability'] = 'local'

        return _dict

    @classmethod
    async def get_available_nodes(cls, image_identifier: str) -> list:
        """

        Args:
            image_identifier: image tag or digest

        Returns:
            (list) list of available nodes of image object

        """
        try:
            image = cls.get_image_data(image_identifier)
        except DockerImage.DoesNotExist:
            return []

        return image.available_at


    @classmethod
    def get_image_data(cls, image_identifier: str) -> "DockerImage":
        """
        get a image data. search with `hash_id`, `repo_digests` or `tags`
        """
        if is_digest(image_identifier):
            # search with digest
            image = cls.get(SQL('repo_digests LIKE \'%%"%s"%%\'' % image_identifier))

        else:
            # search with tag
            try:
                image = cls.get(SQL('tags LIKE \'%%"%s"%%\'' % add_default_tag(image_identifier)))

            except DockerImage.DoesNotExist:
                # search with hash_id
                images = cls.select().where((SQL('hash_id LIKE \'%s%%\'' %
                                                 add_idpref(image_identifier))))

                # if found 0 or a few images
                if len(images) != 1:
                    raise DockerImage.DoesNotExist()

                image = images.first()

        return image


class DockerLayer(BaseModel, CommonDockerObjectFunctions):
    """DockerLayer"""

    digest = CharField(max_length=128, null=True)
    diff_id = CharField(max_length=128)
    chain_id = CharField(max_length=128)
    size = IntegerField() # the size difference of the top layer from parent layer
    available_at = JSONStringField(default=list)
    download_progress = JSONStringField(null=True)

    cache_path = CharField(null=True, default=None) # .tar file in cache dir
    docker_path = CharField(null=True) # layer's directory under /var/lib/docker

MODEL_LIST = [DockerImage, DockerLayer]  # we may discover dynamically
