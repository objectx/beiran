"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

import os
from peewee import Model, SqliteDatabase

SQLITE_FILE_PATH = os.getenv("SQLITE_FILE_PATH", '/var/lib/beiran/beiran.db')
DB = SqliteDatabase(SQLITE_FILE_PATH)


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        """Set database metaclass attribute to DB object"""
        database = DB


def create_tables():
    """
    We need to create tables for first time. This method can be called by an
    init script or manually while development.


    """
    # import them locally!
    from beirand.models import Node, DockerDaemon
    DB.create_tables([Node, DockerDaemon])
