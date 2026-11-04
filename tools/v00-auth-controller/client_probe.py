"""Run inside the CLIENT-ONLY network. Config is private and operator generated."""
import concurrent.futures
import http.client
import json
import os
from pathlib import Path
import socket
import threading
import time
from urllib.parse import urlsplit


def run(config):
    origin = urlsplit(config["controller_origin"])
    evidence = {"schema": "v00-controller-evidence-v1", "cases": [], "full_login_issued": False}
    if len(config.get("forbidden_tcp", [])) != 2 or sorted(t["port"] for t in config["forbidden_tcp"]) != [5432, 9999]:
        raise ValueError("both actual provider and database negative controls required")

    def post(case, discard=False):
        conn = http.client.HTTPConnection(origin.hostname, origin.port, timeout=8)
        try:
            conn.request("POST", case["route"], json.dumps(case["payload"]), {
                "Authorization": "Bearer " + case.get("api_token", config.get("api_token", "")), "Content-Type": "application/json"})
            if discard:
                if conn.sock: conn.sock.shutdown(socket.SHUT_RDWR)
                return None
            response = conn.getresponse()
            body = json.loads(response.read())
            return response.status, body
        finally:
            conn.close()

    for target in config["forbidden_tcp"]:
        denied = False
        try:
            with socket.create_connection((target["host"], target["port"]), timeout=3):
                pass
        except OSError:
            denied = True
        evidence["cases"].append({"id": target["label"], "passed": denied})
        if not denied:
            raise AssertionError("provider/database reachable from client-only network")

    responses = {}
    for case in config.get("cases", []):
        status, body = post(case)
        allowed_http = case["expected_http"] if isinstance(case["expected_http"], list) else [case["expected_http"]]
        passed = status in allowed_http and all(body.get(k) == v for k, v in case.get("expected", {}).items())
        if case.get("same_as"):
            passed = passed and (status, body) == responses[case["same_as"]]
        responses[case["id"]] = (status, body)
        evidence["cases"].append({"id": case["id"], "passed": passed, "http": status,
            "kind": body.get("kind"), "status": body.get("status"), "reason": body.get("reason"),
            "consumed_steps": body.get("consumed_steps")})
        if not passed:
            raise AssertionError("unexpected result: " + case["id"])

    for group in config.get("races", []):
        barrier = threading.Barrier(len(group["requests"]))

        def contender(case):
            barrier.wait(timeout=5)
            return post(case)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(group["requests"])) as pool:
            results = list(pool.map(contender, group["requests"]))
        statuses = sorted(status for status, _ in results)
        passed = statuses == sorted(group["expected_http"])
        evidence["cases"].append({"id": group["id"], "passed": passed, "http": statuses,
                                  "scope": "simultaneous_client_start; DB lock observation is separate"})
        if not passed: raise AssertionError("race result mismatch: " + group["id"])

    for case in config.get("lost_client_reply", []):
        post(case, discard=True)
        deadline = time.monotonic() + 8
        status, body = None, {}
        while time.monotonic() < deadline:
            status, body = post(case | {"route": case["result_route"]})
            if status == case["expected_http"] and body.get("status") == case["expected_status"]:
                break
            time.sleep(0.2)
        passed = status == case["expected_http"] and body.get("status") == case["expected_status"]
        evidence["cases"].append({"id": case["id"], "passed": passed, "http": status,
                                  "status": body.get("status"), "client_read_headers": False})
        if not passed: raise AssertionError("lost response unresolved: " + case["id"])
    return evidence


if __name__ == "__main__":
    # No raw request/config/traceback on failure: fixtures contain proof tokens.
    try:
        result = run(json.loads(Path(os.environ["V00_CLIENT_CONFIG"]).read_text()))
        print(json.dumps(result, sort_keys=True))
    except Exception as exc:
        print(json.dumps({"schema": "v00-controller-evidence-v1", "passed": False,
                          "error_type": type(exc).__name__}))
        raise SystemExit(1)
