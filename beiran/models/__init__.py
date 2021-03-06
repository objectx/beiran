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

"""
Import all data models to make import statements clear.
"""
from peewee import SqliteDatabase

from beiran.log import build_logger
from .base import BaseModel
from .node import Node, PeerAddress

LOGGER = build_logger()

MODEL_LIST = [Node, PeerAddress]


def create_tables(database: SqliteDatabase, model_list: list = None) -> None:
    """
    We need to create tables for first time. This method can be called by an
    init script or manually while development.


    """
    # import them locally!
    LOGGER.info("creating database tables!...")
    database.create_tables(model_list or MODEL_LIST)
