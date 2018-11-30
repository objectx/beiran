"""
Beiran Configuration Module
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
    """Configuration object holds configuration parameters as
    class properties. It overrides default values by values from
    config toml file or environment."""

    def get_config_from_defaults(self, key):
        """get config from default values"""
        return DEFAULTS[key]


    def get_config_from_env(self, ekey):
        """get config from environment variables"""
        return os.getenv("BEIRAN_{}".format(ekey))


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
        except FileNotFoundError as err:
            if 'path' not in kwargs:
                # Configuration file is not specificly requested
                # we tried the default path, and could not find the
                # file. means no config file.
                self.conf = dict()
                return
            raise err

    @property
    def config_dir(self):
        """
        A directory is used to store configuration files. The default
        value is ``/etc/beiran``.

        config.toml: section ``beiran``, key ``config_dir``

        Environment variable: ``BEIRAN_CONFIG_DIR``

        """
        return self.get_config(None, 'CONFIG_DIR')


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

    def get_enabled_plugins(self):
        """Get the list of the enabled plugins"""

        plugins = []
        env_config = self.get_config_from_env('BEIRAN_PLUGINS')
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

            return plugins

        for p_type in self.plugin_types:
            conf = self.get_config(p_type, None)
            if conf is None:
                return []

            for p_name, p_conf in conf.items():
                if 'enabled' in p_conf and p_conf['enabled']:
                    plugins.append({
                        'type': p_type,
                        'name': p_name,
                        'package': 'beiran_%s_%s' % (p_type, p_name)
                    })
        return plugins

    def get_plugin_config(self, p_type, name):
        """Get params of package plugin"""
        conf = self.get_config('%s.%s' % (p_type, name), None)
        if not conf:
            return dict()
        return conf

config = Config() # pylint: disable=invalid-name
