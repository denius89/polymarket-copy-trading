"""Loopback-only invitation preview. Builds the web app and uses a synthetic email provider."""
from contextlib import closing
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import subprocess
from tempfile import TemporaryDirectory
from threading import Lock
from urllib.parse import urlsplit
from uuid import uuid4

import gateway

HOST = '127.0.0.1'
PORT = 19787
ORIGIN = f'http://{HOST}:{PORT}'
EMAIL = 'demo@example.test'
UNIT = {'n': '200', 'd': '1'}
ZERO = {'n': '0', 'd': '1'}
NOTICE = '''
<script>
const hint = document.createElement('p');
hint.setAttribute('role', 'status');
hint.style.cssText = 'padding:12px;border:1px solid #67559a;border-radius:8px;margin-top:16px';
let shownFor;
async function updateTestMail() {
  const main = document.querySelector('main');
  const field = main?.querySelector('input[type="email"], input[autocomplete="one-time-code"]');
  if (!field) { hint.remove(); shownFor = undefined; return; }
  if (shownFor === field) return;
  shownFor = field;
  main.append(hint);
  hint.textContent = 'Тестовый вход · email: demo@example.test';
  if (field.autocomplete !== 'one-time-code') return;
  try {
    const response = await fetch('/__dev__/mail', {cache:'no-store'});
    const {code} = await response.json();
    if (shownFor === field && code) hint.textContent = 'Тестовый код: ' + code;
  } catch {
    if (shownFor === field) hint.textContent = 'Не удалось показать код. Откройте локальное демо заново.';
  }
}
new MutationObserver(updateTestMail).observe(document.body, {childList:true,subtree:true});
updateTestMail();
</script>
'''.encode()


class TestMailbox:
    def __init__(self):
        self.lock = Lock()
        self.code = None

    def issue(self):
        with self.lock:
            self.code = f'{secrets.randbelow(1_000_000):06d}'

    def verify(self, code):
        with self.lock:
            if self.code is None or not code.isascii() or not secrets.compare_digest(self.code, code):
                return False
            self.code = None
            return True

    def clear(self):
        with self.lock:
            self.code = None


class TestResponse:
    def __init__(self, status, value, headers=()):
        self.status = status
        self.payload = json.dumps(value).encode()
        self.headers = headers

    def read(self, _limit):
        return self.payload

    def getheaders(self):
        return self.headers


def product_for(mailbox, session):
    context, challenge, login = (str(uuid4()) for _ in range(3))
    proof = secrets.token_urlsafe(32)
    context_cookie = gateway.CONTEXT_COOKIE + context + '=' + proof
    login_cookie = gateway.LOGIN_COOKIE + login + '=' + proof

    def cookie(value):
        return [('Set-Cookie', value + '; Path=/; Secure; HttpOnly; SameSite=Strict')]

    def session_reply():
        states = {'dataOrigin': 'synthetic', 'controlState': 'copying_not_connected', 'contentState': 'EMPTY'}
        return {
            'session': {
                'summary': {**states, 'sessionId': session, 'mode': 'paper', 'traderDisplayName': 'tradecraft',
                            'venueId': 'polymarket', 'asOf': '2026-11-20T12:00:00Z'},
                'settings': {'sizingMode': 'fixed', 'budget': UNIT, 'fixedAmount': {'n': '10', 'd': '1'},
                             'copyPercent': None, 'marketLimitPercent': '20', 'dailyBuyLimitPercent': '20'},
                'financialSnapshot': {**states, 'free': UNIT, 'equity': UNIT, 'reserved': ZERO,
                                      'positionValue': ZERO, 'tradingResult': ZERO, 'positionCount': '0',
                                      'orderCount': '0', 'coverageState': 'no_trade_data'},
            },
        }

    def respond(method, path, body, headers):
        cookie_values = headers.get('Cookie', '').split('; ')
        if path == '/api/auth/contexts' and method == 'POST':
            return TestResponse(201, {'authContext': {'authContextId': context}}, cookie(context_cookie))
        if path.startswith('/api/auth/'):
            if context_cookie not in cookie_values:
                return TestResponse(403, {'reasonCode': 'ACCESS_DENIED'})
            if path == '/api/auth/contexts/' + context and method == 'GET':
                return TestResponse(200, {'authContext': {'authContextId': context}})
            if path == '/api/auth/request' and method == 'POST':
                if body.get('email') != EMAIL:
                    return TestResponse(400, {'reasonCode': 'INVALID_REQUEST'})
                mailbox.issue()
                return TestResponse(202, {'result': {'kind': 'email_dispatch_accepted', 'challengeId': challenge}})
            if path == '/api/auth/verify' and method == 'POST':
                code = body.get('code')
                if body.get('challengeId') != challenge or not isinstance(code, str) or not mailbox.verify(code):
                    return TestResponse(401, {'reasonCode': 'AUTH_VERIFICATION_FAILED'})
                return TestResponse(200, {'completion': {'loginId': login}}, cookie(login_cookie))
        if method == 'GET' and path in gateway.READS:
            if headers.get('X-Shadow-Login-Id') != login or login_cookie not in cookie_values:
                return TestResponse(401, {'reasonCode': 'AUTH_REQUIRED'})
            if path == '/api/me':
                return TestResponse(200, {'authenticated': True}, [('X-Shadow-Login-Id', login)])
            return TestResponse(200, session_reply())
        return TestResponse(404, {'reasonCode': 'RESOURCE_NOT_FOUND'})

    class TestProduct:
        def __init__(self, *_):
            self.response = None

        def request(self, method, target, body, headers):
            data = json.loads(body) if body else {}
            self.response = respond(method, urlsplit(target).path, data, headers)

        def getresponse(self):
            return self.response

        def close(self):
            pass

    return TestProduct


