"""Generate fresh private synthetic fixtures; no database/server connections."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import uuid

from crypto import Keys, b64url

NAMES = ("basic", "recovery", "closed", "boundary_before", "boundary_at", "boundary_after",
         "context_expiry", "revoke", "expired_login", "key_loss", "corrupt_cipher",
         "loss_before", "loss_after", "logout_a", "logout_b", "logout_lost",
         "continue_a", "continue_b", "corrupt_result", "not_applicable", "wall")


def stamp(t):
    return t.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as file:
        json.dump(value, file, indent=2)
        file.write("\n")


def generate(directory, origin):
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    start = datetime.now(timezone.utc)
    start = start.replace(microsecond=start.microsecond // 1000 * 1000)
    keys = {purpose: {"id": purpose + "-1", "hex": os.urandom(32).hex()}
            for purpose in ("context", "credential", "cipher", "comparison")}
    write_private(directory / "keys.json", keys)
    crypto = Keys(directory / "keys.json")
    fixtures, clients, actors, contexts = {}, {}, {}, []
    for name in NAMES:
        actor = fixtures["logout_a"]["actor_id"] if name == "logout_b" else (
            fixtures["continue_a"]["actor_id"] if name == "continue_b" else str(uuid.uuid4()))
        wall = name == "wall"
        actors[actor] = {"id": actor, "fixed_time": None if wall else stamp(start), "blocked": False}
        f = {key: str(uuid.uuid4()) for key in ("context_id", "operation_id", "login_id", "secret_id")}
        f |= {"actor_id": actor, "proof": b64url(os.urandom(32)), "fixture_token": b64url(os.urandom(32))}
        if name in ("loss_before", "loss_after"):
            f["fault"] = "drop_before_headers" if name == "loss_before" else "drop_after_headers"
        if name == "logout_lost":
            f["logout_fault"] = "drop_before_headers"
        fixtures[name] = f
        clients[name] = {k: f[k] for k in ("context_id", "operation_id", "login_id", "fixture_token")}
        contexts.append({"id": f["context_id"], "actor_id": actor,
            "proof_digest": crypto.proof(f["context_id"], f["proof"]),
            "expires_at": stamp(start + timedelta(minutes=2 if name == "context_expiry" else 30)),
            "login_expires_at": stamp(start + timedelta(days=30)),
            "idle_expires_at": stamp(start + timedelta(days=7))})
    write_private(directory / "server.json", {"fixtures": fixtures})
    write_private(directory / "client.json", {"origin": origin, "fixtures": clients})
    write_private(directory / "seed.json", {"actors": list(actors.values()), "contexts": contexts})
    # Public only: never print context proofs, fixture capabilities, cookie or keys.
    return {"fixtures": len(fixtures), "actors": len(actors), "clock": "fixed_except_wall"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--origin", default="https://session-d0307.invalid:8443")
    args = parser.parse_args()
    print(json.dumps(generate(args.directory, args.origin)))
