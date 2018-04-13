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
        """
        Serialize model to python dict

        Args:
            **kwargs

        Returns:
            (dict): serialized model object

        """
        if 'dialect' in kwargs:
            _kwargs = dict(kwargs)
            del _kwargs['dialect']
            kwargs = _kwargs

        return model_to_dict(self, **kwargs)

    @classmethod
    def from_dict(cls, _dict, **kwargs):
        """
        Deserialize model from python dict
        Args:
            _dict (dict): python dict represents obj

        Returns:
            (BaseModel): model object

        """
        if 'dialect' in kwargs:
            _kwargs = dict(kwargs)
            del _kwargs['dialect']
            kwargs = _kwargs

        return dict_to_model(cls, _dict, **kwargs)

    def update_using_obj(self, obj):
        """
        Update model object with given obj

        Args:
            obj (BaseModel): new object

        Returns:
            (BaseModel): updated base object

        """
        fields = self._meta.fields
        for field in fields:
            setattr(self, field, getattr(obj, field))

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
