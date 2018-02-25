"""
Module for Docker Daemon Data Model
"""
from peewee import CharField, ForeignKeyField
from beiran.models.base import BaseModel, JSONStringField
from beiran.models.node import Node


class DockerDaemon(BaseModel):
    """
    Docker Daemon specific data of Nodes
    """
    node = ForeignKeyField(Node)
    docker_version = CharField(max_length=20)
    storage_driver = CharField(max_length=50)  # overlay2, aufs
    docker_root_dir = CharField(default='/var/lib/docker')
    details = JSONStringField()  # dump all data from docker_client.info()
