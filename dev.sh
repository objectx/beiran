#!/bin/bash -e

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
NAME=$(basename $DIR)
export VIRTUAL_ENV_DIR="${DIR}/env"
unset PYTHON_HOME
export PYTHONPATH=${DIR}:${DIR}/plugins
export PYTHON_BINARY=python3.6
export PKG_DIR=${VIRTUAL_ENV_DIR}/lib/${PYTHON_BINARY}/site-packages

REQS="$PYTHON_BINARY virtualenv pip"

for req in $REQS; do
	if ! which ${req} >/dev/null; then
		1>&2 echo "${req} is not found on your system, please install ${req}"
		1>&2 echo "or you can use docker instead"
		exit 1
	fi
done

if [ ! -d ${VIRTUAL_ENV_DIR} ]; then
	virtualenv env --python=$(which $PYTHON_BINARY)
	source ${VIRTUAL_ENV_DIR}/bin/activate
	pip install ipython
else
	source ${VIRTUAL_ENV_DIR}/bin/activate
fi

STAMP=$(date +%s)
INSTALLED=0
LAST_INSTALL=$(date -r ${VIRTUAL_ENV_DIR}/.last_install +%s 2>/dev/null || echo "0")
packages="beiran plugins/*"
for package in $packages; do
	package_name=$(basename $package)
	if [ ! -h ${PKG_DIR}/$package_name ]; then
		ln -s ${DIR}/$package ${PKG_DIR}/
	fi

	if [ -f $package/requirements.txt ]; then
		REQ_MODIFIED=$(date -r $package/requirements.txt +%s)
		if [ $REQ_MODIFIED -gt $LAST_INSTALL ]; then
			pip install -r $package/requirements.txt
			INSTALLED=1
		fi
	fi
done

if [ $INSTALLED -eq 1 ]; then
	echo $STAMP > ${VIRTUAL_ENV_DIR}/.last_install
fi

cat > ${VIRTUAL_ENV_DIR}/bin/beiran <<EOF
#!/bin/sh -e
exec ${PYTHON_BINARY} -m beiran "\$@"
EOF

cat > ${VIRTUAL_ENV_DIR}/bin/beirand <<EOF
#!/bin/sh -e
exec ${PYTHON_BINARY} -m beiran.daemon "\$@"
EOF

chmod +x ${VIRTUAL_ENV_DIR}/bin/beiran*

export PATH="${VIRTUAL_ENV_DIR}/bin:$PATH"

export LOG_LEVEL=DEBUG
export LOG_FILE=${DIR}/beirand.log
export BEIRAN_RUN_DIR=${DIR}
export BEIRAN_SOCK=${BEIRAN_RUN_DIR}/beirand.sock
export BEIRAN_PORT=${BEIRAN_PORT:-8888}
export BEIRAN_URL=http://localhost:${BEIRAN_PORT}
export BEIRAN_DB_PATH=${DIR}/beiran.db
export LISTEN_ADDR=0.0.0.0
export BEIRAN_CONFIG_DIR=${DIR}

function ps1_context {
	# For any of these bits of context that exist, display them and append
	# a space.
	virtualenv=${NAME}
	for v in "$debian_chroot" "$virtualenv" "$PS1_CONTEXT"; do
		echo -n "${v:+($v) }"
	done
}

export PS1="$(ps1_context)"'\u@\h:\w\$ '

if [ $(basename $SHELL) == "bash" ]; then
	exec $SHELL --norc -i
fi

exec "${@:-$SHELL}"
