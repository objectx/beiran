"""
Module for DockerLayer Model
"""
from peewee import IntegerField, CharField
from beiran.models.base import BaseModel, JSONStringField

class DockerLayer(BaseModel):
    """DockerLayer"""

    digest = CharField(max_length=128)
    local_diff_id = CharField(max_length=128)
    layerdb_diff_id = CharField(max_length=128)
    size = IntegerField()
    available_at = JSONStringField(default=list)
