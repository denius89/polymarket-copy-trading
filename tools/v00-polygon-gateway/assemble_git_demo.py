"""Assemble the closed demo inputs from a verified Git commit or tree."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
from tempfile import TemporaryDirectory


ROOT = "tools/v00-polygon-gateway"
MANIFEST = f"{ROOT}/GIT-DEMO-LOCK.json"
SOURCE_GROUPS = {
    "src": ("package.json", "package-lock.json", "apps", "packages"),
    "sql": (
        "scripts/v00-session-db", "scripts/v00-upstream-db", "scripts/v00-email-db",
        "scripts/polygon-paper-db", "scripts/polygon-http-db",
    ),
}


def git(*args):
    return subprocess.check_output(("git", *args))


def assemble(ref, destination):
    tree = git("rev-parse", "--verify", "--end-of-options", f"{ref}^{{tree}}").decode().strip()
    lock = json.loads(git("show", f"{tree}:{MANIFEST}"))
    if lock["format"] != "polygon-git-demo-v1":
        raise ValueError("Unsupported demo lock")
    for path, expected in lock["mainObjects"].items():
        actual = git("rev-parse", "--verify", f"{tree}:{path}").decode().strip()
        if actual != expected:
            raise ValueError(f"Unexpected Git object for {path}")
    runtime = {}
    for source, expected in lock["runtimeSha256"].items():
        data = git("show", f"{tree}:{source}")
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Unexpected SHA-256 for {source}")
        target = source.replace(f"{ROOT}/", "tools/v00-polygon/", 1)
        runtime[target] = data

    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    with TemporaryDirectory(dir=destination.parent) as temp:
        staging = Path(temp) / "demo"
        staging.mkdir()
        for group, paths in SOURCE_GROUPS.items():
            archive_data = git("archive", "--format=tar", tree, "--", *paths)
            with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:") as archive:
                for member in archive.getmembers():
                    name = PurePosixPath(member.name)
                    if name.is_absolute() or ".." in name.parts or not (member.isdir() or member.isfile()):
                        raise ValueError(f"Unexpected Git archive member: {member.name}")
                archive.extractall(staging / group)
        for path, data in runtime.items():
            target = staging / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        summary = {"assembledTree": tree, **lock}
        (staging / "GIT-DEMO-LOCK.json").write_text(json.dumps(summary, indent=2) + "\n")
        staging.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref", help="Git commit or tree containing this demo lock")
    parser.add_argument("destination", type=Path, help="New directory under an existing parent")
    args = parser.parse_args()
    assemble(args.ref, args.destination)
