FROM centos:7

LABEL maintainer="alkim@rlab.io"

RUN yum install -y epel-release; \
    yum install -y python-pip python-devel gcc; \
    yum install -y yum-utils device-mapper-persistent-data lvm2;

RUN yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo;

RUN yum install -y docker-ce

RUN mkdir /src
WORKDIR /src

ADD [ "requirements.txt", "/src"]
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ADD [ "src", "/src" ]

VOLUME /var/lib/docker
CMD ["bash"]