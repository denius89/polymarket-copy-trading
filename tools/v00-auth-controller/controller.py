"""Private V00 probe service. Test routes are NOT the product D02 transport.

Operator-only fixture bindings; no login issuance, no provider credentials in output.
Database functions/roles are owned by scripts/v00-db. No SQL writes outside them.
"""
import base64
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlsplit

from totp import (InvalidRequest, canonical_uuid, decode_secret, fingerprint,
                  matching_steps, strict_object, verify_request)


class Unavailable(Exception):
    pass


class Postgres:
    # Fixed SQL, never a function name or SQL expression supplied by the client.
    expressions = {
        "lookup": "v00_db.lookup_totp(j)",
        "clock": "v00_db.read_totp_clock(j)",
        "verify": "v00_db.verify_totp(j)",
        "seal": "v00_db.seal_email(j)",
        "outcome": "v00_db.read_email_outcome(j)",
    }

    def __init__(self):
        self.command = json.loads(os.environ.get("V00_PSQL_COMMAND_JSON", '["psql"]'))
        if not isinstance(self.command, list) or not all(isinstance(x, str) for x in self.command):
            raise ValueError("PSQL command must be an operator argv array")

    def call(self, action, fields):
        encoded = base64.b64encode(json.dumps(fields, separators=(",", ":")).encode()).decode()
        query = ("WITH input AS (SELECT convert_from(decode('" + encoded + "','base64'),'UTF8')::jsonb j) "
                 "SELECT coalesce((" + self.expressions[action] + ")::text,'null') FROM input;\n")
        try:
            process = subprocess.run(self.command + ["-XAtq", "-v", "ON_ERROR_STOP=1"],
                                     input=query, capture_output=True, text=True, timeout=5,
                                     env=os.environ | {"PGOPTIONS": "-c statement_timeout=4000 -c lock_timeout=3000"})
            if process.returncode:
                raise Unavailable("database call failed")
            return json.loads(process.stdout)
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            # Never include SQL, driver stderr, credentials, or raw codes in response/log.
            raise Unavailable("database outcome unavailable") from exc


def private_json(path):
    file = Path(path)
    if file.stat().st_mode & 0o077:
        raise ValueError("private fixture file must have mode 0600/0400")
    return json.loads(file.read_text())


