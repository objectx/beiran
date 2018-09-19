"""Shared objects of beiran daemon"""
import logging
import os

from pyee import EventEmitter

from beiran import defaults
from beiran.log import build_logger
from beiran.version import get_version

DATA_DIR = os.getenv("DATA_DIR_PATH", defaults.DATA_DIR)
CONFIG_DIR = os.getenv("CONFIG_DIR_PATH", defaults.CONFIG_DIR)
CACHE_DIR = os.getenv("CACHE_DIR_PATH", defaults.CACHE_DIR)
RUN_DIR = os.getenv("RUN_DIR_PATH", defaults.RUN_DIR)

EVENTS = EventEmitter()

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', defaults.LOG_LEVEL)) # type: ignore
LOG_FILE = os.getenv('LOG_FILE', defaults.LOG_FILE)

VERSION = get_version('short', 'daemon')


class Services:
    """Conventional class for keeping references to global objects"""
    daemon = None
    plugins = {} # type: dict
    logger = build_logger(LOG_FILE, LOG_LEVEL) # type: ignore
