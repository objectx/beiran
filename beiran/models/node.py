"""
Module for Node Data Model
"""
import uuid
import urllib
from datetime import datetime
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
    discovery_method = CharField(max_length=32, null=True)
    config = JSONStringField(null=True)  # { "auto-connect": true } ?

    @classmethod
    def add_or_update(cls, uuid, address, discovery=None, config=None):
        try:
            _self = cls.get(PeerConnection.uuid == uuid,
                            PeerConnection.address == address)
        except cls.DoesNotExist:
            _self = cls(uuid=uuid, address=address)

        _self.last_seen_at = int(datetime.now().timestamp())
        if config:
            _self.config = config
        if discovery:
            _self.discovery_method = discovery
        _self.transport, _, _, _, _ = cls.parse_address(address)
        _self.save()

    @staticmethod
    def parse_address(address):
        parsed = urllib.parse.urlparse(address)
        protocol = parsed.scheme.split('+')[1]
        transport = 'http' if protocol in ['http', 'https'] else 'tcp'
        fragment = parsed.fragment
        hostname = parsed.hostname
        port = parsed.port
        return transport, protocol, hostname, port, fragment


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

    def __init__(self, *args, **kwargs):
        self._address = None
        super().__init__(*args, **kwargs)

    def __str__(self):
        fmt = "Node: {hostname}, Address: {ip}:{port}, UUID: {uuid}"
        return fmt.format(hostname=self.hostname,
                          ip=self.ip_address,
                          port=self.port,
                          uuid=self.uuid)

    @classmethod
    def from_dict(cls, _dict, **kwargs):
        _dict['uuid'] = uuid.UUID(_dict['uuid'])
        node_address = _dict.pop('address', None)
        node = super().from_dict(_dict, **kwargs)
        node._address = node_address
        return node

    def to_dict(self, **kwargs):
        _dict = super().to_dict(**kwargs)
        _dict['uuid'] = self.uuid.hex # pylint: disable=no-member
        _dict['address'] = self.address
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

    def connections(self):
        return PeerConnection.select().order_by(
                PeerConnection.last_seen_at.desc()
            ).where(
                PeerConnection.uuid == self.uuid.hex
            )

    def get_connections(self):
        """Get a list of connection details of node ordered by last seen time"""
        return [
            conn for conn in self.connections()
        ]

    def get_latest_connection(self):
        return self.connections().get()

    def __repr__(self):
        return self.__str__()

    @property
    def address(self, force=False):
        if self._address and not force:
            return self._address
        return self.get_set_address()

    def get_set_address(self, address=None):
        if address:
            self._address = address
        else:
            latest_conn = self.get_latest_connection()
            self._address = latest_conn.address
        return self._address

    def save(self, force_insert=False, only=None):
        super().save(force_insert=force_insert, only=only)
        PeerConnection.add_or_update(
            uuid=self.uuid.hex,
            address=self.address
        )
