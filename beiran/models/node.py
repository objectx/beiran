"""
Module for Node Data Model
"""
from peewee import IntegerField, CharField, UUIDField
from beiran.models.base import BaseModel, JSONStringField
import uuid

class Node(BaseModel):
    """Node is a member of Beiran Cluster"""

    uuid = UUIDField(primary_key=True)
    hostname = CharField(max_length=100)
    ip_address = CharField(max_length=15)  # dotted-decimal
    ip_address_6 = CharField(max_length=39, null=True)  # hexadecimal
    os_type = CharField(max_length=20)  # linux, win,
    os_version = CharField(max_length=255)  # os and version ubuntu 14.04 or output of `uname -a`
    architecture = CharField(max_length=20)  # x86_64
    beiran_version = CharField(max_length=10)  # beiran daemon version of node
    beiran_service_port = IntegerField()

    # docker plugin keys
    # docker_version = CharField(max_length=20)
    # docker_storage_driver = CharField(max_length=50)  # overlay2, aufs
    # docker_root_dir = CharField(default='/var/lib/docker')
    docker = JSONStringField(null=True)  # dump all data from docker_client.info()

    def __str__(self):
        return "Node: {hostname}, Address: {ip}, UUID: {uuid}".format(hostname=self.hostname,
                                                                      ip=self.ip_address,
                                                                      uuid=self.uuid)

    @classmethod
    def from_dict(cls, _dict):
        _dict['uuid'] = uuid.UUID(_dict['uuid'])
        return super().from_dict(_dict)

    def __repr__(self):
        return self.__str__()

    def to_dict(self, **kwargs):
        _dict = super().to_dict(**kwargs)
        _dict['uuid'] = self.uuid.hex
        return _dict

    @property
    def docker_version(self):
        if self.docker is None:
            return None
        return self.docker['ServerVersion']

    @property
    def docker_storage_driver(self):
        if self.docker is None:
            return None
        return self.docker['Driver']

    @property
    def docker_root_dir(self):
        if self.docker is None:
            return None
        return self.docker['DockerRootDir']
