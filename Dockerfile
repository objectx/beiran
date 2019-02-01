FROM python:3.6-alpine
LABEL maintainer="info@beiran.io"

RUN apk add --no-cache g++ python3-dev yajl make linux-headers
RUN apk add --no-cache libffi-dev  # dns discovery requires

COPY beiran /opt/beiran/beiran
COPY setup.py /opt/beiran/README.md/
COPY setup.py /opt/beiran/setup.py
COPY plugins/beiran_package_docker /opt/beiran_package_docker/

WORKDIR /opt/beiran
RUN python setup.py install

WORKDIR /opt/beiran_package_docker
RUN python setup.py install

VOLUME /var/lib/beiran
VOLUME /etc/beiran
