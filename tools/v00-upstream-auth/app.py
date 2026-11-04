"""Isolated upstream HTTP adapter; synthetic completion routes are never exposed."""
import re
import time

from dependency import Unavailable, secret_bytes
from bridge import Denied, read_ref
from ingress import intent
from protocol import decode, require
from provider import six_digits
# Reuse parsing/cookie helpers and the unchanged logout projection only.
from controller import (Controller as SessionController, Rejection, exact, uid,
                        cookie, envelope, selected_login, error)


class CheckedLogout:
    def __init__(self, transaction):
        self.transaction = transaction

    def __enter__(self):
        self.tx = self.transaction.__enter__()
        return self

    def __exit__(self, *args):
        return self.transaction.__exit__(*args)

    def commit(self):
        self.tx.commit()

    def call(self, method, fields):
        if method not in {"logout_prepare", "logout_continue", "logout", "logout_result"}:
            raise Unavailable("non-logout delegation forbidden")
        value = self.tx.call(method, fields)
        decode(method, value, fields)
        return value


class App(SessionController):
    def __init__(self, config, keys, sodium, bridge, ingress, transaction):
        # The parent has synthetic routes, but handle() below never delegates them.
        super().__init__(config, keys, sodium, lambda: CheckedLogout(transaction()))
        self.bridge, self.ingress = bridge, ingress

    def context_fixture(self, ctx):
        matches = [f for f in self.config["fixtures"].values() if f["context_id"] == ctx]
        if len(matches) != 1:
            raise Rejection(404, "RESOURCE_NOT_FOUND")
        return matches[0]

    def public(self, outcome, ref, replay=False):
        kind = outcome.value["kind"]
        if kind == "verification_rejected":
            return 401, error("AUTH_VERIFICATION_FAILED"), [], None
        if kind == "auth_completion_not_issued":
            return 409, error("AUTH_CONTEXT_STATE_CONFLICT"), [], None
        headers = []
        if outcome.cookie:
            require(kind == "login_completed")
            headers.append(("Set-Cookie", cookie("__Host-shadow-user-login-" +
                outcome.value["completion"]["loginId"], outcome.cookie, outcome.expires)))
        if kind == "login_completed":
            return 200, envelope(completion=outcome.value["completion"]), headers, None
        # Read the immutable resolvedAt rather than inventing a timestamp for it.
        read = self.bridge.read(read_ref(ref)).value
        require(read["status"] == "resolved" and read["result"] == outcome.value)
        body = envelope(operationRef={"authContextId": ref["context_id"],
            "authOperationId": ref["operation_id"], "commandType": ref["action"]},
            status="resolved", result=read["result"], resolvedAt=read["resolved_at"])
        # Safe navigation is conservative in this isolated adapter. The result's
        # historical challenge remains available; a full current action resolver
        # is not claimed by this probe package.
        return 200, body, [], None

    def handle(self, method, path, query, body, headers):
        if (method == "POST" and (query or body.get("requestSchemaVersion") != "v1")) or (
                method == "GET" and query.get("requestSchemaVersion") != "v1"):
            raise Rejection(400, "INVALID_REQUEST")
        # Bootstrap only a pre-installed isolated context, never a login/result.
        fixture = re.fullmatch(r"/__v00__/fixtures/([a-z0-9_]+)/context", path)
        if method == "POST" and fixture:
            exact(body, {"requestSchemaVersion"})
            f = self.fixture(fixture.group(1), headers)
            secret_bytes(f["proof"])
            return 201, {"authContextId": f["context_id"]}, [
                ("Set-Cookie", cookie("__Host-shadow-authctx-" + f["context_id"], f["proof"]))], None
        if method == "POST" and path in {"/api/auth/verify", "/api/auth/totp/verify"}:
            deadline = time.monotonic() + 10
            exact(body, {"requestSchemaVersion", "commandType", "authContextId", "authOperationId", "challengeId", "code"})
            action = "C02" if path == "/api/auth/verify" else "AUTH_TOTP_VERIFY"
            if body["commandType"] != action:
                raise Rejection(400, "INVALID_REQUEST")
            ctx, op, challenge = (uid(body[k]) for k in ("authContextId", "authOperationId", "challengeId"))
            try:
                six_digits(body["code"])
            except ValueError:
                raise Rejection(400, "INVALID_REQUEST") from None
            proof_digest = self.context_proof(ctx, headers)
            f = self.context_fixture(ctx)
            ref = intent(self.keys, body, proof_digest)
            admission, executor_proof = self.ingress.capture(ref)
            if action == "C02":
                outcome = self.bridge.verify_email(ref, challenge, admission, executor_proof,
                    f["email"], body["code"], f.get("provider_fault", "none"), deadline=deadline)
            else:
                outcome = self.bridge.verify_totp(ref, challenge, admission, executor_proof, body["code"], deadline=deadline)
            status, value, extra, _ = self.public(outcome, ref)
            return status, value, extra, f.get("response_fault")
        operation = re.fullmatch(r"/api/auth/contexts/([^/]+)/operations/([^/]+)(/login-cookie)?", path)
        if operation:
            ctx, op, recovery = operation.groups()
            uid(ctx); uid(op)
            if (method == "POST") != bool(recovery):
                raise Rejection(404, "RESOURCE_NOT_FOUND")
            fields = body if recovery else query
            exact(fields, {"requestSchemaVersion", "commandType"})
            if fields["commandType"] not in {"C02", "AUTH_TOTP_VERIFY"}:
                raise Rejection(400, "INVALID_REQUEST")
            ref = {"context_id": ctx, "operation_id": op, "action": fields["commandType"],
                   "proof_digest": self.context_proof(ctx, headers)}
            if recovery:
                return self.public(self.bridge.recover(ref), ref)
            value = self.bridge.read(ref).value
            return value["http"], envelope(operationRef={"authContextId": ctx, "authOperationId": op,
                "commandType": ref["action"]}, status=value["status"], result=value["result"],
                resolvedAt=value["resolved_at"]), [], None
        if method == "GET" and path == "/api/me":
            exact(query, {"requestSchemaVersion"})
            login = selected_login(headers)
            value = self.bridge.q01(login, self.login_proof(login, headers)).value
            return 200, {"authenticated": True, "user": {"userId": value["actor_id"], "locale": "en"},
                         "nextAction": "select_trader", "nextActionParams": {}}, [("X-Shadow-Login-Id", login)], None
        if (method == "POST" and path in {"/api/auth/logout-contexts", "/api/auth/logout-contexts/continue", "/api/auth/logout"}) or (
                method == "GET" and re.fullmatch(r"/api/auth/logout-contexts/[^/]+/operations/[^/]+", path)):
            return super().handle(method, path, query, body, headers)
        raise Rejection(404, "RESOURCE_NOT_FOUND")
