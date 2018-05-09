"""Shared objects of beiran daemon"""
import logging
import os

from pyee import EventEmitter

from beiran.log import build_logger
from beiran.version import get_version
from beirand.nodes import Nodes


EVENTS = EventEmitter()

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'DEBUG'))
LOG_FILE = os.getenv('LOG_FILE', '/var/log/beirand.log')

logger = build_logger(LOG_FILE, LOG_LEVEL)  # pylint: disable=invalid-name

VERSION = get_version('short', 'daemon')

NODES = Nodes()

PLUGINS = {}
