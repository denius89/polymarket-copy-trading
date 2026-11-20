"""HTTPS and mTLS edge for a separately configured closed staff pilot."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import ssl
import stat
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from pilot_gateway import stamp
from pilot_gateway_wiring import attach_pilot

PRIVATE_RANGES = tuple(map(ipaddress.ip_network, (
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8',
)))
ASSET_TYPES = {'.js': 'application/javascript', '.css': 'text/css'}


def protected_file(name):
    path = Path(name)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('Expected a canonical path')
    parent = path.parent.stat()
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        trusted_uids = {os.geteuid(), 0}
        if parent.st_uid not in trusted_uids or parent.st_mode & 0o022:
            raise ValueError('Writable private directory')
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid not in trusted_uids:
            raise ValueError('Expected a private file')
        return stream.read(16385)


def load_profile(path):
    data = protected_file(path)
    if len(data) > 16384:
        raise ValueError('Oversized edge profile')
    profile = json.loads(data)
    fields = {'origin', 'listenHost', 'listenPort', 'adminDist', 'certificate',
              'certificateKey', 'clientCA', 'clientPins', 'pilot'}
    if type(profile) is not dict or set(profile) != fields:
        raise ValueError('Invalid edge profile')
    parsed = urlsplit(profile['origin'])
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or (
        profile['origin'] != f'https://{parsed.netloc}'
    ):
        raise ValueError('Expected exact HTTPS origin')
    host = ipaddress.IPv4Address(profile['listenHost'])
    port = profile['listenPort']
    if not any(host in network for network in PRIVATE_RANGES) or type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Expect a private unprivileged listener')
    pins = profile['clientPins']
    if type(pins) is not list or len(pins) != 2 or not all(
        isinstance(pin, str) and re.fullmatch('[a-f0-9]{64}', pin) for pin in pins
    ) or pins[0] == pins[1]:
        raise ValueError('Expect two distinct client certificate pins')
    if profile['pilot'].get('enabled') is not True:
        raise ValueError('Pilot explicitly disabled')
    for field in ('adminDist', 'certificate', 'certificateKey', 'clientCA'):
        value = Path(profile[field])
        if not value.is_absolute() or value.resolve() != value:
            raise ValueError('Expected a canonical artifact path')
    protected_file(profile['certificateKey'])
    return profile, parsed.netloc


class StaffServer(ThreadingHTTPServer):
    def __init__(self, address, handler, tls):
        self.tls = tls
        super().__init__(address, handler)

    def finish_request(self, request, client_address):
        request.settimeout(5)
        with self.tls.wrap_socket(request, server_side=True) as peer:
            super().finish_request(peer, client_address)

    def handle_error(self, request, client_address):
        # Do not log TLS exception details, private paths, or request content.
        pass


def serve(profile, authority):
    app = Path(profile['adminDist'])
    assets = {'/admin/': (app / 'index.html', 'text/html; charset=utf-8')}
    for file in (app / 'assets').iterdir():
        if file.is_file() and not file.is_symlink() and file.suffix in ASSET_TYPES:
            assets[f'/admin/assets/{file.name}'] = (file, ASSET_TYPES[file.suffix])
    if not (app / 'index.html').is_file() or len(assets) == 1:
        raise ValueError('Missing admin build')
    cutoff = stamp(profile['pilot']['cutoffAt'])
    pins = set(profile['clientPins'])

    class Base(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def end_headers(self):
            self.send_header('Strict-Transport-Security', 'max-age=31536000')
            self.send_header('Referrer-Policy', 'no-referrer')
            super().end_headers()

        def reply(self, status, content, media):
            self.send_response(status)
            self.send_header('Content-Type', media)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def gateway_reply(self, status, body):
            self.reply(status, json.dumps(body).encode(), 'application/json; charset=utf-8')

        def dispatch(self):
            path = self.path.partition('?')[0]
            if self.command != 'GET' or path not in assets:
                return self.gateway_reply(404, {'reasonCode': 'RESOURCE_NOT_FOUND'})
            file, media = assets[path]
            self.reply(200, file.read_bytes(), media)

    scoped = attach_pilot(Base, profile['origin'], profile['pilot'], client_ip=lambda h: h.client_address[0])

    class Handler(scoped):
        def dispatch(self):
            self._paper_deadline_ns = time.monotonic_ns() + 5_000_000_000
            peer = self.connection.getpeercert(binary_form=True)
            if not peer or hashlib.sha256(peer).hexdigest() not in pins or self.headers.get_all('Host') != [authority]:
                return self.gateway_reply(403, {'reasonCode': 'ACCESS_DENIED'})
            if datetime.now(timezone.utc) >= cutoff:
                return self.gateway_reply(503, {'reasonCode': 'SERVICE_UNAVAILABLE'})
            return super().dispatch()

        do_GET = do_POST = do_PATCH = dispatch

    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(profile['certificate'], profile['certificateKey'])
    tls.load_verify_locations(cafile=profile['clientCA'])
    tls.verify_mode = ssl.CERT_REQUIRED
    with StaffServer((profile['listenHost'], profile['listenPort']), Handler, tls) as server:
        print('STAFF_HTTPS_READY', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config')
    args = parser.parse_args()
    try:
        serve(*load_profile(args.config))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise SystemExit('Staff HTTPS unavailable') from None
