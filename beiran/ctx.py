"""
A config loader
"""

import os
from os import path
import sys

import pytoml


defaults = {
    'LISTEN_PORT': 8888,
    'LOG_FILE': '/var/log/beirand.log', 
    'LOG_LEVEL': 'DEBUG',
    'CONFIG_DIR': '/etc/beiran',
    'DATA_DIR': '/var/lib/beiran',
    'CACHE_DIR': '/var/cache/beiran',
    'RUN_DIR': '/var/run',
    'DISCOVERY_METHOD': 'zeroconf',
}


class Config:
    def get_config_from_defaults(self, key):
        return defaults[key]


    def get_config_from_env(self, key):
        return os.getenv(key)


    def get_config_from_file(self, key):
        ps = key.split('.')

        val = self.conf
        for p in ps[:-1]:
            if not p in val:
                return None
            val = val[p]
        return val


    def get_config(self, ckey, ekey):
        """
        get the value which associated with ckey or ekey.
        ckey is a key which is used in config.toml
        ekey is a key which is used in environment variables
        """
        val = self.get_config_from_env(ekey) if ekey != None else None
        if val != None:
            return val

        val = self.get_config_from_file(ckey) if ckey != None else None
        if val != None:
            return val

        val = self.get_config_from_defaults(ekey) if ekey != None else None
        if val != None:
            return val

        return None


    def __init__(self, **kwargs):
        if 'path' in kwargs:
            config_path = kwargs['path']
        else:
            config_path = path.join(self.config_dir, 'config.toml')
            
        with open(config_path, 'r') as f:
            self.conf = pytoml.load(f)


    @property
    def config_dir(self):
        return self.get_config(None, 'CONFIG_DIR')


    @property
    def data_dir(self):
        return self.get_config('beiran.data_dir', 'DATA_DIR')


    @property
    def run_dir(self):
        return self.get_config('beiran.run_dir', 'RUN_DIR')


    @property
    def cache_dir(self):
        return self.get_config('beiran.cache_dir', 'CACHE_DIR')


    @property
    def log_level(self):
        return self.get_config('beiran.log_level', 'LOG_LEVEL')


    @property
    def log_file(self):
        return self.get_config('beiran.log_file', 'LOG_FILE')


    @property
    def discovery_method(self):
        return self.get_config('beiran.discovery_method', 'DISCOVERY_METHOD')


    @property
    def listen_port(self):
        return self.get_config('beiran.listen_port', 'LISTEN_PORT')


    @property
    def package_plugins(self):
        d = self.get_config('packages', None)
        if d is None:
            return []

        l = []
        for key, val in d:
            if 'enabled' in val and val['enabled']:
                l.append(key)
        return l


    @property
    def interface_plugins(self):
        d = self.get_config('interfaces', None)
        if d is None:
            return []

        l = []
        for key, val in d:
            if 'enabled' in val and val['enabled']:
                l.append(key)
        return l


    def get_plugin_config(self, key):
        return self.get_config('packages.%s' % key, None)

    def get_interface_config(self, key):
        return self.get_config('packages.%s' % key, None)


config = Config()
