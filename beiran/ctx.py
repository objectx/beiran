"""
A config loader
"""

import os
from os import path

import pytoml


DEFAULTS = {
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
    """Config class"""

    def get_config_from_defaults(self, key):
        """get config from default values"""
        return DEFAULTS[key]


    def get_config_from_env(self, ekey):
        """get config from environment variables"""
        return os.getenv(ekey)


    def get_config_from_file(self, ckey):
        """get config from config.toml"""
        keys = ckey.split('.')

        val = self.conf
        for key in keys:
            if not key in val:
                return None
            val = val[key]
        return val


    def get_config(self, ckey, ekey):
        """
        get the value which associated with ckey or ekey.
        ckey is a key which is used in config.toml
        ekey is the name of environment variables
        """
        val = self.get_config_from_env(ekey) if ekey is not None else None
        if val is not None:
            return val

        val = self.get_config_from_file(ckey) if ckey is not None else None
        if val is not None:
            return val

        val = self.get_config_from_defaults(ekey) if ekey is not None else None
        if val is not None:
            return val

        return None


    def __init__(self, **kwargs):
        """construct config object"""

        if 'path' in kwargs: # pylint: disable=consider-using-get
            config_path = kwargs['path']
        else:
            config_path = path.join(self.config_dir, 'config.toml')

        try:
            with open(config_path, 'r') as config_file:
                self.conf = pytoml.load(config_file)
        except FileNotFoundError as e:
            if 'path' not in kwargs:
                # Configuration file is not specificly requested
                # we tried the default path, and could not find the
                # file. means no config file.
                self.conf = dict()
                return
            raise e


    @property
    def config_dir(self):
        """
        CONFIG_DIR:
          A directory used to store configuration files.
        """
        return self.get_config(None, 'CONFIG_DIR')


    @property
    def data_dir(self):
        """
        DATA_DIR:
          A directory used to store some data.
        """
        return self.get_config('beiran.data_dir', 'DATA_DIR')


    @property
    def run_dir(self):
        """
        RUN_DIR:
          A directory used to store beirand.sock.
        """
        return self.get_config('beiran.run_dir', 'RUN_DIR')


    @property
    def cache_dir(self):
        """
        CACHE_DIR:
          A directory used to store cached files.
        """
        return self.get_config('beiran.cache_dir', 'CACHE_DIR')


    @property
    def log_level(self):
        """
        LOG_LEVEL:
        """
        return self.get_config('beiran.log_level', 'LOG_LEVEL')


    @property
    def log_file(self):
        """
        LOG_FILE:
          A path where beirand will store log files
        """
        return self.get_config('beiran.log_file', 'LOG_FILE')


    @property
    def discovery_method(self):
        """
        DISCOVERY_METHOD:
        """
        return self.get_config('beiran.discovery_method', 'DISCOVERY_METHOD')


    @property
    def listen_port(self):
        """
        LISTEN_PORT:
        """
        return self.get_config('beiran.listen_port', 'LISTEN_PORT')


    @property
    def package_plugins(self):
        """Get the list of the package plugins enabled"""
        conf = self.get_config('packages', None)
        if conf is None:
            return []

        keys = []
        for key, val in conf.items():
            if 'enabled' in val and val['enabled']:
                keys.append(key)
        return keys


    @property
    def interface_plugins(self):
        """Get the list of the interface plugins enabled"""
        conf = self.get_config('interfaces', None)
        if conf is None:
            return []

        keys = []
        for key, val in conf.items():
            if 'enabled' in val and val['enabled']:
                keys.append(key)
        return keys


    def get_package_config(self, key):
        """Get params of package plugin"""
        return self.get_config('packages.%s' % key, None)


    def get_interface_config(self, key):
        """Get params of interface plugin"""
        return self.get_config('interfaces.%s' % key, None)


config = Config() # pylint: disable=invalid-name
