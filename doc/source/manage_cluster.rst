=====
Usage
=====

This document aims to help administrators to manage their Beiran
installation and cluster.

- Learn Beiran CLI and getting help
- Start / Configure Daemon
- Node Operations
- Docker Operations

Beiran CLI
----------
Beiran installation provides a **beiran** binary to manage
your cluster. It provides various commands and sub-commands along with
their help texts. You can append ``--help`` argument to whichever command
or sub-command you run. Whenever you need help, ask **beiran** itself and
append ``--help`` at the end of your command.

Examples::

    $ beiran --help
    $ beiran node --help
    $ beiran node list --help
    $ beiran docker --help
    $ beiran docker image list --help

An help text includes sections below:

usage
    standard cli usage syntax describing how to use the command

description
    information about what command does and some important notes / warnings

options
    list of available options that can be used command and their explanations

commands
    list of available sub-commands which can be append to current command


Sample output::

    $ beiran node --help

    Usage: cli.py node [OPTIONS] COMMAND [ARGS]...

      Node operations.

      List nodes in cluster, learn information about them.

      Please see sub-commands help.

    Options:
      --help  Show this message and exit.

    Commands:
      info          Print node details
      list          List cluster nodes
      probe         Probe a non-discovered node
      start_daemon  Starts the beiran daemon on current node.
      version       Prints the versions of components of current...


Start Daemon
------------
To start daemon just type::

    $ beiran node start_daemon

This command starts daemon using default configuration. Beiran can be
configured by a config file. If can specify a config file by typing::

    $ beiran --config /path/to/config.toml node start_daemon

You can find a sample config file and config parameters in
:doc:`configuration <configuration>` document.

Also Beiran can be configured by environment variables. If both a config
file and an environment variable specified, the latter suppresses.

Please see :doc:`configuration <configuration>` for details.

Node Operations
---------------

Listing Cluster Nodes
+++++++++++++++++++++
Listing nodes is one of the most used commands. It is easy::

    $ beiran node list
    UUID                              IP:Port          Version    Status?
    --------------------------------  ---------------  ---------  ---------
    84ae8786b9244c4fa53ecf0ca75e922d  172.18.0.4:8888  0.0.8d     ready
    b878fb07bb21449a85b6b108b48c11b6  172.18.0.3:8888  0.0.8d     online
    1a28428bf4e74901bbfabf9fec808e00  172.18.0.2:8888  0.0.8d     online
    1c5caefbfb114d7495da01f82bfcf113  172.18.0.5:8888  0.0.8d     online


UUID is the unique identifier of each node.

Status column indicates the current status of nodes. Status can be one of the
following: ``new``, ``init``, ``ready``, ``online``, ``offline``, ``connecting``,
``syncing``, ``closing``, ``lost``, ``unknown``.

Although ``ready`` means ``online``, it is there to distinguish the node on which
you are and running the command.

Please see ``beiran.models.Node`` object in beiran reference for futher details.

Node Information
++++++++++++++++
You can get information about any node with help of ``info`` sub-command::

    $ beiran node info b878fb07bb21449a85b6b108b48c11b6
    Item               Value
    -----------------  ------------------------------------------
    uuid               b878fb07bb21449a85b6b108b48c11b6
    hostname           02a381c2e904
    ip_address         172.18.0.3
    ip_address_6
    port               8888
    os_type            Linux
    os_version         #1 SMP PREEMPT Sat Dec 8 13:49:11 UTC 2018
    architecture       x86_64
    version            0.0.8d
    status             online
    last_sync_version  2
    address            beiran+http://172.18.0.3:8888

If you do not specift a node UUID, it print outs the information of current node::

    $ beiran node info
    Item               Value
    -----------------  --------------------------------------------------------------
    uuid               84ae8786b9244c4fa53ecf0ca75e922d
    hostname           bb6536043849
    ip_address         172.18.0.4
    ip_address_6
    port               8888
    os_type            Linux
    os_version         #1 SMP PREEMPT Sat Dec 8 13:49:11 UTC 2018
    architecture       x86_64
    version            0.0.8d
    status             ready
    last_sync_version  2
    address            beiran+http://172.18.0.4:8888#84ae8786b9244c4fa53ecf0ca75e922d


Version of Node Components
++++++++++++++++++++++++++
Sometimes you want to know the versions of beiran and its components to
verify installation or while investigating a problem::

    $ beiran node version
    CLI Version: 0.0.8d
    Library Version: 0.0.8d
    Server Socket: http+unix:///var/run/beirand.sock
    Daemon Version: 0.0.8d

This command is also useful to check berian node after fresh installation.

Probe Node
++++++++++
Manually probing node is necessary when things go wrong. Generally, **Beiran**
nodes should be able to discover themselves automatically and it must not require
any manual intervention.

It is not only in case of a failure, also in some test / development cases,
manually probing a node can be necessary. In these cases you can use probe
sub-command, such below::

    $ beiran node probe beiran+http://172.18.0.4:8888
    Node is already synchronized!

    $ beiran node probe beiran+http://172.18.0.4:8888
    Status: OK


Docker Operations
-----------------
You can manage docker images and layers with docker plugins cli commands. To
list available commands simple type::

    $ beiran docker --help
    Usage: beiran docker [OPTIONS] COMMAND [ARGS]...

    Docker Commands.

    Manage your docker images and layers in cluster.

    Please see sub-commands help texts.

    Options:
      --help  Show this message and exit.

    Commands:
      image  Manage Docker Images
      layer  Manage Docker Layers


List / Pull Images
++++++++++++++++++
Get a list of downloaded images::

    $ beiran docker image list
    Tags    ID    Size    Availability
    ------  ----  ------  --------------

``Tags``, ``ID`` and ``Size`` are properties originated from docker daemon, while
``Availability`` is from Beiran indicating the nodes on which the image exists.


Pull an image::

    $ beiran docker image pull redis

You can use options ``--from`` and ``--force`` if you want to force client pull
from specific node and ``--progress`` to show download progress.

List downloaded image::

    $ beiran docker image list
    Tags          ID                                                                       Size     Availability
    ------------  -----------------------------------------------------------------------  -------  --------------
    redis:latest  sha256:5958914cc55880091b005658a79645a90fd44ac6a33abef25d6be87658eb9599  90.5MiB  local


Pull command has some useful options. Some of them which might be used more
frequently are below, you can see a list of all options in command's help::

    $ beiran docker image pull --help
    ...

Other options:

--from

    | You can specify a node by passing UUID to pull an image.
    | e.g::

    |    ``$ beiran docker image pull --from NODE_UUID``

--wait

    | By default pull command uses async client and pull
    | operation is done at backgorund. `beiran` exits
    | successfully saying::

    |    ``$ beiran docker image pull --wait hello-world``
    |      Pulling image hello-world from None!
    |      Process is started

    | While pull in progress, you can keep using terminal
    | and run other commands.

    | But if you want to wait or be sure what is happening
    | you can use this option.

--progress

    | This option adds a progress bar to output showing pull
    | operation status approximately.
