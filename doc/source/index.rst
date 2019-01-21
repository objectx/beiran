.. Beiran documentation master file, created by
   sphinx-quickstart on Thu Jan 11 19:20:42 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

==================================
Welcome to Beiran's documentation!
==================================

.. toctree::
   :maxdepth: 2
   :caption: Beiran Documentation
   :hidden:
   :includehidden:

   Home <self>
   Installation Guide <installation>
   Configuration Guide <configuration>
   Usage <usage>
   How to contibute <contribute>
   How to create a plugin <how_to_create_a_plugin>
   Using Kubernetes with Beiran <using_kubernetes_with_beiran>
   Beiran Reference <reference>

   Index <genindex>

Beiran is a set of tools for replacing distribution layer
of package management systems.

.. warning:: At this moment, it is under heavy development and we will be
 announcing an alpha release soon.

It aims provide out-of-box experience to fit along with
existing tools, focuses on security, decentralization and availability.

Beiran creates a cluster of nodes on an underlying p2p network to share
``packages``. Package refers to any binary objects like docker images,
docker layers, apt's deb archives or tar archives.

By version alpha, only docker, apt and npm systems will be supported.
We expect to support more with help of community. If you are interested
in starting a plugin, please follow our :doc:`contribution guide </contribute>`
document.

Getting Started
+++++++++++++++

Installation, configuration and how to manage a Beiran cluster documents
are for you, if you are interested in just trying or starting to
use Beiran on your environment:

  - :doc:`How to install Beiran <installation>`
  - :doc:`Manage Beiran Cluster <usage>`
  - :doc:`Configuration Guide <configuration>`

And you can go on with contribution guide, if you want to help with current
codebase, issues, and documentation or starting a new package plugin:

  - :doc:`How to contibute <contribute>`

While developing, you may want to check Beiran Reference which is generated
from inline doc strings and gives detailed information about codebase:

  - :doc:`Beiran Reference <reference>` (Auto generated inline doc strings)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
