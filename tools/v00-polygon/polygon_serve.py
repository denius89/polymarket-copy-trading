"""Closed polygon UI over the unchanged V00 Auth adapter; no fixture endpoints."""
from pathlib import Path
import json
import os
import ssl
import sys
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v00-recovery-quota'))
import bootstrap
from recovery_serve import recovery_handler
from recovery_app import RecoveryApp
from recovery_bridge import RecoveryBridge
from recovery_database import CompletionTransaction, RecoveryTransaction, RecoveryQuotaTransaction
from dependency import Keys, Sodium, private_json
from email_database import EmailIngressTransaction, EmailWitnessTransaction
from email_ingress import EmailIngress
from provider import Provider
from controller import error
from spa_mount import serve_static

WEB = Path(__file__).resolve().parent / 'web'
ASSETS = {'/': ('index.html', 'text/html; charset=utf-8'),
          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
          '/style.css': ('style.css', 'text/css; charset=utf-8')}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
       "img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")


def polygon_handler(app, origin):
    base = recovery_handler(app, origin)
    host = urlsplit(origin).netloc

    class Handler(base):
        def dispatch(self):
            if serve_static(self, host, CSP):
                return
            if urlsplit(self.path).path.startswith('/__v00__/'):
                return self.reply(404, error('RESOURCE_NOT_FOUND'))
            # Exact allowlist, no directory server, arbitrary path or file lookup.
            if self.command == 'GET' and self.path in {*ASSETS, '/_polygon/health'}:
                if (self.headers.get_all('Host', []) != [host]
                        or self.headers.get_all('Transfer-Encoding', [])
                        or self.headers.get_all('Content-Length', []) not in ([], ['0'])):
                    return self.reply(400, error('INVALID_REQUEST'))
                if self.path == '/_polygon/health':
                    # Process/HTTP liveness only: does not claim DB/Auth readiness.
                    self.send_response(204)
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                filename, mime = ASSETS[self.path]
                data = (WEB / filename).read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Security-Policy', CSP)
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
                self.end_headers()
                self.wfile.write(data)
                return
            return super().dispatch()

        do_GET = dispatch
        do_POST = dispatch

    return Handler


def make_app():
    if os.environ.get('V00_POLYGON_ENABLED') != '1':
        raise SystemExit('closed polygon disabled')
    if any(os.environ.get(name) for name in (
            'V00_RECOVERY_TEST_CONTROL_DIR', 'V00_RECOVERY_GUARD_PROBE_ENABLED', 'V00_FIXTURE_CONFIG')):
        raise SystemExit('fault/fixture configuration forbidden in persistent polygon')
    config = private_json(os.environ['V00_EMAIL_CONFIG'])
    if config.get('fixtures'):
        raise SystemExit('preinstalled context fixtures forbidden')
    commands = [json.loads(os.environ[name]) for name in (
        'V00_EMAIL_PSQL_COMMAND_JSON', 'V00_EMAIL_INGRESS_PSQL_COMMAND_JSON',
        'V00_EMAIL_WITNESS_PSQL_COMMAND_JSON')]
    if any(type(c) is not list or not c or any(type(x) is not str for x in c) for c in commands):
        raise SystemExit('bound role commands required')
    if len({tuple(c) for c in commands}) != 3:
        raise SystemExit('distinct runtime/ingress/provider witness commands required')
    keys, sodium = Keys(os.environ['V00_KEY_FILE']), Sodium()
    runtime = lambda: CompletionTransaction(commands[0])
    ingress = lambda: EmailIngressTransaction(commands[1])
    witness = lambda: EmailWitnessTransaction(commands[2])
    bridge = RecoveryBridge(runtime, Provider(os.environ['V00_PROVIDER_ORIGIN']), keys, sodium,
        witness, ingress, quota_transaction=lambda deadline: RecoveryQuotaTransaction(commands[1], deadline),
        subject_transaction=lambda deadline: RecoveryTransaction(commands[0], deadline))
    return RecoveryApp(config | {'fixtures': {}}, keys, sodium, bridge, EmailIngress(ingress), runtime)


def serve():
    app = make_app()
    origin = os.environ['V00_ORIGIN']
    class Server(ThreadingHTTPServer):
        daemon_threads = True
        def handle_error(self, *_):
            print('{"event":"polygon_transport_error"}', flush=True)
    server = Server((os.environ.get('V00_BIND_HOST', '127.0.0.1'),
                     int(os.environ.get('PORT', '8443'))), polygon_handler(app, origin))
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(os.environ['V00_TLS_CERT_FILE'], os.environ['V00_TLS_KEY_FILE'])
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    print('{"service":"shadow-polygon","scope":"synthetic-auth-only"}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    serve()
