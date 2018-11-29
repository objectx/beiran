FROM dkr.beiran.io/beiran/beiran:dev

RUN apt-get install -y python3.6-dev

ADD [ ".", "/opt/beiran/pyinstaller" ]
RUN pip install pyinstaller
WORKDIR /opt/beiran/pyinstaller

RUN pyinstaller beiran_installer.spec   --clean --log-level DEBUG -y

RUN cp /opt/beiran/pyinstaller/build/beiran_installer/beiran /usr/local/bin/beiran

CMD ["beiran", "--help"]
