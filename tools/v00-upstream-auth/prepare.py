"""Build private adapter fixtures from operator-verified synthetic provider IDs.

No provider/DB connections. Does not create/activate an account or MFA factor.
Run BEFORE the single fixture /otp issuance, after installing observer hooks.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import uuid

from dependency import Keys, b64url, private_json


def stamp(value):
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def generate(directory, mapping, origin):
    if type(mapping) is not dict or set(mapping) != {"fixtures"} or type(mapping["fixtures"]) is not list:
        raise ValueError("invalid provider mapping")
    names, providers = set(), {}
    for item in mapping["fixtures"]:
        if type(item) is not dict or set(item) != {"name", "email", "provider_user_id", "provider_factor_id"}:
            raise ValueError("invalid fixture mapping")
        if not re.fullmatch(r"[a-z0-9_]{1,48}", item["name"]) or item["name"] in names:
            raise ValueError("invalid fixture alias")
        names.add(item["name"])
        for key in ("provider_user_id", "provider_factor_id"):
            value = item[key]
            if value is None and key == "provider_factor_id":
                continue
            if str(uuid.UUID(value)) != value:
                raise ValueError("noncanonical provider identifier")
        email = item["email"]
        if not isinstance(email, str) or not email.isascii() or "@" not in email or any(c.isspace() for c in email):
            raise ValueError("invalid fixture delivery address")
        pair = (email, item["provider_factor_id"])
        previous = providers.setdefault(item["provider_user_id"], pair)
        if previous != pair:
            raise ValueError("inconsistent provider source mapping")
    if not names:
        raise ValueError("empty fixtures")
    root = Path(directory)
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    keys = {purpose: {"id": purpose + "-1", "hex": os.urandom(32).hex()}
            for purpose in ("context", "credential", "cipher", "comparison")}
    write_private(root / "keys.json", keys)
    crypto = Keys(root / "keys.json")
    start = datetime.now(timezone.utc)
    subjects, contexts, fixtures, clients = {}, [], {}, {}
    for item in mapping["fixtures"]:
        provider = item["provider_user_id"]
        if provider not in subjects:
            factor = item["provider_factor_id"]
            subjects[provider] = {"actor_id": str(uuid.uuid4()), "provider_user_id": provider,
                "provider_factor_id": factor, "factor_version": str(uuid.uuid4()) if factor else None, "fixed_time": None}
        ctx, challenge = str(uuid.uuid4()), str(uuid.uuid4())
        proof, token = b64url(os.urandom(32)), b64url(os.urandom(32))
        contexts.append({"id": ctx, "actor_id": subjects[provider]["actor_id"],
            "proof_digest": crypto.proof(ctx, proof), "email_challenge_id": challenge,
            "expires_at": stamp(start + timedelta(minutes=30)),
            "login_expires_at": stamp(start + timedelta(days=30)),
            "idle_expires_at": stamp(start + timedelta(days=7))})
        fixtures[item["name"]] = {"context_id": ctx, "email": item["email"], "proof": proof, "fixture_token": token}
        clients[item["name"]] = {"context_id": ctx, "email_challenge_id": challenge, "fixture_token": token}
    write_private(root / "server.json", {"fixtures": fixtures})
    write_private(root / "client.json", {"origin": origin, "fixtures": clients})
    write_private(root / "seed.json", {"subjects": list(subjects.values()), "contexts": contexts})
    return {"subjects": len(subjects), "contexts": len(contexts), "clock": "wall"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("provider_mapping")
    parser.add_argument("directory")
    parser.add_argument("--origin", default="https://session-upstream.invalid:8443")
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.directory, private_json(args.provider_mapping), args.origin)))
    except Exception as exc:
        print(json.dumps({"created": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
