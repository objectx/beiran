"""
A config loader
"""

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

