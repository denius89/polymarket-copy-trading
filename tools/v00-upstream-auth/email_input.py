"""Accepted email input and secret comparison for the isolated C01/C03 profile.

Addresses are private intent, not identity proof. No raw address in a public
fingerprint, exception, diagnostic record or observer result.
"""
import hashlib
import json
import re

from dependency import ENV, mac


def canonical_email(raw):
    if type(raw) is not str:
        raise ValueError("invalid email")
    try:
        if len(raw.encode("utf-8")) > 512:
            raise ValueError("invalid email")
        value = raw.strip(" ")
        value.encode("ascii")
    except UnicodeError:
        raise ValueError("invalid email") from None
    if len(value) > 254 or value.count("@") != 1:
        raise ValueError("invalid email")
    local, domain = value.split("@")
    atom = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    if not 1 <= len(local) <= 64 or not re.fullmatch(atom + r"(?:\." + atom + r")*", local):
        raise ValueError("invalid email")
    labels = domain.split(".")
    if len(labels) < 2 or any(not 1 <= len(label) <= 63 or not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label) for label in labels):
        raise ValueError("invalid email")
    return value.lower()


def send_intent(keys, body, proof_digest):
    """Called only after closed DTO validation; raw email remains HMAC-only."""
    public = {k: v for k, v in body.items() if k != "email"}
    wire = json.dumps(public, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ctx, op, action = body["authContextId"], body["authOperationId"], body["commandType"]
    if action not in {"C01", "C03"}:
        raise ValueError("invalid send action")
    raw = body["email"] if action == "C01" else ""
    comparison = mac(keys.get("comparison", "comparison-1"), "shadow.auth.sensitive-compare.v1",
                     [ENV, "context", ctx, action, op, "email_request", raw, body["locale"]])
    return {"context_id": ctx, "operation_id": op, "action": action,
            "proof_digest": proof_digest, "fingerprint": hashlib.sha256(wire).hexdigest(),
            "comparison_hmac": comparison, "comparison_key_id": "comparison-1"}
