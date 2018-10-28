import os
from setuptools import setup, find_packages
from beiran.version import get_version


REQUIREMENTS_PATH = 'beiran/requirements.txt'


def read_requirements(path):
    """Read requirements.txt and return a list of requirements."""
    with open(path, 'r') as file:
        reqs = file.read().splitlines()
    return reqs


setup(
    name="beiran",
	version=get_version(component='library'),
	description="Peer to peer focused package distribution system",
	url="https://beiran.io",
    install_requires=read_requirements(REQUIREMENTS_PATH),
    python_requires='~=3.6',
	packages=find_packages(),
	entry_points={
        "console_scripts": [
            "beiran = beiran.__main__:main",
            "beirand = beiran.daemon.__main__:main"
        ]
    },
    data_files=[(REQUIREMENTS_PATH)],
)