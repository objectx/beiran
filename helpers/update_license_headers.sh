#!/usr/bin/env bash
PROJECT_DIR="../"
PREAMBLE="preamble.txt"
TEMP_FILE="preamletemp"
for f in $(find ${PROJECT_DIR} -name '*.py' -or -name '*.doc'); do
    abs_path=$(readlink -f ${f});
    cat ${PREAMBLE} ${abs_path} > ${TEMP_FILE};
    mv ${TEMP_FILE} ${abs_path};
done
