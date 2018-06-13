"""
Module for Node Data Model
"""
import uuid
from peewee import IntegerField, CharField, UUIDField
from beiran.models.base import BaseModel, JSONStringField


# Proposed new model for replacing address and port info in Node model
# This will fix discovering same node over several networks, etc.
# This will also allow us to track manually added nodes
class PeerConnection(BaseModel):
    """Data model for connection details of Nodes"""
    uuid = UUIDField(null=True)
    transport = CharField(max_length=15)
    address = CharField(max_length=255)
    last_seen_at = IntegerField()
    discovery_method = CharField(32)
    config = JSONStringField()  # { "auto-connect": true } ?


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
    version = CharField(max_length=10)  # beiran daemon version of node
    status = CharField(max_length=32, default='new')
    last_sync_version = IntegerField()

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

    @property
    def url(self):
        """Generates node advertise url using ip_address, port and uuid properties"""
        return "http://{}:{}#{}".format(self.ip_address, self.port, self.uuid.hex) # pylint: disable=no-member

    @property
    def url_without_uuid(self):
        """Generates node advertise url using ip_address, port properties"""
        return "http://{}:{}".format(self.ip_address, self.port)

    def get_connections(self):
        """Get a list of connection details of node ordered by last seen time"""
        return [
            conn for conn in PeerConnection.select().order_by(
                PeerConnection.last_seen_at.desc()
            ).where(
                PeerConnection.uuid == self.uuid
            )
        ]

    def __repr__(self):
        return self.__str__()
