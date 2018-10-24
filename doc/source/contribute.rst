==================
Contribution Guide
==================
Since Beiran is a free software and follows the free software
development conventions and patterns, it is open for any kind
of contribution. You can:

  - open an issue to discuss on a bug, a new feature, application
    design or architecture, please see [Creating an Issue document]
  - fork and create a merge request
  - start a new plugin project


Creating a Plugin
-----------------
Beiran's modular architecture allows adding new capabilities,
such as new package systems, different network discovery methods or
new interfaces for k8s like cluster orchestration systems.

Till now, we have 3 kinds of plugins and implementations are followings:

    - package plugins   (docker, apt, npm)
    - discovery plugins (dns, zeroconf)
    - interface plugins (k8s)

