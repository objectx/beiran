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

## Docker Settings

### Install Docker

beiran is run on the machine on which Docker is installed.

### Change Storage Driver

You need to use `overlay2`. Stop your Docker daemon.

```sh
$ systemctl stop docker.service
```

Edit Systemd Service File. (/lib/systemd/system/docker.service)

```bash
ExecStart=/usr/bin/dockerd -H fd:// -s overlay2
```

Start Docker daemon.

```sh
$ systemctl daemon-reload
$ systemctl start docker.service
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

### Install tar-split

beiran's docker plugin needs [tar-split](https://github.com/vbatts/tar-split) now. Please create the binary file and set `tar_split_path`;

```
$ go get github.com/vbatts/tar-split
$ export BEIRAN_PACKAGE_DOCKER_CONFIG='tar_split_path=path/to/tar-split'
```

Or, copy the binary file to the plugin directory (deafult `tar-split_path` is there)

```
$ go get github.com/vbatts/tar-split
$ cp path/to/tar-split plugins/beiran_package_docker/
```


## Virtualenv

### - Setup

This will setup a virtualenv under `env` folder here

```sh
$ ./dev.sh
```

#### - Settings (Environment Variables)

```sh
export BEIRAN_LOG_LEVEL=DEBUG
export BEIRAN_LOG_FILE=$(pwd)/beirand.log
export BEIRAN_SOCKET_FILE=$(pwd)/beirand.sock
export BEIRAN_DB_FILE=$(pwd)/beiran.db
export BEIRAN_CONFIG_DIR=$(pwd)
```

#### - Start Daemon

```sh
./dev.sh
beirand
```

or as root (potentially UNSAFE) to allow beiran to peek into /var/lib/docker

```sh
./dev.sh
sudo -E beirand
```

#### - Use cli

```sh
beiran image list
```

## Build

```sh
docker-compose build
```

## Environment variables

All has default values.

```
BEIRAN_LISTEN_INTERFACE
BEIRAN_LISTEN_ADDRESS
BEIRAN_HOSTNAME
BEIRAN_SOCKET_FILE
```

## Using (PoC)

```sh
docker-compose up
```

CURL'ing unix socket

```sh
curl --no-buffer -XGET --unix-socket /var/run/beirand.sock http://localhost/events
```
