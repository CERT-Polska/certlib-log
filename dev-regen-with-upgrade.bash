#!/bin/bash

CERTLIB_LOG_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
"${CERTLIB_LOG_DIR}/dev-regen.bash" "$@" --upgrade
