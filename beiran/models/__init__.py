"""
Import all data models to make import statements clear.
"""
from beiran.log import build_logger
from .base import BaseModel
from .node import Node, PeerConnection
# from .docker_objects import DockerImage, DockerLayer

LOGGER = build_logger()

MODEL_LIST = [Node, PeerConnection] # DockerImage, DockerLayer]


def create_tables(database, model_list=None):
    """
    We need to create tables for first time. This method can be called by an
    init script or manually while development.


    """
    # import them locally!
    LOGGER.info("creating database tables!...")
    database.create_tables(model_list or MODEL_LIST)
