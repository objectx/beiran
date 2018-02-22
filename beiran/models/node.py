"""
Module for Node Data Model
"""
from peewee import IntegerField, CharField, UUIDField
from beiran.models.base import BaseModel


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

    def __str__(self):
        return "Node: {hostname}, Address: {ip}, UUID: {uuid}".format(hostname=self.hostname,
                                                                      ip=self.ip_address,
                                                                      uuid=self.uuid)

    def __repr__(self):
        return self.__str__()
