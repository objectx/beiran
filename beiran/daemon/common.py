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

"""Shared objects of beiran daemon"""
import logging

from pyee import EventEmitter

from beiran.config import config
from beiran.log import build_logger
from beiran.version import get_version


EVENTS = EventEmitter()
VERSION = get_version('short', 'daemon')

def build_logger_with_env_level(filename: str = config.log_file) -> logging.Logger:
    """Build logger class with the environment variable LOG_LEVEL"""
    log_level = logging.getLevelName(config.log_level)
    return build_logger(filename, log_level) # type: ignore

class Services:
    """Conventional class for keeping references to global objects"""
    daemon = None
    plugins = {} # type: dict
    logger = None

    @classmethod
    def get_logger(cls):
        """Builds and returns a logger instance on demand"""
        if not cls.logger:
            cls.logger = build_logger_with_env_level()
        return cls.logger
