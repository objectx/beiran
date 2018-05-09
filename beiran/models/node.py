"""
Module for Node Data Model
"""
import uuid
from peewee import IntegerField, CharField, UUIDField
from beiran.models.base import BaseModel, JSONStringField

# Proposed new model for replacing address and port info in Node model
# This will fix discovering same node over several networks, etc.
# This will also allow us to track manually added nodes
#
# class PeerConnection(BaseModel):
#     uuid = UUIDField(null=True)
#     transport = CharField(max_length=15)
#     address = CharField(max_length=255)
#     last_seen_at = IntegerField()
#     discovery_method = CharField(32)
#     config = JSONStringField()  # { "auto-connect": true } ?


class Node(BaseModel):
    """Node is a member of Beiran Cluster"""

    uuid = UUIDField(primary_key=True)
    hostname = CharField(max_length=100)
    ip_address = CharField(max_length=15)  # dotted-decimal
    ip_address_6 = CharField(max_length=39, null=True)  # hexadecimal
    port = IntegerField()
    os_type = CharField(max_length=20)  # linux, win,
    os_version = CharField(max_length=255)  # os and version ubuntu 14.04 or output of `uname -a`
    architecture = CharField(max_length=20)  # x86_64
    beiran_version = CharField(max_length=10)  # beiran daemon version of node
    beiran_service_port = IntegerField()
    docker = JSONStringField(null=True)  # dump all data from docker_client.info()
    status = CharField(max_length=32, default='new')

    def __str__(self):
        fmt = "Node: {hostname}, Address: {ip}:{port}, UUID: {uuid}"
        return fmt.format(hostname=self.hostname,
                          ip=self.ip_address,
                          port=self.port,
                          uuid=self.uuid)

    @classmethod
    def from_dict(cls, _dict, **kwargs):
        _dict['uuid'] = uuid.UUID(_dict['uuid'])
        return super().from_dict(_dict, **kwargs)

    def to_dict(self, **kwargs):
        _dict = super().to_dict(**kwargs)
        _dict['uuid'] = self.uuid.hex # pylint: disable=no-member
        if 'dialect' in kwargs and kwargs['dialect'] == 'api':
            _dict.pop('status')
        return _dict

    def __repr__(self):
        return self.__str__()

    @property
    def docker_version(self):
        """Docker version"""
        return self.docker['ServerVersion'] if self.docker else None

    @property
    def docker_storage_driver(self):
        """Docker storage driver"""
        return self.docker['Driver'] if self.docker else None

    @property
    def docker_root_dir(self):
        """Docker root directory"""
        return self.docker['DockerRootDir'] if self.docker else None
