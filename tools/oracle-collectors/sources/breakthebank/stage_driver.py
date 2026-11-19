"""Stage the two locked wheels into an isolated Python import directory."""
import argparse
from hashlib import sha256
from pathlib import Path, PurePosixPath
import platform
import stat
import sys
from zipfile import ZipFile

WHEELS = {
    'psycopg-3.3.9-py3-none-any.whl':
        'd2d7d04a1ce6dab4f5b27316bea3b52585cafa2f2d631e5b09dd69823f5c26f6',
    'psycopg_binary-3.3.9-cp314-cp314-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl':
        'eed1ac135d652e4454777afb4e4bb52cf88520bbfa2f30ae83066cd4df656697',
}
ROOTS = {'psycopg', 'psycopg-3.3.9.dist-info', 'psycopg_binary',
         'psycopg_binary-3.3.9.dist-info', 'psycopg_binary.libs'}


def wheel_payload(wheel_dir):
    files = {}
    for name, expected in WHEELS.items():
        wheel = wheel_dir / name
        if sha256(wheel.read_bytes()).hexdigest() != expected:
            raise ValueError('Driver wheel checksum mismatch')
        with ZipFile(wheel) as archive:
            for member in archive.infolist():
                path = PurePosixPath(member.filename)
                if (path.is_absolute() or '..' in path.parts or path.parts[0] not in ROOTS
                        or path.suffix == '.pth' or stat.S_ISLNK(member.external_attr >> 16)
                        or path in files):
                    raise ValueError('Unexpected wheel layout')
                if not member.is_dir():
                    files[path] = archive.read(member)
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if (sys.implementation.name, sys.version_info[:2], sys.platform, platform.machine()) != (
            'cpython', (3, 14), 'linux', 'aarch64'):
        parser.error('Driver requires Linux ARM64 with CPython 3.14')
    files = wheel_payload(Path(__file__).resolve().parent / 'wheels')
    args.output.mkdir(mode=0o700)
    for name, data in files.items():
        target = args.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print('Isolated PostgreSQL driver bytes staged.')


if __name__ == '__main__':
    main()
