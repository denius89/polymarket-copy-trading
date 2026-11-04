"""Operator-only fault endpoint: accept one exact request, never forward anything.

There is intentionally no upstream address, HTTP client, forwarding path, retry,
TLS bypass, or control action to release a buffered request. Only sanitized counts
and source dispatch IDs may be observed. The input secret is read from stdin.
"""
import argparse
from datetime import datetime, timezone
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import socket
import sys
import threading
import time
import uuid


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class State:
    def __init__(self, email, code, observer_token, hold_seconds):
        if (not isinstance(email, str) or not email.isascii() or "@" not in email
                or not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code)
                or not isinstance(observer_token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", observer_token)
                or not 6 <= hold_seconds <= 15):
            raise ValueError("invalid private proxy setup")
        self._expected = json.dumps({"email": email, "token": code, "type": "email"}, separators=(",", ":")).encode()
        self._observer = observer_token.encode()
        self.hold_seconds, self._lock = hold_seconds, threading.Lock()
        self.seen = self.accepted = self.closed = self.rejected = 0
        self.dispatch_id = self.accepted_at = self.closed_at = None

    def observe_allowed(self, authorization):
        return isinstance(authorization, str) and hmac.compare_digest(
            authorization.encode(), b"Bearer " + self._observer)

    def accept(self, raw, user_agent):
        with self._lock:
            self.seen += 1
            prefix = "shadow-v00-upstream/"
            try:
                dispatch = user_agent[len(prefix):] if user_agent.startswith(prefix) else ""
                valid_dispatch = str(uuid.UUID(dispatch)) == dispatch
            except (ValueError, AttributeError, TypeError):
                valid_dispatch = False
            if (self.accepted or self._expected is None or not valid_dispatch
                    or not hmac.compare_digest(raw, self._expected)):
                self.rejected += 1
                return False
            self.accepted = 1
            self.dispatch_id, self.accepted_at = dispatch, stamp()
            # There is no queued request to forward later. Discard the secret
            # immediately; the hold models uncertain transport, not stored mail.
            self._expected = None
            return True

    def close_accepted(self):
        with self._lock:
            self.closed += 1
            self.closed_at = stamp()

    def reject_shape(self):
        with self._lock:
            self.seen += 1
            self.rejected += 1

    def snapshot(self):
        with self._lock:
            return {"schema": "v00-no-forward-proxy-v1", "seen_requests": self.seen,
                    "accepted_requests": self.accepted, "rejected_requests": self.rejected,
                    "closed_requests": self.closed, "forwarded_requests": 0,
                    "dispatch_id": self.dispatch_id, "accepted_at": self.accepted_at,
                    "closed_at": self.closed_at, "hold_seconds": self.hold_seconds}


def handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, value):
            raw = json.dumps(value, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if (self.path != "/__operator__/snapshot" or len(self.headers.get_all("Authorization", [])) != 1
                    or not state.observe_allowed(self.headers.get("Authorization"))):
                self.reply(404, {"error": "not_found"})
                return
            self.reply(200, state.snapshot())

        def do_POST(self):
            self.connection.settimeout(3)
            lengths = self.headers.get_all("Content-Length", [])
            if (self.path != "/verify" or self.headers.get_all("Transfer-Encoding", [])
                    or len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,4}", lengths[0])
                    or not 0 < int(lengths[0]) <= 1024
                    or self.headers.get_all("Content-Type", []) != ["application/json"]
                    or len(self.headers.get_all("User-Agent", [])) != 1):
                state.reject_shape()
                self.reply(400, {"error": "invalid_probe_request"})
                return
            raw = self.rfile.read(int(lengths[0]))
            accepted = state.accept(raw, self.headers["User-Agent"])
            del raw
            if not accepted:
                self.reply(502, {"error": "probe_not_forwarded"})
                return
            # The real adapter's 5-second provider timeout expires while this
            # endpoint sends no headers/body. Never manufacture an Auth response.
            threading.Event().wait(state.hold_seconds)
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.close_connection = True
            state.close_accepted()

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9998)
    parser.add_argument("--hold-seconds", type=float, default=7)
    args = parser.parse_args()
    if os.environ.get("V00_NO_FORWARD_PROXY_ENABLED") != "1":
        raise SystemExit("test proxy disabled")
    value = json.loads(sys.stdin.readline())
    if type(value) is not dict or set(value) != {"email", "code", "observer_token"}:
        raise ValueError("invalid private setup")
    state = State(value["email"], value["code"], value["observer_token"], args.hold_seconds)
    del value

    class Server(ThreadingHTTPServer):
        def handle_error(self, *_):
            print('{"event":"proxy_transport_error"}', flush=True)

    server = Server((args.bind, args.port), handler(state))
    print('{"event":"no_forward_proxy_ready"}', flush=True)
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"event": "proxy_stopped", "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
