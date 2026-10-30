#!/bin/bash

CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME='pyyaml-src-req.in'
CERTLIB_LOG_PYYAML_SRC_REQ_TXT_FILENAME='pyyaml-src-req.txt'
CERTLIB_LOG_CYTHON_REQ_IN_FILENAME='cython-req.in'
CERTLIB_LOG_CYTHON_REQ_TXT_FILENAME='cython-req.txt'

CERTLIB_LOG_PYYAML_SRC_REQ_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd -- "${CERTLIB_LOG_PYYAML_SRC_REQ_DIR}" || exit 1
ls -l ../../src/certlib/log.py > /dev/null || exit 1
ls -l "${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}" > /dev/null || exit 1

if ! CERTLIB_LOG_PYYAML_VERSION=$(
  python3 -I pyyaml-src-version.py "${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}" ../dev-requirements.txt
); then
  exit 1
fi

# Just in case...
../../check-and-upgrade-pip-to-v26-2-2.bash > /dev/null || exit 1

# Note: to build PyYAML from its *sdist*, Cython is always required,
# despite that it is not going to be used (`PYYAML_FORCE_LIBYAML=0`).
echo "Regenerating '${CERTLIB_LOG_CYTHON_REQ_TXT_FILENAME}'..."
pip-compile --no-config \
            --resolver backtracking \
            --allow-unsafe \
            --strip-extras \
            --pip-args "--only-binary :all:" \
            --generate-hashes \
            "$@" \
            --constraint ../build-constraints.txt \
            --constraint ../dev-requirements.txt \
            --output-file "${CERTLIB_LOG_CYTHON_REQ_TXT_FILENAME}" \
            "${CERTLIB_LOG_CYTHON_REQ_IN_FILENAME}" \
             > /dev/null \
    || exit 1
echo "OK, '${CERTLIB_LOG_CYTHON_REQ_TXT_FILENAME}' regenerated."

if [[ "$CERTLIB_LOG_PYYAML_VERSION" == "same" ]]; then
  echo "OK, the PyYAML version did not change, so no extra work is needed."
  exit 0
fi
echo "The PyYAML version changed to ${CERTLIB_LOG_PYYAML_VERSION}," \
     "so '${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}' and" \
     "'${CERTLIB_LOG_PYYAML_SRC_REQ_TXT_FILENAME}' need to be adjusted..."

echo "Updating '${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}'..."
printf -- '--no-binary :all:\n\npyyaml==%s\n' "${CERTLIB_LOG_PYYAML_VERSION}" \
    > "${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}" \
    || exit 1
echo "OK, '${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}' updated."

echo "Regenerating '${CERTLIB_LOG_PYYAML_SRC_REQ_TXT_FILENAME}'..."
pip-compile --no-config \
            --resolver backtracking \
            --allow-unsafe \
            --strip-extras \
            --pip-args "--no-binary :all:" \
            --generate-hashes \
            --output-file "${CERTLIB_LOG_PYYAML_SRC_REQ_TXT_FILENAME}" \
            "${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}" \
             > /dev/null \
    || exit 1
echo "OK, '${CERTLIB_LOG_PYYAML_SRC_REQ_TXT_FILENAME}' regenerated."
