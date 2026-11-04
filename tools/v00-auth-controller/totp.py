"""V00 test controller primitives. No provider tokens or full Shadow login issuance."""

import base64
import hashlib
import hmac
import json
import re
import struct
import uuid


class InvalidRequest(ValueError):
    pass


def strict_object(raw):
    if len(raw) > 8192:
        raise InvalidRequest("request too large")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InvalidRequest("duplicate field")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(InvalidRequest("number")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InvalidRequest("invalid JSON") from exc
    if not isinstance(value, dict):
        raise InvalidRequest("object required")
    return value


def canonical_uuid(value):
    if not isinstance(value, str):
        raise InvalidRequest("UUID required")
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError()
    except ValueError as exc:
        raise InvalidRequest("canonical UUID required") from exc
    return value


def verify_request(value):
    # Test transport, deliberately not an implementation of D02 routes/proofs.
    if set(value) != {"operationId", "contextId", "challengeId", "code"}:
        raise InvalidRequest("unknown or missing field")
    for key in ("operationId", "contextId", "challengeId"):
        canonical_uuid(value[key])
    if not isinstance(value["code"], str) or not re.fullmatch(r"[0-9]{6}", value["code"]):
        raise InvalidRequest("six ASCII digits required")
    return value


def hotp(secret, step):
    digest = hmac.digest(secret, struct.pack(">Q", step), "sha1")
    offset = digest[-1] & 15
    number = int.from_bytes(digest[offset:offset + 4], "big") & 0x7fffffff
    return f"{number % 1000000:06d}"


def decode_secret(encoded):
    # Only operator-provisioned fixture secrets enter here, never request data.
    return base64.b32decode(encoded + "=" * (-len(encoded) % 8), casefold=False)


def matching_steps(secret, code, unix_seconds):
    if not isinstance(unix_seconds, int) or isinstance(unix_seconds, bool) or unix_seconds < 30:
        raise ValueError("trusted integral server time required")
    current = unix_seconds // 30
    # Do not stop at the first match: collisions must consume the whole set.
    return [step for step in range(current - 1, current + 2)
            if hmac.compare_digest(hotp(secret, step), code)]


def fingerprint(key, principal_id, request):
    # A plain hash of a six-digit code is enumerable; use a private stable key.
    material = json.dumps(["v00-totp-request-v1", principal_id, request],
                          ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key, material, hashlib.sha256).hexdigest()
