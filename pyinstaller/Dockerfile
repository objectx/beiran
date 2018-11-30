FROM python:3.6-alpine AS builder

RUN apk add --no-cache \
    git \
    openssh-client \
    python-dev \
    gcc \
    g++ \
    linux-headers \
    musl-dev \
    python3-dev \
    make

RUN pip install flake8==3.5.0 flake8-docstrings==1.3.0 pylint==2.0.0 bandit==1.4.0 mypy pyinstaller

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

#ADD plugins/beiran_interface_k8s/requirements.txt /opt/beiran/r-k8s.txt
#RUN pip install -r /opt/beiran/r-k8s.txt

RUN pip install pyinstaller

ADD beiran /opt/beiran/beiran
ADD plugins /opt/beiran/plugins
ADD pyinstaller /opt/beiran/pyinstaller

ENV PYTHONPATH=/opt/beiran:/opt/beiran/plugins
WORKDIR /opt/beiran/pyinstaller

RUN pyinstaller beiran_installer.spec   --clean --log-level DEBUG -y
RUN cp /opt/beiran/pyinstaller/build/beiran_installer/beiran /usr/local/bin/beiran

FROM alpine:3.8

COPY --from=builder /opt/beiran/pyinstaller/build/beiran_installer/beiran /bin/

VOLUME /var/lib/beiran
VOLUME /etc/beiran

ENTRYPOINT ["/bin/beiran"]

CMD ["--help"]
