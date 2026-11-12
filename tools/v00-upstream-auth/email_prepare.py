"""Operator-only private input files for an isolated email-entry run.

No network, SQL, provider calls or Auth-context fixtures. Input identity/factor
preflight remains the operator's job; seed_directory independently checks provider
email. Output contains synthetic addresses/keys and must remain private.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets

from dependency import Keys, private_json
from email_crypto import address_digest
from email_input import canonical_email
from controller import uid


def save(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, separators=(",", ":"))
        stream.write("\n")


def prepare(source, destination):
    if type(source) is not dict or set(source) != {"origin", "entries"} or type(source["entries"]) is not list:
        raise ValueError("invalid private setup")
    from urllib.parse import urlsplit
    origin = urlsplit(source["origin"])
    if origin.scheme != "https" or not origin.hostname or origin.path or origin.query or origin.fragment or origin.username or origin.password:
        raise ValueError("exact HTTPS origin required")
    rows, names, actors, addresses = [], set(), set(), set()
    for row in source["entries"]:
        if type(row) is not dict or set(row) != {"name", "actor_id", "email"}:
            raise ValueError("invalid directory input")
        if type(row["name"]) is not str or not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", row["name"]):
            raise ValueError("invalid safe alias")
        actor, email = uid(row["actor_id"]), canonical_email(row["email"])
        if row["name"] in names or actor in actors or email in addresses:
            raise ValueError("duplicate isolated identity")
        names.add(row["name"]); actors.add(actor); addresses.add(email)
        rows.append(row | {"email": email})
    if not rows:
        raise ValueError("missing verified identities")
    root = Path(destination)
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    key_ids = {"context": "context-1", "credential": "credential-1", "comparison": "comparison-1",
               "cipher": "cipher-1", "email_address": "email-address-1", "email_cipher": "email-cipher-1"}
    key_file = root / "keys.json"
    save(key_file, {purpose: {"id": key_id, "hex": secrets.token_hex(32)} for purpose, key_id in key_ids.items()})
    keys = Keys(key_file)
    entries = [{"actor_id": row["actor_id"], "address_digest": address_digest(keys, row["email"]),
                "address_key_id": "email-address-1", "normalized_email": row["email"]} for row in rows]
    save(root / "directory-input.json", {"entries": entries})
    save(root / "app.json", {"fixtures": {}})
    for row in rows:
        save(root / (row["name"] + "-client.json"), {"origin": source["origin"], "email": row["email"]})
    return {"private_files_created": len(rows) + 3, "directory_entries": len(rows), "contexts_created": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="private synthetic identity input, mode0600")
    parser.add_argument("destination", help="new private directory; refuses overwrite")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(private_json(args.source), args.destination)), flush=True)
    except Exception as exc:
        print(json.dumps({"passed": False, "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
