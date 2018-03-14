"""Shared objects of beiran daemon"""
import logging
import os

import docker
from pyee import EventEmitter
from aiodocker import Docker

from beiran.log import build_logger
from beiran.version import get_version
from beirand.nodes import Nodes


EVENTS = EventEmitter()

LOG_LEVEL = logging.getLevelName(os.getenv('LOG_LEVEL', 'DEBUG'))
LOG_FILE = os.getenv('LOG_FILE', '/var/log/beirand.log')

logger = build_logger(LOG_FILE, LOG_LEVEL)  # pylint: disable=invalid-name

VERSION = get_version('short', 'daemon')

# Initialize docker client
DOCKER_CLIENT = docker.from_env()

# docker low level api client to get image data
DOCKER_LC = docker.APIClient()

# we may have a settings file later, create this dir while init wherever it would be
DOCKER_TAR_CACHE_DIR = "tar_cache"

AIO_DOCKER_CLIENT = Docker()

try:
    NODES = Nodes()
except AttributeError:

    def db_init():
        """Initialize database"""
        from peewee import SqliteDatabase
        from beiran.models.base import DB_PROXY

        # check database file exists
        beiran_db_path = os.getenv("BEIRAN_DB_PATH", '/var/lib/beiran/beiran.db')
        db_file_exists = os.path.exists(beiran_db_path)

        if not db_file_exists:
            logger.info("sqlite file does not exist, creating file %s!..", beiran_db_path)
            open(beiran_db_path, 'a').close()

        # init database object
        database = SqliteDatabase(beiran_db_path)
        DB_PROXY.initialize(database)

        if not db_file_exists:
            logger.info("db hasn't initialized yet, creating tables!..")
            from beiran.models import create_tables

            create_tables(database)

    db_init()
    NODES = Nodes()