class Controller:
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.key = bytes.fromhex(config["fingerprint_key_hex"])
        if len(self.key) != 32:
            raise ValueError("32-byte private fingerprint key required")

    def authorize(self, authorization):
        if not authorization.startswith("Bearer "):
            return None
        value = authorization[7:]
        for token, principal in self.config["principals"].items():
            if hmac.compare_digest(value.encode(), token.encode()):
                return principal
        return None

    def clock_trusted(self, mode):
        if mode == "fixed_fixture":
            return True  # DB-admin fixed fixture, always labelled as such in evidence.
        if mode != "wall":
            return False
        try:
            sample = json.loads(Path(os.environ["V00_CLOCK_ATTESTATION"]).read_text())
            now = time.time()
            return (sample.get("trusted") is True and
                    sample["checked_at"] <= now < sample["valid_until"])
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def verify(self, principal, request, lookup_only=False):
        verify_request(request)
        context = self.config["contexts"].get(request["contextId"])
        if context is None or context["principal_id"] != principal:
            return 404, {"reason": "hidden_context"}
        binding = {"context_id": request["contextId"], "operation_id": request["operationId"],
                   "fingerprint": fingerprint(self.key, principal, request)}
        original = self.db.call("lookup", binding)
        if original is not None:
            return original.get("http", 200), original
        if lookup_only:
            # Absence is not proof that a concurrent/original request cannot finish.
            return 202, {"status": "unresolved", "full_login_issued": False}
        clock = self.db.call("clock", {"context_id": request["contextId"]})
        if not self.clock_trusted(clock["clock_mode"]):
            return 503, {"reason": "untrusted_clock", "full_login_issued": False}
        seconds = clock["unix_seconds"]
        if type(seconds) is not int:
            raise Unavailable("invalid clock shape")
        steps = matching_steps(decode_secret(context["secret_base32"]), request["code"], seconds)
        result = self.db.call("verify", binding | {
            "challenge_id": request["challengeId"], "factor_version": context["factor_version"],
            "evaluation_step": seconds // 30, "matched_steps": steps, "clock_trusted": True})
        return result.get("http", 200), result

    def email(self, principal, request, lookup_only=False):
        if set(request) != {"operationId"}:
            raise InvalidRequest("only operationId accepted")
        operation = canonical_uuid(request["operationId"])
        fixture = self.config.get("email_operations", {}).get(operation)
        if fixture is None or fixture["principal_id"] != principal:
            return 404, {"reason": "hidden_operation"}
        if not lookup_only:
            seal = self.db.call("seal", {"operation_id": operation, "user_id": fixture["user_id"],
                "token_digest": fixture["token_digest"],
                "fingerprint": fingerprint(self.key, principal, {"operation": operation,
                    "user": fixture["user_id"], "token_digest": fixture["token_digest"]})})
            if seal.get("http") != 200:
                return seal.get("http", 503), seal | {"full_login_issued": False}
            # Only the first successfully returned durable dispatch permit sends HTTP.
            # A lost seal reply, replay, or uncertain provider result must never resend.
            if seal.get("dispatch_allowed") is True:
                self.dispatch(fixture)
                if fixture.get("fault") == "after_effect_before_result":
                    raise Unavailable("injected loss before local result read")
        result = self.db.call("outcome", {"operation_id": operation})
        return (200 if result.get("status") == "confirmed_effect" else 202), result | {"full_login_issued": False}

    def dispatch(self, fixture):
        # Operator-bound origin/path/fault mode; none can be supplied by HTTP callers.
        origin = urlsplit(self.config["provider_origin"])
        if origin.scheme != "http" or origin.username or origin.password or origin.path not in ("", "/"):
            raise Unavailable("private HTTP provider origin required")
        fault = fixture.get("fault", "none")
        if fault == "before_send":
            # Durable sealed intent with no dispatch: intentionally remains uncertain.
            # No fictitious rollback/closed_without_dispatch inferred from this branch.
            return
        conn = http.client.HTTPConnection(origin.hostname, origin.port, timeout=5)
        try:
            conn.request("GET", fixture["verify_path"], headers={"Connection": "close"})
            if fault == "before_headers":
                # Actual socket close before reading ANY provider headers, not merely body discard.
                if conn.sock:
                    conn.sock.shutdown(socket.SHUT_RDWR)
                return
            response = conn.getresponse()
            # Neither 303 nor a provider success is used as the authoritative outcome.
            # The local result always comes from the independent transaction witness.
            response.read()
        except (OSError, http.client.HTTPException):
            pass  # Unknown, never resend or synthesize a verification rejection.
        finally:
            conn.close()


def serve():
    controller = Controller(private_json(os.environ["V00_FIXTURE_CONFIG"]), Postgres())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Default request/access logs may contain identifiers; evidence is separate.

        def do_POST(self):
            try:
                principal = controller.authorize(self.headers.get("Authorization", ""))
                if principal is None:
                    return self.reply(401, {"reason": "test_principal_required"})
                if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                    raise InvalidRequest("one Content-Length required")
                size = int(self.headers["Content-Length"])
                if size < 0 or size > 8192:
                    raise InvalidRequest("invalid body size")
                self.connection.settimeout(5)
                request = strict_object(self.rfile.read(size))
                if self.path in ("/v00/totp", "/v00/totp/result"):
                    status, result = controller.verify(principal, request, self.path.endswith("/result"))
                elif self.path in ("/v00/email", "/v00/email/result"):
                    status, result = controller.email(principal, request, self.path.endswith("/result"))
                else:
                    status, result = 404, {"reason": "not_found"}
                self.reply(status, result)
            except (InvalidRequest, ValueError):
                self.reply(400, {"reason": "invalid_request"})
            except (Unavailable, OSError, KeyError, TypeError):
                self.reply(503, {"reason": "outcome_unavailable", "full_login_issued": False})

        def reply(self, status, result):
            raw = json.dumps(result, separators=(",", ":")).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except OSError:
                pass  # Lost client response does not undo or repeat a committed outcome.

    server = ThreadingHTTPServer((os.environ.get("V00_BIND", "0.0.0.0"),
                                  int(os.environ.get("V00_PORT", "8080"))), Handler)
    server.serve_forever()


if __name__ == "__main__":
    serve()
