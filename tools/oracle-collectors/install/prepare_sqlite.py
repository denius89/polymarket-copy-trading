#!/usr/bin/env python3
"""Create an empty isolated SQLite ledger using the exact collector migration."""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New SQLite path")
    parser.add_argument("--policy", required=True, type=Path, help="Approved policy JSON in integer microunits")
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    if set(policy) != {"opening", "daily", "market"} or any(type(v) is not int or v <= 0 for v in policy.values()):
        parser.error("Expected positive integer opening, daily and market microunits")
    source = ROOT.parent / "collectors" / "polymarket-v2"
    sys.path.insert(0, str(source))
    import storage

    baseline = json.loads((ROOT / "sqlite" / "baseline-schema.json").read_text(encoding="utf-8"))["schema"]
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(args.output)) as db:
            for entry in baseline:
                db.execute(entry["sql"])
            db.commit()
            before = storage.audit(db, policy)
            storage.install(db, baseline, policy)
            if storage.audit(db) != before or db.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Seedless migration changed the empty ledger")
    except Exception:
        args.output.unlink()
        raise
    print("Created empty SQLite ledger with collector schema and no active writer.")


if __name__ == "__main__":
    main()
