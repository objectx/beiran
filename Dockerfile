FROM golang:1.11.6-stretch AS tar-split-builder
RUN go get -d github.com/vbatts/tar-split/cmd/tar-split
RUN go build -o /tar-split -a -ldflags '-extldflags "-static"' /go/src/github.com/vbatts/tar-split/cmd/tar-split

FROM python:3.6-stretch
LABEL maintainer="info@beiran.io"
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip git curl make libsqlite3-dev libyajl-dev libyajl2

RUN mkdir -p /opt/beiran/beiran
WORKDIR /opt

ADD beiran/requirements.txt /opt/beiran/r-lib.txt
RUN pip install -r /opt/beiran/r-lib.txt

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

COPY --from=tar-split-builder /tar-split /opt/beiran/plugins/beiran_package_docker/tar-split

RUN echo 'alias beiran="python -m beiran.cli"\nalias beirand="python -m beiran.daemon"\n' > /root/.bashrc

ADD [ "beiran", "/opt/beiran/beiran" ]

ADD [ "plugins", "/opt/beiran/plugins" ]

ENV PYTHONPATH=/opt/beiran:/opt/beiran/plugins

VOLUME /var/lib/beiran
VOLUME /etc/beiran

CMD [ "python3", "-m", "beiran.daemon" ]
