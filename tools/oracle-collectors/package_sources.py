#!/usr/bin/env python3
"""Verify and package the recorded Oracle collector sources without running them."""

import argparse
import gzip
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ORIGIN_MARKER = b"@@ORACLE_APP_ORIGIN@@"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def verify_sources(release, spec, oracle_origin):
    source_root = ROOT / "sources" / release
    paths = set()
    stored_paths = set()
    contents = {}
    for item in spec["files"]:
        path = item["path"]
        stored = item.get("template", path)
        if (not re.fullmatch(r"[\w.-]+\.py(?:\.in)?", stored, re.ASCII)
                or not re.fullmatch(r"[\w.-]+\.py", path, re.ASCII)
                or path in paths or stored in stored_paths):
            raise ValueError(f"Invalid or duplicate source entry: {path}")
        paths.add(path)
        stored_paths.add(stored)
        source = source_root / stored
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing or linked source: {release}/{stored}")
        content = source.read_bytes()
        if "template" in item:
            if digest(content) != item["template_sha256"] or content.count(ORIGIN_MARKER) != 1:
                raise ValueError(f"Template digest mismatch: {release}/{stored}")
            if oracle_origin is None:
                continue
            content = content.replace(ORIGIN_MARKER, oracle_origin.encode("ascii"))
        if digest(content) != item["sha256"]:
            raise ValueError(f"Oracle digest mismatch: {release}/{path}")
        contents[path] = content
    if {item.name for item in source_root.iterdir()} != stored_paths:
        raise ValueError(f"Unexpected files in {release}")
    return contents


def package_sources(destination, contents):
    with destination.open("xb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for path, content in sorted(contents.items()):
                    member = tarfile.TarInfo(path)
                    member.size = len(content)
                    member.mode = 0o644
                    archive.addfile(member, io.BytesIO(content))


def main():
    manifest = json.loads((ROOT / "releases.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported source manifest version")
    releases = manifest["releases"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", choices=releases)
    parser.add_argument("--oracle-origin-file", type=Path, help="Local text file containing the original HTTPS origin")
    parser.add_argument("--output", type=Path, help="New path for the verified source archive")
    args = parser.parse_args()
    origin = None
    try:
        if args.oracle_origin_file:
            origin = args.oracle_origin_file.read_text(encoding="ascii").strip()
            parsed = urlsplit(origin)
            if not re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]+)?", origin) or not parsed.hostname:
                raise ValueError("Expected a bare HTTPS origin without credentials, path or query")
        spec = releases[args.release]
        contents = verify_sources(args.release, spec, origin)
        pending = len(spec["files"]) - len(contents)
        if args.output:
            if pending:
                raise ValueError("The original Oracle origin is required to package this release")
            package_sources(args.output, contents)
        print(f"{args.release}: {len(contents)} Oracle digests verified"
              + (f"; {pending} Git templates verified, original origin required" if pending else ""))
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
