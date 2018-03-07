"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

import json

from peewee import Model, Proxy, TextField

DB_PROXY = Proxy()


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        """Set database metaclass attribute to DB object"""
        database = DB_PROXY


class JSONStringField(TextField):
    """A basic JSON Field based on text field"""

    # pylint: disable=arguments-differ
    def db_value(self, val):
        """dict to string"""
        return json.dumps(val)

    def python_value(self, val):
        """string to python dict"""
        return val if val is None else json.loads(val)
    # pylint: enable=arguments-differ
