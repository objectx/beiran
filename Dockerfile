FROM python:3.6-jessie
LABEL maintainer="info@beiran.io"
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip git curl make libsqlite3-dev

RUN mkdir -p /opt/beiran/beiran
WORKDIR /opt

ADD beiran/requirements.txt /opt/beiran/r-lib.txt
RUN pip install -r /opt/beiran/r-lib.txt

ADD beiran_cli/requirements.txt /opt/beiran/r-cli.txt
RUN pip install -r /opt/beiran/r-cli.txt

ADD beirand/requirements.txt /opt/beiran/r-daemon.txt
RUN pip install -r /opt/beiran/r-daemon.txt

ADD plugins/beiran_discovery_dns/requirements.txt /opt/beiran/r-dns.txt
RUN pip install -r /opt/beiran/r-dns.txt

ADD plugins/beiran_discovery_zeroconf/requirements.txt /opt/beiran/r-zeroconf.txt
RUN pip install -r /opt/beiran/r-zeroconf.txt

ADD plugins/beiran_package_docker/requirements.txt /opt/beiran/r-docker.txt
RUN pip install -r /opt/beiran/r-docker.txt

# ADD plugins/beiran_package_npm/requirements.txt /opt/beiran/r-npm.txt
# RUN pip install -r /opt/beiran/r-npm.txt

ADD [ "beirand", "/opt/beiran/beirand" ]
ADD [ "beiran", "/opt/beiran/beiran" ]
ADD [ "beiran_cli", "/opt/beiran/beiran_cli" ]

ADD [ "plugins/beiran_discovery_dns", "/opt/beiran/beiran_discovery_dns" ]
ADD [ "plugins/beiran_discovery_zeroconf", "/opt/beiran/beiran_discovery_zeroconf" ]
ADD [ "plugins/beiran_package_docker", "/opt/beiran/beiran_package_docker" ]
# ADD [ "plugins/beiran_package_npm", "/opt/beiran/beiran_package_npm" ]

ENV PYTHONPATH=/opt/beiran

VOLUME /var/lib/beiran
VOLUME /etc/beiran

CMD [ "python3", "-m", "beirand" ]
