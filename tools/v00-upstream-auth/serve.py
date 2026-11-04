"""Opt-in TLS server for the isolated V00 bridge. No installation/provisioning."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import socket
import ssl
import uuid
from urllib.parse import urlsplit, parse_qsl

from dependency import Keys, Sodium, Unavailable, private_json
from database import Transaction, IngressTransaction
from bridge import Bridge, Denied
from ingress import Ingress
from provider import Provider
from app import App
from controller import Rejection, strict_json, error


def handler(app, origin):
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query
            or parsed.fragment or parsed.username or parsed.password):
        raise ValueError("exact HTTPS origin required")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def handle_one_request(self):
            self.connection.settimeout(5)
            super().handle_one_request()

        def reply(self, status, body, headers=(), fault=None):
            if fault == "drop_before_headers":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.close_connection = True
                return
            data = b"" if body is None else json.dumps(body, separators=(",", ":"), allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Request-Id", str(uuid.uuid4()))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            for key, value in headers:
                self.send_header(key, value)
            self.end_headers()
            if fault == "drop_after_headers":
                self.wfile.flush()
                self.connection.shutdown(socket.SHUT_RDWR)
                self.close_connection = True
                return
            self.wfile.write(data)

        def dispatch(self):
            try:
                if self.headers.get_all("Host", []) != [parsed.netloc]:
                    raise Rejection(400, "INVALID_REQUEST")
                url = urlsplit(self.path)
                if url.scheme or url.netloc or url.fragment:
                    raise Rejection(400, "INVALID_REQUEST")
                if self.headers.get_all("Transfer-Encoding", []):
                    raise Rejection(400, "INVALID_REQUEST")
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) > 1 or any(not re.fullmatch(r"[0-9]+", x) for x in lengths):
                    raise Rejection(400, "INVALID_REQUEST")
                length = int(lengths[0]) if lengths else 0
                if length > 8192:
                    raise Rejection(413, "REQUEST_TOO_LARGE")
                if self.command == "GET":
                    if length:
                        raise Rejection(400, "INVALID_REQUEST")
                    pairs = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True,
                                      encoding="utf-8", errors="strict")
                    if len({k for k, _ in pairs}) != len(pairs):
                        raise Rejection(400, "INVALID_REQUEST")
                    query, body = dict(pairs), {}
                else:
                    if url.query:
                        raise Rejection(400, "INVALID_REQUEST")
                    if (self.headers.get_all("Origin", []) != [origin]
                            or self.headers.get_all("X-Shadow-Auth-Request", []) != ["1"]
                            or self.headers.get_all("Sec-Fetch-Site", []) not in ([], ["same-origin"])):
                        raise Rejection(403, "ACCESS_DENIED")
                    media = self.headers.get_all("Content-Type", [])
                    if len(media) != 1 or not re.fullmatch(r"application/json(?:\s*;\s*charset=utf-8)?", media[0], re.I):
                        raise Rejection(415, "UNSUPPORTED_MEDIA_TYPE")
                    if self.headers.get_all("Content-Encoding", []) not in ([], ["identity"]):
                        raise Rejection(415, "UNSUPPORTED_MEDIA_TYPE")
                    body, query = strict_json(self.rfile.read(length)), {}
                if self.command == "GET" and url.path == "/__v00__/runner" and not url.query:
                    self.reply(200, {"profile": "isolated-upstream-v00"})
                    return
                status, value, extra, fault = app.handle(self.command, url.path, query, body, self.headers)
                self.reply(status, value, extra, fault)
            except Rejection as exc:
                self.reply(exc.status, error(exc.reason))
            except Denied as exc:
                self.reply(exc.http, error(exc.reason))
            except (ValueError, UnicodeError):
                self.reply(400, error("INVALID_REQUEST"))
            except (Unavailable, OSError, KeyError, TypeError):
                self.reply(503, error("SERVICE_UNAVAILABLE"))

        do_GET = dispatch
        do_POST = dispatch

    return Handler


def serve():
    if os.environ.get("V00_UPSTREAM_ENABLED") != "1":
        raise SystemExit("isolated upstream adapter disabled")
    config = private_json(os.environ["V00_UPSTREAM_CONFIG"])
    keys, sodium = Keys(os.environ["V00_KEY_FILE"]), Sodium()
    runtime_command = json.loads(os.environ["V00_UPSTREAM_PSQL_COMMAND_JSON"])
    ingress_command = json.loads(os.environ["V00_INGRESS_PSQL_COMMAND_JSON"])
    if runtime_command == ingress_command:
        raise SystemExit("distinct ingress and runtime connections required")
    runtime = lambda: Transaction(runtime_command)
    ingress = Ingress(lambda: IngressTransaction(ingress_command))
    bridge = Bridge(runtime, Provider(os.environ["V00_PROVIDER_ORIGIN"]), keys, sodium)
    app = App(config, keys, sodium, bridge, ingress, runtime)

    class Server(ThreadingHTTPServer):
        def handle_error(self, *_):
            # No request values, stack locals or provider response in stdout/logs.
            print('{"event":"upstream_transport_error"}', flush=True)

    server = Server(("0.0.0.0", int(os.environ.get("PORT", "8443"))), handler(app, os.environ["V00_ORIGIN"]))
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(os.environ["V00_TLS_CERT_FILE"], os.environ["V00_TLS_KEY_FILE"])
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    print(json.dumps({"service": "v00-upstream-auth", "libsodium": sodium.version}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()
