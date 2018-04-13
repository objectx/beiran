"""
Module for DockerImage Model
"""
from peewee import IntegerField, CharField, BooleanField
from beiran.models.base import BaseModel, JSONStringField

class DockerImage(BaseModel):
    """DockerImage"""

    created_at = IntegerField()
    hash_id = CharField(max_length=128)
    parent_hash_id = CharField(max_length=128, null=True)
    size = IntegerField()
    tags = JSONStringField(default=list)
    data = JSONStringField(null=True)
    available_at = JSONStringField(default=list)
    layers = JSONStringField(default=list)

    has_not_found_layers = BooleanField(default=False)
    has_unknown_layers = BooleanField(default=False)

    @classmethod
    def from_dict(cls, _dict, **kwargs):
        if 'dialect' in kwargs and kwargs['dialect'] == "docker":
            new_dict = {}

            new_dict['created_at'] = _dict['Created']
            new_dict['hash_id'] = _dict['Id']
            new_dict['parent_hash_id'] = _dict['ParentId'] if _dict['ParentId'] != '' else None
            new_dict['tags'] = _dict['RepoTags']
            new_dict['size'] = _dict['Size']
            new_dict['data'] = dict(_dict)

            _dict = new_dict
        return super().from_dict(_dict, **kwargs)

    def set_available_at(self, uuid_hex):
        if uuid_hex in self.available_at:
            return
        self.available_at.append(uuid_hex)

    def unset_available_at(self, uuid_hex):
        if uuid_hex not in self.available_at:
            return
        self.available_at = [n for n in self.available_at if n != uuid_hex]
