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

"""setup.py for packaging beiran"""
from setuptools import setup, find_packages


REQUIREMENTS_PATH = 'requirements.txt'


def read_requirements(path):
    """Read requirements.txt and return a list of requirements."""
    with open(path, 'r') as file:
        reqs = file.read().splitlines()
    return reqs

def read_long_description():
    """Read a file written about long description of the package."""
    with open("README.md", "r") as file:
        long_description = file.read()
    return long_description


def find_beiran_packages():
    """Find beiran package."""
    return find_packages(
        # exclude=["plugins", "doc", "helpers",]
    )


def get_version():
    """
    Reads VERSION file
    Returns:
        (str): plugin version

    """

    with open('VERSION', 'r') as file:
        version = file.read()
    return version


setup(
    name="beiran_interface_k8s",
    version=get_version(),
    author="RainLab",
    author_email="info@rainlab.co.jp",
    description="Beiran Kubernetes Plugin",
    keywords=['beiran', 'kubernetes', 'k8s', 'p2p package manager', 'system tools'],
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://beiran.io",

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Software Distribution"
        "Topic :: System :: Systems Administration",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",  # ???
        "Operating System :: OS Independent",
    ],

    install_requires=read_requirements(REQUIREMENTS_PATH),
    python_requires='~=3.6',

    packages=find_beiran_packages(),
)
