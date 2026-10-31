#!/bin/bash
set -Eeuo pipefail

require_virtualenv=true
if [ "$#" -eq 1 ] && [ "$1" = "--no-require-virtualenv" ]; then
  require_virtualenv=false
elif [ "$#" -ne 0 ]; then
  echo "ERROR: usage: $0 [--no-require-virtualenv]" >&2
  exit 1
fi

resolve_python_bin() {
  python3 - "$require_virtualenv" <<'PY'
import sys
from pathlib import Path

py_ver = sys.version_info[:2]
if py_ver < (3, 10):
    sys.exit(
        f"ERROR: no secure version of pip exists "
        f"for Python {py_ver[0]}.{py_ver[1]}!"
    )

if sys.argv[1] == "true" and sys.prefix == sys.base_prefix:
    sys.exit(
        "ERROR: no virtual environment is in use!"
    )

environment_path = Path(sys.prefix)
if not environment_path.is_absolute():
    sys.exit(
        f"ERROR: the Python environment directory path "
        f"{str(environment_path)!a} is not absolute!"
    )

python_bin_path = Path(sys.executable)
if not python_bin_path.is_relative_to(environment_path):
    sys.exit(
        f"ERROR: the Python executable path should be "
        f"absolute, and it should be a subpath of the "
        f"Python environment directory (which is: "
        f"{str(environment_path)!a}), but it is not: "
        f"{str(python_bin_path)!a}!"
    )
assert python_bin_path.is_absolute()

print(python_bin_path)
PY
}

check_pip_version() {
  "$python_bin" - "$1" <<'PY'
import re
import sys
import pip

MINIMUM_SECURE_PIP_VERSION = (26, 2, 2)
MINIMUM_SECURE_PIP_VERSION_STR = ".".join(map(str, MINIMUM_SECURE_PIP_VERSION))

STATUS_FATAL_ERROR = 1
STATUS_INSECURE_PIP_VERSION = 2

def parse_version(s):
    if not re.search(r"^[0-9]+(?:[.][0-9]+)*$", s):
        print(
            f"ERROR: the format of the pip version "
            f"{s!a} is unsupported by this script.",
            file=sys.stderr,
        )
        sys.exit(STATUS_FATAL_ERROR)
    return tuple(int(part) for part in s.split("."))

cmd = sys.argv[1]
pip_version_under_test = parse_version(pip.__version__)

if cmd == "just-print-min-secure-ver":
    print(MINIMUM_SECURE_PIP_VERSION_STR)

elif cmd in ("pre-check", "post-check"):
    if pip_version_under_test < MINIMUM_SECURE_PIP_VERSION:
        if cmd != "pre-check":
            print(
                f"ERROR: an *INSECURE* version of pip is "
                f"still here: {pip.__version__}! (*older* "
                f"than {MINIMUM_SECURE_PIP_VERSION_STR})",
                file=sys.stderr,
            )
        sys.exit(STATUS_INSECURE_PIP_VERSION)
    print(
        f"OK, the pip version is {pip.__version__} "
        f"(>= {MINIMUM_SECURE_PIP_VERSION_STR})."
    )

else:
    print(
        f"ERROR: unrecognized internal subcommand: {cmd!a}",
        file=sys.stderr,
    )
    sys.exit(STATUS_FATAL_ERROR)
PY
}

if ! python_bin=$(resolve_python_bin); then
  exit 1
fi

if ! PIP_REQUIRE_VIRTUALENV="$require_virtualenv" "$python_bin" -m pip freeze >/dev/null 2>&1; then
  echo "ERROR: pip is unavailable or cannot be run with ${python_bin}!" >&2
  exit 1
fi

if check_pip_version pre-check; then
  exit 0
else
  rc=$?
  if [ "$rc" -ne 2 ]; then
    exit 1
  fi
fi

if ! minimum_secure_pip_version=$(check_pip_version just-print-min-secure-ver); then
  exit 1
fi

if ! PIP_REQUIRE_VIRTUALENV="$require_virtualenv" "$python_bin" -m pip install --no-cache-dir --no-deps "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"; then
  echo "ERROR: failed to upgrade pip to the version ${minimum_secure_pip_version}!" >&2
  exit 1
fi

if ! check_pip_version post-check; then
  exit 1
fi

exit 0
