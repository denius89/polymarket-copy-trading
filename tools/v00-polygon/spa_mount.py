"""Serve only the reviewed static distributions under dedicated SPA prefixes."""
from pathlib import Path
import re
from urllib.parse import urlsplit

BUILDS = Path('/app/distributions')
MOUNTS = ('app', 'admin')
ROUTE = re.compile(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/?')
ASSET = re.compile(r'[A-Za-z0-9_-]+\.(?:js|css|svg|png|webp|ico|woff2)')
MIME = {
    'js': 'text/javascript; charset=utf-8',
    'css': 'text/css; charset=utf-8',
    'svg': 'image/svg+xml',
    'png': 'image/png',
    'webp': 'image/webp',
    'ico': 'image/x-icon',
    'woff2': 'font/woff2',
}


def resolve(path, builds=BUILDS):
    # Match the mount before looking up an on-disk path. Asset subdirectories
    # and URL decoding are intentionally unsupported for these Vite bundles.
    if not path.startswith('/'):
        return None
    name, separator, suffix = path[1:].partition('/')
    if name not in MOUNTS:
        return None
    root = builds / name
    index = root / 'index.html'
    if not index.is_file():
        return (404, None, None)
    if not separator:
        return (308, None, f'/{name}/')
    if suffix.startswith('assets/'):
        asset = suffix.removeprefix('assets/')
        if not ASSET.fullmatch(asset):
            return (404, None, None)
        file = root / 'assets' / asset
        return (200, file, MIME[file.suffix[1:]]) if file.is_file() else (404, None, None)
    if not suffix or ROUTE.fullmatch(suffix):
        return (200, index, 'text/html; charset=utf-8')
    return (404, None, None)


def serve_static(handler, host, csp):
    if handler.command != 'GET':
        return False
    target = urlsplit(handler.path)
    result = resolve(target.path)
    if result is None:
        return False
    if (target.scheme or target.netloc or target.fragment
            or handler.headers.get_all('Host', []) != [host]
            or handler.headers.get_all('Transfer-Encoding', [])
            or handler.headers.get_all('Content-Length', []) not in ([], ['0'])):
        handler.send_error(400)
        return True
    status, path, value = result
    data = path.read_bytes() if path is not None else b''
    handler.send_response(status)
    if status == 308:
        handler.send_header('Location', value)
    if status == 200:
        handler.send_header('Content-Type', value)
        handler.send_header('Content-Security-Policy', csp)
        handler.send_header('X-Content-Type-Options', 'nosniff')
        handler.send_header('Referrer-Policy', 'no-referrer')
        handler.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Content-Length', str(len(data)))
    handler.end_headers()
    if data:
        handler.wfile.write(data)
    return True
