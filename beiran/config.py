"""
A config loader
"""

import os
import pkgutil

from typing import List, Union, Any
import logging

import pytoml

LOGGER = logging.getLogger()


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


class ConfigMeta(type):
    """
    Metaclass for config object.
    """
    _instances: dict = {}

    def __new__(mcs, *args, **kwargs):
        if mcs not in mcs._instances:
            mcs._instances[mcs] = super(
                ConfigMeta, mcs).__new__(mcs, *args, **kwargs)

        return mcs._instances[mcs]


class Config(metaclass=ConfigMeta):
    """Config class"""

    def __init__(self, config_file=None):
        """construct config object"""
        self.conf = dict()
        self._enabled_plugins = list()

        if config_file:
            self.conf = self.load_from_file(config_file)

    def get_config_from_file(self, ckey=None):
        """get config from config.toml"""
        if ckey is None:
            return None

        keys = ckey.split('.')

        val = self.conf
        for key in keys:
            if not key in val:
                return None
            val = val[key]
        return val

    def get_config(self, ckey: str = '', ekey: str = '') -> Union[Any, object]:
        """
        Seek for config val through environment and config depending
        on given keys.

        One of the args `ckey`, `ekey` must be specified.

        Args:
            ckey: key in config file
            ekey: key in environment

        Returns:
            str, dict: value

        """
        if not any([ckey, ekey]):
            return None

        return \
            os.getenv(ekey) or \
            self.get_config_from_file(ckey) or \
            DEFAULTS.get(ekey, None)

    @staticmethod
    def load_from_file(config_file: str):
        """
        Load config values from given file
        Args:
            config_file (str): file path

        Returns:

        """
        try:
            with open(config_file, 'r') as cfile:
                return pytoml.load(cfile)
        except FileNotFoundError:
            LOGGER.error(
                "Could not found config file at location: %s",
                config_file)
        except pytoml.core.TomlError as err:
            LOGGER.error(
                "Could not load config toml file, "
                "please check your config file syntax. %s", err
            )


    @property
    def config_dir(self):
        """
        CONFIG_DIR:
          A directory used to store configuration files.
        """
        return self.get_config('beiran.config_dir', 'CONFIG_DIR')


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
    def plugin_types(self):
        """Return the list of supported plugin types"""
        return ['package', 'interface', 'discovery']

    @property
    def enabled_plugins(self) -> List[dict]:
        """
        Returns enabled plugin list.

        Returns:
            (list): enabled plugins specified in config file or env

        """
        return self._enabled_plugins or self.get_enabled_plugins()

    def get_enabled_plugins(self):
        """Get the list of the enabled plugins"""

        plugins = []
        env_config = os.getenv('BEIRAN_PLUGINS')
        if env_config:
            try:
                for p_package in env_config.split(','):
                    (p_type, p_name) = p_package.split('.')
                    if p_type not in self.plugin_types:
                        raise Exception("Unknown plugin type: %s" % (p_type))
                    plugins.append({
                        "type": p_type,
                        "name": p_name,
                        "package": 'beiran_%s_%s' % (p_type, p_name)
                    })
            except Exception:
                raise Exception("Cannot parse BEIRAN_PLUGINS variable from environment")

            self._enabled_plugins = plugins  # cache it!
            return plugins

        for p_type in self.plugin_types:
            conf = self.get_config(ckey=p_type)
            if not conf:
                continue

            for p_name, p_conf in conf.items():
                if 'enabled' in p_conf and p_conf['enabled']:
                    plugins.append({
                        'type': p_type,
                        'name': p_name,
                        'package': 'beiran_%s_%s' % (p_type, p_name)
                    })
        self._enabled_plugins = plugins
        return plugins

    def get_plugin_config(self, p_type, name):
        """Get params of package plugin"""
        conf = self.get_config(ckey='%s.%s' % (p_type, name))
        if not conf:
            return dict()
        return conf

    @staticmethod
    def get_installed_plugins() -> List[str]:
        """
        Iterates installed packages and modules to match beiran modules.

        Returns:
            list: list of package name of installed beiran plugins.

        """

        return [
            name
            for finder, name, ispkg
            in pkgutil.iter_modules()
            if name.startswith('beiran_')
        ]

    def __call__(self, config_file=None):
        """
        Allow reinitialize instance with a new config file

        Args:
            config_file: config file path

        Returns:
            self: reinitialized instance

        """
        return self.__init__(config_file)


config = Config() # pylint: disable=invalid-name
