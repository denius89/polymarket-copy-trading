"""D03-07 isolated HTTP adapter. Synthetic completion, no real Auth/provider path.

Private fixture bootstrap/complete routes are not production endpoints. D03-10
quotas, full D02 routing, provider/audit/witness integration remain outside scope.
"""
import hmac
from datetime import datetime, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import socket
import ssl
import uuid
from urllib.parse import urlsplit, parse_qsl

from crypto import Keys, Sodium, Unavailable, aad, b64url, private_json, secret_bytes
from storage import Transaction


class Rejection(Exception):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Rejection(400, "INVALID_REQUEST")


def uid(value):
    try:
        u = uuid.UUID(value)
        if str(u) != value or u.version != 4:
            raise ValueError()
        return value
    except (ValueError, TypeError, AttributeError):
        raise Rejection(400, "INVALID_REQUEST") from None


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("nonfinite")
    def check(value, depth=0):
        if depth > 8:
            raise ValueError("depth")
        if isinstance(value, str):
            value.encode("utf-8", errors="strict")
        elif isinstance(value, dict):
            for k, v in value.items():
                check(k, depth + 1)
                check(v, depth + 1)
        elif isinstance(value, list):
            for v in value:
                check(v, depth + 1)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        check(value)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise Rejection(400, "INVALID_REQUEST") from None


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def error(reason):
    return {"reasonCode": reason, "reasonDetails": {"code": reason, "params": {}},
            "nextAction": None, "nextActionParams": {}}


def envelope(**fields):
    return fields | {"observedAt": now(), "nextAction": None, "nextActionParams": {}}


def cookie(name, value, expires=None, delete=False):
    result = f"{name}={value}; Path=/; Secure; HttpOnly; SameSite=Strict"
    if delete:
        return result + "; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
    if expires:
        stamp = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        result += "; Expires=" + format_datetime(stamp, usegmt=True)
    return result


def selected_cookie(headers, name):
    values = []
    for header in headers.get_all("Cookie", []):
        for pair in header.split(";"):
            k, separator, v = pair.strip().partition("=")
            if k == name and separator:
                values.append(v)
    if not values:
        raise Rejection(401, "AUTH_REQUIRED")
    if len(values) != 1:
        raise Rejection(400, "INVALID_REQUEST")
    try:
        secret_bytes(values[0])
    except ValueError:
        raise Rejection(401, "AUTH_REQUIRED") from None
    return values[0]


def selected_login(headers, optional=False):
    values = headers.get_all("X-Shadow-Login-Id", [])
    if not values and optional:
        return None
    if len(values) != 1:
        raise Rejection(400, "INVALID_REQUEST")
    return uid(values[0])


def accepted(result):
    if result["http"] >= 400:
        raise Rejection(result["http"], result["reason"])
    return result


