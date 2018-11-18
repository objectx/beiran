===================
Configuration Guide
===================

Beiran configuration is managed by module `config.py`. This module
provides a global ``config`` object holding all configuration
parameters.

The object can be imported and used as::

    import logging
    from beiran.config import config

    ...

    logging.set_level(config.log_level)

Config object can load all values from a toml file and / or
environment. Environment values override all others, if a
corresponding value provided.

A sample `config.toml` is included consisting all possible parameters
with default values. You can simply copy from installation directory
to an editable path. Installation directory's location depends on
your platform and installation way.

Tune `config.toml` and set ``BEIRAN_CONF_FILE`` env variable
pointing your tuned file.

Also you can override `config.toml` values with environment variables.
All environment variables starts with ``BEIRAN_`` and you can find a
a list of them below.

.. autoclass:: beiran.config.Config
    :members:
    :exclude-members: get_config_from_defaults, get_config_from_env, get_config_from_file, get_config, get_plugin_config, get_enabled_plugins, plugin_types
    :show-inheritance:
