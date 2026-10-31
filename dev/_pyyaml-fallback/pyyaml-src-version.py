import re
import sys


def get_version(src: str) -> str:
    try:
        with open(src, encoding='ascii') as r:
            s = r.read().strip()
        if match := re.search(r'(?mia)^pyyaml==(\d+.\d+.[-.\w]+)\s*\\?$', s):
            return match.group(1)
        raise ValueError(f'unexpected content of {src!a}: {s!a}')
    except Exception as exc:
        sys.exit(
            f'Could not extract the package '
            f'version from {src!a}! ({exc})'
        )


def main(arguments) -> int | str:
    if 1 <= len(arguments) <= 2:
        if len(arguments) == 1:
            print(get_version(src=arguments[0]))
        else:
            assert len(arguments) == 2
            v1 = get_version(src=arguments[0])
            v2 = get_version(src=arguments[1])
            if v1 == v2:
                print('same')
            else:
                print(v2)
        return 0
    print('Wrong number of command-line arguments!', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
