==================
Installation Guide
==================
Since Beiran is written in Python, you have many alternatives to install
and run Beiran:

    - Pip
    - Source Code
    - Inside a Docker Container
    - Package Managers

Pip
---
Beiran requires Python 3. It is **strongly recommended** using an isolated
environment to install Beiran with pip. After creating and activating a
virtual enviroment run the following command::

    $ pip install git+{beiran_git_latest_release}

And thats it. Beiran is ready to be configured and run.

Source Code
-----------
Beiran requires Python 3. It is **strongly recommended** using an isolated
environment to install Beiran from source code. After creating and activating
a virtual enviroment run the following command::

    $ git clone {beiran_git_latest_release} beiran
    $ cd beiran
    $ sudo python setup install

And thats it. Beiran is ready to be configured and run.


Docker
------
Simply run::

    $ git clone {beiran_git_latest_release} beiran
    $ cd beiran
    $ docker build -t beiran .

A successful build generates a docker image of which default `CMD` is
`python3 -m beiran.daemon`. So when you run a container, a daemon will start::

    $ docker run --name beiran
    Found plugins; []
    [2019-01-21 15:42:17,272] [beiran] INFO - Checking the data folder...
    [2019-01-21 15:42:17,272] [beiran] INFO - Initializing database...
    [2019-01-21 15:42:17,272] [beiran] INFO - sqlite file does not exist, creating file /var/lib/beiran/beiran.db!..
    [2019-01-21 15:42:17,273] [beiran] DEBUG - Checking tables
    [2019-01-21 15:42:17,273] [beiran] DEBUG - Checking a model
    [2019-01-21 15:42:17,274] [beiran] INFO - Database schema is not up-to-date, destroying
    [2019-01-21 15:42:17,274] [beiran] DEBUG - Checking a model
    [2019-01-21 15:42:17,275] [beiran] INFO - Database schema is not up-to-date, destroying
    [2019-01-21 15:42:17,275] [beiran] DEBUG - Checking tables done
    [2019-01-21 15:42:17,275] [beiran] INFO - db hasn't initialized yet, creating tables!..
    [2019-01-21 15:42:17,275] [beiran] INFO - creating database tables!...
    [2019-01-21 15:42:17,310] [beiran] INFO - uuid.conf file does not exist yet or is invalid, creating a new one here: /etc/beiran/uuid.conf
    [2019-01-21 15:42:17,310] [beiran] INFO - local nodes UUID is: ed790115533a4e7ab3b5fdc3999b2283
    [2019-01-21 15:42:17,314] [beiran] WARNING - Cannot find sync_version_file. Creating new file
    [2019-01-21 15:42:17,376] [beiran] INFO - local node added, known nodes are: {'ed790115533a4e7ab3b5fdc3999b2283': Node: 44c983c06cdd, Address: 172.17.0.2:8888, UUID: ed790115-533a-4e7a-b3b5-fdc3999b2283}
    [2019-01-21 15:42:17,384] [beiran] INFO - Starting Daemon HTTP Server...
    [2019-01-21 15:42:17,385] [beiran] INFO - Listening on unix socket: /var/run/beirand.sock
    [2019-01-21 15:42:17,386] [beiran] INFO - Listening on tcp socket: 0.0.0.0:8888

You can use same image by overriding container's `cmd`::

    $ docker run --name beiran python3 -m beiran --help
    Usage: __main__.py [OPTIONS] COMMAND [ARGS]...

      Manage Beiran Daemon and Beiran Cluster

      Please use --help option with commands and sub-commands to get their
      detailed usage.

      beiran [COMMAND] [SUB-COMMAND...] --help

      beiran --help
      beiran node --help
      beiran node probe --help
      beiran docker image list --help

      If you need, specify --config before everything:

      beiran --config /path/to/config.toml sub-command sub-command args options

    Options:
      --debug        Enable debug logs.
      --config TEXT  Path to a Beiran config file. It must be a TOML file.
      --help         Show this message and exit.

    Commands:
      node  Node operations.

