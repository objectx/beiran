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

WORKDIR /opt/beiran_interface_k8s
RUN python setup.py install

ADD helpers/pyinstaller /opt/pyinstaller

#ENV PYTHONPATH=/opt/beiran:/opt/beiran/plugins

WORKDIR /opt/pyinstaller

RUN /pyinstaller/pyinstaller.sh --onefile --name beiran \
                               --clean --log-level DEBUG --noconfirm \
                               --hidden-import  beiran.cli_node \
                               --hidden-import  beiran_package_docker.cli_docker \
                               --hidden-import  beiran_interface_k8s \
                               --hidden-import  beiran.plugins.discovery_dns \
                               --hidden-import  beiran.plugins.discovery_zeroconf \
                               --paths /opt/pyinstaller \
                               --paths ../beiran/beiran \
                               --paths ../beiran_package_docker/beiran_package_docker \
                               --paths ../beiran_interface_k8s/beiran_interface_k8s \
                               --exclude-module pycrypto \
                               --exclude-module PyInstaller \
                               --additional-hooks-dir ./hooks/ \
                               --runtime-hook ./hooks/hook-beiran.plugin.py \
                               ../beiran/beiran/__main__.py

RUN cat /opt/pyinstaller/build/beiran/warn-beiran.txt

FROM alpine:3.8

RUN apk add --no-cache \
    yajl \
    yajl-dev

COPY --from=pyinstaller /opt/pyinstaller/dist/beiran /bin/

VOLUME /var/lib/beiran
VOLUME /etc/beiran

ENTRYPOINT ["/bin/beiran"]

CMD ["--help"]
