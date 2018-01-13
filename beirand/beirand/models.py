"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

from peewee import IntegerField, CharField, DateField, ForeignKeyField, UUIDField
from peewee import Model, SqliteDatabase

db = SqliteDatabase('beirand.db')


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        database = db


class Node(BaseModel):
    """Node is a member of Beiran Cluster"""

    uuid = UUIDField()
    hostname = CharField(max_length=100)
    ip_address_v4 = CharField(max_length=15)  # dotted-decimal
    ip_address_v6 = CharField(max_length=39)  # hexadecimal
    os_type = CharField(max_length=20)  # linux, win,
    os_version = CharField(max_length=255)  # os and version ubuntu 14.04 or output of `uname -a`
    architecture = CharField(max_length=20)  # x86_64
    beiran_version = CharField(max_length=10)  # beiran daemon version of node
    beiran_service_port = IntegerField()


class DockerDaemon(BaseModel):
    """
    Docker Daemon specific data of Nodes
    """
    node = ForeignKeyField(Node)
    docker_version = CharField(max_length=20)
    storage_driver = CharField(max_length=50)  # overlay2, aufs
    docker_root_dir = CharField(default='/var/lib/docker')
