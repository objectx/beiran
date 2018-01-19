beiran poc
==========

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

## Build

```
./make.sh build_daemon_image
```

## Using (PoC)

```
cd beirand
docker-compose up -d
```

CURL'ing unix socket

```
curl --no-buffer -XGET --unix-socket /var/run/beirand.sock http://localhost/events
```
