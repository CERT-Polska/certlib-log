#!/bin/bash

CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME='pyyaml-src-req.in'
CERTLIB_LOG_PYYAML_SRC_REQ_TXT_FILENAME='pyyaml-src-req.txt'
CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR='.tmp-for-pyyaml-wheel'
CERTLIB_LOG_PYYAML_BUILD_VENV_DIR='.venv-temporary-for-building-pyyaml'

echo "Starting building and installing PyYAML..."

CERTLIB_LOG_PYYAML_SRC_REQ_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd -- "${CERTLIB_LOG_PYYAML_SRC_REQ_DIR}" || exit 1
ls -l ../../src/certlib/log.py > /dev/null || exit 1
ls -l "${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}" > /dev/null || exit 1

# Just in case...
../../check-and-upgrade-pip-to-v26-2-2.bash > /dev/null || exit 1

if ! CERTLIB_LOG_PYYAML_VERSION=$(
    python3 -I pyyaml-src-version.py "${CERTLIB_LOG_PYYAML_SRC_REQ_IN_FILENAME}"
); then
    exit 1
fi

if ! CERTLIB_LOG_PYYAML_INSTALL_VENV_DIR=$(
    python3 -I -c 'import sys; print(sys.prefix)'
); then
    exit 1
fi

if [[ -d "${CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR}" ]]; then
    echo "Hmm, '${CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR}'" \
          "already exists. It will be removed now!" >&2
    rm -rf -- "${CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR}" || exit 1
fi

echo "Creating temporary directory '${CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR}'..."
mkdir "${CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR}" || exit 1

if [[ -d "${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}" ]]; then
    echo "Hmm, '${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}'" \
          "already exists. It will be removed now!" >&2
    rm -rf -- "${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}" || exit 1
fi

echo "Creating temporary virtual environment in '${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}'..."
python3 -m venv "${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}" || exit 1

echo "Activating the '${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}' virtual environment..."
source "${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}/bin/activate" || exit 1

echo "Ensuring that pip>=26.2.2 is installed..."
../../check-and-upgrade-pip-to-v26-2-2.bash || exit 1

# Note: to build PyYAML from its *sdist*, Cython is always required,
# despite that it is not going to be used (`PYYAML_FORCE_LIBYAML=0`).
echo "Installing/upgrading necessary tools..."
python3 -m pip install --force-reinstall \
                       --upgrade \
                       --require-hashes \
                       --require-virtualenv \
                       --only-binary :all: \
                       --constraint ../build-constraints.txt \
                       --constraint ../dev-requirements.txt \
                       --constraint cython-req.txt \
                       pip build setuptools wheel packaging cython \
                       > /dev/null \
    || exit 1
echo "Checking whether the pip>=26.2.2 condition is still met..."
python3 -c \
    'import sys, pip; sys.exit(
        f"Too old pip! ({pip.__version__})"
        if tuple(map(int, pip.__version__.split(".")))[:3] < (26, 2, 2)
        else 0)' \
    || exit 1
echo "OK, necessary tools installed/upgraded."

echo "Creating temporary build space..."
if ! CERTLIB_LOG_PYYAML_BUILD_DIR=$(mktemp -d); then
    exit 1
fi
trap 'rm -rf -- "$CERTLIB_LOG_PYYAML_BUILD_DIR"' EXIT

echo "Downloading and verifying PyYAML version" \
     "${CERTLIB_LOG_PYYAML_VERSION} source package..."

python3 -m pip download --require-hashes \
                        --require-virtualenv \
                        --no-binary=:all: \
                        --no-deps \
                        --no-build-isolation \
                        --dest "${CERTLIB_LOG_PYYAML_BUILD_DIR}" \
                        -r "${CERTLIB_LOG_PYYAML_SRC_REQ_TXT_FILENAME}" \
    || exit 1

echo "Unpacking the archive..."
cd "${CERTLIB_LOG_PYYAML_BUILD_DIR}" || exit 1
tar -xzf "pyyaml-${CERTLIB_LOG_PYYAML_VERSION}.tar.gz" || exit 1
cd "pyyaml-${CERTLIB_LOG_PYYAML_VERSION}" || exit 1

echo "Building pure-Python universal wheel..."
export PYYAML_FORCE_LIBYAML="0"
python3 -m build --wheel --no-isolation --quiet || exit 1

if ! wheel_path=$(ls dist/*.whl); then
    exit 1
fi
wheel_target_dir=${CERTLIB_LOG_PYYAML_SRC_REQ_DIR}/${CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR}
wheel_filename=$(basename -- "${wheel_path}") || exit 1
mv "${wheel_path}" "${wheel_target_dir}/${wheel_filename}" || exit 1
echo "OK, PyYAML wheel is ready: '${wheel_target_dir}/${wheel_filename}'."

echo "Removing the temporary build space..."
rm -rf -- "${CERTLIB_LOG_PYYAML_BUILD_DIR}" || exit 1

cd -- "${CERTLIB_LOG_PYYAML_SRC_REQ_DIR}" || exit 1

echo "Deactivating the '${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}' virtual environment..."
deactivate || exit 1

echo "Removing the '${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}' virtual environment..."
rm -rf -- "${CERTLIB_LOG_PYYAML_BUILD_VENV_DIR}" || exit 1

echo "Activating the '${CERTLIB_LOG_PYYAML_INSTALL_VENV_DIR}' virtual environment..."
source "${CERTLIB_LOG_PYYAML_INSTALL_VENV_DIR}/bin/activate" || exit 1

# Just in case...
../../check-and-upgrade-pip-to-v26-2-2.bash > /dev/null || exit 1

python3 -m pip install --upgrade \
                       --require-virtualenv \
                       --only-binary :all: \
                       --no-deps \
                       --no-index \
                       "${wheel_target_dir}/${wheel_filename}" \
    || exit 1

echo "Removing the '${CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR}' directory..."
rm -rf -- "${CERTLIB_LOG_PYYAML_BUILD_RESULT_DIR}" || exit 1

echo "OK, finished building and installing PyYAML."
