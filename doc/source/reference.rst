================
Beiran Reference
================

Beiran Project is composed of 4 main parts:

  - **Beiran Lib** includes common assets used by other parts
    such as common / base classes, methods, etc.
  - **Beiran Daemon** is the main functional part. As its name describes, it starts
    as a daemon and makes the running on host machine a member of beiran cluster.
    Also provides an API to clients and other beiran peers.
  - **Beiran CLI** is the command line interface to beiran daemons to manage
    the beiran cluster. It is one of the best friends of system admins.
  - **Beiran Plugins** allows cluster to manage packages of many systems like
    docker, apt, npm or pip.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   beiran
   beirand
   plugins


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
