# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Beiran Configuration Module
"""

import os
import pkgutil
import logging
from typing import List, Union, Any

import toml

LOGGER = logging.getLogger()

DEFAULTS = {
    'LISTEN_PORT': 8888,
    'LISTEN_ADDRESS': '0.0.0.0',
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
    """Configuration object holds configuration parameters as
    class properties. It overrides default values by values from
    config toml file or environment."""

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
            os.getenv("BEIRAN_{}".format(ekey)) or \
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
                return toml.load(cfile)
        except FileNotFoundError:
            LOGGER.error(
                "Could not found config file at location: %s",
                config_file)
        except toml.decoder.TomlDecodeError as err:
            LOGGER.error(
                "Could not load config toml file, "
                "please check your config file syntax. %s", err
            )

    @property
    def config_dir(self):
        """
        A directory is used to store configuration files. The default
        value is ``/etc/beiran``.

        config.toml: section ``beiran``, key ``config_dir``

        Environment variable: ``BEIRAN_CONFIG_DIR``

        """
        return self.get_config('beiran.config_dir', 'CONFIG_DIR')


    @property
    def data_dir(self):
        """
        A directory is used to store miscellaneous beiran data. The
        default value is ``/var/lib/beiran``.

        config.toml: section ``beiran``, key ``data_dir``

        Environment variable: ``BEIRAN_DATA_DIR``

        """
        return self.get_config('beiran.data_dir', 'DATA_DIR')


    @property
    def run_dir(self):
        """
        A directory used to store beirand.sock. The default value is
        ``/var/run``.

        config.toml: section ``beiran``, key ``run_dir``

        Environment variable: ``BEIRAN_RUN_DIR``

        """
        return self.get_config('beiran.run_dir', 'RUN_DIR')

    @property
    def cache_dir(self):
        """
        A directory used to store cached files. The default value is
        ``/var/cache/beiran``.

        config.toml: section ``beiran``, key ``cache_dir``

        Environment variable: ``BEIRAN_CACHE_DIR``

        """
        return self.get_config('beiran.cache_dir', 'CACHE_DIR')

    @property
    def log_level(self):
        """
        Logging level. The default value is ``DEBUG``. Beiran use
        Python Standard Lib's logging module. Standard logging level
        strings are valid. Please see logging module in standard
        library further details.

        config.toml: section ``beiran``, key ``log_level``

        Environment variable: ``BEIRAN_LOG_LEVEL``

        """
        return self.get_config('beiran.log_level', 'LOG_LEVEL')

    @property
    def log_file(self):
        """
        A file path for storing logs. The default value is
        ``/var/log/beirand.log``.

        config.toml: section ``beiran``, key ``log_file``

        Environment variable: ``BEIRAN_LOG_FILE``

        """
        return self.get_config('beiran.log_file', 'LOG_FILE')

    @property
    def discovery_method(self):
        """
        Service discovery method for beiran daemons to find each
        others. The default value is ``zeroconf``. It can be eighter
        ``zeroconf``, ``dns`` or any other discovery plugins name.

        config.toml: section ``beiran``, key ``discovery_method``

        Environment variable: ``BEIRAN_DISCOVERY_METHOD``

        """
        return self.get_config('beiran.discovery_method', 'DISCOVERY_METHOD')

    @property
    def listen_address(self):
        """
        Beiran daemon's listen address. It can be any valid IP address.
        The default value is ``0.0.0.0``

        config.toml: section ``beiran``, key ``listen_address``

        Environment variable: ``BEIRAN_LISTEN_ADDRESS``

        """
        return self.get_config('beiran.listen_address', 'LISTEN_ADDRESS')

    @property
    def listen_port(self):
        """
        Beiran daemon's running port. It can be any available tcp
        port on host. The default value is ``8888``

        config.toml: section ``beiran``, key ``listen_port``

        Environment variable: ``BEIRAN_LISTEN_PORT``

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
