"""
A config loader
"""

import os
from os import path
import sys

import pytoml

from . import defaults

try:
    with open(path.join(defaults.CONFIG_FOLDER, 'config.toml'), 'r') as f:
        conf = pytoml.load(f)
except FileNotFoundError:
    print('file not found')
    sys.exit(1)
except:
    print('something is wrong')
    sys.exit(1)


class Config:
    @staticmethod
    def get_params(envname, keyname, default):
        val = os.getenv(envname)
        if not val is None:
            return val

        if keyname in conf['beiran']:
            return conf['beiran'][keyname]
        else:
            return default

        
    @staticmethod
    def get_config_folder():
        return Config.get_params('CONFIG_FOLDER_PATH', 'config_folder', defaults.CONFIG_FOLDER)

    @staticmethod
    def get_data_folder():
        return Config.get_params('DATA_FOLDER_PATH', 'data_folder', defaults.DATA_FOLDER)

    @staticmethod
    def get_log_level():
        return Config.get_params('LOG_LEVEL', 'log_level', defaults.LOG_LEVEL)

    @staticmethod
    def get_log_file():
        return Config.get_params('LOG_FILE', 'log_file', defaults.LOG_FILE)

    @staticmethod
    def get_discovery_method():
        return Config.get_params('DISCOVERY_METHOD', 'discovery_method', None)

    @staticmethod
    def get_package_plugins():
        return conf['beiran']['package_plugins']

    @staticmethod
    def get_interface_plugins():
        return conf['beiran']['interface_plugins']

    @staticmethod
    def get_plugin_config(name):
        return conf['package:%s' % name]

    @staticmethod
    def get_interface_config(name):
        return conf['interface:%s' % name]

