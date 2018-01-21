"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

from peewee import Model, SqliteDatabase
import os

sqlite_file_path = os.getenv("SQLITE_FILE_PATH", '/var/lib/beiran/beiran.db')
db = SqliteDatabase(sqlite_file_path)


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        database = db


def create_tables():
    """
    We need to create tables for first time. This method can be called by an
    init script or manually while development.


    """
    # import them locally!
    from beirand.models import Node, DockerDaemon
    db.create_tables([Node, DockerDaemon])
