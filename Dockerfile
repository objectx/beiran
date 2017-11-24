FROM centos:7

MAINTAINER Rain.lab

RUN yum install -y epel-release; \
    yum install -y python-pip python-devel gcc; \
    yum install -y yum-utils device-mapper-persistent-data lvm2;

RUN yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo;

RUN yum install -y docker-ce

ADD [ "src", "/src" ]
ADD [ "requirements.txt", "/src"]

WORKDIR /src

RUN pip install -r requirements.txt

VOLUME /var/lib/docker
CMD ["bash"]