def preview_edge(gateway_port, invitations, mailbox, key):
    class Edge(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def response(self, status, payload=b'', headers=()):
            self.send_response(status)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def relay(self):
            if self.headers.get_all('Host') != [f'{HOST}:{PORT}']:
                return self.response(421)
            path = urlsplit(self.path).path
            if self.command == 'GET' and path == '/__dev__/open':
                invitations.revoke()
                mailbox.clear()
                return self.response(302, headers=[('Location', gateway.ROOT + '#' + invitations.issue(900))])
            if self.command == 'GET' and path == '/__dev__/mail':
                with mailbox.lock:
                    data = json.dumps({'code': mailbox.code}).encode()
                return self.response(200, data, [('Content-Type', 'application/json')])
            headers = dict(self.headers.items())
            headers['X-Shadow-Invite-Edge'] = key
            if self.command == 'POST':
                length = self.headers.get('Content-Length', '')
                if not length.isdigit() or int(length) > 4096:
                    return self.response(400)
                body = self.rfile.read(int(length))
            else:
                body = None
            with closing(http.client.HTTPConnection(HOST, gateway_port, timeout=10)) as connection:
                connection.request(self.command, self.path, body, headers)
                result = connection.getresponse()
                content = result.read()
                if result.status == 200 and path.startswith(gateway.APP) and result.getheader('Content-Type', '').startswith('text/html'):
                    content = content.replace(b'</body>', NOTICE + b'</body>')
                forwarded = [(name, value) for name, value in result.getheaders()
                             if name.lower() not in {'date', 'server', 'content-length', 'cache-control'}]
                return self.response(result.status, content, forwarded)

        do_GET = do_POST = relay

    return ThreadingHTTPServer((HOST, PORT), Edge)


def run():
    from os import environ
    from socket import create_connection
    from threading import Thread
    from time import sleep

    repo = Path(__file__).resolve().parents[2]
    with TemporaryDirectory(prefix='shadow-test-mail-') as work:
        root = Path(work)
        dist = root / 'dist'
        env = {**environ, 'VITE_PUBLIC_BASE': gateway.APP, 'VITE_SHADOW_API_PREFIX': gateway.APP.rstrip('/')}
        subprocess.run(['npm', 'run', 'build', '--workspace', '@cct/web', '--', '--outDir', str(dist)],
                       cwd=repo, env=env, check=True)
        key = secrets.token_hex(32)
        (root / 'edge.key').write_text(key)
        cert, private = root / 'local.crt', root / 'local.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-keyout', str(private), '-out', str(cert)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        with ThreadingHTTPServer((HOST, 0), BaseHTTPRequestHandler) as reservation:
            gateway_port = reservation.server_port
        session = str(uuid4())
        mailbox = TestMailbox()
        invitations = gateway.Invitations(root / 'invitations.sqlite3', 900)
        gateway.ProductConnection = product_for(mailbox, session)
        config = {'origin': ORIGIN, 'edgeKeyFile': str(root / 'edge.key'), 'upstreamCaFile': str(cert),
                  'upstreamClientCertFile': str(cert), 'upstreamClientKeyFile': str(private), 'distDir': str(dist),
                  'listenHost': HOST, 'listenPort': gateway_port, 'participant': 'participant-b', 'sessionId': session}
        Thread(target=gateway.serve, args=(config, invitations), daemon=True).start()
        for _ in range(30):
            try:
                with create_connection((HOST, gateway_port), timeout=0.3):
                    break
            except OSError:
                sleep(0.1)
        else:
            raise RuntimeError('Local invitation preview did not start')
        with preview_edge(gateway_port, invitations, mailbox, key) as edge:
            print(f'{ORIGIN}/__dev__/open', flush=True)
            edge.serve_forever()


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        pass
