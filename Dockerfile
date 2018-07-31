FROM python:3.6-jessie
LABEL maintainer="info@beiran.io"
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip git curl make libsqlite3-dev libyajl-dev libyajl2

RUN mkdir -p /opt/beiran/beiran
WORKDIR /opt

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

ADD plugins/beiran_interface_k8s/requirements.txt /opt/beiran/r-k8s.txt
RUN pip install -r /opt/beiran/r-k8s.txt

# ADD plugins/beiran_package_npm/requirements.txt /opt/beiran/r-npm.txt
# RUN pip install -r /opt/beiran/r-npm.txt

ADD [ "beirand", "/opt/beiran/beirand" ]
ADD [ "beiran", "/opt/beiran/beiran" ]

ADD [ "plugins", "/opt/beiran/plugins" ]

ENV PYTHONPATH=/opt/beiran:/opt/beiran/plugins

VOLUME /var/lib/beiran
VOLUME /etc/beiran

CMD [ "python3", "-m", "beirand" ]
