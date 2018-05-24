FROM python:3.6-jessie
LABEL maintainer="info@beiran.io"
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip git curl make libsqlite3-dev

RUN pip install flake8 flake8-docstrings pylint

ADD beiran/requirements.txt /root/r-lib.txt
RUN pip3 install -r /root/r-lib.txt

ADD beirand/requirements.txt /root/r-daemon.txt
RUN pip3 install -r /root/r-daemon.txt

ADD plugins/beiran_discovery_dns/requirements.txt /opt/beiran/r-dns.txt
RUN pip install -r /opt/beiran/r-dns.txt

ADD plugins/beiran_discovery_zeroconf/requirements.txt /opt/beiran/r-zeroconf.txt
RUN pip install -r /opt/beiran/r-zeroconf.txt

ADD plugins/beiran_package_docker/requirements.txt /opt/beiran/r-docker.txt
RUN pip install -r /opt/beiran/r-docker.txt
