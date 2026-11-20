"""Export a staff Q06 release candidate from the selected Git tree."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory

ROOT = 'tools/staff-q06-release'
BASE = 'tools/staff-q06-local'
RELEASE_FILES = ('README.md', 'gateway.py', 'compose.yaml', 'build-admin.sh', 'config', 'operator')


def git(*args):
    return subprocess.check_output(('git', *args))


def extract(tree, destination):
    data = git('archive', tree, '--', *(f'{ROOT}/{name}' for name in RELEASE_FILES))
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError(f'Unexpected Git archive path: {path}')
        archive.extractall(destination)


def assemble(ref, destination):
    tree = git('rev-parse', '--verify', '--end-of-options', f'{ref}^{{tree}}').decode().strip()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    with TemporaryDirectory(dir=destination.parent) as work_dir:
        work = Path(work_dir)
        assembler = work / 'assemble-pilot.py'
        assembler.write_bytes(git('show', f'{tree}:{BASE}/assemble.py'))
        pilot = work / 'pilot'
        subprocess.run([sys.executable, str(assembler), tree, str(pilot)], check=True)
        extract(tree, work)
        release = work / ROOT
        (pilot / 'api').rename(release / 'src')
        for source in ('pilot_gateway.py', 'pilot_gateway_wiring.py', 'provision_material.py'):
            shutil.copyfile(pilot / 'operator' / source, release / source)
        shutil.copyfile(pilot / 'gateway/v00-polygon/gateway_core.py', release / 'gateway_core.py')
        (pilot / 'staff-db').rename(release / 'staff-db')
        images = json.loads((pilot / 'build-lock.json').read_text())['images']
        (release / 'release-lock.json').write_text(json.dumps({
            'format': 'staff-q06-release-v1', 'gitTree': tree, 'nodeImage': images['node'],
            'sha256': {str(f.relative_to(release)): hashlib.sha256(f.read_bytes()).hexdigest()
                       for f in sorted(release.rglob('*')) if f.is_file()},
        }, indent=2) + '\n')
        release.rename(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ref')
    parser.add_argument('destination', type=Path)
    options = parser.parse_args()
    assemble(options.ref, options.destination.absolute())
