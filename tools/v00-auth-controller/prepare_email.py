"""Operator-only synthetic provider setup; NEVER mount in the client container.

V00_EMAIL_OUTPUT is private output; stdout prints only counts. URLs/passwords stay
in memory/private file. Does not confirm the email or invoke the controller.
"""
import hashlib
import html
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import parse_qs, urlsplit
import uuid


def request(origin, method, path, payload=None):
    url = urlsplit(origin)
    if url.scheme != "http": raise ValueError("private HTTP origin required")
    conn = http.client.HTTPConnection(url.hostname, url.port, timeout=8)
    try:
        conn.request(method, path, json.dumps(payload) if payload is not None else None,
                     {"Content-Type": "application/json"})
        response = conn.getresponse()
        if response.status != 200: raise RuntimeError("provider or mailbox unavailable")
        return json.loads(response.read())
    finally:
        conn.close()


def prepare():
    auth, mail = os.environ["V00_PROVIDER_ORIGIN"], os.environ["V00_MAIL_ORIGIN"]
    output = {}
    for fault in json.loads(os.environ.get("V00_EMAIL_FAULTS", '["before_headers","after_effect_before_result","before_send"]')):
        if fault not in {"none", "before_headers", "after_effect_before_result", "before_send"}:
            raise ValueError("unknown fixture")
        address = "v00-controller-" + secrets.token_hex(10) + "@shadow-v00.invalid"
        user = request(auth, "POST", "/signup", {"email": address, "password": secrets.token_urlsafe(32)})
        user_id = user.get("id") or user["user"]["id"]
        path = None
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline and path is None:
            messages = request(mail, "GET", "/api/v1/messages")
            for item in messages.get("messages", []):
                if not any(x.get("Address") == address for x in item.get("To", [])): continue
                message = request(mail, "GET", "/api/v1/message/" + item["ID"])
                match = re.search(r'https?://[^\s"<>]+/verify\?[^\s"<>]+',
                                  html.unescape(message.get("HTML", "") + " " + message.get("Text", "")))
                if match:
                    url = urlsplit(match.group())
                    query = parse_qs(url.query)
                    if url.path != "/verify" or query.get("type") != ["signup"] or len(query.get("token", [])) != 1:
                        raise ValueError("unsupported verification binding")
                    path, token = url.path + "?" + url.query, query["token"][0]
                    break
            if path is None: time.sleep(0.2)
        if path is None: raise RuntimeError("synthetic mail missing")
        output[str(uuid.uuid4())] = {"principal_id": os.environ["V00_TEST_PRINCIPAL"], "user_id": user_id,
            "token_digest": hashlib.sha256(token.encode("ascii")).hexdigest(), "verify_path": path, "fault": fault}
    destination = Path(os.environ["V00_EMAIL_OUTPUT"])
    # O_EXCL refuses to overwrite a previous run or follow a pre-existing symlink.
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(output, stream)
    print(json.dumps({"prepared_synthetic_email_operations": len(output)}))


if __name__ == "__main__":
    try:
        prepare()
    except Exception as exc:
        print(json.dumps({"prepared": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
