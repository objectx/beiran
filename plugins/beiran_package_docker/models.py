# TODO : Move docker models here
# TODO : Support plugin models on daemon
"""
Module for DockerLayer and DockerImage Model
"""
from datetime import datetime
from peewee import IntegerField, CharField, BooleanField, SQL
from beiran.models.base import BaseModel, JSONStringField
from beirand.common import Services


class CommonDockerObjectFunctions:
    """..."""

    available_at = JSONStringField(default=list)

    def set_available_at(self, uuid_hex):
        """add uuid of node to available_at list"""
        if uuid_hex in self.available_at:
            return
        self.available_at.append(uuid_hex)

    def unset_available_at(self, uuid_hex):
        """remove uuid of node from available_at list"""
        if uuid_hex not in self.available_at:
            return
        self.available_at = [n for n in self.available_at if n != uuid_hex]


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
    username = CharField()

    has_not_found_layers = BooleanField(default=False)
    has_unknown_layers = BooleanField(default=False)

    @classmethod
    def from_dict(cls, _dict, **kwargs):
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
            new_dict['username'] = _dict["ContainerConfig"]["User"]
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
            new_dict['username'] = new_dict['username']
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
    async def get_available_nodes_by_tag(cls, image_name):
        """

        Args:
            image_name: image name

        Returns:
            (list) list of available nodes of image object

        """

        # image must have a tag, default is latest
        try:
            image_name, tag = image_name.split(":")
        except ValueError:
            tag = "latest"

        image_tag = "{image_name}:{tag}".format(image_name=image_name, tag=tag)

        try:
            image = cls.select().where(
                SQL('tags LIKE \'%%"%s"%%\'' % image_tag)).get()
            return image.available_at
        except DockerImage.DoesNotExist:
            pass


class DockerLayer(BaseModel, CommonDockerObjectFunctions):
    """DockerLayer"""

    digest = CharField(max_length=128)
    local_diff_id = CharField(max_length=128)
    layerdb_diff_id = CharField(max_length=128)
    size = IntegerField()
    available_at = JSONStringField(default=list)


MODEL_LIST = [DockerImage, DockerLayer]  # we may discover dynamically
