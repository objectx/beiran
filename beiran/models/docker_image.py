"""
Module for DockerImage Model
"""
import uuid
from peewee import IntegerField, CharField, UUIDField
from beiran.models.base import BaseModel, JSONStringField

# {'Containers': -1, 'Created': 1488573174, 'Id': 'sha256:8914de95a28d740add2b8e1c952c9d238dd968ce8e7794e47233cbd7bbe934a4', 'Labels': None, 'ParentId': '', 'RepoDigests': ['alpine@sha256:99588bc8883c955c157d18fc3eaa4a3c1400c223e6c7cabca5f600a3e9f8d5cd', 'registry.rancher.caaspoc.aws.kddi.com/furkan/project1@sha256:9d7abc298e586b1f107971c67e00d89276033f0282b8a109b76f50dba7116533'], 'RepoTags': ['alpine:edge', 'registry.rancher.caaspoc.aws.kddi.com/furkan/project1:edge'], 'SharedSize': -1, 'Size': 3996004, 'VirtualSize': 3996004}


class DockerImage(BaseModel):
    """DockerImage"""

    created_at = IntegerField()
    hash_id = CharField(max_length=128)
    parent_hash_id = CharField(max_length=128,null=True)
    size = IntegerField()
    tags = JSONStringField(default=list) # ["tag1", "tag2"]
    data = JSONStringField(null=True)
    available_at = JSONStringField(default=list) # [ "node1", "node2" ]

    @classmethod
    def from_dict(cls, _dict, format="api"):
        if format == "docker":
            new_dict = {}

            new_dict['created_at'] = _dict['Created']
            new_dict['hash_id'] = _dict['Id']
            new_dict['parent_hash_id'] = _dict['ParentId'] if _dict['ParentId'] != '' else None
            new_dict['tags'] = _dict['RepoTags']
            new_dict['size'] = _dict['Size']
            new_dict['data'] = dict(_dict)

        return super().from_dict(new_dict)
