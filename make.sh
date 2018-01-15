#!/bin/bash -e

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
IMAGE=${IMAGE:-dkr.rlab.io/poc/beiran}
DAEMON_IMAGE=${DAEMON_IMAGE:-${IMAGE}/daemon}
TEST_IMAGE=${TEST_IMAGE:-${IMAGE}/test}
TAG=${TAG:-latest}
DOCKER_ENV_OPTS="-e MAKE_NEST_LEVEL"

if [ "$MAKE_NEST_LEVEL" = "" ]; then
	export MAKE_NEST_LEVEL=0
else
	export MAKE_NEST_LEVEL=$(( ${MAKE_NEST_LEVEL} + 1 ))
fi

trap cleanup ERR 

cleanup() {
	export MAKE_NEST_LEVEL=$(( ${MAKE_NEST_LEVEL} - 1 ))
}

usage() {
	1>&2 echo "./make.sh test_image"
	exit 1
}

log() {
	for i in $(seq 1 ${MAKE_NEST_LEVEL}); do
		echo -n "  "
	done
	echo "$@"
}

errlog() {
	1>&2 log "$@"
}

if [ $# -lt 1 ]; then
	usage
fi

ACTION=$1; shift

task() {
	if [ ${#TASKS} -eq 0 ]; then
		current_task=0
	else
		current_task=$(( $current_task + 1 ))
	fi
	log "=====[ Task: $1 ]====="
	TASK=( )
	TASK[name]=$1
	TASK[desc]=$2
	DEP_FILES=( )
	DEP_STEPS=( )
}

dep-file() {
	if [ ! -f $1 ]; then
		errlog "Cannot find dependency: $1"
		exit 1
	fi
	DEP_FILES+=( "$1" )
}

dep-step() {
	DEP_STEPS+=( "$1" )
	$0 $1
}

find_last_modification_of() {
	echo "$@" | xargs -n 1 stat -c %Y | sort -r | head -n 1
}

docker_get_image_stamp() {
	date --date="$(docker inspect -f '{{ .Created }}' $1)" +%s 2>/dev/null || echo '0'
}

# Returns unixtime of valid cache (or 0)
cache_check_test_image() {
	docker_get_image_stamp $TEST_IMAGE:$TAG
}

if [ "$ACTION" = "test_image" ]; then
	task "test_image" "Build container image for testing"
	dep-file test/Dockerfile
	dep-file beiran/requirements.txt
	dep-file beirand/requirements.txt
	dep-file beiran-cli/requirements.txt
	cache_valid_from=$(find_last_modification_of ${DEP_FILES[@]})
	image_created_at=$(docker_get_image_stamp $TEST_IMAGE:$TAG)
	if [ $image_created_at -lt $cache_valid_from ]; then
		log "Building test image"
		docker build -f test/Dockerfile -t ${TEST_IMAGE}:${TAG} .
	else
		log "Skipping build of test image"
	fi
fi

if [ "$ACTION" = "push_test_image" ]; then
	task "push_test_image" "Push container image for testing"
	dep-step test_image
	docker push ${TEST_IMAGE}:${TAG}
fi

if [ "$ACTION" = "test" ]; then
	task "test" "Run tests again codebase"
	for test_script in $(ls -1 test/*.sh | sort); do ${test_script}; done
	pytest
fi

if [ "$ACTION" = "test_using_docker" ]; then
	task "test_using_docker" "Run tests again codebase using test image"
	dep-step test_image
	TTY=$( ( [ -t 1 ] && echo 't' ) || true)
	docker run -i${TTY} \
		--rm \
		-v $DIR:/src:ro \
		-v /src_copy \
		-w /src_copy \
		$DOCKER_ENV_OPTS \
		${TEST_IMAGE}:${TAG} \
		bash -c "cp -r /src/. /src_copy/; $0 test"
fi

if [ "$ACTION" = "build_daemon_image" ]; then
	task "build_daemon_image" "Build daemon docker image"
	docker build -f beirand/Dockerfile -t ${DAEMON_IMAGE}:${TAG} .
fi

if [ "$ACTION" = "push_daemon_image" ]; then
	task "push_daemon_image" "Push daemon docker image"
	dep-step build_daemon_image
fi

log "=====[ Done: ${TASK[name]} ]====="

cleanup
