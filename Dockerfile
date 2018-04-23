FROM python:3.6-jessie
LABEL maintainer="info@beiran.io"
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip git curl make libsqlite3-dev

RUN mkdir -p /opt/beiran/beiran
WORKDIR /opt

# Install bats
ADD beiran/requirements.txt /opt/beiran/r-lib.txt
RUN pip install -r /opt/beiran/r-lib.txt

ADD beiran_cli/requirements.txt /opt/beiran/r-cli.txt
RUN pip install -r /opt/beiran/r-cli.txt

ADD beirand/requirements.txt /opt/beiran/r-daemon.txt
RUN pip install -r /opt/beiran/r-daemon.txt

ADD [ "beirand/beirand", "/opt/beiran/beirand" ]
ADD [ "beiran", "/opt/beiran/beiran" ]
ADD [ "beiran_cli", "/opt/beiran/beiran_cli" ]

ENV PYTHONPATH=/opt/beiran/beirand:/opt/beiran

VOLUME /var/lib/beiran
VOLUME /etc/beiran

CMD [ "python3", "-m", "beirand" ]
