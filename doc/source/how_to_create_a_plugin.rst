=============================
How to create a Beiran Plugin
=============================
Before starting, please check our :doc:`contribution guideline <contribution>`.

Creating a Plugin
-----------------
Beiran's modular architecture allows adding new capabilities,
such as new package systems, different network discovery methods or
new interfaces for k8s like cluster orchestration systems.

Till now, we have 3 kinds of plugins and implementations are followings:

    - package plugins   (docker, apt, npm)
    - discovery plugins (dns, zeroconf)
    - interface plugins (k8s)

A plugin basically extends Beiran Daemon's objects such as API endpoints,
discovery classes, data models, cli commands, etc. Also Beiran library
has some useful classes which are ready to use while developing a
package plugin and other kinds of plugins as well.

A Beiran plugin is basically a python package which contains python
modules such as:

    - plugin_name.py (eg. docker.py)
    - models.py
    - api.py
    - cli_plugin_name.py (eg. cli_docker.py)
    - util.py
    - ...

Most of them are optional. `plugin_name.py` contains the main object
which is extended on base plugin classes. For example base class would be
`BasePackagePlugin`, if it is a package plugin or `BaseDiscoveryPlugin`
if it is a discovery plugin.

`models.py` is for data models and unless lack of extraordinary situation,
its objects must be extended on base model class which can be easily imported
on path `beiran.models.base.BaseModel`

The `api.py` module includes http / ws endpoints which are appended to daemon's
main endpoint set. Beiran use `Tornado` to serve http / ws endpoints. So handlers
and enpoint routes must be written how `Tornado` requires.

Plugin's routes must be prefixed by suitable name to make them distinguishable.
For example docker plugin's routes have `docker`::

    ROUTES = [
        (r'/docker/images', ImageList),
        (r'/docker/layers', LayerList),
        (r'/docker/images/(.*(?<!/info)$)', ImagesTarHandler),
        (r'/docker/images/(.*/info)', ImageInfoHandler),
        (r'/docker/layers/([0-9a-fsh:]+)', LayerDownload),
    ]


Beiran have also some base handlers which are ready to use and allow
developers to handle easily many cases, such as `RPCEndpoint`,
`JSONEndpoint`.



The `cli_plugin_name.py` module is for command line interface methods. This module's
methods (commands and sub-commands) are appended as a sub-command named `plugin_name`
to main command beiran, such as::

    $ beiran plugin_name sub-command
    $ beiran plugin_name sub-command sub-command

The cli module must have an empty method called `cli` for auto discovery and import
purposes. For example docker plugin cli modlue `cli_docker.py` has method below::

    @click.group("docker", short_help="docker subcommands")
    def cli():
        """Main subcommand method."""
        pass

Other modules are arbitrary and depends on how your implementation is structured.
