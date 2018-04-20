"""Shared objects of beiran daemon"""
import logging
import os

import docker
from pyee import EventEmitter
from aiodocker import Docker

from beiran.log import build_logger
from beiran.version import get_version
from beirand.nodes import Nodes


EVENTS = EventEmitter()

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'DEBUG'))
LOG_FILE = os.getenv('LOG_FILE', '/var/log/beirand.log')

logger = build_logger(LOG_FILE, LOG_LEVEL)  # pylint: disable=invalid-name

VERSION = get_version('short', 'daemon')

# # we may have a settings file later, create this dir while init wherever it would be
# DOCKER_TAR_CACHE_DIR = "tar_cache"

# # Initialize docker client
# DOCKER_CLIENT = docker.from_env()
# AIO_DOCKER_CLIENT = Docker()

# # docker low level api client to get image data
# DOCKER_LC = docker.APIClient()

DOCKER_CLIENT = None
AIO_DOCKER_CLIENT = None
DOCKER_LC = None
DOCKER_TAR_CACHE_DIR = None

NODES = Nodes()
