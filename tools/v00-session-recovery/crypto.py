"""Isolated D03-07 codecs. AC07/AC38 bytes are TEST profiles, not D02 codecs."""
import base64
import ctypes as C
import ctypes.util
import hashlib
import hmac
import json
import os
import re
from pathlib import Path


class Unavailable(Exception):
    """Never include private material or driver stderr in public errors."""


def private_json(path):
    p = Path(path)
    if p.stat().st_mode & 0o077:
        raise Unavailable("private file permissions")
    return json.loads(p.read_text())


def b64url(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def secret_bytes(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", value):
        raise ValueError("invalid proof encoding")
    raw = base64.urlsafe_b64decode(value + "=")
    if len(raw) != 32 or b64url(raw) != value:
        raise ValueError("noncanonical proof")
    return raw


def frame(value):
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return len(raw).to_bytes(4, "big") + raw


def domain(value):
    return value.encode("ascii") + b"\0"


def mac(key, label, values):
    return hmac.new(key, domain(label) + b"".join(frame(v) for v in values), hashlib.sha256).hexdigest()


ENV = "v00-d03-07"
LOGIN_FORMAT = "v00-test-login-cookie-v1"
CIPHER_FORMAT = "v00-test-short-secret-xchacha20poly1305-v1"
META_FIELDS = ("environment", "realm", "login_id", "secret_id", "source_context_id",
               "source_operation_id", "owner_kind", "owner_id", "purpose",
               "cipher_format", "credential_format", "reveal_until")


def aad(metadata):
    if (set(metadata) != set(META_FIELDS) or metadata["environment"] != ENV
            or metadata["realm"] != "user" or metadata["owner_kind"] != "login"
            or metadata["owner_id"] != metadata["login_id"] or metadata["purpose"] != "login_cookie"
            or metadata["cipher_format"] != CIPHER_FORMAT or metadata["credential_format"] != LOGIN_FORMAT
            or not all(isinstance(metadata[k], str) for k in META_FIELDS)):
        raise Unavailable("unexpected crypto metadata")
    return domain("shadow.v00.session.aad.v1") + b"".join(frame(metadata[k]) for k in META_FIELDS)


class Keys:
    """Reload key file for each use, so key loss is a real unavailable condition."""
    def __init__(self, path):
        self.path = path

    def get(self, purpose, key_id):
        try:
            entry = private_json(self.path)[purpose]
            if entry["id"] != key_id:
                raise ValueError("key id mismatch")
            raw = bytes.fromhex(entry["hex"])
            if len(raw) != 32:
                raise ValueError("invalid key length")
            return raw
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise Unavailable("key unavailable") from exc

    def proof(self, context_id, value, kind="user_auth"):
        # Normative AC06 random-context verifier. No derived proof/rotation here.
        return mac(self.get("context", "context-1"), "shadow.auth.context-verify.v1",
                   [ENV, "user", kind, context_id, "context_proof", "random-context-proof-v1", secret_bytes(value)])

    def login(self, login_id, value, key_id="credential-1"):
        secret_bytes(value)
        return mac(self.get("credential", key_id), "shadow.v00.login-verify.v1",
                   [ENV, "user", login_id, LOGIN_FORMAT, value])

    def fingerprint(self, value):
        # Fixed closed ASCII-only fixture body; not a generic JCS implementation.
        wire = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return mac(self.get("comparison", "comparison-1"), "shadow.v00.intent.v1", [ENV, wire])


class Sodium:
    """Thin call to the official combined-mode libsodium API, no custom cipher."""
    def __init__(self, path=None):
        found = path or os.environ.get("V00_SODIUM_LIBRARY") or ctypes.util.find_library("sodium")
        if not found:
            raise Unavailable("libsodium unavailable")
        self.lib = C.CDLL(found)
        self.lib.sodium_init.restype = C.c_int
        if self.lib.sodium_init() < 0:
            raise Unavailable("libsodium initialization")
        self.lib.sodium_version_string.restype = C.c_char_p
        self.version = self.lib.sodium_version_string().decode("ascii")
        self.enc = self.lib.crypto_aead_xchacha20poly1305_ietf_encrypt
        self.enc.argtypes = [C.c_void_p, C.POINTER(C.c_ulonglong), C.c_void_p, C.c_ulonglong,
                             C.c_void_p, C.c_ulonglong, C.c_void_p, C.c_void_p, C.c_void_p]
        self.enc.restype = C.c_int
        self.dec = self.lib.crypto_aead_xchacha20poly1305_ietf_decrypt
        self.dec.argtypes = [C.c_void_p, C.POINTER(C.c_ulonglong), C.c_void_p, C.c_void_p,
                             C.c_ulonglong, C.c_void_p, C.c_ulonglong, C.c_void_p, C.c_void_p]
        self.dec.restype = C.c_int

    def encrypt(self, plaintext, ad, key):
        if len(key) != 32:
            raise Unavailable("invalid cipher key")
        nonce = os.urandom(24)
        out, length = C.create_string_buffer(len(plaintext) + 16), C.c_ulonglong()
        if self.enc(out, C.byref(length), plaintext, len(plaintext), ad, len(ad), None, nonce, key) != 0:
            raise Unavailable("encryption failed")
        return base64.b64encode(out.raw[:length.value]).decode(), base64.b64encode(nonce).decode()

    def decrypt(self, ciphertext, nonce, ad, key):
        try:
            encrypted = base64.b64decode(ciphertext, validate=True)
            n = base64.b64decode(nonce, validate=True)
            if not 16 <= len(encrypted) <= 1024 or len(n) != 24 or len(key) != 32:
                raise ValueError("invalid cipher material")
            out, length = C.create_string_buffer(len(encrypted) - 16), C.c_ulonglong()
            if self.dec(out, C.byref(length), None, encrypted, len(encrypted), ad, len(ad), n, key) != 0:
                raise ValueError("authentication failed")
            return out.raw[:length.value]
        except (ValueError, TypeError) as exc:
            raise Unavailable("cipher unavailable") from exc
