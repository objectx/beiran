FROM python:3-jessie
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip python-pycurl

# Install bats
RUN cd /root; git clone --depth=1 https://github.com/sstephenson/bats.git; cd bats; ./install.sh /usr

RUN pip3 install pyresttest
RUN mkdir /tests
ADD beirand.yaml /tests/beirand.yaml
WORKDIR /tests
ENTRYPOINT ["pyresttest"]


# usage:
# docker build -t beiran/resttest .
# docker run --rm -e SERVER='172.0.1.2:8888' -v `pwd`:/tests beiran/resttest $SERVER beirand.yaml
