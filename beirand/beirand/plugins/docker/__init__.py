"""
Import all plugin classes to make import statements clear.
"""
from .docker import DockerPackaging

PLUGIN_NAME = 'docker'
PLUGIN_TYPE = 'package'
PLUGIN_CLASS = DockerPackaging
