from beirand.models import BaseModel
from playhouse.shortcuts import model_to_dict
from peewee import IntegerField, CharField, UUIDField

nodes = {}


class Node(BaseModel):
    """Node is a member of Beiran Cluster"""

    uuid = UUIDField(primary_key=True)
    hostname = CharField(max_length=100)
    ip_address = CharField(max_length=15)  # dotted-decimal
    ip_address_6 = CharField(max_length=39)  # hexadecimal
    os_type = CharField(max_length=20)  # linux, win,
    os_version = CharField(max_length=255)  # os and version ubuntu 14.04 or output of `uname -a`
    architecture = CharField(max_length=20)  # x86_64
    beiran_version = CharField(max_length=10)  # beiran daemon version of node
    beiran_service_port = IntegerField()

    def __str__(self):
        return "Node: {hostname}, Address: {ip}".format(hostname=self.hostname, ip=self.ip_address)

    def __repr__(self):
        return self.__str__()

    def remove_node(self):
        """Remove node from nodes dict"""
        nodes.pop(self.uuid)

    def append_node(self):
        """Append node into nodes dict"""
        nodes.update({self.uuid: model_to_dict(self)})
