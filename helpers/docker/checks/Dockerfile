FROM python:3.6-alpine

RUN apk add --no-cache \
    git \
    openssh-client \
    python-dev \
    gcc \
    g++ \
    linux-headers \
    musl-dev \
    make

RUN pip install flake8==3.5.0 flake8-docstrings==1.3.0 pylint==2.0.0 bandit==1.4.0 mypy

ADD beiran/requirements.txt /opt/beiran/r-lib.txt
RUN pip install -r /opt/beiran/r-lib.txt

ADD plugins/beiran_package_docker/requirements.txt /opt/beiran/r-docker.txt
RUN pip install $(grep -iv "beiran" /opt/beiran/r-docker.txt)

ADD plugins/beiran_interface_k8s/requirements.txt /opt/beiran/r-k8s.txt
RUN pip install -r /opt/beiran/r-k8s.txt
