FROM dkr.beiran.io/beiran/pyinstaller:alpine-3.6-pyinstaller-v3.4 AS pyinstaller

RUN apk add --no-cache \
    openssh-client \
    python-dev \
    g++ \
    linux-headers \
    python3-dev \
    make \
    yajl \
    yajl-dev

RUN pip install flake8==3.5.0 flake8-docstrings==1.3.0 pylint==2.0.0 bandit==1.4.0 mypy

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

ADD beiran /opt/beiran/beiran
ADD plugins /opt/beiran/plugins
ADD pyinstaller /opt/beiran/pyinstaller
ENV PYTHONPATH=/opt/beiran:/opt/beiran/plugins

WORKDIR /opt/beiran/pyinstaller

RUN /pyinstaller/pyinstaller.sh --onefile --name beiran \
                               --clean --log-level DEBUG --noconfirm \
                               --hidden-import  beiran.cli_node \
                               --hidden-import  beiran_package_docker.cli_docker \
                               --hidden-import  beiran_discovery_dns \
                               --hidden-import  beiran_discovery_dns.dns \
                               --hidden-import  beiran_discovery_zeroconf \
                               --hidden-import  beiran_discovery_zeroconf.zeroconf \
                               --paths /opt/beiran/pyinstaller \
                               --paths ../beiran \
                               --paths ../plugins/beiran_package_docker \
                               --exclude-module pycrypto \
                               --exclude-module PyInstaller \
                               --additional-hooks-dir ./hooks/ \
                               --runtime-hook ./hooks/hook-beiran.plugin.py \
                               ../beiran/__main__.py

FROM alpine:3.8

RUN apk add --no-cache \
    yajl \
    yajl-dev

COPY --from=pyinstaller /opt/beiran/pyinstaller/dist/beiran /bin/

VOLUME /var/lib/beiran
VOLUME /etc/beiran

ENTRYPOINT ["/bin/beiran"]

CMD ["--help"]
