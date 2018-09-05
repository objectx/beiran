"""Shared objects of beiran daemon"""
import logging
import os

from pyee import EventEmitter

from beiran import defaults
from beiran.ctx import Config
from beiran.log import build_logger
from beiran.version import get_version

DATA_FOLDER = Config.get_data_folder()
CONFIG_FOLDER = Config.get_config_folder()

EVENTS = EventEmitter()

LOG_LEVEL = logging.getLevelName(Config.get_log_level())
LOG_FILE = Config.get_log_file()

VERSION = get_version('short', 'daemon')


class Services:
    """Conventional class for keeping references to global objects"""
    daemon = None
    plugins = {}
    logger = build_logger(LOG_FILE, LOG_LEVEL)
