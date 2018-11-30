==================
Contribution Guide
==================

What can I do?
--------------
Since Beiran is a free software and follows the free software
development conventions and patterns, it is open for any kind
of contribution.

    - if you find a bug, please report by creating an issue
    - if you need a new feature, an enhancement or any kind of
      changes, please create an issue,
    - if you have already fixed or implemented something, please
      create a merge request,
    - start a plugin project

How to code
-----------
Before starting any kind of contribution, please check our contribution
guidelines.

    - :doc:`Coding conventions <coding_style_guide>`
    - :doc:`Git practices <git_practices>`
    - :doc:`How to create an issue <issue>`

.. toctree::
   :hidden:
   :maxdepth: 1
   :titlesonly:

   Coding conventions <coding_style_guide>
   Git practices <git_practices>
   How to create an issue <issue>

Creating a Plugin
-----------------
Beiran's modular architecture allows adding new capabilities,
such as new package systems, different network discovery methods or
new interfaces for k8s like cluster orchestration systems.

Till now, we have 3 kinds of plugins and implementations are followings:

    - package plugins   (docker, apt, npm)
    - discovery plugins (dns, zeroconf)
    - interface plugins (k8s)

Please continue with :doc:`How to Create A plugin<how_to_create_a_plugin>`

.. toctree::
   :hidden:
   :maxdepth: 1
   :titlesonly:

   How to Create A plugin<how_to_create_a_plugin>

