"""
Support library for beiran daemon
"""

import ipaddress
import json
import netifaces
import os
import socket
import tarfile
from uuid import uuid4


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

<< << << < HEAD


def get_default_gateway_ip_interface():
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
        raise ValueError("""Please check environment variable LISTEN_ADDR,
                         it must be a valid IP4 address. `{}` is not a valid one!""".format(env_addr))


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
            for ip in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                if ip == os.environ.get('LISTEN_ADDR'):
                    return interface

        raise ValueError("Your LISTEN_ADDR does not match any network interface!")

    _, interface = get_default_gateway_ip_interface()

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

    ip, _ = get_default_gateway_ip_interface()

    return ip


def get_hostname(self):
    """ Gets hostname for discovery
    """
    if 'HOSTNAME' in os.environ:
        return os.environ['HOSTNAME']
    return socket.gethostname()


def local_node_uuid():
    """
    Get UUID from config file if it exists, else return a new one and write it to config file

    Returns:
        str: uuid in hex

    """
    uuid_conf_path = "/".join([os.getenv("CONFIG_FOLDER_PATH", '/etc/beiran'), 'uuid.conf'])
    try:
        f = open(uuid_conf_path)
        uuid = f.read()
        f.close()
        if len(uuid) != 32:
            raise ValueError
    except (FileNotFoundError, ValueError):
        uuid = uuid4().hex
        f = open(uuid_conf_path, 'w')
        f.write(uuid)
        f.close()

    return uuid
