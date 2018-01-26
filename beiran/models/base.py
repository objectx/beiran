"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

import os

from peewee import Model, SqliteDatabase

# check database file check
BEIRAN_DB_PATH = os.getenv("BEIRAN_DB_PATH", '/var/lib/beiran/beiran.db')

if not os.path.exists(BEIRAN_DB_PATH):
    open(BEIRAN_DB_PATH, 'a').close()

DB = SqliteDatabase(BEIRAN_DB_PATH)


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        """Set database metaclass attribute to DB object"""
        database = DB
