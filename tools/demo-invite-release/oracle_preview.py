"""Temporary test preview on a private Oracle interface. Never connects to product Auth."""
import argparse
from contextlib import closing
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import re
import secrets
import ssl
from threading import Thread
from time import sleep
from urllib.parse import urlsplit
from uuid import uuid4

import dev_preview
import gateway

ROOT = '/app/dev-demo/'
APP = ROOT + 'demo/'
ISSUE_ENDPOINT = APP + 'api/auth/request'
NOTICE = '''
<script>
const originalFetch = window.fetch.bind(window);
let testCode;
window.fetch = async (input, init) => {
  const response = await originalFetch(input, init);
  if (typeof input === 'string' && new URL(input,location.href).pathname === '/app/dev-demo/demo/api/auth/request' && response.ok) {
    const message = await response.clone().json();
    testCode = message.testCode;
  }
  return response;
};
const hint = document.createElement('p');
hint.setAttribute('role','status');
hint.style.cssText='padding:12px;border:1px solid #67559a;border-radius:8px;margin-top:16px';
function showTestMail() {
  const main=document.querySelector('main');
  const email=main?.querySelector('input[type="email"]');
  const code=main?.querySelector('input[autocomplete="one-time-code"]');
  if (!email && !code) { hint.remove(); testCode=undefined; return; }
  if (!hint.isConnected) main.append(hint);
  const text=code && testCode ? 'Тестовый код: '+testCode : 'Режим разработки · demo@example.test';
  if (hint.textContent !== text) hint.textContent=text;
}
function observeLogin() {
  new MutationObserver(showTestMail).observe(document.body,{childList:true,subtree:true});
  showTestMail();
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',observeLogin);
else observeLogin();
</script>
'''.encode()


def edge_server(config, mailbox, edge_key, internal_port):
    host = urlsplit(config['origin']).netloc

    class Edge(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def response(self, status, payload=b'', headers=()):
            self.send_response(status)
            self.send_header('Cache-Control', 'private, no-store')
            self.send_header('Content-Length', str(len(payload)))
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def relay(self):
            edge_headers = self.headers.get_all('X-Shadow-Invite-Edge', [])
            if (self.headers.get_all('Host') != [host] or len(edge_headers) != 1
                    or not secrets.compare_digest(edge_headers[0].encode(), edge_key.encode())):
                return self.response(403)
            target = urlsplit(self.path)
            if target.netloc or not target.path.startswith(ROOT):
                return self.response(404)
            if self.command == 'POST':
                lengths = self.headers.get_all('Content-Length', [])
                if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,4}', lengths[0]) or int(lengths[0]) > 4096:
                    return self.response(400)
                body = self.rfile.read(int(lengths[0]))
            else:
                body = None
            forwarded_names = {'cookie', 'origin', 'content-type', 'x-shadow-login-id'}
            inbound = {k: v for k, v in self.headers.items() if k.lower() in forwarded_names}
            inbound.update({'Host': host, 'X-Shadow-Invite-Edge': edge_key})
            try:
                with closing(HTTPConnection('127.0.0.1', internal_port, timeout=10)) as connection:
                    connection.request(self.command, self.path, body, inbound)
                    result = connection.getresponse()
                    content = result.read()
                    response_headers = [(name, value) for name, value in result.getheaders()
                                        if name.lower() not in {'date', 'server', 'content-length', 'cache-control'}]
                    if result.status == 200 and target.path.startswith(APP) and result.getheader('Content-Type', '').startswith('text/html'):
                        content = content.replace(b'<head>', b'<head>' + NOTICE, 1)
                    if result.status == 202 and target.path == ISSUE_ENDPOINT:
                        response = json.loads(content)
                        with mailbox.lock:
                            response['testCode'] = mailbox.code
                        content = json.dumps(response).encode()
                    return self.response(result.status, content, response_headers)
            except (OSError, ValueError):
                return self.response(503)

        do_GET = do_POST = relay

    return ThreadingHTTPServer((config['listenHost'], config['listenPort']), Edge)


def run(config, invitations):
    from socket import create_connection

    gateway.ROOT = ROOT
    gateway.APP = APP
    gateway.LANDING = gateway.LANDING.replace(b'/app/invite/', ROOT.encode())
    edge_key = Path(config['edgeKeyFile']).read_text().strip()
    if not re.fullmatch(r'[a-f0-9]{64}', edge_key):
        raise ValueError('Invalid private edge key')
    mailbox = dev_preview.TestMailbox()
    session = str(uuid4())
    gateway.ProductConnection = dev_preview.product_for(mailbox, session)
    inner_port = config['innerPort']
    local_config = {**config, 'listenHost':'127.0.0.1', 'listenPort':inner_port,
                    'sessionId':session, 'participant':'participant-b'}
    with edge_server(config, mailbox, edge_key, inner_port) as server:
        Thread(target=gateway.serve, args=(local_config, invitations), daemon=True).start()
        for _ in range(30):
            try:
                with create_connection(('127.0.0.1', inner_port), timeout=0.2):
                    break
            except OSError:
                sleep(0.1)
        else:
            raise RuntimeError('Preview gateway did not start')
        server.serve_forever()


def main():
    from os import umask
    umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    parser.add_argument('command', choices=('serve','issue','revoke'))
    parser.add_argument('--minutes', type=int, choices=range(1, 181), default=120)
    args = parser.parse_args()
    config = gateway.json_object(args.config.read_bytes())
    origin = urlsplit(config['origin'])
    ip = ipaddress.ip_address(config['listenHost'])
    if origin.scheme != 'https' or not origin.hostname or origin.path or origin.query or origin.fragment:
        parser.error('The preview requires its exact HTTPS origin')
    if not ip.is_private or ip.is_unspecified:
        parser.error('The preview listener requires a private interface')
    invitations = gateway.Invitations(config['database'], 7200)
    if args.command == 'serve':
        run(config, invitations)
    elif args.command == 'issue':
        print(config['origin'] + ROOT + '#' + invitations.issue(args.minutes * 60))
    else:
        invitations.revoke()


if __name__ == '__main__':
    main()
