#!/usr/bin/env python3
"""Build a source, schema and dependency bundle without starting services."""

import argparse
import json
from pathlib import Path
import re

from package_sources import ROOT, digest, package_sources, verify_sources

INSTALL = ROOT / "install"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle-origin-file", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        origin = args.oracle_origin_file.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]+)?", origin):
            raise ValueError("Expected bare original HTTPS origin")
        source_manifest = json.loads((ROOT / "releases.json").read_text(encoding="utf-8"))
        lock = json.loads((INSTALL / "install-lock.json").read_text(encoding="utf-8"))
        if source_manifest["schema_version"] != 1 or lock["schema_version"] != 1:
            raise ValueError("Unsupported manifest version")
        contents = {}
        for name, entry in lock["files"].items():
            data = (INSTALL / name).read_bytes()
            if digest(data) != entry["sha256"]:
                raise ValueError(f"Installation input hash mismatch: {name}")
            contents[f"install/{name}"] = data
        for release, spec in source_manifest["releases"].items():
            source = verify_sources(release, spec, origin)
            for name, data in source.items():
                contents[f"collectors/{release}/{name}"] = data
            contents[f"collectors/{release}/maker-timestamp-observation.json"] = contents[
                "install/assets/maker-timestamp-observation.json"]
        contents["collectors/polymarket-v2/BASELINE-SCHEMA.json"] = contents[
            "install/sqlite/baseline-schema.json"]
        for name, sha in lock["driver_wheels"].items():
            data = (args.wheel_dir / name).read_bytes()
            if digest(data) != sha:
                raise ValueError(f"Wheel hash mismatch: {name}")
            contents[f"wheels/{name}"] = data
        for name in ("README.md", "install-lock.json", "prepare_sqlite.py"):
            contents[f"install/{name}"] = (INSTALL / name).read_bytes()
        for path in sorted((INSTALL / "config").glob("*.example")):
            contents[f"install/config/{path.name}"] = path.read_bytes()
        contents["releases.json"] = (ROOT / "releases.json").read_bytes()
        manifest = "".join(f"{digest(data)}  {name}\n" for name, data in sorted(contents.items()))
        contents["SHA256SUMS"] = manifest.encode("ascii")
        package_sources(args.output, contents)
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Install bundle built with {len(contents)} entries.")


if __name__ == "__main__":
    main()
