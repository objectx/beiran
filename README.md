# beiran poc

![Build Status](https://drone.rsnc.io/api/badges/rlab/beiran/status.svg)

## What is beiran

- [Draft Spec](Draft-Spec.md)
- [Roadmap](ROADMAP.md)

## Python libraries and tools

- [asyncio](https://docs.python.org/3/library/asyncio.html) (event loop)
- [tornado](https://www.tornadoweb.org) (http and network library)
- [pytest](https://pytest.org) (testing)
- [docker](https://github.com/docker/docker-py) (for querying docker daemon)
- [zeroconf](https://pypi.python.org/pypi/zeroconf) (for local node discovery)
- [click](https://pypi.python.org/pypi/click) (for cli options, commands)

## Docker Setteings

### Install Docker

beiran is run on the machine on which Docker is installed. 

### Change Storage Driver

You need to use `overlay2`. Stop your Docker daemon.

```sh
systemctl stop docker.service 
```

Edit Systemed Service File. (/lib/systemd/system/docker.service)

```
ExecStart=/usr/bin/dockerd -H fd:// -s overlay2
```

Start Docker daemon. 

```sh
systemctl daemon-reload 
systemctl start docker.service
```

Check your Storage Driver.

```sh
$ docker info
Containers: 0
 Running: 0
 Paused: 0
 Stopped: 0
Images: 0
Server Version: 17.03.2-ce
Storage Driver: overlay2
...
```

## Virtualenv

### - Setup

```sh
mkdir env
virtualenv env --python=/usr/bin/python3.6
source env/bin/activate
pip install -r beirand/requirements.txt
pip install -r beiran/requirements.txt
pip install -r beiran_cli/requirements.txt
pip install ipython
ln -s $(pwd)/beirand/beirand env/lib/python3.6/site-packages/
ln -s $(pwd)/beiran env/lib/python3.6/site-packages/
ln -s $(pwd)/beiran_cli env/lib/python3.6/site-packages/beiran_cli
```

#### - Settings (Environment Variables)

```sh
export LOG_LEVEL=DEBUG
export LOG_FILE=$(pwd)/beirand.log
export BEIRAN_SOCK=$(pwd)/beirand.sock
export BEIRAN_DB_PATH=$(pwd)/beiran.db
export CONFIG_FOLDER_PATH=$(pwd)
```

#### - Start Daemon

```sh
source env/bin/activate
python -m beirand
```

or as root (potentially UNSAFE) to allow beiran to peek into /var/lib/docker

```sh
source env/bin/activate
sudo -E python -m beirand
```

#### - Use cli

```sh
python -m beiran_cli image list
```

## Build

```sh
./make.sh build_daemon_image
```

## Environment variables

All has default values.

```sh
LISTEN_INTERFACE
LISTEN_ADDR
HOSTNAME
BEIRAN_SOCK
```

## Using (PoC)

```sh
cd beirand
docker-compose up --scale beirand=3
```

CURL'ing unix socket

```sh
curl --no-buffer -XGET --unix-socket /var/run/beirand.sock http://localhost/events
```
