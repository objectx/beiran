"""
A config loader
"""

from os import path
import sys

import pytoml

import defaults


try:
    with open(path.join(defaults.CONFIG_FOLDER, 'config.toml'), 'r') as f:
        _conf = pytoml.load(f)
except FileNotFoundError:
    print('file not found')
    sys.exit(1)
except:
    print('something is wrong')
    sys.exit(1)

if __name__ == '__main__':
    print(_conf)
