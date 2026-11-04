"""Single-attempt private provider transport for the authorized V00 profile.

No automatic retry, redirect, token refresh or JWT minting. Callers must obtain
and persist their scoped dispatch permit BEFORE invoking a mutating method.
Responses can contain credentials: never log them or persist ordinary history.
"""
import http.client
import json
import re
import socket
import ssl
from urllib.parse import urlsplit
import uuid


class UnknownOutcome(Exception):
    pass


class ConfirmedNotSent(Exception):
    """Only an operator-injected branch before the transport is even created."""


def canonical_id(value):
    parsed = uuid.UUID(value)
    if str(parsed) != value:
        raise ValueError("canonical provider id required")
    return value


def six_digits(code):
    if not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code):
        raise ValueError("six ASCII digits required")
    return code


class Provider:
    def __init__(self, origin, connection_factory=None):
        self.origin = urlsplit(origin)
        if (self.origin.scheme not in ("http", "https") or not self.origin.hostname
                or self.origin.username or self.origin.password or self.origin.path not in ("", "/")
                or self.origin.query or self.origin.fragment):
            raise ValueError("trusted private provider origin required")
        self.factory = connection_factory

    def _connection(self):
        if self.factory:
            return self.factory()
        kind = http.client.HTTPSConnection if self.origin.scheme == "https" else http.client.HTTPConnection
        options = {"timeout": 5}
        if self.origin.scheme == "https":
            options["context"] = ssl.create_default_context()
        return kind(self.origin.hostname, self.origin.port, **options)

    def request(self, method, path, payload, dispatch_id, bearer=None, fault="none"):
        canonical_id(dispatch_id)
        if fault not in {"none", "before_send", "after_send", "after_headers", "after_body"}:
            raise ValueError("unknown operator fault")
        if fault == "before_send":
            raise ConfirmedNotSent("operator fault before any provider transport")
        conn = self._connection()
        try:
            headers = {"Content-Type": "application/json", "Accept": "application/json",
                       "User-Agent": "shadow-v00-upstream/" + dispatch_id}
            if bearer is not None:
                if not isinstance(bearer, str) or not bearer or "\r" in bearer or "\n" in bearer:
                    raise ValueError("invalid private bearer")
                headers["Authorization"] = "Bearer " + bearer
            conn.request(method, path, body=None if payload is None else json.dumps(payload, separators=(",", ":")), headers=headers)
            if fault == "after_send":
                if conn.sock:
                    conn.sock.shutdown(socket.SHUT_RDWR)
                raise UnknownOutcome("operator fault after dispatch")
            response = conn.getresponse()
            if fault == "after_headers":
                raise UnknownOutcome("operator fault after provider headers")
            if 300 <= response.status < 400:
                raise UnknownOutcome("unexpected provider redirect")
            raw = response.read(65537)
            if len(raw) > 65536:
                raise UnknownOutcome("provider response too large")
            if fault == "after_body":
                raise UnknownOutcome("operator fault before response handoff")
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                raise UnknownOutcome("unexpected provider envelope")
            # Status alone is not a correlated durable outcome. The bridge must
            # validate the expected action and its independent storage witness.
            return response.status, body
        except (OSError, http.client.HTTPException, ValueError) as exc:
            raise UnknownOutcome("provider outcome unavailable") from exc
        finally:
            conn.close()

    def send_email(self, email, dispatch_id, fault="none"):
        return self.request("POST", "/otp", {"email": email, "create_user": True}, dispatch_id, fault=fault)

    def verify_email(self, email, code, dispatch_id, fault="none"):
        return self.request("POST", "/verify", {"email": email, "token": six_digits(code), "type": "email"}, dispatch_id, fault=fault)

    def enroll(self, bearer, dispatch_id):
        return self.request("POST", "/factors", {"factor_type": "totp", "friendly_name": "V00 upstream"}, dispatch_id, bearer)

    def challenge(self, factor_id, bearer, dispatch_id, fault="none"):
        return self.request("POST", "/factors/" + canonical_id(factor_id) + "/challenge", {}, dispatch_id, bearer, fault)

    def verify_totp(self, factor_id, challenge_id, code, bearer, dispatch_id, fault="none"):
        return self.request("POST", "/factors/" + canonical_id(factor_id) + "/verify",
                            {"challenge_id": canonical_id(challenge_id), "code": six_digits(code)}, dispatch_id, bearer, fault)

    def current_user(self, bearer, read_id):
        return self.request("GET", "/user", None, read_id, bearer)
