FROM centos:7

LABEL maintainer="alkim@rlab.io"

RUN yum install -y epel-release; \
    yum install -y gcc yum-utils device-mapper-persistent-data lvm2;

RUN yum -y install https://centos7.iuscommunity.org/ius-release.rpm
RUN yum -y install python36u python36u-pip python36u-devel

RUN ln -s /usr/bin/pip3.6 /usr/bin/pip

RUN yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo;

RUN yum install -y docker-ce

RUN mkdir /src
WORKDIR /src

ADD [ "requirements.txt", "/src"]
#RUN pip3.6 install --upgrade pip
RUN pip install -r requirements.txt

ADD [ "src", "/src" ]

VOLUME /var/lib/docker
CMD ["bash"]