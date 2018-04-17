FROM python:3-alpine

RUN apk add --no-cache \
    git \
    openssh-client \
    && pip install flake8 flake8-docstrings pylint
RUN apk add --update --no-cache python-dev gcc g++ linux-headers musl-dev

ADD beiran/requirements.txt /root/r-lib.txt
RUN pip3 install -r /root/r-lib.txt

ADD beiran_cli/requirements.txt /root/r-cli.txt
RUN pip3 install -r /root/r-cli.txt

ADD beirand/requirements.txt /root/r-daemon.txt
RUN pip3 install -r /root/r-daemon.txt
