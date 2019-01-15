===================
Configuration Guide
===================

Beiran configuration is managed by module `config.py`. This module
provides a global ``config`` object holding all configuration
parameters.

Config object loads all values from a toml file and / or
environment variables. Environment variables override all others,
if a corresponding value provided.

All environment variables starts with ``BEIRAN_`` and you can find a
a list of them in module's documentation section below.

A sample `config.toml` file is below. Copy, edit and use it:

.. literalinclude:: ../config.toml
   :language: python
   :emphasize-lines: 12,15-18
   :linenos:


Also, a copy of `config.toml` can be found in installation
directory. Installation directory's location depends on your platform and
installation way.

.. warning:: Do not forget setting ``BEIRAN_CONF_FILE`` env
  variable pointing your tuned file or using parameter `--config`
  if you prefer `beiran` cli binary.



.. autoclass:: beiran.config.Config
    :members:
    :exclude-members: get_config_from_defaults, get_config_from_env, get_config_from_file, get_config, get_plugin_config, get_enabled_plugins, plugin_types
    :show-inheritance:
