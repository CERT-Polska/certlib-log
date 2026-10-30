#!/bin/bash

echo "Starting *development*-only installation" \
     "of 'certlib.log' and necessary stuff..."

CERTLIB_LOG_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd -- "${CERTLIB_LOG_DIR}" || exit 1
ls -l ./src/certlib/log.py > /dev/null || exit 1

echo "OK, set the current working directory to" \
     "the project's root '${CERTLIB_LOG_DIR}'."

find . -type f -name '*.pyc' -delete \
    && find . -type d -name '__pycache__' -delete \
|| echo "Warning: could not delete some *.pyc and/or __pycache__ stuff." >&2

echo "Checking whether a virtual environment is activated..."
python3 -c 'import sys; sys.exit(int(sys.prefix == sys.base_prefix))' || {
    echo "No virtual environment is activated." >&2
    CERTLIB_LOG_DEV_VENV_DIR='./dev/venv'

    if [[ ! -d "${CERTLIB_LOG_DEV_VENV_DIR}" ]]; then
        echo "As ${CERTLIB_LOG_DEV_VENV_DIR} does not exist, a new virtual" \
             "environment in '${CERTLIB_LOG_DEV_VENV_DIR}' will be created..."
        python3 -m venv "${CERTLIB_LOG_DEV_VENV_DIR}" || exit 1
    fi

    echo "Activating the '${CERTLIB_LOG_DEV_VENV_DIR}' virtual environment..."
    source "${CERTLIB_LOG_DEV_VENV_DIR}/bin/activate" || exit 1
} || exit 1

echo "Ensuring that pip>=26.2.2 is installed..."
./check-and-upgrade-pip-to-v26-2-2.bash || exit 1

echo "Reinstalling/upgrading pip..."
python3 -m pip install --force-reinstall \
                       --upgrade \
                       --require-hashes \
                       --require-virtualenv \
                       --only-binary :all: \
                       --constraint dev/dev-requirements.txt \
                       pip \
                       > /dev/null \
    || exit 1
echo "Checking whether the pip>=26.2.2 condition is still met..."
python3 -c \
    'import sys, pip; sys.exit(
        f"Too old pip! ({pip.__version__})"
        if tuple(map(int, pip.__version__.split(".")))[:3] < (26, 2, 2)
        else 0)' \
    || exit 1

echo "OK, ready to install the actual stuff..."

# PyYAML does not provide wheels for all versions, so
# we need to fall back to building it from its *sdist*.
python3 -m pip install --upgrade \
                       --require-hashes \
                       --require-virtualenv \
                       --only-binary :all: \
                       --constraint dev/dev-requirements.txt \
                       pyyaml \
                       &> /dev/null \
    || ./dev/_pyyaml-fallback/build-and-install.bash \
    || {
        echo "Failed to install *development*-only" \
             "dependencies of 'certlib.log'!" >&2
        exit 1
    }
python3 -m pip install --upgrade \
                       --require-hashes \
                       --require-virtualenv \
                       --only-binary :all: \
                       --constraint dev/dev-requirements.txt \
                       -r dev/dev-requirements-lower-bounds.txt \
    || {
        echo "Failed to install *development*-only" \
             "dependencies of 'certlib.log'!" >&2
        exit 1
    }
python3 -m pip install --upgrade \
                       --require-virtualenv \
                       --only-binary :all: \
                       --build-constraint dev/build-constraints.txt \
                       --no-deps \
                       -e .[dev] \
    || {
        echo "Failed to install 'certlib.log'!" >&2
        exit 1
    }

if [[ -v CERTLIB_LOG_DEV_VENV_DIR ]]; then
    echo "OK, 'certlib.log' and its *development*-only dependencies" \
         "have been installed in the '${CERTLIB_LOG_DEV_VENV_DIR}'" \
         "virtual environment."
else
    echo "OK, 'certlib.log' and its *development*-only dependencies" \
         "have been installed in the current virtual environment."
fi

echo
echo "** BUT PLEASE NOTE that it is a *development*-only installation" \
     "(just for running tests with 'pytest', or building docs with" \
     "'mkdocs build -f docs/mkdocs.yml', or performing type checks" \
     "with 'mypy -p certlib.log; mypy tests/test_certlib_log.py', etc.)."

if [[ -v CERTLIB_LOG_DEV_VENV_DIR ]]; then
    echo
    echo "**** ALSO, PLEASE NOTE that to run/import the installed stuff" \
         "you need to ensure you *use* that environment. In particular," \
         "you can activate it now by executing the following bash command:"
    echo
    echo "     cd -- '${CERTLIB_LOG_DIR}'" \
              "&& source ${CERTLIB_LOG_DEV_VENV_DIR}/bin/activate"
fi
echo
