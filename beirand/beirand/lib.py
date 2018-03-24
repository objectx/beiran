"""
Support library for beiran daemon
"""
import asyncio
import os
import ipaddress
import json
import platform
import socket
import tarfile
from uuid import uuid4, UUID

import aiohttp
import async_timeout
import netifaces


from beiran.log import build_logger
from beiran.version import get_version

LOGGER = build_logger()
LOCAL_NODE_UUID_CACHED = None

def docker_sha_summary(sha):
    """
    shorten sha to 12 bytes length str as docker uses

    e.g "sha256:53478ce18e19304e6e57c37c86ec0e7aa0abfe56dff7c6886ebd71684df7da25" to "53478ce18e19"

    Args:
        sha (string): sha string

    Returns:
        string

    """
    return sha.split(":")[1][0:12]


def docker_find_layer_dir_by_sha(sha):
    """
    try to find local layer directory containing tar archive contents pulled from remote repository

    Args:
        sha (string): sha string

    Returns:
        string directory path or None

    """

    local_diff_dir = '/var/lib/docker/image/overlay2/distribution/v2metadata-by-diffid/sha256'
    local_cache_id = '/var/lib/docker/image/overlay2/layerdb/sha256/{diff_file_name}/cache-id'
    local_layer_dir = '/var/lib/docker/overlay2/{layer_dir_name}/diff/'

    for file_name in os.listdir(local_diff_dir):
        # f_path = file'{local_diff_dir}/{file_name}'  # python 3.5 does not support file strings.
        f_path = '{}/{}'.format(local_diff_dir, file_name)
        file = open(f_path)
        try:
            content = json.load(file)
            if not content[0].get('Digest', None) == sha:
                continue  # next file

            file.close()

            with open(local_cache_id.format(diff_file_name=file_name)) as file:
                return local_layer_dir.format(layer_dir_name=file.read())

        except ValueError:
            pass


def create_tar_archive(dir_path, output_file_path):
    """
    create a tar archive from given path

    Args:
        output_file_path: directory path to be saved!
        dir_path (string): directory path to be tarred!

    Returns:


    """
    with tarfile.open(output_file_path, "w") as tar:
        tar.add(dir_path, arcname='.')

def local_node_uuid():
    """
    Get UUID from config file if it exists, else return a new one and write it to config file

    Returns:
        (UUID): uuid in hex

    """
    global LOCAL_NODE_UUID_CACHED

    if LOCAL_NODE_UUID_CACHED:
        return LOCAL_NODE_UUID_CACHED

    uuid_conf_path = "/".join([os.getenv("CONFIG_FOLDER_PATH", '/etc/beiran'), 'uuid.conf'])
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

def get_default_gateway_interface():
    """
    Get default gateway's ip and interface info.

    Returns:
        tuple: ip address, interface name. (10.0.2.2, eth0)

    """
    return netifaces.gateways()['default'][netifaces.AF_INET]


def get_listen_address():
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


def get_listen_port():
    """
    Get listen port from env or default 8888
    Returns:
        str: listen port

    """
    try:
        return int(os.environ.get('LISTEN_PORT', '8888'))
    except ValueError:
        raise ValueError('LISTEN_PORT must be a valid port number!')


def get_listen_interface():
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


def get_advertise_address():
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

    ip_v4, _ = get_default_gateway_interface()

    return ip_v4


def get_hostname():
    """ Gets hostname for discovery
    """
    if 'HOSTNAME' in os.environ:
        return os.environ['HOSTNAME']
    return socket.gethostname()


def get_plugin_list():
    """Return plugin list"""

    # docker only for poc
    return {
        "active_plugins": [
            "docker",
        ]
    }


def collect_node_info():
    """
    Collect and return Node info

    Returns:
        dict: node informations

    """
    return {
        "uuid": local_node_uuid().hex,
        "hostname": get_hostname(),
        "ip_address": get_listen_address(),
        "ip_address_6": None,
        "os_type": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "beiran_version": get_version(),
        "beiran_service_port": get_listen_port()
    }


async def async_fetch(url, timeout=3):
    """
    Async http get with aiohttp
    Args:
        url (str): get url
        timeout (int): timeout

    Returns:
        (int, dict): resonse status code, response json

    """
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(timeout):
            async with session.get(url) as resp:
                status, response = resp.status, await resp.json()
                return status, response


async def fetch_docker_info(aiodocker):
    """
    Fetch async docker daemon information

    Returns:
        (dict): docker status and information

    """

    try:
        info = await aiodocker.system.info()
        return {
            "status": True,
            "daemon_info": info
        }
    except Exception as error:
        LOGGER.error("Error while connecting local docker daemon %s", error)
        return {
            "status": False,
            "error": str(error)
        }


async def update_docker_info(local_node, aiodocker):
    """
    Makes an async call to docker `client` and get info for `local_node`

    Args:
        local_node (Node):
        client (docker):

    Returns:
        (None): updates `local_node` object


    """
    LOGGER.debug("Updating local docker info")
    retry_after = 0

    while retry_after < 30:
        docker_info = await fetch_docker_info(aiodocker)
        if docker_info["status"]:
            LOGGER.debug(" *** Found local docker daemon *** ")
            local_node.docker = docker_info['daemon_info']
            break
        else:
            LOGGER.debug("Cannot fetch docker info, retrying after %d seconds", retry_after)
            await asyncio.sleep(5)
        retry_after += 5


def db_init():
    """Initialize database"""
    from peewee import SqliteDatabase
    from beiran.models.base import DB_PROXY
    from beirand.common import logger

    # check database file exists
    beiran_db_path = os.getenv("BEIRAN_DB_PATH", '/var/lib/beiran/beiran.db')
    db_file_exists = os.path.exists(beiran_db_path)

    if not db_file_exists:
        logger.info("sqlite file does not exist, creating file %s!..", beiran_db_path)
        open(beiran_db_path, 'a').close()

    # init database object
    database = SqliteDatabase(beiran_db_path)
    DB_PROXY.initialize(database)

    if not db_file_exists:
        logger.info("db hasn't initialized yet, creating tables!..")
        from beiran.models import create_tables

        create_tables(database)
