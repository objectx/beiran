"""Shared objects of beiran daemon"""
import logging
import os

from pyee import EventEmitter

import beiran.defaults as defaults
from beiran.log import build_logger
from beiran.version import get_version

DATA_FOLDER = os.getenv("DATA_FOLDER_PATH", defaults.DATA_FOLDER)
CONFIG_FOLDER = os.getenv("CONFIG_FOLDER_PATH", defaults.CONFIG_FOLDER)

EVENTS = EventEmitter()

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', defaults.LOG_LEVEL)) # type: ignore
LOG_FILE = os.getenv('LOG_FILE', defaults.LOG_FILE)

VERSION = get_version('short', 'daemon')

class Services:
    """Conventional class for keeping references to global objects"""
    daemon = None
    plugins = {} # type: dict
    logger = build_logger(LOG_FILE, LOG_LEVEL) # type: ignore
