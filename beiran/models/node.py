"""
Module for Node Data Model
"""
from typing import Union, Any, Tuple
from uuid import UUID
from urllib.parse import urlparse
import re
from datetime import datetime
from peewee import IntegerField, CharField, UUIDField
from beiran.models.base import BaseModel, JSONStringField
from beiran.log import build_logger

LOGGER = build_logger('beiran.models.node')


class PeerAddress(BaseModel):  # pylint: disable=too-many-instance-attributes
    """Data model for connection details of Nodes"""

    uuid = UUIDField(null=True)
    transport = CharField(max_length=15, default="http")
    address = CharField(max_length=255)
    last_seen_at = IntegerField(default=datetime.now().timestamp())
    discovery_method = CharField(max_length=32, null=True)
    config = JSONStringField(null=True)  # { "auto-connect": true } ?

    def __init__(self, *args: Any, **kwargs: Any) -> None:
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
            _, protocol, host, path, port, _uuid, unix_socket = self.parse_address(addr)

        addr = self.build_node_address(host=host, port=port, uuid=uuid, path=path,
                                       protocol=protocol, socket=unix_socket)

        self.transport, self.protocol, self.host, self.path, \
        self.port, _uuid, self.unix_socket = self.parse_address(addr)

        if _uuid:
            self.uuid = UUID(_uuid)

        self.address = addr

    def to_dict(self, **kwargs: Any) -> dict:
        """
        Serialize PeerAddress object

        Args:
            **kwargs: extra parameters

        Returns:
            dict: serialized object

        """
        _dict = super().to_dict(**kwargs)
        _dict['uuid'] = self.uuid.hex # pylint: disable=no-member
        _dict['host'] = self.host
        _dict['port'] = self.port
        _dict['protocol'] = self.protocol
        _dict['unix_socket'] = self.unix_socket
        _dict['path'] = self.path
        return _dict

    @classmethod
    def from_dict(cls, _dict: dict, **kwargs: Any) -> "PeerAddress":
        """
        Deserialize PeerAddress object from given `_dict`

        Args:
            _dict(dict): dict containing model attributes and data
            **kwargs: extra parameters

        Returns:
            PeerAddress: deserialized object

        """
        _dict['uuid'] = UUID(_dict['uuid'])
        obj = super().from_dict(_dict, **kwargs)
        return obj

    @property
    def location(self) -> str:
        """
        Location string which is used by clients.

        Returns:
            (str): network location string

        """
        if not self.unix_socket:
            return "{}://{}:{}".format(self.protocol, self.host, self.port)

        return "{}+unix://{}".format(self.protocol, self.path)

    @staticmethod
    def validate_address(address) -> bool:
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
            LOGGER.error("Address is broken: %s", address)

        return bool(matched)

    # pylint: disable=too-many-arguments
    def build_node_address(self, host: str, path: str = None,
                           uuid : str = None, port: int = None,
                           protocol: str = None, socket: bool = False) -> str:
        """
        Build a node address with given host, port, protocol and uuid

        Args:
            host (str): hostname
            uuid (str): uuid of node
            path (str): address path
            port (int): service port
            protocol (str): protocol, default http
            socket (str): is unix socket? default False

        Returns:
            str: formatted address

        """
        port_str = ":{}".format(port or 8888)
        protocol = protocol or 'http'
        unix_socket = "+unix" if socket else ""
        if unix_socket:
            unix_socket = "+unix"
            port_str = ""
            hostname = path
        else:
            hostname = host

        address_format = "beiran+{protocol}{unix_socket}://{hostname}{port}#{uuid}"
        address = address_format.format(
            hostname=hostname,
            port=port_str,
            protocol=protocol,
            unix_socket=unix_socket,
            uuid=uuid
        )
        if not uuid:
            address = address.split('#')[0]

        return address

    @classmethod
    def add_or_update(cls, uuid: str, address: str,
                      discovery: str = None, config: dict = None) -> None:
        """
        Update with or create a new peer_address object from provided information.

        Args:
            uuid (str): uuid
            address (str): address
            discovery (str): discovery channel
            config (dict): config dict

        Returns:

        """
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
        _self.save()

    @staticmethod
    def parse_address(address: str) -> Tuple[str, str, str, str, int, str, bool]:
        """
        Parse beiran address

        Args:
            address (str): beiran address

        Returns:
            (tuple): address details

        """
        parsed = urlparse(address)
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

    # The state stands for that Node is just created and any operation is not processed yet.
    STATUS_NEW = 'new'

    # The state stands for that beirand just starts the initialization.
    STATUS_INIT = 'init'

    # The state stands for that beirand just finished the initialization and ready to work.
    STATUS_READY = 'ready'

    # The state stands for that beirand finds the other beirand and can communicate with it.
    STATUS_ONLINE = 'online'

    # The state stands for that beirand finished communicating with the other beirand.
    STATUS_OFFLINE = 'offline'

    # The state stands for that beirand is connecting to the other beirand.
    STATUS_CONNECTING = 'connecting'

    # The state stands for that beirand is syncing to the other beirand.
    STATUS_SYNCING = 'syncing'

    # The state stands for that beirand is about to exit.
    STATUS_CLOSING = 'closing'

    # The state stands for that beirand becomes unable to communicate with the other beirand.
    STATUS_LOST = 'lost'

    # The state stands for that Node doesn't have the parameter 'status'.
    STATUS_UNKNOWN = 'unknown'

    uuid = UUIDField(primary_key=True)
    hostname = CharField(max_length=100)
    ip_address = CharField(max_length=15)  # dotted-decimal
    ip_address_6 = CharField(max_length=39, null=True)  # hexadecimal
    port = IntegerField()
    os_type = CharField(max_length=20)  # linux, win,
    os_version = CharField(max_length=255)  # os and version ubuntu 14.04 or output of `uname -a`
    architecture = CharField(max_length=20)  # x86_64
    version = CharField(max_length=10)  # beiran daemon version of node
    status = CharField(max_length=32, default=STATUS_NEW)  # type: Union[CharField, str]
    last_sync_version = IntegerField()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._address = None
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        fmt = "Node: {hostname}, Address: {ip}:{port}, UUID: {uuid}"
        return fmt.format(hostname=self.hostname,
                          ip=self.ip_address,
                          port=self.port,
                          uuid=self.uuid)

    @classmethod
    def from_dict(cls, _dict: dict, **kwargs: Any) -> "Node":
        _dict['uuid'] = UUID(_dict['uuid'])
        node_address = _dict.pop('address', None)
        node = super().from_dict(_dict, **kwargs)
        node.set_get_address(node_address)
        return node

    def to_dict(self, **kwargs) -> dict:
        _dict = super().to_dict(**kwargs)

        # pylint: disable=no-member
        _dict['uuid'] = self.uuid.hex  # type: ignore
        _dict['address'] = self.address
        if 'dialect' in kwargs and kwargs['dialect'] == 'api':
            _dict.pop('status')
        return _dict

    @property
    def url(self) -> str:
        """Generates node advertise url using ip_address, port and uuid properties"""
        return "http://{}:{}#{}".format(self.ip_address, self.port, self.uuid.hex) # pylint: disable=no-member

    @property
    def url_without_uuid(self) -> str:
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
            PeerAddress.uuid == self.uuid.hex  # pylint: disable=no-member
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
    def address(self, force=False):  # type: ignore
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
        """
        Set or get address of node

        Args:
            address (str): beiran address string

        Returns:
            (str): beiran address string

        """
        if address:
            self._address = address
        else:
            latest_conn = self.get_latest_connection()
            self._address = latest_conn.address
        return self._address

    def save(self, save_peer_conn=True, force_insert=False, only=None):  # pylint: disable=arguments-differ
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
