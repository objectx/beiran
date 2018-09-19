"""
Support library for beiran daemon
"""
import os
import ipaddress
import platform
import socket
from uuid import uuid4, UUID

import netifaces

from beiran.log import build_logger
from beiran.models import PeerAddress
from beiran.version import get_version

from beiran import defaults
from beirand import common

LOGGER = build_logger()
LOCAL_NODE_UUID_CACHED = None


def local_node_uuid() -> UUID:
    """
    Get UUID from config file if it exists, else return a new one and write it to config file

    Returns:
        (UUID): uuid in hex

    TODO:
     - Group this function and similar functionality in a class
       that will allow eliminate the global usage

    """
    global LOCAL_NODE_UUID_CACHED  # pylint: disable=global-statement

    if LOCAL_NODE_UUID_CACHED:
        return LOCAL_NODE_UUID_CACHED

    config_folder = os.getenv("CONFIG_FOLDER_PATH", defaults.CONFIG_FOLDER)
    uuid_conf_path = "/".join([config_folder, 'uuid.conf'])
    try:
        uuid_file = open(uuid_conf_path)
        uuid_hex = uuid_file.read()
        uuid = UUID(uuid_hex)
        uuid_file.close()
        if len(uuid_hex) != 32:
            raise ValueError
    except (FileNotFoundError, ValueError):
        LOGGER.info("uuid.conf file does not exist yet or is invalid, creating a new one here: %s",
                    uuid_conf_path)
        uuid = uuid4()
        uuid_file = open(uuid_conf_path, 'w')
        uuid_file.write(uuid.hex)
        uuid_file.close()

    LOGGER.info("local nodes UUID is: %s", uuid.hex)
    LOCAL_NODE_UUID_CACHED = uuid

    return uuid


def get_default_gateway_interface() -> tuple:
    """
    Get default gateway's ip and interface info.

    Returns:
        tuple: ip address, interface name. (10.0.2.2, eth0)

    """
    return netifaces.gateways()['default'][netifaces.AF_INET]


def get_listen_address() -> str:
    """

    Returns:
        string: daemon listen IP address

    """
    env_addr = ''

    try:  # try to get from environment variable
        env_addr = os.environ['LISTEN_ADDR']
        listen_address = ipaddress.ip_address(env_addr)
        return listen_address.compressed

    except KeyError:  # if env var is not set
        listen_interface = get_listen_interface()
        return netifaces.ifaddresses(listen_interface)[netifaces.AF_INET][0]['addr']

    except ValueError:  # if env var is set erroneously
        raise ValueError(
            """Please check environment variable LISTEN_ADDR,
            it must be a valid IP4 address. `{}` is not a valid one!""".format(env_addr))


def get_listen_port() -> int:
    """
    Get listen port from env or default 8888
    Returns:
        int: listen port

    """
    try:
        return int(os.environ.get('LISTEN_PORT', defaults.LISTEN_PORT))
    except ValueError:
        raise ValueError('LISTEN_PORT must be a valid port number!')


def get_listen_interface() -> str:
    """
    Seek for listen interface in order described below and return it.

    First try LISTEN_INTERFACE env var.
    Second try to find the interface of ip address specified by LISTEN_ADDR env var.
    Third, if LISTEN_ADDR is not set return default gateway's interface

    Returns
        string: listen address.

    """

    if 'LISTEN_INTERFACE' in os.environ:
        return os.environ['LISTEN_INTERFACE']

    if 'LISTEN_ADDR' in os.environ:
        for interface in netifaces.interfaces():
            for ip_v4 in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                if ip_v4 == os.environ.get('LISTEN_ADDR'):
                    return interface

        raise ValueError("Your LISTEN_ADDR does not match any network interface!")

    _, interface = get_default_gateway_interface()

    return interface


def get_advertise_address() -> str:
    """
    First try environment variable `ADVERTISE_ADDR`. If it is not set,
    return the listen address unless it is `0.0.0.0`.

    Lastly return default gateway's ip address

    Returns
        string: listen address.


    Returns:
        string: ip address of advertise address

    """

    if 'ADVERTISE_ADDR' in os.environ:
        return os.environ['ADVERTISE_ADDR']

    listen_address = get_listen_address()

    if listen_address != '0.0.0.0':
        return listen_address

    _, default_interface = get_default_gateway_interface()
    return netifaces.ifaddresses(default_interface)[netifaces.AF_INET][0]['addr']


def get_hostname() -> str:
    """ Gets hostname for discovery
    """
    if 'HOSTNAME' in os.environ:
        return os.environ['HOSTNAME']
    return socket.gethostname()

def sync_version_file_path() -> str:
    """Return sync_version file path"""
    path = common.DATA_FOLDER + "/sync_version"
    return path

async def update_sync_version_file(version: int):
    """Write new sync_version to the sync_version file"""

    path = sync_version_file_path()

    if not os.path.exists(path):
        LOGGER.warning('Cannot find sync_version_file. Creating new file')
    with open(path, 'w') as file:
        file.write(str(version))

def get_sync_version() -> int:
    """
    Gets last sync_version from local file.

    Returns
        int: sync version.
    """

    path = sync_version_file_path()
    sync_version = 0

    try:
        with open(path, 'r') as file:
            sync_version = int(file.read())
    except FileNotFoundError:
        LOGGER.warning('Cannot find sync_version_file. Creating new file')
        with open(path, 'w') as file:
            file.write(str(sync_version))
    except ValueError:
        raise ValueError("Sync version must be an integer! " +
                         "Check your SYNC_VERSION_FILE ({})".format(path))

    return sync_version

def get_plugin_list() -> dict:
    """Return plugin list"""

    # docker only for poc
    return {
        "active_plugins": [
            "docker",
        ]
    }


def collect_node_info() -> dict:
    """
    Collect and return Node info

    Returns:
        dict: node informations

    """
    peer_address = PeerAddress(
        uuid=local_node_uuid().hex,
        host=get_advertise_address(),
        port=get_listen_port(),
    )
    return {
        "uuid": local_node_uuid().hex,
        "address": peer_address.address,
        "hostname": get_hostname(),
        "ip_address": get_advertise_address(),
        "port": get_listen_port(),
        "ip_address_6": None,
        "os_type": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "version": get_version(),
        "last_sync_version": get_sync_version()
    }
