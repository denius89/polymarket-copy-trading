"""Real Chrome cookie checks over the upstream flow; codes enter private stdin."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import uuid

from dependency import private_json
from provider import six_digits

spec = importlib.util.spec_from_file_location("session_browser_driver",
    Path(__file__).resolve().parents[1] / "v00-session-recovery" / "browser_probe.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
Browser = driver.Browser


def run(config, endpoint, name, code_supplier, mfa=False, response_loss=False):
    browser, checks = Browser(endpoint), []
    fixture, origin = config["fixtures"][name], config["origin"]
    ctx = fixture["context_id"]

    def check(case, condition):
        checks.append({"case": case, "passed": bool(condition), "layer": "browser"})
        if not condition:
            raise AssertionError(case)

    def history(op, action):
        return browser.fetch(f"/api/auth/contexts/{ctx}/operations/{op}?requestSchemaVersion=v1&commandType={action}")

    def recovery(op, action):
        return browser.fetch(f"/api/auth/contexts/{ctx}/operations/{op}/login-cookie",
                             {"requestSchemaVersion": "v1", "commandType": action})

    def verify(action, challenge):
        op = str(uuid.uuid4())
        code = six_digits(code_supplier("email" if action == "C02" else "totp"))
        body = {"requestSchemaVersion": "v1", "commandType": action, "authContextId": ctx,
                "authOperationId": op, "challengeId": challenge, "code": code}
        issued = browser.fetch("/api/auth/verify" if action == "C02" else "/api/auth/totp/verify", body)
        check(action + "_direct", issued.get("networkError") is True if response_loss else issued.get("status") == 200)
        read = history(op, action)
        check(action + "_original_result", read.get("status") == 200 and read["body"]["status"] == "resolved"
              and read["body"]["operationRef"] == {"authContextId": ctx, "authOperationId": op, "commandType": action})
        return op, read["body"]["result"], issued

    try:
        browser.call("POST", "/url", {"url": origin + "/__v00__/runner"})
        started = browser.fetch(f"/__v00__/fixtures/{name}/context", {"requestSchemaVersion": "v1"},
                                {"Authorization": "Bearer " + fixture["fixture_token"]})
        check("context_bootstrap", started.get("status") == 201)
        op, result, issued = verify("C02", fixture["email_challenge_id"])
        action = "C02"
        if mfa:
            check("email_without_full_login", result["kind"] == "auth_step_required" and
                  not any(key.startswith("__Host-shadow-user-login-") for key in browser.cookies()))
            op, result, issued = verify("AUTH_TOTP_VERIFY", result["challengeId"])
            action = "AUTH_TOTP_VERIFY"
        check("login_completed", result["kind"] == "login_completed")
        login = result["completion"]["loginId"]
        cookie_name = "__Host-shadow-user-login-" + login

        def me():
            return browser.fetch("/api/me?requestSchemaVersion=v1", headers={"X-Shadow-Login-Id": login})

        current_cookies = browser.cookies()
        original = current_cookies.get(cookie_name)
        check("javascript_cannot_read_auth", browser.js("return document.cookie") == "")
        if original is not None:
            check("full_cookie_attributes", original["secure"] and original["httpOnly"] and
                  original["sameSite"] == "Strict" and original["path"] == "/" and
                  original["domain"] == urlsplit(origin).hostname and "expiry" in original)
        if response_loss:
            # Observe cookie delivery, then Q01 first. No assumption based on network error.
            first = me()
            check("loss_q01_first", first.get("status") == (200 if original is not None else 401))
            check("loss_history_stable", history(op, action)["body"]["result"] == result)
            if original is None:
                check("loss_explicit_recovery", recovery(op, action).get("status") == 200)
        else:
            check("full_cookie_present", original is not None)
            browser.call("DELETE", "/cookie/" + cookie_name)
            check("lost_cookie_q01", me().get("status") == 401)
            before = history(op, action)
            check("history_never_reissues", before.get("status") == 200 and cookie_name not in browser.cookies())
            check("explicit_recovery", recovery(op, action).get("status") == 200)
            recovered = browser.cookies()[cookie_name]
            check("same_secret_and_expiry", recovered["value"] == original["value"] and recovered["expiry"] == original["expiry"])
        current = me()
        check("q01_selected_login", current.get("status") == 200 and current.get("login") == login)
        closed = recovery(op, action)
        check("q01_closes_recovery", closed.get("status") == 409 and closed["body"]["reasonCode"] == "AUTH_COOKIE_RECOVERY_CLOSED")
        check("erasure_keeps_login", me().get("status") == 200)
        prep = browser.fetch("/api/auth/logout-contexts", {"requestSchemaVersion": "v1"}, {"X-Shadow-Login-Id": login})
        check("logout_target", prep.get("status") == 201 and prep["body"]["logoutContext"]["loginId"] == login)
        logout_ctx, logout_op = prep["body"]["logoutContext"]["logoutContextId"], str(uuid.uuid4())
        out = browser.fetch("/api/auth/logout", {"requestSchemaVersion": "v1", "commandType": "C07",
            "logoutContextId": logout_ctx, "authOperationId": logout_op})
        check("logout_clears_selected_cookie", out.get("status") == 204 and cookie_name not in browser.cookies())
        check("logged_out_not_current", me().get("status") == 401)
        return {"profile": "upstream-browser-v1", "fixture": name, "checks": checks,
                "browser": {"name": browser.capabilities.get("browserName"), "version": browser.capabilities.get("browserVersion")},
                "source": {"context_id": ctx, "operation_id": op, "action": action, "login_id": login},
                "cookie_delivered_with_lost_response": original is not None if response_loss else None}
    finally:
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--webdriver", default="http://127.0.0.1:9515")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--mfa", action="store_true")
    parser.add_argument("--response-loss", action="store_true")
    args = parser.parse_args()

    def supply(stage):
        print(json.dumps({"event": "need_code", "stage": stage}), flush=True)
        value = json.loads(sys.stdin.readline())
        if type(value) is not dict or set(value) != {"code"}:
            raise ValueError("invalid private code input")
        return six_digits(value["code"])

    try:
        print(json.dumps(run(private_json(args.config), args.webdriver, args.fixture, supply,
                             args.mfa, args.response_loss)), flush=True)
    except Exception as exc:
        print(json.dumps({"passed": False, "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
