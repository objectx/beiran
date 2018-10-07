"""Shared objects of beiran daemon"""
import logging
import os

from pyee import EventEmitter

from beiran.ctx import config
from beiran.log import build_logger
from beiran.version import get_version


EVENTS = EventEmitter()
LOG_LEVEL = logging.getLevelName(config.log_level)
VERSION = get_version('short', 'daemon')


class Services:
    """Conventional class for keeping references to global objects"""
    daemon = None
    plugins = {} # type: dict
    logger = build_logger(config.log_file, LOG_LEVEL) # type: ignore
