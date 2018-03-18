"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

import json

from peewee import Model, Proxy, TextField
from playhouse.shortcuts import model_to_dict, dict_to_model

DB_PROXY = Proxy()


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        """Set database metaclass attribute to DB object"""
        database = DB_PROXY

    def to_dict(self, **kwargs):
        return model_to_dict(self, **kwargs)

    @classmethod
    def from_dict(_class, _dict):
        return dict_to_model(_class, _dict)

    def update_using_obj(self, obj):
        fields = self._meta.fields
        for f in fields:
            setattr(self, f, getattr(obj, f))

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
