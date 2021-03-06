# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Support library for beiran daemon
"""
import os
import ipaddress
import platform
import socket
from uuid import uuid4, UUID

import netifaces

from beiran.config import config
from beiran.log import build_logger
from beiran.models import PeerAddress
from beiran.version import get_version


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

    uuid_conf_path = "/".join([config.config_dir, 'uuid.conf'])
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
        env_addr = config.listen_address
        listen_address = ipaddress.ip_address(env_addr)
        return listen_address.compressed

    except KeyError:  # if env var is not set
        listen_interface = get_listen_interface()
        return netifaces.ifaddresses(listen_interface)[netifaces.AF_INET][0]['addr']

    except ValueError:  # if env var is set erroneously
        raise ValueError(
            """Please check config file for listen_address or environment
            variable BEIRAN_LISTEN_ADDRESS, it must be a valid IP4 address.
            `{}` is not a valid one!""".format(env_addr))


def get_listen_interface() -> str:
    """
    Seek for listen interface in order described below and return it.

    First try BEIRAN_LISTEN_INTERFACE env var.
    Second try to find the interface of ip address specified by config.listen_address.
    Third, if config.listen_address is not set return default gateway's interface

    Returns
        string: listen address.

    """

    if config.listen_interface:
        return config.listen_interface

    if config.listen_address:
        for interface in netifaces.interfaces():
            for ip_v4 in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                if ip_v4 == config.listen_address:
                    return interface

        raise ValueError("Your BEIRAN_LISTEN_ADDRESS does not match any network interface!")

    _, interface = get_default_gateway_interface()

    return interface


def get_advertise_address() -> str:
    """
    First try environment variable `BEIRAN_LISTEN_ADDRESS`. If it is not set,
    return the listen address unless it is `0.0.0.0`.

    Lastly return default gateway's ip address

    Returns
        string: listen address.


    Returns:
        string: ip address of advertise address

    """
    listen_address = get_listen_address()

    if listen_address != '0.0.0.0':
        return listen_address

    _, default_interface = get_default_gateway_interface()
    return netifaces.ifaddresses(default_interface)[netifaces.AF_INET][0]['addr']


def get_hostname() -> str:
    """ Gets hostname for discovery
    """
    if config.hostname:
        return config.hostname
    return socket.gethostname()


def sync_version_file_path() -> str:
    """Return sync_version file path"""
    path = config.data_dir + "/sync_version"
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


def collect_node_info() -> dict:
    """
    Collect and return Node info

    Returns:
        dict: node information

    """
    peer_address = PeerAddress(
        uuid=local_node_uuid().hex,
        host=get_advertise_address(),
        port=config.listen_port,
    )
    return {
        "uuid": local_node_uuid().hex,
        "address": peer_address.address,
        "hostname": get_hostname(),
        "ip_address": get_advertise_address(),
        "port": config.listen_port,
        "ip_address_6": None,
        "os_type": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "version": get_version(),
        "last_sync_version": get_sync_version()
    }
