from beirand.models import BaseModel
from beirand.models import Node
from peewee import CharField, ForeignKeyField


class DockerDaemon(BaseModel):
    """
    Docker Daemon specific data of Nodes
    """
    node = ForeignKeyField(Node)
    docker_version = CharField(max_length=20)
    storage_driver = CharField(max_length=50)  # overlay2, aufs
    docker_root_dir = CharField(default='/var/lib/docker')
