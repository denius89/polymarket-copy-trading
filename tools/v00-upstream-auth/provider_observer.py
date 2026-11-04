"""Operator-only single-forward provider observer; separate from hold_proxy.

Count mode forwards the original request once immediately. Late mode forwards
that same request once after 12 seconds, beyond the original admission budget.
There is no release action, resend, redirect, refresh, or provider response log.
"""
import argparse
import http.client
from http.server import ThreadingHTTPServer
import json
import os
import re
import ssl
import sys
import threading
from urllib.parse import urlsplit

from hold_proxy import State, handler, stamp


class Observer(State):
    def __init__(self, email, code, observer_token, mode, origin, connection_factory=None):
        super().__init__(email, code, observer_token, 7)
        if mode not in {"count", "late"}:
            raise ValueError("invalid observation mode")
        target = urlsplit(origin)
        if (target.scheme not in {"http", "https"} or not target.hostname or target.username or target.password
                or target.path not in {"", "/"} or target.query or target.fragment):
            raise ValueError("invalid trusted provider origin")
        self.mode, self.target, self.factory = mode, target, connection_factory
        self.forward_attempts = self.provider_responses = self.forward_errors = 0
        self.forward_started_at = self.provider_headers_at = self.provider_body_at = self.provider_status = None

    def snapshot(self):
        value = super().snapshot()
        # A send attempt is not proof of receipt or a provider DB transaction.
        value.pop("forwarded_requests")
        with self._lock:
            return value | {"schema": "v00-provider-observer-v1", "mode": self.mode,
                            "delay_seconds": 12 if self.mode == "late" else 0,
                            "forward_attempts": self.forward_attempts, "provider_responses": self.provider_responses,
                            "forward_errors": self.forward_errors, "forward_started_at": self.forward_started_at,
                            "provider_headers_at": self.provider_headers_at, "provider_body_at": self.provider_body_at,
                            "provider_status": self.provider_status}

    def forward_once(self, raw, user_agent):
        with self._lock:
            if self.accepted != 1 or self.forward_attempts != 0:
                raise ValueError("single original forward required")
            self.forward_attempts = 1
            self.forward_started_at = stamp()
        if self.factory:
            conn = self.factory()
        else:
            cls = http.client.HTTPSConnection if self.target.scheme == "https" else http.client.HTTPConnection
            options = {"timeout": 5}
            if self.target.scheme == "https":
                options["context"] = ssl.create_default_context()
            conn = cls(self.target.hostname, self.target.port, **options)
        try:
            conn.request("POST", "/verify", body=raw, headers={"Content-Type": "application/json",
                         "Accept": "application/json", "User-Agent": user_agent})
            response = conn.getresponse()
            with self._lock:
                self.provider_headers_at, self.provider_status = stamp(), response.status
            body = response.read(65537)
            if len(body) > 65536 or 300 <= response.status < 400:
                raise ValueError("unusable provider reply")
            with self._lock:
                self.provider_responses = 1
                self.provider_body_at = stamp()
            return response.status, body
        except (OSError, ValueError, http.client.HTTPException):
            with self._lock:
                self.forward_errors += 1
            raise
        finally:
            conn.close()


def observer_handler(state):
    class Handler(handler(state)):
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
            agent = self.headers["User-Agent"]
            if not state.accept(raw, agent):
                del raw
                self.reply(502, {"error": "original_request_only"})
                return
            try:
                if state.mode == "late":
                    # This is the ONE original forwarding, not a retry after timeout.
                    threading.Event().wait(12)
                status, body = state.forward_once(raw, agent)
                del raw
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                del body
            except (OSError, ValueError, http.client.HTTPException):
                # A disconnected adapter is expected for late mode. Never resend.
                pass
            finally:
                self.close_connection = True
                state.close_accepted()
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("count", "late"), required=True)
    parser.add_argument("--provider-origin", default="http://auth:9999")
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9998)
    args = parser.parse_args()
    if os.environ.get("V00_PROVIDER_OBSERVER_ENABLED") != "1":
        raise ValueError("operator observer disabled")
    value = json.loads(sys.stdin.readline())
    if type(value) is not dict or set(value) != {"email", "code", "observer_token"}:
        raise ValueError("invalid private setup")
    state = Observer(value["email"], value["code"], value["observer_token"], args.mode, args.provider_origin)
    del value

    class Server(ThreadingHTTPServer):
        def handle_error(self, *_):
            print('{"event":"observer_transport_error"}', flush=True)

    server = Server((args.bind, args.port), observer_handler(state))
    print(json.dumps({"event": "provider_observer_ready", "mode": args.mode}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"event": "observer_stopped", "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
