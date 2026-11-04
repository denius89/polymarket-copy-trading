"""Real WebDriver browser checks. Credentials only in memory/private input file.

Start ChromeDriver separately in the isolated client container. Trust test CA in
the browser; acceptInsecureCerts is false and certificate bypass flags are absent.
"""
import argparse
import json
import urllib.request
import uuid

from crypto import private_json


class Browser:
    def __init__(self, endpoint):
        self.endpoint = endpoint.rstrip("/")
        self.session = None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        result = self.call("POST", "/session", {"capabilities": {"alwaysMatch": {
            "browserName": "chrome", "acceptInsecureCerts": False,
            "goog:chromeOptions": {"args": ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage"]}}}})
        self.session = result["sessionId"]
        self.capabilities = result["capabilities"]
        self.call("POST", "/timeouts", {"script": 12000, "pageLoad": 15000})

    def call(self, method, path, data=None):
        prefix = "/session/" + self.session if self.session else ""
        request = urllib.request.Request(self.endpoint + prefix + path, method=method,
            data=None if data is None else json.dumps(data).encode(), headers={"Content-Type": "application/json"})
        with self.opener.open(request, timeout=20) as response:
            value = json.load(response)["value"]
        if isinstance(value, dict) and "error" in value:
            raise RuntimeError("WebDriver command failed")
        return value

    def js(self, script, *args):
        return self.call("POST", "/execute/sync", {"script": script, "args": list(args)})

    def fetch(self, path, body=None, headers=None):
        # Includes browser-generated Origin/Sec-Fetch-Site; JS cannot forge these.
        return self.call("POST", "/execute/async", {"script": """
const [path,body,headers,done]=arguments;
const options={credentials:'include',headers:{...headers},cache:'no-store'};
if(body!==null){options.method='POST';options.body=JSON.stringify(body);
 options.headers['Content-Type']='application/json';options.headers['X-Shadow-Auth-Request']='1';}
fetch(path,options).then(async r=>{try{const t=await r.text();done({status:r.status,
 body:t?JSON.parse(t):null,login:r.headers.get('X-Shadow-Login-Id')});}
 catch(e){done({networkError:true,status:r.status});}}).catch(()=>done({networkError:true}));
""", "args": [path, body, headers or {}]})

    def cookies(self):
        return {c["name"]: c for c in self.call("GET", "/cookie")}

    def close(self):
        if self.session:
            self.call("DELETE", "")


def run(config, endpoint):
    browser = Browser(endpoint)
    results = []
    def check(name, condition):
        results.append({"case": name, "passed": bool(condition), "layer": "browser"})
        if not condition:
            raise AssertionError(name)
    def start(name):
        f = config["fixtures"][name]
        h = {"Authorization": "Bearer " + f["fixture_token"]}
        r = browser.fetch(f"/__v00__/fixtures/{name}/context", {"requestSchemaVersion": "v1"}, h)
        check(name + "_context", r.get("status") == 201)
        r = browser.fetch(f"/__v00__/fixtures/{name}/complete", {"requestSchemaVersion": "v1",
            "commandType": "C02", "authOperationId": f["operation_id"]}, h)
        return f, r
    def me(f):
        return browser.fetch("/api/me?requestSchemaVersion=v1", headers={"X-Shadow-Login-Id": f["login_id"]})
    def recovery(f):
        return browser.fetch(f'/api/auth/contexts/{f["context_id"]}/operations/{f["operation_id"]}/login-cookie',
                             {"requestSchemaVersion": "v1", "commandType": "C02"})
    def history(f):
        return browser.fetch(f'/api/auth/contexts/{f["context_id"]}/operations/{f["operation_id"]}?requestSchemaVersion=v1&commandType=C02')
    try:
        browser.call("POST", "/url", {"url": config["origin"] + "/__v00__/runner"})
        f, issued = start("recovery")
        check("completion", issued.get("status") == 200)
        name = "__Host-shadow-user-login-" + f["login_id"]
        cookies = browser.cookies()
        original = cookies[name]
        context = cookies["__Host-shadow-authctx-" + f["context_id"]]
        check("full_cookie_security", original["secure"] and original["httpOnly"] and original["sameSite"] == "Strict"
              and original["path"] == "/" and "expiry" in original and original["domain"] == "session-d0307.invalid")
        check("context_session_cookie", "expiry" not in context and context["secure"] and context["httpOnly"])
        check("javascript_cannot_read_auth_cookies", browser.js("return document.cookie") == "")
        browser.call("DELETE", "/cookie/" + name)
        check("lost_cookie_q01", me(f).get("status") == 401)
        historical = history(f)
        check("history_does_not_restore_cookie", historical.get("status") == 200 and name not in browser.cookies())
        check("explicit_recovery", recovery(f).get("status") == 200)
        recovered = browser.cookies()[name]
        check("same_secret_and_expiry", recovered["value"] == original["value"] and recovered["expiry"] == original["expiry"])
        r = me(f)
        check("q01_verifies_selected", r.get("status") == 200 and r.get("login") == f["login_id"])
        r = recovery(f)
        check("q01_closes_new_issuance", r.get("status") == 409 and r["body"]["reasonCode"] == "AUTH_COOKIE_RECOVERY_CLOSED")
        check("existing_cookie_survives_erasure", me(f).get("status") == 200)
        check("historical_result_stable", history(f)["body"]["result"] == historical["body"]["result"])

        a, _ = start("logout_a")
        tab_a = browser.call("GET", "/window")
        browser.js("sessionStorage.setItem('probeSelectedLogin',arguments[0]);", a["login_id"])
        prep = browser.fetch("/api/auth/logout-contexts", {"requestSchemaVersion": "v1"}, {"X-Shadow-Login-Id": a["login_id"]})
        ctx = prep["body"]["logoutContext"]["logoutContextId"]
        tab_b = browser.call("POST", "/window/new", {"type": "tab"})["handle"]
        browser.call("POST", "/window", {"handle": tab_b})
        browser.call("POST", "/url", {"url": config["origin"] + "/__v00__/runner"})
        b, _ = start("logout_b")
        browser.js("sessionStorage.setItem('probeSelectedLogin',arguments[0]);", b["login_id"])
        an, bn = "__Host-shadow-user-login-" + a["login_id"], "__Host-shadow-user-login-" + b["login_id"]
        b_cookie = browser.cookies()[bn]
        browser.call("POST", "/window", {"handle": tab_a})
        check("separate_tab_selection", browser.js("return sessionStorage.getItem('probeSelectedLogin')") == a["login_id"])
        continued = browser.fetch("/api/auth/logout-contexts/continue", {"requestSchemaVersion": "v1",
            "sourceLogoutContextId": ctx, "authorizationMode": "current_user"}, {"X-Shadow-Login-Id": b["login_id"]})
        check("continue_keeps_original_target", continued.get("status") == 201 and continued["body"]["logoutContext"]["loginId"] == a["login_id"])
        cctx = continued["body"]["logoutContext"]["logoutContextId"]
        op = str(uuid.uuid4())
        payload = {"requestSchemaVersion": "v1", "commandType": "C07", "logoutContextId": cctx, "authOperationId": op}
        mismatch = browser.fetch("/api/auth/logout", payload, {"X-Shadow-Login-Id": b["login_id"]})
        check("wrong_selected_logout_target_rejected", mismatch.get("status") == 400 and me(b).get("status") == 200)
        out = browser.fetch("/api/auth/logout", payload)
        check("logout_a_only", out.get("status") == 204 and an not in browser.cookies() and browser.cookies()[bn]["value"] == b_cookie["value"])
        check("b_still_current", me(b).get("status") == 200)
        read = browser.fetch(f"/api/auth/logout-contexts/{cctx}/operations/{op}?requestSchemaVersion=v1")
        check("logout_history", read.get("status") == 200 and read["body"]["status"] == "completed")

        for case in ("loss_before", "loss_after"):
            lost, response = start(case)
            check(case + "_response_lost", response.get("networkError") is True)
            n = "__Host-shadow-user-login-" + lost["login_id"]
            present = n in browser.cookies()
            check(case + "_cookie_observation", present == (case == "loss_after"))
            current = me(lost)  # Always Q01 first after uncertain completion transport.
            before = history(lost)
            check(case + "_history_confirmed", before.get("status") == 200)
            if not present:
                check(case + "_q01_missing", current.get("status") == 401)
                check(case + "_recovery", recovery(lost).get("status") == 200)
                current = me(lost)
            check(case + "_eventual_q01", current.get("status") == 200)
        lost, _ = start("logout_lost")
        prep = browser.fetch("/api/auth/logout-contexts", {"requestSchemaVersion": "v1"}, {"X-Shadow-Login-Id": lost["login_id"]})
        ctx = prep["body"]["logoutContext"]["logoutContextId"]
        op = str(uuid.uuid4())
        out = browser.fetch("/api/auth/logout", {"requestSchemaVersion": "v1", "commandType": "C07", "logoutContextId": ctx, "authOperationId": op})
        check("logout_response_lost", out.get("networkError") is True)
        check("stale_browser_cookie_does_not_revive", me(lost).get("status") == 401)
        read = browser.fetch(f"/api/auth/logout-contexts/{ctx}/operations/{op}?requestSchemaVersion=v1")
        check("lost_logout_result_recovered", read.get("status") == 200 and read["body"]["status"] == "completed")
        return results, {"browser": browser.capabilities.get("browserName"), "version": browser.capabilities.get("browserVersion")}
    finally:
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("client")
    parser.add_argument("--webdriver", default="http://127.0.0.1:9515")
    args = parser.parse_args()
    try:
        results, browser = run(private_json(args.client), args.webdriver)
        print(json.dumps({"browser": browser}))
        for result in results:
            print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"passed": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
