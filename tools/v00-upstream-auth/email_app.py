"""Public entry routes for the isolated existing-user C01/C03 V00 profile."""
import re

from app import App
from bridge import Denied, read_ref
from controller import Rejection, cookie, envelope, error, exact, uid
from email_api import send_request
from email_crypto import encrypt_email, address_digest
from email_clock import current_clock
from email_input import send_intent
from ingress import intent
from protocol import timestamp
from provider import six_digits


class EmailApp(App):
    def context_fixture(self, _ctx):
        # Compatibility for inherited TOTP routes only. This grants no identity;
        # all context/actor/factor checks are in the new namespace.
        return {}

    def current(self, ref):
        return self.bridge.context(ref["context_id"], ref["proof_digest"])

    @staticmethod
    def current_navigation(state):
        ctx = state["auth_context"]
        pause = state["paused_until"]
        if pause is not None and timestamp(pause) > timestamp(state["observed_at"]):
            params = {"retryAt": pause} if timestamp(pause) <= timestamp(ctx["expiresAt"]) else {}
            return "retry_later", params
        if state["pending_operation"]:
            return None, {}
        return {"totp_verification": ("complete_totp", {"authContextId": ctx["authContextId"]}),
                "totp_enrollment": ("enroll_totp", {"authContextId": ctx["authContextId"]})}.get(ctx["stage"], (None, {}))

    def public(self, outcome, ref, replay=False):
        kind = outcome.value["kind"]
        if kind == "login_completed":
            return super().public(outcome, ref, replay)
        state = self.current(ref)
        action, params = self.current_navigation(state)
        if kind == "verification_rejected":
            body = error("AUTH_VERIFICATION_FAILED")
            body.update(nextAction=action, nextActionParams=params)
            return 401, body, [], None
        if kind == "auth_completion_not_issued":
            return super().public(outcome, ref, replay)
        value = self.bridge.read(read_ref(ref)).value
        if value["status"] != "resolved" or value["result"] != outcome.value:
            from dependency import Unavailable
            raise Unavailable("inconsistent operation read")
        body = envelope(operationRef={"authContextId": ref["context_id"], "authOperationId": ref["operation_id"],
            "commandType": ref["action"]}, status="resolved", result=value["result"], resolvedAt=value["resolved_at"])
        body.update(nextAction=action, nextActionParams=params)
        return 202 if kind == "email_dispatch_accepted" else 200, body, [], None

    def handle(self, method, path, query, body, headers):
        try:
            return self.dispatch_entry(method, path, query, body, headers)
        except Denied as denied:
            if denied.http == 429:
                # Retry timing is optional; don't invent it from a missing source.
                value = error(denied.reason)
                value["nextAction"] = "retry_later"
                return 429, value, [], None
            raise

    def dispatch_entry(self, method, path, query, body, headers):
        if (method == "POST" and (query or body.get("requestSchemaVersion") != "v1")) or (
                method == "GET" and (body or query.get("requestSchemaVersion") != "v1")):
            raise Rejection(400, "INVALID_REQUEST")
        if path.startswith("/__v00__/fixtures/"):
            raise Rejection(404, "RESOURCE_NOT_FOUND")
        if method == "POST" and path == "/api/auth/contexts":
            exact(body, {"requestSchemaVersion"})
            value, proof = self.bridge.create_context()
            ctx = value["auth_context"]
            reply = {"authContext": ctx, "observedAt": value["observed_at"],
                     "nextAction": None, "nextActionParams": {}}
            return 201, reply, [("Set-Cookie", cookie("__Host-shadow-authctx-" + ctx["authContextId"], proof))], None
        context = re.fullmatch(r"/api/auth/contexts/([^/]+)", path)
        if method == "GET" and context:
            exact(query, {"requestSchemaVersion"})
            ctx = uid(context.group(1))
            value = self.bridge.context(ctx, self.context_proof(ctx, headers), confirm=True)
            action, params = {"totp_verification": ("complete_totp", {"authContextId": ctx}),
                              "totp_enrollment": ("enroll_totp", {"authContextId": ctx})}.get(
                                  value["auth_context"]["stage"], (None, {}))
            return 200, {"authContext": value["auth_context"], "observedAt": value["observed_at"],
                         "nextAction": action, "nextActionParams": params}, [], None
        if method == "POST" and path in {"/api/auth/request", "/api/auth/resend"}:
            deadline = current_clock().deadline
            action = "C01" if path == "/api/auth/request" else "C03"
            email = send_request(body, action)
            ctx, op = body["authContextId"], body["authOperationId"]
            proof_digest = self.context_proof(ctx, headers)
            ref = send_intent(self.keys, body, proof_digest)
            binding = None if action == "C03" else {"address_digest": address_digest(self.keys, email),
                                                    "address_key_id": "email-address-1"}
            capture = ref | {"challenge_id": body.get("expectedChallengeId"), "locale": body["locale"],
                             "email_binding": binding}
            admission, executor, expires, created = self.ingress.capture(capture)
            material = encrypt_email(self.keys, self.sodium, ctx, email, expires) if action == "C01" and created else None
            outcome = self.bridge.send(ref, admission, executor, material, deadline=deadline)
            return self.public(outcome, ref)
        if method == "POST" and path in {"/api/auth/verify", "/api/auth/totp/verify"}:
            deadline = current_clock().deadline
            exact(body, {"requestSchemaVersion", "commandType", "authContextId", "authOperationId", "challengeId", "code"})
            action = "C02" if path == "/api/auth/verify" else "AUTH_TOTP_VERIFY"
            if body["commandType"] != action:
                raise Rejection(400, "INVALID_REQUEST")
            ctx, op, challenge = (uid(body[k]) for k in ("authContextId", "authOperationId", "challengeId"))
            six_digits(body["code"])
            ref = intent(self.keys, body, self.context_proof(ctx, headers))
            admission, executor, _, _ = self.ingress.capture(ref | {"challenge_id": challenge, "locale": None, "email_binding": None})
            if action == "C02":
                outcome = self.bridge.verify_entry(ref, challenge, admission, executor, body["code"], deadline=deadline)
            else:
                outcome = self.bridge.verify_totp(ref, challenge, admission, executor, body["code"], deadline=deadline)
            return self.public(outcome, ref)
        operation = re.fullmatch(r"/api/auth/contexts/([^/]+)/operations/([^/]+)", path)
        if method == "GET" and operation:
            exact(query, {"requestSchemaVersion", "commandType"})
            if type(query["commandType"]) is not str or query["commandType"] not in {"C01", "C02", "C03", "AUTH_TOTP_VERIFY"}:
                raise Rejection(400, "INVALID_REQUEST")
            ctx, op = (uid(v) for v in operation.groups())
            ref = {"context_id": ctx, "operation_id": op, "action": query["commandType"],
                   "proof_digest": self.context_proof(ctx, headers)}
            value = self.bridge.read(ref).value
            return value["http"], envelope(operationRef={"authContextId": ctx, "authOperationId": op,
                "commandType": ref["action"]}, status=value["status"], result=value["result"],
                resolvedAt=value["resolved_at"]), [], None
        return super().handle(method, path, query, body, headers)
