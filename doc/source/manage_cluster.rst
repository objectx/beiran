=====================
Manage Beiran Cluster
=====================

This document aims to help administrators to manage their Beiran
installation and cluster.

- Learn Beiran CLI and getting help
- Start / Configure Daemon
- Node Operations

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
Listing nodes is one of the most used commands. It is easy:
    $ beiran node list

