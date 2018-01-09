#!/bin/bash -e

export BEIRAN_ROOT=$(git rev-parse --show-toplevel)
echo "Detected beiran root dir: ${BEIRAN_ROOT}"

mkdir -p ${BEIRAN_ROOT}/run || true
export BEIRAN_SOCK=${BEIRAN_ROOT}/run/beirand.sock
