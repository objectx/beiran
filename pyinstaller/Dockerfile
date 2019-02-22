FROM dkr.beiran.io/beiran/pyinstaller:alpine-3.6-pyinstaller-v3.4 AS pyinstaller

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

#WORKDIR /opt/beiran_interface_k8s
#RUN python setup.py install

ADD pyinstaller /opt/pyinstaller

ENV PYTHONPATH=/opt/beiran:/opt/beiran/plugins

WORKDIR /opt/pyinstaller

RUN /pyinstaller/pyinstaller.sh --onefile --name beiran \
                               --clean --log-level DEBUG --noconfirm \
                               --hidden-import  beiran.cli_node \
                               --hidden-import  beiran_package_docker.cli_docker \
                               --hidden-import  beiran_discovery_dns \
                               --hidden-import  beiran_discovery_dns.dns \
                               --hidden-import  beiran_discovery_zeroconf \
                               --hidden-import  beiran_discovery_zeroconf.zeroconf \
                               --paths /opt/pyinstaller \
                               --paths ../beiran/beiran \
                               --paths ../beiran_package_docker/beiran_package_docker \
                               --exclude-module pycrypto \
                               --exclude-module PyInstaller \
                               --additional-hooks-dir ./hooks/ \
                               --runtime-hook ./hooks/hook-beiran.plugin.py \
                               ../beiran/beiran/__main__.py

FROM alpine:3.8

RUN apk add --no-cache \
    yajl \
    yajl-dev

COPY --from=pyinstaller /opt/beiran/pyinstaller/dist/beiran /bin/

VOLUME /var/lib/beiran
VOLUME /etc/beiran

ENTRYPOINT ["/bin/beiran"]

CMD ["--help"]
