#!/bin/bash

# Copyright (c) 2026, CERT Polska. All rights reserved.
#
# This file's content is free software; you can redistribute and/or
# modify it under the terms of the *BSD 3-Clause "New" or "Revised"
# License* (see the `LICENSE.txt` file in the source code repository:
# https://github.com/CERT-Polska/certlib-log/blob/main/LICENSE.txt).

CERTLIB_LOG_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
"${CERTLIB_LOG_DIR}/dev-regen.bash" "$@" --upgrade
