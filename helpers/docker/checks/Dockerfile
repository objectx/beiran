FROM dkr.beiran.io/beiran/beiran:dev
LABEL maintainer="info@beiran.io"

RUN apk add --no-cache \
    git \
    openssh-client \
    python-dev \
    gcc \
    musl-dev \
    curl-dev

RUN pip install flake8==3.5.0 flake8-docstrings==1.3.0 pylint==2.0.0 bandit==1.4.0 mypy pyresttest==1.7.1

ADD mypy.ini /opt/mypy.ini
ADD .pylintrc /opt/pylintrc

ENV PYTHONPATH=/opt/beiran

WORKDIR /opt
