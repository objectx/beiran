"""
Import all data models to make import statements clear.
"""
from beiran.log import build_logger
from .base import BaseModel
from .docker import DockerDaemon
from .node import Node

LOGGER = build_logger()


def create_tables(database):
    """
    We need to create tables for first time. This method can be called by an
    init script or manually while development.


    """
    # import them locally!
    LOGGER.info("creating database tables!...")
    database.create_tables([Node, DockerDaemon])
