import os
from setuptools import setup, find_packages


# PLUGIN_LIST = 




DISCOVERY_REQUIREMENTS_PATH = 'beiran_discovery_dns/requirements.txt'
INTERFACE_REQUIREMENTS_PATH = 'beiran_interface_k8s/requirements.txt'


def read_requirements(path):
    """Read requirements.txt and return a list of requirements."""
    with open(path, 'r') as file:
        reqs = file.read().splitlines()
    return reqs


setup(
    name="beiran_discovery_dns",
    version='0.0.9',
    description="Peer to peer focused package distribution system",
    url="https://beiran.io",
    install_requires=read_requirements(DISCOVERY_REQUIREMENTS_PATH),
    python_requires='~=3.6',
    packages=['beiran_discovery_dns'],
    data_files=[(DISCOVERY_REQUIREMENTS_PATH)],
)

setup(
    name="beiran_interface_k8s",
    version='0.0.9',
    description="Peer to peer focused package distribution system",
    url="https://beiran.io",
    install_requires=read_requirements(INTERFACE_REQUIREMENTS_PATH),
    python_requires='~=3.6',
    packages=['beiran_interface_k8s']),
    data_files=[(INTERFACE_REQUIREMENTS_PATH)],
)