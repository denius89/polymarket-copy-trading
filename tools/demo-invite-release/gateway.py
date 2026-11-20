"""Private release gateway for a one-time invitation to read an existing demo."""
import argparse
from contextlib import closing
import hashlib
import hmac
import http.client
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import ssl
import time
from urllib.parse import urlsplit

ROOT = '/app/invite/'
APP = ROOT + 'demo/'
GRANT = '__Secure-shadow-demo-invite'
UUID = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
TOKEN = re.compile(r'[A-Za-z0-9_-]{43}')
AUTH_CONTEXT = re.compile(rf'/api/auth/contexts/({UUID})(?:/operations/{UUID})?')
READS = {'/api/me', '/api/sessions/current'}
WRITES = {'/api/auth/contexts', '/api/auth/request', '/api/auth/verify', '/api/auth/totp/verify'}
ASSET = re.compile(r'assets/[A-Za-z0-9_.-]+\.(?:css|js)')
PAGES = {'login', 'home', 'positions', 'activity', 'help'}
LOGIN_COOKIE = '__Host-shadow-user-login-'
CONTEXT_COOKIE = '__Host-shadow-authctx-'
PROOF_PREFIX = '__Secure-shadow-invite-proof-'
LIMIT = 128 * 1024

LANDING = '''<!doctype html>
<html lang="ru"><meta charset="utf-8"><title>Приглашение в демо</title>
<style>
body{background:#0c1018;color:#f1f2fa;font:16px system-ui;max-width:440px;margin:12vh auto;padding:16px}
button{background:#7043da;color:white;padding:12px 24px;border:0;border-radius:9px;font:inherit}
</style>
<main><h1>Приглашение в демо</h1><button>Открыть демо</button><p role="status"></p></main>
<script>
const token=location.hash.slice(1);
history.replaceState(null,'',location.pathname);
const button=document.querySelector('button');
const notice=document.querySelector('[role=status]');
button.addEventListener('click',async()=>{
  button.disabled=true;
  try{
    const response=await fetch('/app/invite/redeem',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
    if(response.ok){location.replace('/app/invite/demo/login');return;}
    notice.textContent=response.status===403?'Ссылка истекла или уже была использована.':'Сервис временно недоступен. Попробуйте ещё раз.';
    button.disabled=response.status===403;
  }catch{
    notice.textContent='Не удалось открыть демо. Попробуйте ещё раз.';
    button.disabled=false;
  }
});
</script></html>
'''.encode()


def digest(token):
    return hashlib.sha256(token.encode('ascii')).hexdigest()


