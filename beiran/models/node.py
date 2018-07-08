"""
Module for Node Data Model
"""
from uuid import UUID
import urllib
import re
from datetime import datetime
from peewee import IntegerField, CharField, UUIDField
from beiran.models.base import BaseModel, JSONStringField
from beiran.log import build_logger

logger = build_logger()


# Proposed new model for replacing address and port info in Node model
# This will fix discovering same node over several networks, etc.
# This will also allow us to track manually added nodes
class PeerAddress(BaseModel):
    """Data model for connection details of Nodes"""

    uuid = UUIDField(null=True)
    transport = CharField(max_length=15, default="http")
    address = CharField(max_length=255)
    last_seen_at = IntegerField(default=datetime.now().timestamp())
    discovery_method = CharField(max_length=32, null=True)
    config = JSONStringField(null=True)  # { "auto-connect": true } ?

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uuid = kwargs.pop('uuid', None)

        if uuid and isinstance(uuid, UUID):
            uuid = uuid.hex

        addr = kwargs.pop('address', None)
        host = kwargs.pop('host', None)
        path = kwargs.pop('path', None)
        port = kwargs.pop('port', None)
        protocol = kwargs.pop('protocol', None)
        unix_socket = kwargs.pop('socket', False)

        if addr:
            if not addr.startswith("beiran+"):
                addr = "beiran+{}".format(addr)
            self.is_valid = self.validate_address(addr)
            transport, protocol, host, path, port, _uuid, unix_socket = self.parse_address(addr)

        addr = self.build_node_address(host=host, port=port, uuid=uuid, path=path, protocol=protocol, socket=unix_socket)
        self.transport, self.protocol, self.host, self.path, self.port, _uuid, self.unix_socket = self.parse_address(addr)

        if _uuid:
            self.uuid = UUID(_uuid)

        self.address = addr

    def to_dict(self, **kwargs):
        _dict = super().to_dict(**kwargs)
        _dict['uuid'] = self.uuid.hex # pylint: disable=no-member
        _dict['host'] = self.host
        _dict['port'] = self.port
        _dict['protocol'] = self.protocol
        _dict['unix_socket'] = self.unix_socket
        _dict['path'] = self.path
        return _dict

    def from_dict(cls, _dict, **kwargs):
        _dict['uuid'] = UUID(_dict['uuid'])
        obj = super().from_dict(_dict, **kwargs)
        return obj

    @property
    def location(self):
        if not self.unix_socket:
            return "{}://{}:{}".format(self.protocol, self.host, self.port)
        else:
            return "{}+unix://{}".format(self.protocol, self.path)

    @staticmethod
    def validate_address(address):
        """
        Validate address

        Args:
            address (str): peer address

        Returns:
            (bool): True if address matches pattern, else False

        """
        url_pattern = re.compile(r'^(beiran)\+(https?|wss?)(?:\+(unix))?://([^#]+)(?:#(.+))?$',
                                 re.IGNORECASE)
        matched = url_pattern.match(address)
        if not matched:
            logger.error("Address is broken: %s", address)

        return matched

    def build_node_address(self, host, path=None, uuid=None, port=None, protocol=None, socket=False):
        """
        Build a node address with given host, port, protocol and uuid

        Args:
            host: hostname
            uuid: uuid of node
            path: address path
            port: service port
            protocol: protocol, default http
            socket: is unix socket? default False

        Returns:

        """
        port = ":{}".format(port or 8888)
        protocol = protocol or 'http'
        unix_socket = "+unix" if socket else ""
        if unix_socket:
            unix_socket = "+unix"
            port = ""
            hostname = path
        else:
            hostname = host

        ADDRESS_FORMAT = "beiran+{protocol}{unix_socket}://{hostname}{port}#{uuid}"
        address = ADDRESS_FORMAT.format(hostname=hostname,
                                             port=port,
                                             protocol=protocol,
                                             unix_socket=unix_socket,
                                             uuid=uuid)
        if not uuid:
            address = address.split('#')[0]

        return address

    @classmethod
    def add_or_update(cls, uuid, address, discovery=None, config=None):
        try:
            _self = cls.get(PeerAddress.uuid == uuid,
                            PeerAddress.address == address)
        except cls.DoesNotExist:
            _self = cls(uuid=uuid, address=address)

        _self.last_seen_at = int(datetime.now().timestamp())
        if config:
            _self.config = config
        if discovery:
            _self.discovery_method = discovery
        _self.transport, _, _, _, _, _, _ = cls.parse_address(address)
        _self.save()

    @staticmethod
    def parse_address(address):
        parsed = urllib.parse.urlparse(address)
        scheme = parsed.scheme
        unix_socket = False
        try:
            beiran_scheme = parsed.scheme.split('+')
            protocol = beiran_scheme[1]
            if len(beiran_scheme) > 2 and beiran_scheme[2] == 'unix':
                unix_socket = True
        except IndexError:
            protocol = scheme
        transport = 'http' if protocol in ['http', 'https'] else 'tcp'
        fragment = parsed.fragment
        hostname = parsed.hostname
        path = parsed.path
        port = parsed.port
        return transport, protocol, hostname, path, port, fragment, unix_socket

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
        _dict['uuid'] = UUID(_dict['uuid'])
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
        """
        Query for all node connections ordered by last seen time
        Returns:
            query object.

        """
        return PeerAddress.select().order_by(
                PeerAddress.last_seen_at.desc()
            ).where(
                PeerAddress.uuid == self.uuid.hex
            )

    def get_connections(self):
        """
        Get a list of connection details of node ordered by last seen time
        Returns:
            (list) list of PeerAddress of node

        """
        return [
            conn for conn in self.connections()
        ]

    def get_latest_connection(self):
        """
        Get the latest PeerAddress of node
        Returns:
            (PeerAddress) connection object

        """
        return self.connections().get()

    def __repr__(self):
        return self.__str__()

    @property
    def address(self, force=False):
        """
        Returns peer address of node in beiran address format.

        If `force` is True, it gets from db.

        Args:
            force (bool): from db or not

        Returns:
            (str): peer address string

        """
        if self._address and not force:
            return self._address
        return self.set_get_address()

    def set_get_address(self, address=None):
        if address:
            self._address = address
        else:
            latest_conn = self.get_latest_connection()
            self._address = latest_conn.address
        return self._address

    def save(self, save_peer_conn=True, force_insert=False, only=None):
        super().save(force_insert=force_insert, only=only)
        if save_peer_conn:
            PeerAddress.add_or_update(
                uuid=self.uuid,
                address=self.address
            )

    @classmethod
    def add_or_update(cls, node):
        """
        Update with or create a new node object from provided `node` object.
        Args:
            node (Node): node object

        Returns:
            (Node): node object

        """
        try:
            node_ = Node.get(Node.uuid == node.uuid)
            node_.update_using_obj(node)
            node_.save()

        except Node.DoesNotExist:
            node_ = node
            # https://github.com/coleifer/peewee/blob/0ed129baf1d6a0855afa1fa27cde5614eb9b2e57/peewee.py#L5103
            node_.save(force_insert=True)

        return node_
