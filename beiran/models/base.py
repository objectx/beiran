"""
Module of Beirand data models. Beirand data models use Peewee ORM.
"""

import json
from typing import Any, TypeVar, Type
from peewee import Model, Proxy, TextField
from playhouse.shortcuts import model_to_dict, dict_to_model

DB_PROXY = Proxy()

BaseModelType = TypeVar('BaseModelType', bound='BaseModel')


class BaseModel(Model):
    """Base model object having common attributes, to be extended by data models."""

    class Meta:
        """Set database metaclass attribute to DB object"""
        database = DB_PROXY

    def to_dict(self, **kwargs: Any) -> dict:
        """
        Serialize model to python dict

        Args:
            **kwargs: model attributes

        Returns:
            (dict): serialized model object

        """
        kwargs.pop('dialect', None)
        return model_to_dict(self, **kwargs)

    @classmethod
    def from_dict(cls:  Type[BaseModelType], _dict: dict, **kwargs: Any) -> BaseModelType:
        """
        Deserialize model from python dict

        Args:
            _dict (dict): python dict represents obj

        Returns:
            BaseModel: model object

        """
        kwargs.pop('dialect', None)
        return dict_to_model(cls, _dict, **kwargs)

    def update_using_obj(self, obj: "BaseModel") -> None:
        """
        Update model object with given obj

        Args:
            obj (BaseModel): new object

        """
        fields = self._meta.fields
        for field in fields:
            setattr(self, field, getattr(obj, field))


class JSONStringField(TextField):
    """A basic JSON Field based on text field"""

    def db_value(self, value: dict) -> str:
        """dict to string"""
        return json.dumps(value)

    def python_value(self, value: str) -> dict:
        """string to python dict"""
        return value if value is None else json.loads(value)
