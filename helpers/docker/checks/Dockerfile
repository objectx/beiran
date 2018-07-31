FROM python:3.6-alpine

RUN apk add --no-cache \
    git \
    openssh-client \
    python-dev \
    gcc \
    g++ \
    linux-headers \
    musl-dev \
    make

RUN pip install flake8==3.5.0 flake8-docstrings==1.3.0 pylint==2.0.0 bandit==1.4.0 mypy

ADD beiran/requirements.txt /opt/beiran/r-lib.txt
RUN pip install -r /opt/beiran/r-lib.txt

ADD beirand/requirements.txt /opt/beiran/r-daemon.txt
RUN pip install -r /opt/beiran/r-daemon.txt

ADD plugins/beiran_discovery_dns/requirements.txt /opt/beiran/r-dns.txt
RUN pip install -r /opt/beiran/r-dns.txt

ADD plugins/beiran_discovery_zeroconf/requirements.txt /opt/beiran/r-zeroconf.txt
RUN pip install -r /opt/beiran/r-zeroconf.txt

ADD plugins/beiran_package_docker/requirements.txt /opt/beiran/r-docker.txt
RUN pip install -r /opt/beiran/r-docker.txt
