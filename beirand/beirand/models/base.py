"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

from peewee import Model, SqliteDatabase

db = SqliteDatabase('beirand.db')


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        database = db
