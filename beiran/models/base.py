"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

from peewee import Model, Proxy

DB_PROXY = Proxy()


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        """Set database metaclass attribute to DB object"""
        database = DB_PROXY
