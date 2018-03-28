FROM python:3-jessie
LABEL maintainer="beiran@rlab.io"
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip git curl make libsqlite3-dev

RUN mkdir -p /src
WORKDIR /src

# Install bats
ADD beiran/requirements.txt /src/r-lib.txt
RUN pip3 install -r /src/r-lib.txt

ADD beiran_cli/requirements.txt /src/r-cli.txt
RUN pip3 install -r /src/r-cli.txt

ADD beirand/requirements.txt /src/r-daemon.txt
RUN pip3 install -r /src/r-daemon.txt

ADD [ "beirand/beirand", "/src/beirand" ]
ADD [ "beiran", "/src/beiran"]

ENV PYTHONPATH=/src/beirand:/src
WORKDIR /src/beirand

VOLUME /var/lib/beiran
VOLUME /etc/beiran

CMD [ "python3", "/src/beirand/main.py" ]
