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

    pip install beiran

And thats it. Beiran is ready to be configured and run.

Source Code
-----------
Beiran requires Python 3. It is **strongly recommended** using an isolated
environment to install Beiran from source code. After creating and activating
a virtual enviroment run the following command::

    git clone git.rlab.io/beiran/beiran.git beiran
    cd beiran
    sudo python setup install

And thats it. Beiran is ready to be configured and run.


Docker
------
Simply run::

    docker run --name beiran rlab/beiran


Package Managers
----------------
You can install Beiran via your package manager, if it is listed
below. Beiran pre-build packages are available for following systems:

    - Debian
    - Ubuntu
    - Devuan
    - RHEL
    - Centos
    - Arch Linux

So if yours is an Ubuntu, you can install the command as below::

    apt-get install beiran

