"""Closed HTTP rehearsal: real staff gateway adapter, mTLS, and pinned UI files."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import time

from pilot_gateway_wiring import attach_pilot


PRIVATE = Path(__file__).resolve().parent / 'gatewaycfg'
DIST = Path(__file__).resolve().parent / 'api/apps/admin/dist'


def serve():
    config = json.loads((PRIVATE / 'gateway.json').read_text())
    expected_client = (PRIVATE / 'client.sha256').read_text().strip()
    default_dist = DIST.with_name('dist-default')
    assets = {'/admin/': DIST / 'index.html', '/admin/__disabled': default_dist / 'index.html'}
    for dist in (DIST, default_dist):
        assets.update({f'/admin/assets/{path.name}': path for path in (dist / 'assets').iterdir()})

    class Base(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def gateway_reply(self, status, value):
            payload = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def dispatch(self):
            path = assets.get(self.path) if self.command == 'GET' else None
            if path is None:
                return self.gateway_reply(404, {'reasonCode': 'RESOURCE_NOT_FOUND'})
            payload = path.read_bytes()
            media = {'.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript'}[path.suffix]
            self.send_response(200)
            self.send_header('Content-Type', media)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    scoped = attach_pilot(Base, 'https://localhost:18443', config)

    class Handler(scoped):
        def dispatch(self):
            self._paper_deadline_ns = time.monotonic_ns() + 5_000_000_000
            der = self.connection.getpeercert(binary_form=True)
            if not der or hashlib.sha256(der).hexdigest() != expected_client:
                return self.gateway_reply(403, {'reasonCode': 'ACCESS_DENIED'})
            return super().dispatch()

        do_GET = dispatch
        do_POST = dispatch

    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(PRIVATE / 'gateway.crt', PRIVATE / 'gateway.key')
    tls.load_verify_locations(cafile=PRIVATE / 'client.crt')
    tls.verify_mode = ssl.CERT_REQUIRED
    server = ThreadingHTTPServer(('127.0.0.1', 18443), Handler)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    print('PILOT_PRIVATE_GATEWAY_READY', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    serve()
