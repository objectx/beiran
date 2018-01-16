FROM python:3-jessie
LABEL maintainer="beiran@rlab.io"
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip git curl make

RUN mkdir /src
WORKDIR /src

# Install bats
ADD beiran/requirements.txt /src/r-lib.txt
RUN pip3 install -r /src/r-lib.txt

ADD [ "beiran", "/src" ]

ADD beiran-cli/requirements.txt /src/r-cli.txt
RUN pip3 install -r /src/r-cli.txt

ADD [ "beiran-cli", "/src" ]

ADD beirand/requirements.txt /src/r-daemon.txt
RUN pip3 install -r /src/r-daemon.txt

ADD [ "beirand", "/src" ]

CMD [ "python3 /src/beirand/beirand/main.py" ]
