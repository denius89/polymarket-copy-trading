"""Real transport probe. Codes arrive on stdin, never in argv or public reports.

This is not browser evidence. Run from the isolated client network with a trusted
CA; the client must not reach provider, Mailpit or PostgreSQL directly.
"""
import argparse
import http.cookiejar
import http.client
import json
import ssl
import sys
import urllib.error
import urllib.request
import uuid

from dependency import private_json
from provider import six_digits


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


class Client:
    def __init__(self, origin, ca):
        self.origin = origin
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca)),
            urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, path, body=None, headers=None):
        values = dict(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode()
            values |= {"Content-Type": "application/json", "Origin": self.origin,
                       "X-Shadow-Auth-Request": "1", "Sec-Fetch-Site": "same-origin"}
        req = urllib.request.Request(self.origin + path, data=data, headers=values)
        try:
            response = self.opener.open(req, timeout=12)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("oversized response")
            return response.status, json.loads(raw) if raw else None, response.headers

    def operation(self, ctx, op, action, recover=False):
        path = f"/api/auth/contexts/{ctx}/operations/{op}"
        fields = {"requestSchemaVersion": "v1", "commandType": action}
        return self.request(path + "/login-cookie", fields) if recover else self.request(
            path + "?requestSchemaVersion=v1&commandType=" + action)

    def me(self, login):
        return self.request("/api/me?requestSchemaVersion=v1", headers={"X-Shadow-Login-Id": login})


def run(config, ca, name, code_supplier, expect_mfa=False, allow_response_loss=False):
    client, checks = Client(config["origin"], ca), []
    fixture = config["fixtures"][name]
    ctx = fixture["context_id"]

    def check(case, passed):
        entry = {"case": case, "passed": bool(passed)}
        checks.append(entry)
        if not passed:
            raise AssertionError(case)

    started = client.request(f"/__v00__/fixtures/{name}/context", {"requestSchemaVersion": "v1"},
                             {"Authorization": "Bearer " + fixture["fixture_token"]})
    check("context_only_bootstrap", started[0] == 201 and started[1] == {"authContextId": ctx} and
          "user-login" not in started[2].get("Set-Cookie", ""))
    original_cookie = None

    def verify(action, challenge):
        op = str(uuid.uuid4())
        code = six_digits(code_supplier("email" if action == "C02" else "totp"))
        body = {"requestSchemaVersion": "v1", "commandType": action, "authContextId": ctx,
                "authOperationId": op, "challengeId": challenge, "code": code}
        path = "/api/auth/verify" if action == "C02" else "/api/auth/totp/verify"
        try:
            direct = client.request(path, body)
        except (OSError, urllib.error.URLError, http.client.HTTPException):
            if not allow_response_loss:
                raise
            direct = None
        history = client.operation(ctx, op, action)
        check(action + "_resolved_original", history[0] == 200 and history[1]["status"] == "resolved" and
              history[1]["operationRef"] == {"authContextId": ctx, "authOperationId": op, "commandType": action})
        check(action + "_history_no_cookie", history[2].get("Set-Cookie") is None)
        if direct is not None:
            check(action + "_direct_success", direct[0] == 200)
        return op, history[1]["result"], direct

    op, result, direct = verify("C02", fixture["email_challenge_id"])
    action = "C02"
    if expect_mfa:
        check("email_requires_real_totp", result["kind"] == "auth_step_required" and
              result["stage"] == "totp_verification")
        check("email_stage_no_login_cookie", direct is None or direct[2].get("Set-Cookie") is None)
        op, result, direct = verify("AUTH_TOTP_VERIFY", result["challengeId"])
        action = "AUTH_TOTP_VERIFY"
    check("full_completion", result["kind"] == "login_completed")
    completion = result["completion"]
    login = completion["loginId"]
    check("completion_original_operation", completion["authContextId"] == ctx and completion["authOperationId"] == op)
    if direct is not None:
        original_cookie = direct[2].get("Set-Cookie")
        check("completion_cookie_attributes", original_cookie is not None and all(
            part in original_cookie for part in ("Secure", "HttpOnly", "SameSite=Strict", "Path=/", "Expires=")))
    need_recovery = True
    if direct is None:
        # The cookie may have arrived before the response was lost. First Q01,
        # then an explicit recovery only if this login is actually unavailable.
        first_me = client.me(login)
        check("loss_checks_q01_first", first_me[0] in (200, 401))
        need_recovery = first_me[0] == 401
    if need_recovery:
        recovered = client.operation(ctx, op, action, recover=True)
        check("recovery_original_completion", recovered[0] == 200 and recovered[1]["completion"] == completion)
        if original_cookie is not None:
            check("recovery_same_cookie_and_expiry", recovered[2].get("Set-Cookie") == original_cookie)
    me = client.me(login)
    check("q01_verified_login", me[0] == 200 and me[1]["authenticated"] is True and me[2].get("X-Shadow-Login-Id") == login)
    closed = client.operation(ctx, op, action, recover=True)
    check("q01_closes_recovery", closed[0] == 409 and closed[1]["reasonCode"] == "AUTH_COOKIE_RECOVERY_CLOSED"
          and closed[2].get("Set-Cookie") is None)
    check("cipher_erasure_keeps_login", client.me(login)[0] == 200)
    prep = client.request("/api/auth/logout-contexts", {"requestSchemaVersion": "v1"}, {"X-Shadow-Login-Id": login})
    check("logout_context", prep[0] == 201 and prep[1]["logoutContext"]["loginId"] == login)
    logout_ctx, logout_op = prep[1]["logoutContext"]["logoutContextId"], str(uuid.uuid4())
    body = {"requestSchemaVersion": "v1", "commandType": "C07", "logoutContextId": logout_ctx, "authOperationId": logout_op}
    logged_out = client.request("/api/auth/logout", body)
    check("logout_exact_cookie", logged_out[0] == 204 and logged_out[2].get("Set-Cookie", "").startswith(
        "__Host-shadow-user-login-" + login + "=;"))
    check("logout_replay", client.request("/api/auth/logout", body)[0] == 204)
    check("logout_revokes_selected_login", client.me(login)[0] == 401)
    return {"profile": "upstream-transport-v1", "fixture": name, "checks": checks,
            "source": {"context_id": ctx, "operation_id": op, "action": action, "login_id": login}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--ca", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--mfa", action="store_true")
    parser.add_argument("--allow-response-loss", action="store_true")
    args = parser.parse_args()

    def supply(stage):
        print(json.dumps({"event": "need_code", "stage": stage}), flush=True)
        value = json.loads(sys.stdin.readline())
        if type(value) is not dict or set(value) != {"code"}:
            raise ValueError("invalid private code input")
        return six_digits(value["code"])

    try:
        report = run(private_json(args.config), args.ca, args.fixture, supply, args.mfa, args.allow_response_loss)
        print(json.dumps(report), flush=True)
    except Exception as exc:
        print(json.dumps({"passed": False, "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