class Controller:
    def __init__(self, config, keys, sodium, transaction=Transaction):
        self.config, self.keys, self.sodium, self.transaction = config, keys, sodium, transaction

    def fixture(self, name, headers):
        f = self.config["fixtures"].get(name)
        token = headers.get("Authorization", "")
        if f is None or not hmac.compare_digest(token.encode(), ("Bearer " + f["fixture_token"]).encode()):
            raise Rejection(404, "RESOURCE_NOT_FOUND")
        return f

    def context_proof(self, ctx, headers, kind="user_auth"):
        prefix = "authctx" if kind == "user_auth" else "logoutctx"
        value = selected_cookie(headers, f"__Host-shadow-{prefix}-{ctx}")
        return self.keys.proof(ctx, value, kind)

    def login_proof(self, login, headers):
        value = selected_cookie(headers, "__Host-shadow-user-login-" + login)
        return self.keys.login(login, value)

    def recovered(self, result):
        if result["http"] != 200:
            return None
        plaintext = self.sodium.decrypt(result["ciphertext"], result["nonce"], aad(result["metadata"]),
            self.keys.get("cipher", result["key_id"]))
        try:
            value = plaintext.decode("ascii")
            digest = self.keys.login(result["metadata"]["login_id"], value, result["credential_key_id"])
        except (ValueError, UnicodeError) as exc:
            raise Unavailable("recovered secret invalid") from exc
        if not hmac.compare_digest(digest, result["cookie_digest"]):
            raise Unavailable("recovered verifier mismatch")
        c = result["result"]["completion"]
        if (c["loginId"] != result["metadata"]["login_id"]
                or c["authContextId"] != result["metadata"]["source_context_id"]
                or c["authOperationId"] != result["metadata"]["source_operation_id"]):
            raise Unavailable("source mismatch")
        return cookie("__Host-shadow-user-login-" + c["loginId"], value, result["login_expires_at"])

    def handle(self, method, path, query, body, headers):
        """Returns status, public body, headers, operator-only response-loss mode."""
        if method == "POST":
            if query or body.get("requestSchemaVersion") != "v1":
                raise Rejection(400, "INVALID_REQUEST")
        else:
            if query.get("requestSchemaVersion") != "v1":
                raise Rejection(400, "INVALID_REQUEST")
        fixture_match = re.fullmatch(r"/__v00__/fixtures/([a-z0-9_]+)/(context|complete)", path)
        if method == "POST" and fixture_match:
            name, action = fixture_match.groups()
            f = self.fixture(name, headers)
            ctx, op = f["context_id"], f["operation_id"]
            if action == "context":
                exact(body, {"requestSchemaVersion"})
                return 201, {"authContextId": ctx}, [("Set-Cookie", cookie("__Host-shadow-authctx-" + ctx, f["proof"]))], None
            exact(body, {"requestSchemaVersion", "authOperationId", "commandType"})
            if body["commandType"] != "C02" or uid(body["authOperationId"]) != op:
                raise Rejection(400, "INVALID_REQUEST")
            base = {"context_id": ctx, "proof_digest": self.context_proof(ctx, headers), "operation_id": op}
            with self.transaction() as tx:
                plan = accepted(tx.call("plan_completion", base | {"fingerprint": self.keys.fingerprint(body),
                    "login_id": f["login_id"], "secret_id": f["secret_id"]}))
                set_cookie = None
                if plan["replay"]:
                    result = plan["result"]
                    recovered = tx.call("recover", base)
                    if recovered["http"] == 409 and recovered["reason"] == "AUTH_COOKIE_RECOVERY_CLOSED":
                        pass  # Exact historical completion remains available without cookie.
                    else:
                        accepted(recovered)
                        set_cookie = self.recovered(recovered)
                else:
                    value = b64url(os.urandom(32))
                    ciphertext, nonce = self.sodium.encrypt(value.encode("ascii"), aad(plan["metadata"]),
                        self.keys.get("cipher", "cipher-1"))
                    completed = accepted(tx.call("complete", base | {"fingerprint": self.keys.fingerprint(body),
                        "cookie_digest": self.keys.login(f["login_id"], value), "ciphertext": ciphertext,
                        "nonce": nonce, "key_id": "cipher-1", "credential_key_id": "credential-1"}))
                    result = completed["result"]
                    set_cookie = cookie("__Host-shadow-user-login-" + f["login_id"], value, completed["login_expires_at"])
                tx.commit()
            return 200, envelope(completion=result["completion"]), ([] if set_cookie is None else [("Set-Cookie", set_cookie)]), f.get("fault")

        operation = re.fullmatch(r"/api/auth/contexts/([^/]+)/operations/([^/]+)(/login-cookie)?", path)
        if operation:
            ctx, op, recovery = operation.groups()
            uid(ctx); uid(op)
            if (method == "POST") != bool(recovery):
                raise Rejection(404, "RESOURCE_NOT_FOUND")
            fields = body if recovery else query
            exact(fields, {"requestSchemaVersion", "commandType"})
            # This fixture profile seals only C02; do not silently alias another action.
            if fields["commandType"] != "C02":
                raise Rejection(400, "INVALID_REQUEST")
            base = {"context_id": ctx, "proof_digest": self.context_proof(ctx, headers), "operation_id": op}
            with self.transaction() as tx:
                r = tx.call("recover" if recovery else "lookup_result", base)
                if recovery and r["http"] == 409:
                    tx.commit()  # Deadline erasure is a lawful committed negative outcome.
                    raise Rejection(409, r["reason"])
                accepted(r)
                set_cookie = self.recovered(r) if recovery else None
                tx.commit()
            if recovery:
                return 200, envelope(completion=r["result"]["completion"]), [("Set-Cookie", set_cookie)], None
            resolved = r["status"] == "resolved"
            stamp = r.get("resolved_at")
            if resolved and stamp is None:
                raise Unavailable("missing historical resolution timestamp")
            return r["http"], envelope(operationRef={"authContextId": ctx, "authOperationId": op, "commandType": "C02"},
                status=r["status"], result=r["result"], resolvedAt=stamp), [], None

        if method == "GET" and path == "/api/me":
            exact(query, {"requestSchemaVersion"})
            login = selected_login(headers)
            with self.transaction() as tx:
                r = accepted(tx.call("q01", {"login_id": login, "cookie_digest": self.login_proof(login, headers)}))
                tx.commit()
            return 200, {"authenticated": True, "user": {"userId": r["actor_id"], "locale": "en"},
                         "nextAction": "select_trader", "nextActionParams": {}}, [("X-Shadow-Login-Id", r["login_id"])], None

        if method == "POST" and path in {"/api/auth/logout-contexts", "/api/auth/logout-contexts/continue"}:
            continuing = path.endswith("/continue")
            exact(body, {"requestSchemaVersion", "sourceLogoutContextId", "authorizationMode"} if continuing else {"requestSchemaVersion"})
            login, ctx, proof = selected_login(headers), str(uuid.uuid4()), b64url(os.urandom(32))
            fields = {"logout_context_id": ctx, "cookie_digest": self.login_proof(login, headers),
                      "logout_proof_digest": self.keys.proof(ctx, proof, "logout")}
            if continuing:
                if body["authorizationMode"] not in {"original_login", "current_user"}:
                    raise Rejection(400, "INVALID_REQUEST")
                fields |= {"source_context_id": uid(body["sourceLogoutContextId"]), "authorization_login_id": login,
                           "authorization_mode": body["authorizationMode"]}
            else:
                fields["login_id"] = login
            with self.transaction() as tx:
                r = accepted(tx.call("logout_continue" if continuing else "logout_prepare", fields))
                tx.commit()
            view = {"logoutContextId": ctx, "loginId": r["target_login_id"], "realm": "user",
                    "createdAt": r["created_at"], "expiresAt": r["expires_at"]}
            if continuing:
                view["sourceLogoutContextId"] = r["source_context_id"]
            return 201, envelope(logoutContext=view), [("Set-Cookie", cookie("__Host-shadow-logoutctx-" + ctx, proof, r["expires_at"]))], None

        logout_read = re.fullmatch(r"/api/auth/logout-contexts/([^/]+)/operations/([^/]+)", path)
        if method == "POST" and path == "/api/auth/logout" or method == "GET" and logout_read:
            if method == "POST":
                exact(body, {"requestSchemaVersion", "commandType", "logoutContextId", "authOperationId"})
                if body["commandType"] != "C07":
                    raise Rejection(400, "INVALID_REQUEST")
                ctx, op = uid(body["logoutContextId"]), uid(body["authOperationId"])
            else:
                exact(query, {"requestSchemaVersion"})
                ctx, op = map(uid, logout_read.groups())
            base = {"logout_context_id": ctx, "proof_digest": self.context_proof(ctx, headers, "logout"), "operation_id": op}
            with self.transaction() as tx:
                r = accepted(tx.call("logout_result", base))
                if method == "POST":
                    selected = selected_login(headers, optional=True)
                    if selected is not None and selected != r["target_login_id"]:
                        raise Rejection(400, "INVALID_REQUEST")
                    r = accepted(tx.call("logout", base | {"fingerprint": self.keys.fingerprint(body)}))
                tx.commit()
            if method == "POST":
                target = r["result"]["target_login_id"]
                fault = next((f.get("logout_fault") for f in self.config["fixtures"].values() if f["login_id"] == target), None)
                return 204, None, [("Set-Cookie", cookie("__Host-shadow-user-login-" + target, "", delete=True))], fault
            return r["http"], envelope(operationRef={"logoutContextId": ctx, "authOperationId": op,
                "loginId": r["target_login_id"], "commandType": "C07"}, status=r["status"],
                confirmedAt=r["result"]["confirmed_at"] if r["result"] else None), [], None
        raise Rejection(404, "RESOURCE_NOT_FOUND")


