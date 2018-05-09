#!/bin/bash -e

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
NAME=$(basename $DIR)
export VIRTUAL_ENV="${DIR}/env"
unset PYTHON_HOME
export PYTHONPATH=${DIR}/beirand:${DIR}

REQS="python3.6 virtualenv pip"

for req in $REQS; do
	if ! which ${req} >/dev/null; then
		1>&2 echo "${req} is not found on your system, please install ${req}"
		1>&2 echo "or you can use docker instead"
		exit 1
	fi
done

if [ ! -d $DIR/env ]; then
	virtualenv env --python=$(which python3.6)
	source ${DIR}/env/bin/activate
	pip install ipython
fi

source ${DIR}/env/bin/activate

STAMP=$(date +%s)
INSTALLED=0
LAST_INSTALL=$(date -r ${DIR}/env/.last_install +%s 2>/dev/null || echo "0")
packages="beiran beirand beiran_cli plugins/*"
for package in $packages; do
	package_name=$(basename $package)
	if [ ! -d env/lib/python3.6/site-packages/$package_name ]; then
		ln -s ${DIR}/$package env/lib/python3.6/site-packages/
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
	echo $STAMP > ${DIR}/env/.last_install
fi

if [ ! -x $VIRTUAL_ENV/bin/beiran ]; then
	cat > $VIRTUAL_ENV/bin/beiran <<EOF
#!/bin/sh -e
exec python3.6 -m beiran_cli "\$@"
EOF

	cat > $VIRTUAL_ENV/bin/beirand <<EOF
#!/bin/sh -e
exec python3.6 -m beirand "\$@"
EOF

	chmod +x $VIRTUAL_ENV/bin/beiran*
fi

export PATH="$VIRTUAL_ENV/bin:$PATH"

export LOG_LEVEL=DEBUG
export LOG_FILE=${DIR}/beirand.log
export BEIRAN_SOCK=${DIR}/beirand.sock
export BEIRAN_PORT=${BEIRAN_PORT:-8888}
export BEIRAN_URL=http://localhost:${BEIRAN_PORT}
export BEIRAN_DB_PATH=${DIR}/beiran.db
export LISTEN_ADDR=0.0.0.0
export CONFIG_FOLDER_PATH=${DIR}

alias beirand="python3.6 -m beirand"
alias beiran="python3.6 -m beiran"

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
