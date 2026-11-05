"""Explicitly enabled service for the separately installed recovery-quota profile."""
from http.server import ThreadingHTTPServer
import json
import os
import re
import ssl
import time
from urllib.parse import urlsplit

import bootstrap
from dependency import Keys, Sodium, private_json
from controller import error
from email_database import EmailIngressTransaction, EmailWitnessTransaction
from email_ingress import EmailIngress
from email_serve import email_handler
from provider import Provider
from recovery_bridge import RecoveryBridge, recovery_deadline
from recovery_database import CompletionTransaction, RecoveryTransaction, RecoveryQuotaTransaction
from recovery_app import RecoveryApp


def recovery_handler(app, origin):
    base = email_handler(app, origin)

    class Handler(base):
        def reply(self, status, body, headers=(), fault=None):
            path = urlsplit(getattr(self, "path", "")).path
            is_recovery = (getattr(self, "command", None) == "POST" and re.fullmatch(
                r"/api/auth/contexts/[^/]+/operations/[^/]+/login-cookie", path))
            if is_recovery and (200 <= status < 300 or any(k.lower() == "set-cookie" for k, _ in headers)):
                if time.monotonic() >= recovery_deadline():
                    status, body, headers, fault = 503, error("SERVICE_UNAVAILABLE"), (), None
            return super().reply(status, body, headers, fault)

    return Handler


def serve():
    if os.environ.get("V00_RECOVERY_QUOTA_ENABLED") != "1":
        raise SystemExit("isolated recovery quota disabled")
    config = private_json(os.environ["V00_EMAIL_CONFIG"])
    if config.get("fixtures"):
        raise SystemExit("no preinstalled context fixtures")
    keys, sodium = Keys(os.environ["V00_KEY_FILE"]), Sodium()
    commands = [json.loads(os.environ[name]) for name in (
        "V00_EMAIL_PSQL_COMMAND_JSON", "V00_EMAIL_INGRESS_PSQL_COMMAND_JSON", "V00_EMAIL_WITNESS_PSQL_COMMAND_JSON")]
    if any(type(c) is not list or not c or any(type(x) is not str for x in c) for c in commands):
        raise SystemExit("separate bound executor commands required")
    if len({tuple(c) for c in commands}) != 3:
        raise SystemExit("distinct runtime/ingress/witness roles required")
    runtime = lambda: CompletionTransaction(commands[0])
    ingress = lambda: EmailIngressTransaction(commands[1])
    witness = lambda: EmailWitnessTransaction(commands[2])
    quota = lambda deadline: RecoveryQuotaTransaction(commands[1], deadline)
    subject = lambda deadline: RecoveryTransaction(commands[0], deadline)
    observe = None
    if os.environ.get("V00_RECOVERY_TEST_CONTROL_DIR"):
        from instrument import instrument
        quota, subject, observe = instrument(quota, subject)
    bridge = RecoveryBridge(runtime, Provider(os.environ["V00_PROVIDER_ORIGIN"]), keys, sodium,
        witness, ingress, quota_transaction=quota, subject_transaction=subject, observe=observe)
    app = RecoveryApp(config | {"fixtures": {}}, keys, sodium, bridge, EmailIngress(ingress), runtime)

    class Server(ThreadingHTTPServer):
        def handle_error(self, *_):
            print('{"event":"recovery_quota_transport_error"}', flush=True)

    server = Server(("0.0.0.0", int(os.environ.get("PORT", "8443"))), recovery_handler(app, os.environ["V00_ORIGIN"]))
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(os.environ["V00_TLS_CERT_FILE"], os.environ["V00_TLS_KEY_FILE"])
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    print(json.dumps({"service": "v00-recovery-quota", "libsodium": sodium.version}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()