def serve():
    controller = Controller(private_json(os.environ["V00_FIXTURE_CONFIG"]), Keys(os.environ["V00_KEY_FILE"]), Sodium())
    origin = os.environ["V00_ORIGIN"]
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("exact HTTPS origin required")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def handle_one_request(self):
            self.connection.settimeout(5)
            super().handle_one_request()

        def reply(self, status, body, headers=(), fault=None):
            if fault == "drop_before_headers":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.close_connection = True
                return
            data = b"" if body is None else json.dumps(body, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Request-Id", str(uuid.uuid4()))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            for key, value in headers:
                self.send_header(key, value)
            self.end_headers()
            if fault == "drop_after_headers":
                self.wfile.flush()
                self.connection.shutdown(socket.SHUT_RDWR)
                self.close_connection = True
                return
            self.wfile.write(data)

        def dispatch(self):
            try:
                if self.headers.get_all("Host", []) != [parsed.netloc]:
                    raise Rejection(400, "INVALID_REQUEST")
                url = urlsplit(self.path)
                if url.scheme or url.netloc or url.fragment:
                    raise Rejection(400, "INVALID_REQUEST")
                if self.command == "GET" and url.path == "/__v00__/runner" and not url.query:
                    page = b"<!doctype html><meta charset=utf-8><title>D03-07 private runner</title><p>Isolated synthetic session probe.</p>"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(page)))
                    self.end_headers(); self.wfile.write(page)
                    return
                if self.headers.get("Transfer-Encoding"):
                    raise Rejection(400, "INVALID_REQUEST")
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) > 1 or any(not re.fullmatch(r"[0-9]+", x) for x in lengths):
                    raise Rejection(400, "INVALID_REQUEST")
                length = int(lengths[0]) if lengths else 0
                if length > 8192:
                    raise Rejection(413, "REQUEST_TOO_LARGE")
                if self.command == "GET":
                    if length:
                        raise Rejection(400, "INVALID_REQUEST")
                    pairs = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True, encoding="utf-8", errors="strict")
                    if len({k for k, _ in pairs}) != len(pairs):
                        raise Rejection(400, "INVALID_REQUEST")
                    query, body = dict(pairs), {}
                else:
                    if url.query:
                        raise Rejection(400, "INVALID_REQUEST")
                    media = self.headers.get_all("Content-Type", [])
                    if len(media) != 1 or not re.fullmatch(r'application/json(?:\s*;\s*charset=utf-8)?', media[0], re.I):
                        raise Rejection(415, "UNSUPPORTED_MEDIA_TYPE")
                    encoding = self.headers.get_all("Content-Encoding", [])
                    if encoding not in ([], ["identity"]):
                        raise Rejection(415, "UNSUPPORTED_MEDIA_TYPE")
                    body, query = strict_json(self.rfile.read(length)), {}
                    if (self.headers.get_all("Origin", []) != [origin]
                            or self.headers.get_all("X-Shadow-Auth-Request", []) != ["1"]
                            or self.headers.get_all("Sec-Fetch-Site", []) not in ([], ["same-origin"])):
                        raise Rejection(403, "ACCESS_DENIED")
                status, body, extra, fault = controller.handle(self.command, url.path, query, body, self.headers)
                self.reply(status, body, extra, fault)
            except Rejection as exc:
                self.reply(exc.status, error(exc.reason))
            except (ValueError, UnicodeError):
                self.reply(400, error("INVALID_REQUEST"))
            except (Unavailable, OSError, KeyError, TypeError):
                self.reply(503, error("SERVICE_UNAVAILABLE"))

        do_GET = dispatch
        do_POST = dispatch

    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8443"))), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(os.environ["V00_TLS_CERT_FILE"], os.environ["V00_TLS_KEY_FILE"])
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    print(json.dumps({"service": "v00-session-recovery", "libsodium": controller.sodium.version}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()
