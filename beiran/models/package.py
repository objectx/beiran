"""
Base Package Data Model
"""

from peewee import IntegerField, CharField
from beiran.models.base import BaseModel, JSONStringField
from beiran.log import build_logger

LOGGER = build_logger('beiran.models.node')


class Package(BaseModel):
    # def __new__(cls, *args, **kwargs):
    #     instance = super().__new__(cls, *args, **kwargs)
    #     instance.make_up_fields()
    #     return instance
    #
    # @classmethod
    # def make_up_fields(cls):
    #     """"""
    #     return NotImplemented

    BASE_FIELD_MAP = dict()

    def __init__(self, *args, **kwargs):
        """
        While initializing model instance, call regularly super init, and after
        set package specific attributes defined in BASE_FIELD_MAP

        Args:
            *args:
            **kwargs:

        """

        super().__init__(*args, **kwargs)
        for field, cfield in self.BASE_FIELD_MAP.items():
            setattr(self, cfield, self.__getattribute__(field))


    id = CharField(max_length=128, primary_key=True)
    name = JSONStringField(default=list, null=True)
    version = CharField(max_length=128, null=True)
    available_at = JSONStringField(default=list, null=True)
    size = IntegerField(null=True)

    def serialize(self):
        """
        Serialize model as a python dict object

        Returns:
            dict: key value

        """
        object_dict = super().to_dict()
        for field, cfield in self.BASE_FIELD_MAP.items():
            value = object_dict.get(field, None)
            if value:
                object_dict[cfield] = value
                # del object_dict[field]

        return object_dict


    @classmethod
    def deserialize(cls, object_dict):
        """
        Create an instance from a python dict.

        Returns:
            Package: package instance

        """
        for field, cfield in cls.BASE_FIELD_MAP.items():
            value = object_dict.get(cfield, None)
            if value:
                object_dict[field] = value
                del object_dict[cfield]

        return super().from_dict(object_dict)

    @classmethod
    def get_by_id(cls, id):
        """
        Try to get and return instance of Package identified by `id`

        Args:
            id (str): package identifier

        Returns:
            Package: package instance

        """

        return cls.get_or_none(cls.id == id)

    @classmethod
    def get_by_name_version(cls, name, version=None):
        try:
            return cls.filter_by_name_version(name=name, version=version).get()
        except cls.DoesNotExist:
            return None

    @classmethod
    def filter_by_name_version(cls, name, version=None):
        query = cls.select()
        query = query.filter(cls.name==name)
        if version:
            query = query.filter(cls.version==version)

        return query

    @classmethod
    def add_or_update(cls, obj):
        """

        Args:
            obj (Package): package instance

        Returns:
            Package: updated package instance

        """
        _obj = cls.get_or_create(obj.id, save_new=False)
        _obj.update_using_obj(obj)
        _obj.save()
        return _obj

    @classmethod
    def get_or_create(cls, id, save_new=True):
        try:
            return cls.get(cls.id == id)
        except cls.DoesNotExist:
            new_obj = cls(id=id)
            if save_new:
                new_obj.save(force_insert=True)
            return new_obj

    def is_available_on_node(self, node_uuid):
        """
        Check whether the package is available on node identified by `node_uuid`,
        Args:
            node_uuid: node identifier

        Returns:
            bool: True, if package available else False.

        """
        return node_uuid in self.available_at

    def set_available_on_node(self, node_uuid):
        """
        Appends node identified by `node_uuid` into available nodes.

        Args:
            node_uuid: node identifier

        Returns:
            bool: always True, since no other possibility

        """

        if not self.is_available_on_node(node_uuid):
            self.available_at.append(node_uuid)
        return True

    def unset_available_on_node(self, node_uuid):
        """
        Remove node identified by `node_uuid` from available nodes.

        Args:
            node_uuid: node identifier

        Returns:
            bool: always True, since no other possibility

        """

        if self.is_available_on_node(node_uuid):
            self.available_at = [node for node in self.available_at if node != node_uuid]

        return True

    def save(self, force_insert=False, only=None):
        super().save(force_insert=True, only=only)


class Apt(Package):
    BASE_FIELD_MAP = {
        "id": "sha256",
        "name": "package",
    }

    filename = CharField(max_length=512, null=True)


class Npm(Package):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.id:
            self.id = "NPM:{}:{}".format(self.name, self.version)

import os
from peewee import Proxy
from peewee import SqliteDatabase

beiran_db_path = 'test.db'
db_file_exists = os.path.exists(beiran_db_path)
DB_PROXY = Proxy()
# init database object
database = SqliteDatabase(beiran_db_path)
DB_PROXY.initialize(database)

#bind database to model
Apt.bind(database)
Npm.bind(database)

database.drop_tables([Apt, Npm])
database.create_tables([Apt, Npm] )

p = Apt(
    id="123455",
    name="p1",
    version="v1",
)

p.save()


n = Npm(
    name="npm_p1",
    version="npm_v1",
)

n.save()

p_serialized = p.serialize()
assert 'sha256' in p_serialized

pp_serialized = p.deserialize(p.serialize()).serialize()
assert 'sha256' in pp_serialized

n_serialized = n.serialize()
assert 'id' in n_serialized
assert 'NPM:{}:{}'.format(n.name, n.version) == n.id