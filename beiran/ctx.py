"""
A config loader
"""

import os
from os import path
import sys

import pytoml

from . import defaults

try:
    with open(path.join(defaults.CONFIG_DIR, 'config.toml'), 'r') as f:
        conf = pytoml.load(f)
except FileNotFoundError:
    print('file not found')
    sys.exit(1)
except Exception as e:
    print('something is wrong')
    print(e)
    sys.exit(1)


class Config:
    @staticmethod
    def get_params(envname, keyname, default):
        val = os.getenv(envname)
        if not val is None:
            return val

        keys = keyname.split('.')

        val = conf
        for key in keys[:-1]:
            val = val[key] if not val is None and key in val else None
        return val if not val is None else default

        
    @staticmethod
    def get_config_dir():
        return Config.get_params('CONFIG_DIR_PATH', 'beiran.config_dir', defaults.CONFIG_DIR)

    @staticmethod
    def get_data_dir():
        return Config.get_params('DATA_DIR_PATH', 'beiran.data_dir', defaults.DATA_DIR)

    @staticmethod
    def get_run_dir():
        return Config.get_params('RUN_DIR_PATH', 'beiran.run_dir', defaults.RUN_DIR)

    @staticmethod
    def get_cache_dir():
        return Config.get_params('CACHE_DIR_PATH', 'beiran.cache_dir', defaults.CACHE_DIR)

    @staticmethod
    def get_log_level():
        return Config.get_params('LOG_LEVEL', 'beiran.log_level', defaults.LOG_LEVEL)

    @staticmethod
    def get_log_file():
        return Config.get_params('LOG_FILE', 'beiran.log_file', defaults.LOG_FILE)

    @staticmethod
    def get_discovery_method():
        return Config.get_params('DISCOVERY_METHOD', 'beiran.discovery_method', None)

    @staticmethod
    def get_package_plugins():
        if not 'packages' in conf:
            return []

        l = []
        for key in conf['packages'].keys():
            if 'enabled' in conf['packages'][key] and conf['packages'][key]['enabled']:
                l.append(key)
        return l

    @staticmethod
    def get_interface_plugins():
        if not 'interfaces' in conf:
            return []

        l = []
        for key in conf['interfaces'].keys():
            if 'enabled' in conf['interfaces'][key] and conf['interfaces'][key]['enabled']:
                l.append(key)
        return l


    @staticmethod
    def get_plugin_config(name):
        return conf['package:%s' % name]

    @staticmethod
    def get_interface_config(name):
        return conf['interface:%s' % name]

