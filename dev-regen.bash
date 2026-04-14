#!/bin/bash

# We want to use the oldest version of Python supported by us:
CERTLIB_LOG_DEV_REQ_REGEN_PYTHON=python3.10
CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR='./dev/.venv-temporary-for-req-regen'
if [[ -n "$*" ]]; then
    CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION=" (passing to pip-compile the extra argument(s): $*)"
else
    CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION=""
fi

if [[ -d "$CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR" ]]; then
    echo "Hmm, ${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}" \
          "already exists. It will be removed now!" >&2
    rm -rf "$CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR" || exit 1
fi

echo "Creating temporary virtual environment in '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}'..."
"$CERTLIB_LOG_DEV_REQ_REGEN_PYTHON" -m venv "$CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR" || exit 1

echo "Activating the '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}' virtual environment..."
source "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}/bin/activate" || exit 1

echo "Installing/upgrading necessary tools..."
python3 -m pip install --upgrade --require-virtualenv --use-pep517 \
    pip pip-tools setuptools wheel || exit 1
echo "OK, necessary tools installed/upgraded."

echo "Regenerating *doc* requirements...$CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION"
cd docs && \
    pip-compile --allow-unsafe --generate-hashes --strip-extras "$@" doc-requirements.in && \
    cd ..
[[ "$?" != 0 ]] && exit 1
echo "OK, *doc* requirements regenerated."

echo "Regenerating *test* requirements...$CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION"
cd tests && \
    pip-compile --allow-unsafe --generate-hashes --strip-extras "$@" test-requirements.in && \
    cd ..
[[ "$?" != 0 ]] && exit 1
echo "OK, *test* requirements regenerated."

echo "Regenerating *dev* requirements...$CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION"
cd dev && \
    pip-compile --allow-unsafe --strip-extras "$@" dev-requirements.in && \
    cd ..
[[ "$?" != 0 ]] && exit 1
echo "OK, *dev* requirements regenerated."

echo "Deactivating the '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}' virtual environment..."
deactivate || exit 1

echo "Removing the '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}' virtual environment..."
rm -rf "$CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR" || exit 1

echo "OK, finished the entire procedure of regenerating dev/doc/test requirements."