class Invitations:
    def __init__(self, database, duration):
        self.database = Path(database)
        self.duration = duration
        with closing(self.connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS invitation (token TEXT PRIMARY KEY, expires INTEGER NOT NULL)')
            db.execute('''CREATE TABLE IF NOT EXISTS grant_access (
                grant TEXT PRIMARY KEY, expires INTEGER NOT NULL, context TEXT, login TEXT)''')

    def connect(self):
        return sqlite3.connect(self.database, timeout=3, isolation_level='IMMEDIATE')

    def issue(self, lifetime):
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            for table in ('invitation', 'grant_access'):
                db.execute(f'DELETE FROM {table} WHERE expires <= ?', (now,))
                if db.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone():
                    raise ValueError('An invitation or its access is already active')
            db.execute('INSERT INTO invitation VALUES (?,?)', (digest(token), now + lifetime))
        return token

    def redeem(self, token):
        if not isinstance(token, str) or not TOKEN.fullmatch(token):
            return None
        now = int(time.time())
        grant = secrets.token_urlsafe(32)
        with closing(self.connect()) as db, db:
            deleted = db.execute('DELETE FROM invitation WHERE token=? AND expires>?', (digest(token), now))
            if deleted.rowcount != 1:
                return None
            db.execute('INSERT INTO grant_access VALUES (?,?,NULL,NULL)', (digest(grant), now + self.duration))
        return grant

    def read(self, grant):
        if not TOKEN.fullmatch(grant):
            return None
        with closing(self.connect()) as db:
            return db.execute('SELECT context,login FROM grant_access WHERE grant=? AND expires>?',
                              (digest(grant), int(time.time()))).fetchone()

    def bind(self, grant, context, login, previous_context):
        with closing(self.connect()) as db, db:
            return db.execute('''UPDATE grant_access SET context=?,login=?
                WHERE grant=? AND expires>? AND context IS ? AND (login IS NULL OR login=?)''',
                              (context, login, digest(grant), int(time.time()), previous_context, login)).rowcount == 1

    def revoke(self):
        with closing(self.connect()) as db, db:
            db.execute('DELETE FROM invitation')
            db.execute('DELETE FROM grant_access')


class ProductConnection(http.client.HTTPSConnection):
    def __init__(self, config, tls):
        self.address = (config['upstreamHost'], config['upstreamPort'])
        super().__init__(config['upstreamServerName'], context=tls, timeout=10)

    def connect(self):
        raw = socket.create_connection(self.address, timeout=self.timeout)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


def json_object(payload):
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError('A JSON object is required')
    return data


def validated_uuid(value):
    return isinstance(value, str) and re.fullmatch(UUID, value) is not None


def serve(config, database):
    origin = config['origin']
    public_host = urlsplit(origin).netloc
    edge_key = Path(config['edgeKeyFile']).read_text().strip()
    assert re.fullmatch(r'[a-f0-9]{64}', edge_key)
    tls = ssl.create_default_context(cafile=config['upstreamCaFile'])
    tls.load_cert_chain(config['upstreamClientCertFile'], config['upstreamClientKeyFile'])
    dist = Path(config['distDir']).resolve(strict=True)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, payload=b'', media='application/json', headers=()):
            self.send_response(status)
            self.send_header('Cache-Control', 'private, no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.send_header('Content-Type', media)
            self.send_header('Content-Length', str(len(payload)))
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def api_error(self, status, reason):
            self.reply(status, json.dumps({'reasonCode': reason}).encode())

        def do_GET(self):
            self.dispatch()

        def do_POST(self):
            self.dispatch()

        def dispatch(self):
            try:
                self.route()
            except (OSError, sqlite3.Error, http.client.HTTPException):
                self.api_error(503, 'SERVICE_UNAVAILABLE')
            except (TypeError, ValueError, KeyError, CookieError):
                self.api_error(400, 'INVALID_REQUEST')

        def route(self):
            if self.headers.get_all('Host') != [public_host] or len(self.headers.get_all('X-Shadow-Invite-Edge', [])) != 1:
                return self.api_error(403, 'ACCESS_DENIED')
            if not hmac.compare_digest(self.headers['X-Shadow-Invite-Edge'].encode(), edge_key.encode()):
                return self.api_error(403, 'ACCESS_DENIED')
            target = urlsplit(self.path)
            if target.netloc or not target.path.startswith(ROOT):
                return self.api_error(404, 'RESOURCE_NOT_FOUND')
            if self.command == 'POST':
                if self.headers.get_all('Origin') != [origin] or self.headers.get('Transfer-Encoding'):
                    return self.api_error(403, 'ACCESS_DENIED')
                lengths = self.headers.get_all('Content-Length', [])
                if len(lengths) != 1 or not lengths[0].isdigit() or int(lengths[0]) > 4096:
                    return self.api_error(400, 'INVALID_REQUEST')
                if self.headers.get('Content-Type') != 'application/json':
                    return self.api_error(400, 'INVALID_REQUEST')
                body = self.rfile.read(int(lengths[0]))
            else:
                body = None
            if target.path == ROOT and self.command == 'GET':
                return self.reply(200, LANDING, 'text/html; charset=utf-8')
            if target.path == ROOT + 'redeem' and self.command == 'POST':
                fields = json_object(body)
                if set(fields) != {'token'} or target.query:
                    return self.api_error(400, 'INVALID_REQUEST')
                clean_grant = database.redeem(fields['token'])
                if not clean_grant:
                    return self.api_error(403, 'ACCESS_DENIED')
                cookie = f'{GRANT}={clean_grant}; Path={ROOT}; Secure; HttpOnly; SameSite=Strict; Max-Age={database.duration}'
                return self.reply(200, b'{}', headers=[('Set-Cookie', cookie)])
            if not target.path.startswith(APP):
                return self.api_error(404, 'RESOURCE_NOT_FOUND')
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            grant_cookie = cookies.get(GRANT)
            grant = grant_cookie.value if grant_cookie else ''
            binding = database.read(grant)
            if not binding:
                return self.api_error(403, 'ACCESS_DENIED')
            relative = target.path[len(APP):]
            if relative.startswith('api/'):
                return self.product('/' + relative, target.query, body, cookies, grant, binding)
            if self.command != 'GET' or (relative not in PAGES and not ASSET.fullmatch(relative)):
                return self.api_error(404, 'RESOURCE_NOT_FOUND')
            path = dist / (relative if ASSET.fullmatch(relative) else 'index.html')
            if not path.is_file():
                return self.api_error(404, 'RESOURCE_NOT_FOUND')
            media = {'.html':'text/html; charset=utf-8', '.js':'text/javascript', '.css':'text/css'}[path.suffix]
            return self.reply(200, path.read_bytes(), media)

        def product(self, path, query, body, cookies, grant, binding):
            context, login = binding
            auth_match = AUTH_CONTEXT.fullmatch(path)
            if body is None:
                if path not in READS and not auth_match:
                    return self.api_error(404, 'RESOURCE_NOT_FOUND')
                if auth_match and auth_match[1] != context:
                    return self.api_error(403, 'ACCESS_DENIED')
            else:
                if path not in WRITES:
                    return self.api_error(404, 'RESOURCE_NOT_FOUND')
                if login or (path != '/api/auth/contexts' and (context is None or json_object(body).get('authContextId') != context)):
                    return self.api_error(403, 'ACCESS_DENIED')
            headers = {'Host': public_host, 'X-Shadow-Edge-Participant': config['participant']}
            if path in READS:
                if not login or self.headers.get_all('X-Shadow-Login-Id') != [login]:
                    return self.api_error(401, 'AUTH_REQUIRED')
                headers['X-Shadow-Login-Id'] = login
            if body is not None:
                headers.update({'Origin': origin, 'Sec-Fetch-Site':'same-origin',
                                'X-Shadow-Auth-Request':'1', 'Content-Type':'application/json'})
            allowed_cookies = {CONTEXT_COOKIE + context} if context else set()
            if login:
                allowed_cookies.add(LOGIN_COOKIE + login)
            proofs = SimpleCookie()
            for name in allowed_cookies:
                scoped = cookies.get(PROOF_PREFIX + name)
                if scoped:
                    proofs[name] = scoped.value
            headers['Cookie'] = '; '.join(proof.OutputString() for proof in proofs.values())
            conn = ProductConnection(config, tls)
            try:
                conn.request(self.command, path + ('?' + query if query else ''), body, headers)
                reply = conn.getresponse()
                payload = reply.read(LIMIT + 1)
                if len(payload) > LIMIT:
                    return self.api_error(503, 'RECORD_UNAVAILABLE')
                forwarded = []
                if reply.status in (200, 201, 202):
                    value = json_object(payload)
                    if path == '/api/auth/contexts' and reply.status == 201:
                        new_context = value.get('authContext', {}).get('authContextId')
                        if not validated_uuid(new_context) or not database.bind(grant, new_context, None, context):
                            return self.api_error(503, 'RECORD_UNAVAILABLE')
                        context = new_context
                    if path == '/api/sessions/current':
                        summary = (value.get('session') or {}).get('summary') or {}
                        if summary.get('sessionId') != config['sessionId']:
                            return self.api_error(403, 'ACCESS_DENIED')
                    completion = value.get('completion') or (value.get('result') or {}).get('completion')
                    if completion and (path in WRITES or auth_match):
                        candidate = completion.get('loginId')
                        if not validated_uuid(candidate) or not database.bind(grant, context, candidate, context):
                            return self.api_error(503, 'RECORD_UNAVAILABLE')
                        login = candidate
                    allowed = {CONTEXT_COOKIE + context} if context else set()
                    if login:
                        allowed.add(LOGIN_COOKIE + login)
                    for name, header in reply.getheaders():
                        if name.lower() == 'set-cookie' and header.partition('=')[0] in allowed:
                            upstream_cookie = SimpleCookie(header)
                            original, proof = next(iter(upstream_cookie.items()))
                            scoped_cookie = SimpleCookie()
                            scoped_cookie[PROOF_PREFIX + original] = proof.value
                            scoped = scoped_cookie[PROOF_PREFIX + original]
                            scoped['path'] = APP
                            scoped['secure'] = scoped['httponly'] = True
                            scoped['samesite'] = 'Strict'
                            for attr in ('max-age','expires'):
                                if proof[attr]:
                                    scoped[attr] = proof[attr]
                            forwarded.append(('Set-Cookie', scoped.OutputString()))
                        if name.lower() == 'x-shadow-login-id' and path == '/api/me' and header == login:
                            forwarded.append(('X-Shadow-Login-Id', header))
                return self.reply(reply.status, payload, headers=forwarded)
            finally:
                conn.close()

    with ThreadingHTTPServer((config['listenHost'], config['listenPort']), Handler) as server:
        server.serve_forever()


def main():
    from os import umask
    umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    parser.add_argument('command', choices=('serve', 'issue', 'revoke'))
    parser.add_argument('--minutes', type=int, choices=range(1, 61), default=15)
    args = parser.parse_args()
    config = json_object(args.config.read_bytes())
    if re.fullmatch(r'https://[A-Za-z0-9.-]+(?::[0-9]+)?', config['origin']) is None:
        parser.error('An exact HTTPS origin is required')
    if not validated_uuid(config['sessionId']):
        parser.error('A specific demo session is required')
    if config['participant'] not in ('participant-a', 'participant-b'):
        parser.error('Unknown configured participant')
    access_minutes = config['accessMinutes']
    if type(access_minutes) is not int or not 1 <= access_minutes <= 120:
        parser.error('Access must expire within two hours')
    database = Invitations(config['database'], access_minutes * 60)
    if args.command == 'serve':
        serve(config, database)
    elif args.command == 'issue':
        print(config['origin'] + ROOT + '#' + database.issue(args.minutes * 60))
    else:
        database.revoke()


if __name__ == '__main__':
    main()
