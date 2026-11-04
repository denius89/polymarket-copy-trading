"""Transport checks, never presented as browser cookie evidence."""
import argparse
import http.cookiejar
import json
import ssl
import urllib.error
import urllib.request

from crypto import private_json


class Client:
    def __init__(self, config, ca):
        self.config = config
        self.jar = http.cookiejar.CookieJar()
        context = ssl.create_default_context(cafile=ca)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=context), urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, path, body=None, headers=None):
        values = dict(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            values |= {"Content-Type": "application/json", "Origin": self.config["origin"], "X-Shadow-Auth-Request": "1"}
        req = urllib.request.Request(self.config["origin"] + path, data=data, headers=values)
        try:
            r = self.opener.open(req, timeout=7)
        except urllib.error.HTTPError as exc:
            r = exc
        raw = r.read()
        return r.status, json.loads(raw) if raw else None, r.headers

    def start(self, name):
        f = self.config["fixtures"][name]
        header = {"Authorization": "Bearer " + f["fixture_token"]}
        r = self.request(f"/__v00__/fixtures/{name}/context", {"requestSchemaVersion": "v1"}, header)
        assert r[0] == 201
        r = self.request(f"/__v00__/fixtures/{name}/complete", {"requestSchemaVersion": "v1",
            "authOperationId": f["operation_id"], "commandType": "C02"}, header)
        assert r[0] == 200
        return f, r

    def operation(self, f, recovery=False):
        path = f'/api/auth/contexts/{f["context_id"]}/operations/{f["operation_id"]}'
        if recovery:
            return self.request(path + "/login-cookie", {"requestSchemaVersion": "v1", "commandType": "C02"})
        return self.request(path + "?requestSchemaVersion=v1&commandType=C02")

    def me(self, f):
        return self.request("/api/me?requestSchemaVersion=v1", headers={"X-Shadow-Login-Id": f["login_id"]})


def run(config, ca):
    c = Client(config, ca)
    checks = []
    def check(name, condition):
        checks.append({"case": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)
    f, issued = c.start("basic")
    original = issued[1]["completion"]
    check("completion_cookie_attributes", all(s in issued[2]["Set-Cookie"] for s in ("Secure", "HttpOnly", "SameSite=Strict", "Path=/", "Expires=")))
    history = c.operation(f)
    check("history_no_cookie", history[0] == 200 and history[1]["result"]["completion"] == original and history[2].get("Set-Cookie") is None)
    recovery = c.operation(f, True)
    check("recovery_exact_cookie", recovery[0] == 200 and recovery[2]["Set-Cookie"] == issued[2]["Set-Cookie"])
    me = c.me(f)
    check("q01_selected_login", me[0] == 200 and me[1]["authenticated"] is True and me[2]["X-Shadow-Login-Id"] == f["login_id"])
    closed = c.operation(f, True)
    check("q01_closes_recovery", closed[0] == 409 and closed[1]["reasonCode"] == "AUTH_COOKIE_RECOVERY_CLOSED" and closed[2].get("Set-Cookie") is None)
    check("erasure_keeps_login", c.me(f)[0] == 200)
    check("history_immutable_after_close", c.operation(f)[1]["result"]["completion"] == original)
    missing = c.request("/api/me?requestSchemaVersion=v1")
    check("selected_header_required", missing[0] == 400)
    prep = c.request("/api/auth/logout-contexts", {"requestSchemaVersion": "v1"}, {"X-Shadow-Login-Id": f["login_id"]})
    ctx = prep[1]["logoutContext"]["logoutContextId"]
    import uuid
    op = str(uuid.uuid4())
    body = {"requestSchemaVersion": "v1", "commandType": "C07", "logoutContextId": ctx, "authOperationId": op}
    result = c.request("/api/auth/logout", body)
    check("logout_exact_cookie", result[0] == 204 and result[1] is None and result[2]["Set-Cookie"].startswith("__Host-shadow-user-login-" + f["login_id"] + "=;"))
    read = c.request(f"/api/auth/logout-contexts/{ctx}/operations/{op}?requestSchemaVersion=v1")
    check("logout_history_no_cookie", read[0] == 200 and read[1]["status"] == "completed" and read[2].get("Set-Cookie") is None)
    check("logout_replay", c.request("/api/auth/logout", body)[0] == 204)
    check("revoked_not_current", c.me(f)[0] == 401)
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("client")
    parser.add_argument("--ca", required=True)
    args = parser.parse_args()
    try:
        for result in run(private_json(args.client), args.ca):
            print(json.dumps(result))
    except Exception as exc:
        # Exception messages/requests may contain secrets; only sanitized type.
        print(json.dumps({"passed": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
