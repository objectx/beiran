"""Shared objects of beiran daemon"""
import logging
import os

from pyee import EventEmitter

from beiran.ctx import config
from beiran.log import build_logger
from beiran.version import get_version

DATA_DIR = config.data_dir
CONFIG_DIR = config.config_dir
RUN_DIR = config.run_dir
CACHE_DIR = config.cache_dir

EVENTS = EventEmitter()

LOG_LEVEL = logging.getLevelName(config.log_level)
LOG_FILE = config.log_file

VERSION = get_version('short', 'daemon')


class Services:
    """Conventional class for keeping references to global objects"""
    daemon = None
    plugins = {} # type: dict
    logger = build_logger(LOG_FILE, LOG_LEVEL) # type: ignore
