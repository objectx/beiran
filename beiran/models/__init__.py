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
