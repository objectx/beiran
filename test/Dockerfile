FROM python:3-alpine
RUN apt-get update && apt-get -y install \
	--no-install-recommends \
	python3-pip git curl make

# Install bats
RUN cd /root; git clone --depth=1 https://github.com/sstephenson/bats.git; cd bats; ./install.sh /usr

RUN pip3 install pytest pylint

ADD beiran/requirements.txt /root/r-lib.txt
RUN pip3 install -r /root/r-lib.txt

ADD beiran_cli/requirements.txt /root/r-cli.txt
RUN pip3 install -r /root/r-cli.txt

ADD beirand/requirements.txt /root/r-daemon.txt
RUN pip3 install -r /root/r-daemon.txt
