"""Export the isolated staff Q06 composition from a Git revision."""
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory

ROOT = "tools/staff-q06-local"
DEMO_ASSEMBLER = "tools/v00-polygon-gateway/assemble_git_demo.py"


def git(*args):
    return subprocess.check_output(("git", *args))


def assemble(ref: str, destination: Path) -> None:
    tree = git("rev-parse", "--verify", "--end-of-options", f"{ref}^{{tree}}").decode().strip()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    with TemporaryDirectory(dir=destination.parent) as directory:
        work = Path(directory)
        runner = work / "assemble-demo.py"
        runner.write_bytes(git("show", f"{tree}:{DEMO_ASSEMBLER}"))
        base = work / "base"
        subprocess.run([sys.executable, str(runner), tree, str(base)], check=True)

        archive = git("archive", "--format=tar", tree, "--", f"{ROOT}/kit")
        with tarfile.open(fileobj=io.BytesIO(archive)) as files:
            for member in files.getmembers():
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                    raise ValueError(f"Unexpected Git archive member: {member.name}")
            files.extractall(work)
        stage = work / ROOT / "kit"
        shutil.copytree(stage / "api", base / "src", dirs_exist_ok=True)
        shutil.rmtree(stage / "api")
        (base / "src").rename(stage / "api")
        (base / "sql" / "scripts").rename(stage / "base-sql")
        (base / "tools").rename(stage / "gateway")
        lock = json.loads((base / "GIT-DEMO-LOCK.json").read_text())
        (stage / "build-lock.json").write_text(json.dumps({
            "assembledTree": tree,
            "images": lock["images"],
        }, indent=2) + "\n")
        stage.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref")
    parser.add_argument("destination", type=Path)
    options = parser.parse_args()
    assemble(options.ref, options.destination.resolve())
