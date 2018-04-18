FROM python:3.6-alpine

RUN apk add --no-cache \
    git \
    openssh-client \
    python-dev \
    gcc \
    g++ \
    linux-headers \
    musl-dev

RUN pip install flake8 flake8-docstrings pylint

ADD beiran/requirements.txt /root/r-lib.txt
RUN pip3 install -r /root/r-lib.txt

ADD beiran_cli/requirements.txt /root/r-cli.txt
RUN pip3 install -r /root/r-cli.txt

ADD beirand/requirements.txt /root/r-daemon.txt
RUN pip3 install -r /root/r-daemon.txt
