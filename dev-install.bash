#!/bin/bash

find . -type f -name '*.pyc' -delete
find . -type d -name '__pycache__' -delete

python3 -m pip install --upgrade --require-virtualenv --use-pep517 pip 2>/dev/null || {
    [[ "$?" != 3 ]] && exit 1
    echo "No virtual environment is activated." >&2
    CERTLIB_LOG_DEV_VENV_DIR='./dev/venv'
    if [[ ! -d "$CERTLIB_LOG_DEV_VENV_DIR" ]]; then
        echo "As ${CERTLIB_LOG_DEV_VENV_DIR} does not exist, a new virtual" \
             "environment in '${CERTLIB_LOG_DEV_VENV_DIR}' will be created..."
        python3 -m venv "${CERTLIB_LOG_DEV_VENV_DIR}" || exit 1
        echo "OK, ${CERTLIB_LOG_DEV_VENV_DIR} created."
    else
        echo "OK, ${CERTLIB_LOG_DEV_VENV_DIR} already exists."
    fi
    echo "Activating the '${CERTLIB_LOG_DEV_VENV_DIR}' virtual environment..."
    source "${CERTLIB_LOG_DEV_VENV_DIR}/bin/activate" || exit 1
    echo "OK, "${CERTLIB_LOG_DEV_VENV_DIR}" activated."
    python3 -m pip install --upgrade --require-virtualenv --use-pep517 pip || exit 1
}
[[ "$?" != 0 ]] && exit 1

echo "OK, ready to install the actual stuff..."

python3 -m pip install --require-virtualenv --use-pep517 -r dev/dev-requirements.txt && \
    python3 -m pip install --require-virtualenv --use-pep517 -c dev/dev-requirements.txt -e .[dev]
[[ "$?" != 0 ]] && {
    echo "Failed to install 'certlib.log' and/or its *dev*-only dependencies!" >&2
    exit 1
}
if [[ -v CERTLIB_LOG_DEV_VENV_DIR ]]; then
    echo "OK, 'certlib.log' and its *dev*-only dependencies have been" \
         "installed in the '${CERTLIB_LOG_DEV_VENV_DIR}' virtual" \
         "environment. ***PLEASE NOTE*** that to run/import the installed" \
         "stuff you need to use this environment. In particular, you" \
         "can activate the environment by executing the following bash" \
         "command: 'source ${CERTLIB_LOG_DEV_VENV_DIR}/bin/activate'"
else
    echo "OK, 'certlib.log' and its *dev*-only dependencies have" \
         "been installed in the current virtual environment."
fi
echo "Please also NOTE that this is a *development-only* installation" \
     "(just for running tests with 'pytest', or building docs with" \
     "'mkdocs serve -f docs/mkdocs.yml')"
