"""Explicitly enabled TLS service for the isolated existing-user email profile."""
from http.server import ThreadingHTTPServer
import json
import os
import ssl

from dependency import Keys, Sodium, private_json
from email_app import EmailApp
from email_bridge import EmailBridge
from email_clock import request_clock
from email_database import EmailTransaction, EmailIngressTransaction, EmailWitnessTransaction
from email_ingress import EmailIngress
from provider import Provider
from serve import handler


def email_handler(app, origin):
    base = handler(app, origin)

    class Handler(base):
        def handle_one_request(self):
            with request_clock():
                return super().handle_one_request()

    return Handler


def serve():
    if os.environ.get("V00_EMAIL_ENTRY_ENABLED") != "1":
        raise SystemExit("isolated email entry disabled")
    config = private_json(os.environ["V00_EMAIL_CONFIG"])
    if config.get("fixtures"):
        raise SystemExit("preinstalled context fixtures forbidden in email entry")
    keys, sodium = Keys(os.environ["V00_KEY_FILE"]), Sodium()
    commands = [json.loads(os.environ[name]) for name in (
        "V00_EMAIL_PSQL_COMMAND_JSON", "V00_EMAIL_INGRESS_PSQL_COMMAND_JSON", "V00_EMAIL_WITNESS_PSQL_COMMAND_JSON")]
    if any(type(c) is not list or not c or any(type(x) is not str for x in c) for c in commands):
        raise SystemExit("separate bound executor commands required")
    if len({tuple(c) for c in commands}) != 3:
        raise SystemExit("distinct ingress/runtime/witness roles required")
    runtime = lambda: EmailTransaction(commands[0])
    ingress_tx = lambda: EmailIngressTransaction(commands[1])
    witness_tx = lambda: EmailWitnessTransaction(commands[2])
    bridge = EmailBridge(runtime, Provider(os.environ["V00_PROVIDER_ORIGIN"]), keys, sodium, witness_tx, ingress_tx)
    app = EmailApp(config | {"fixtures": {}}, keys, sodium, bridge, EmailIngress(ingress_tx), runtime)

    class Server(ThreadingHTTPServer):
        def handle_error(self, *_):
            print('{"event":"email_entry_transport_error"}', flush=True)

    server = Server(("0.0.0.0", int(os.environ.get("PORT", "8443"))), email_handler(app, os.environ["V00_ORIGIN"]))
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(os.environ["V00_TLS_CERT_FILE"], os.environ["V00_TLS_KEY_FILE"])
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    print(json.dumps({"service": "v00-email-entry", "libsodium": sodium.version}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()
