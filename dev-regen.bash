#!/bin/bash

# We want to use the oldest version of Python supported by us:
CERTLIB_LOG_DEV_REQ_REGEN_PYTHON='python3.10'
CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR='./dev/.venv-temporary-for-req-regen'
if [[ -n "$*" ]]; then
    CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION=" (passing to pip-compile the extra argument(s): '$*')"
else
    CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION=""
fi

echo "Starting the procedure of regenerating dev/doc/test requirements..."

CERTLIB_LOG_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd -- "${CERTLIB_LOG_DIR}" || exit 1
ls -l ./src/certlib/log.py > /dev/null || exit 1

echo "OK, set the current working directory to" \
     "the project's root '${CERTLIB_LOG_DIR}'."

if [[ -d "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}" ]]; then
    echo "Hmm, '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}'" \
          "already exists. It will be removed now!" >&2
    rm -rf -- "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}" || exit 1
fi

echo "Creating temporary virtual environment in '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}'..."
"${CERTLIB_LOG_DEV_REQ_REGEN_PYTHON}" -m venv "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}" || exit 1

echo "Activating the '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}' virtual environment..."
source "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}/bin/activate" || exit 1

echo "Ensuring that pip>=26.2.2 is installed..."
./check-and-upgrade-pip-to-v26-2-2.bash || exit 1

echo "Installing/upgrading necessary tools..."
python3 -m pip install --force-reinstall \
                       --upgrade \
                       --require-hashes \
                       --require-virtualenv \
                       --only-binary :all: \
                       --constraint dev/build-constraints.txt \
                       --constraint dev/dev-requirements.txt \
                       pip pip-tools setuptools wheel packaging \
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

echo "Regenerating *doc* requirements...${CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION}"
cd docs \
    && pip-compile --no-config \
                   --resolver backtracking \
                   --allow-unsafe \
                   --strip-extras \
                   --pip-args "--only-binary :all:" \
                   --generate-hashes \
                   "$@" \
                   --output-file doc-requirements.txt \
                   doc-requirements.in \
                   > /dev/null \
    && cd .. \
    || exit 1
echo "OK, *doc* requirements regenerated."

echo "Regenerating *test* requirements...${CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION}"
cd tests \
    && pip-compile --no-config \
                   --resolver backtracking \
                   --allow-unsafe \
                   --strip-extras \
                   --pip-args "--only-binary :all:" \
                   --generate-hashes \
                   "$@" \
                   --output-file test-requirements.txt \
                   test-requirements.in \
                   > /dev/null \
    && cd .. \
    || exit 1
echo "OK, *test* requirements regenerated."

echo "Regenerating *dev* requirements...${CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION}"
cd dev \
    && pip-compile --no-config \
                   --resolver backtracking \
                   --allow-unsafe \
                   --strip-extras \
                   --pip-args "--only-binary :all:" \
                   --generate-hashes \
                   "$@" \
                   --output-file dev-requirements.txt \
                   dev-requirements.in \
                   > /dev/null \
    && cd .. \
    || exit 1
echo "OK, *dev* requirements regenerated."

echo "Updating *dev* requirements' lower bounds..."
cp -a dev/dev-requirements.txt "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}/_tmp_file" \
    && {
python3 - "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}/_tmp_file" <<'PY'
import sys

read_from = 'dev/dev-requirements.txt'
write_to = sys.argv[1]
with open(read_from, 'rb') as r, open(write_to, 'wb') as w:
    for lineno, line in enumerate(r, start=1):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith((b'#', b'-')):
            if not (line.count(b'==') == 1 and line.endswith(b' \\\n')):
                sys.exit(
                    f'Unexpected line #{lineno} in {read_from!a}: {line!a}'
                )
            w.write(
                line.replace(b'==', b'>=').rstrip().rstrip(b'\\').rstrip()
                + b'\n'
            )
PY
    } \
    && mv "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}/_tmp_file" dev/dev-requirements-lower-bounds.txt \
    || exit 1
echo "OK, *dev* requirements' lower bounds updated."

echo "Regenerating build constraints...${CERTLIB_LOG_DEV_REQ_REGEN_ARGS_ANNOTATION}"
cd dev \
    && pip-compile --no-config \
                   --resolver backtracking \
                   --allow-unsafe \
                   --strip-extras \
                   --pip-args "--only-binary :all:" \
                   --generate-hashes \
                   "$@" \
                   --all-build-deps \
                   --only-build-deps \
                   --constraint dev-requirements.txt \
                   --output-file build-constraints.txt \
                   ../pyproject.toml \
                   > /dev/null \
    && cd .. \
    || exit 1
echo "OK, build constraints regenerated."

./dev/_pyyaml-fallback/req-update-and-regen.bash "$@" || exit 1

echo "Deactivating the '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}' virtual environment..."
deactivate || exit 1

echo "Removing the '${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}' virtual environment..."
rm -rf -- "${CERTLIB_LOG_DEV_REQ_REGEN_VENV_DIR}" || exit 1

echo "OK, finished the entire procedure of regenerating dev/doc/test requirements."
