FROM python:3.6-alpine
LABEL maintainer="info@beiran.io"

RUN apk add --no-cache g++ python3-dev yajl yajl-dev make linux-headers
RUN apk add --no-cache libffi-dev  # dns discovery requires

COPY beiran /opt/beiran/beiran
COPY README.md /opt/beiran/README.md
COPY setup.py /opt/beiran/setup.py
COPY plugins/beiran_package_docker /opt/beiran_package_docker/
COPY plugins/beiran_interface_k8s /opt/beiran_interface_k8s/

WORKDIR /opt/beiran
RUN python setup.py install

WORKDIR /opt/beiran_package_docker
RUN python setup.py install

WORKDIR /opt/beiran_interface_k8s
RUN python setup.py install

VOLUME /var/lib/beiran
VOLUME /etc/beiran

COPY beiran/config.toml /etc/beiran/config.toml

ENTRYPOINT ["beiran", "--config", "/etc/beiran/config.toml"]
