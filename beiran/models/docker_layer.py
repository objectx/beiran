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

    def set_available_at(self, uuid_hex):
        if uuid_hex in self.available_at:
            return
        self.available_at.append(uuid_hex)

    def unset_available_at(self, uuid_hex):
        if uuid_hex not in self.available_at:
            return
        self.available_at = [n for n in self.available_at if n != uuid_hex]
