"""
Import all data models to make import statements clear.
"""
from .base import BaseModel
from .node import Node
from .docker import DockerDaemon
from beiran.log import build_logger

logger = build_logger()


def create_tables(db):
    """
    We need to create tables for first time. This method can be called by an
    init script or manually while development.


    """
    # import them locally!
    logger.info("creating database tables!...")
    db.create_tables([Node, DockerDaemon])
