==================
Installation Guide
==================
Since Beiran is written in Python, you have many alternatives to install
and run Beiran:

    - Prebuilt Binary
    - Inside a Docker Container
    - Pip
    - Source Code

Prebuilt Binary
---------------
Each release, we publish a prebuilt executable binary which is ready to download and
use. Download the latest binary and copy it to a location that is in your `$PATH`
variable. Example below assumes `/usr/local/bin` directory exists on your system
and it is in `$PATH` variable::

    $ wget {latest_binary_download} -o beiran
    $ chmod +x beiran
    $ mv beiran /usr/local/bin

Make sure `yajl` package is installed on your system, see section `Yajl`_ section of this document below.

And test the installation::

    $ beiran --version


Docker
------
Pull and use it. You can access latest, stable or old versions. Main
docker repository address is::

    {docker_main_repo}

Please **do not forget** to add suitable tag for your need:

- `stable` for latest stable,
- `x.y.z` for version x.y.z,
- `latest` or none for master development branch.

Generally you do::

    $ docker pull {docker_main_repo}:stable
    $ docker run --name beiran {docker_main_repo}:stable --version

Entrypont of image is `beiran`, therefore you no need to repeat `beiran` while running.
You are supposed to add arguments, subcommands or parameters. So an equivalent command
of `beiran node list`::

    $ docker run --name beiran --rm {docker_main_repo}:stable node list


.. warning:: You can build your own docker image by using `Dockerfile` that you
   can find in root folder of source code. To do that please clone repo and run
   build command like below::

       $ docker build -t beiran .

   Unless you checkout a tag, the image will be produced latest development source
   code. If you need latest stable, please checkout to |latest_release_version|
   tag before building.

   Building image may take some time. And be aware that the name of the built image
   is `beiran` so, please replace



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

And that's it. Beiran is ready to be configured and run.



Yajl
++++
Some of fancy Beiran features require ``yajl`` package is installed on your system.
Most of Linux distributions, BSD and Mac OSX package managers have ``yajl`` package.
It is easy to install for most platforms.

Debian / Ubuntu::

    $ apt-get install libyajl2

Arch::

    $ pacman -S yajl

Mac OSX::

    $ brew install yajl  # homebrew
    $ port install yajl  # macports

Windows:

See https://github.com/lloyd/yajl/blob/master/BUILDING.win32