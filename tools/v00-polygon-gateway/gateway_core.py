"""Private paper-gateway primitives. No listener, migration or activation on import."""
from contextlib import contextmanager
from contextvars import ContextVar
import base64
import hashlib
import hmac
import http.client
import io
import json
import re
import struct
import time
from urllib.parse import urlsplit

NS = 1_000_000_000
DOMAIN = b'shadow.polygon.ingress.v1\0'
MAX_BODY = 65536
MAX_REPLY = 262144
INTERNAL = ('x-shadow-internal-deadline-ns', 'x-shadow-internal-body-sha256',
            'x-shadow-internal-proof')
FORWARD = ('origin', 'content-type', 'content-encoding', 'sec-fetch-site',
           'x-shadow-auth-request', 'x-shadow-login-id', 'cookie', 'x-correlation-id')
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
_ROUTES = (
    ('GET', r'/api/traders'),
    ('GET', rf'/api/traders/(?:polymarket|limitless)/{UUID}'),
    ('POST', r'/api/demo/drafts'),
    ('GET', rf'/api/demo/drafts/{UUID}'),
    ('PATCH', rf'/api/demo/drafts/{UUID}'),
    ('POST', r'/api/demo/validate'),
    ('POST', r'/api/sessions'),
    ('GET', r'/api/sessions/current'),
    ('GET', rf'/api/sessions/{UUID}'),
    ('GET', rf'/api/commands/{UUID}'),
)
_q01_deadline = ContextVar('polygon_q01_deadline', default=None)


class GatewayUnavailable(Exception):
    pass


class InvalidRequest(Exception):
    def __init__(self, status=400):
        self.status = status


def remaining(deadline_ns, clock=time.monotonic_ns):
    left = deadline_ns - clock()
    if left <= 0:
        raise GatewayUnavailable('original request budget elapsed')
    return left / NS


def route_allowed(method, target):
    # HTTP origin-form only; no decoding/canonicalization before signing.
    if not isinstance(target, str) or not target.startswith('/') or target.startswith('//'):
        return False
    if any(ord(c) <= 32 or ord(c) >= 127 for c in target):
        return False
    url = urlsplit(target)
    if url.scheme or url.netloc or url.fragment:
        return False
    return any(method == m and re.fullmatch(p, url.path) for m, p in _ROUTES)


def signed_headers(key, method, target, body, deadline_ns):
    if type(key) is not bytes or len(key) != 32:
        raise GatewayUnavailable('invalid ingress key')
    if type(deadline_ns) is not int or not 0 < deadline_ns < 10**19:
        raise GatewayUnavailable('invalid trusted deadline')
    digest = hashlib.sha256(body).hexdigest()
    mac = hmac.new(key, DOMAIN, hashlib.sha256)
    for value in (method, target, digest, str(deadline_ns)):
        encoded = value.encode('utf8')
        mac.update(struct.pack('!I', len(encoded)))
        mac.update(encoded)
    proof = base64.urlsafe_b64encode(mac.digest()).rstrip(b'=').decode('ascii')
    return dict(zip(INTERNAL, (str(deadline_ns), digest, proof)))


def request_headers(headers, origin, method, length):
    """Copy only explicit public fields; caller internal/forwarded fields never pass."""
    host = urlsplit(origin).netloc
    if headers.get_all('Host', []) != [host]:
        raise InvalidRequest()
    if headers.get_all('Transfer-Encoding', []):
        raise InvalidRequest()
    lengths = headers.get_all('Content-Length', [])
    if len(lengths) > 1 or any(not re.fullmatch(r'[0-9]+', x) for x in lengths):
        raise InvalidRequest()
    declared = int(lengths[0]) if lengths else 0
    if declared != length or (method == 'GET' and length):
        raise InvalidRequest()
    if length > MAX_BODY:
        raise InvalidRequest(413)
    result = {'Host': host, 'Content-Length': str(length)}
    for name in FORWARD:
        values = headers.get_all(name, [])
        if len(values) > 1:
            raise InvalidRequest()
        if values:
            result[name] = values[0]
    if method in ('POST', 'PATCH'):
        if (headers.get_all('Origin', []) != [origin]
                or headers.get_all('X-Shadow-Auth-Request', []) != ['1']
                or headers.get_all('Sec-Fetch-Site', []) not in ([], ['same-origin'])):
            raise InvalidRequest(403)
        media = result.get('content-type', '')
        if (not re.fullmatch(r'application/json(?:\s*;\s*charset=utf-8)?', media, re.I)
                or headers.get_all('Content-Encoding', []) not in ([], ['identity'])):
            raise InvalidRequest(415)
    return result


def read_body(stream, length, deadline_ns, connection, clock=time.monotonic_ns):
    """read1 avoids waiting for the whole body under a resetting idle timeout."""
    if not 0 <= length <= MAX_BODY:
        raise InvalidRequest(413)
    parts = []
    size = 0
    while size < length:
        connection.settimeout(remaining(deadline_ns, clock))
        chunk = stream.read1(min(8192, length - size))
        remaining(deadline_ns, clock)
        if not chunk:
            raise InvalidRequest()
        parts.append(chunk)
        size += len(chunk)
    remaining(deadline_ns, clock)
    return b''.join(parts)


@contextmanager
def q01_budget(deadline_ns):
    remaining(deadline_ns)
    token = _q01_deadline.set(deadline_ns)
    try:
        yield
    finally:
        _q01_deadline.reset(token)


def bounded_runtime(factory):
    """Cap existing transaction; never renew Q01 budget after parsing or queueing."""
    def create():
        deadline = _q01_deadline.get()
        if deadline is not None:
            remaining(deadline)
        tx = factory()
        if deadline is not None:
            # Factory/process creation is charged to the same absolute clock.
            tx.deadline = min(tx.deadline, deadline / NS)
        return tx
    return create


class UpstreamDeadlineReader(io.RawIOBase):
    """One absolute bound for response headers and body, including slow trickles."""
    def __init__(self, raw, sock, deadline_ns):
        self.raw, self.sock, self.deadline_ns = raw, sock, deadline_ns

    def readable(self):
        return True

    def readinto(self, buffer):
        self.sock.settimeout(remaining(self.deadline_ns))
        count = self.raw.readinto(buffer)
        remaining(self.deadline_ns)
        return count

    def close(self):
        try:
            self.raw.close()
        finally:
            super().close()


class ResponseSocket:
    def __init__(self, sock, deadline_ns):
        self.sock, self.deadline_ns = sock, deadline_ns

    def makefile(self, mode):
        raw = self.sock.makefile(mode, buffering=0)
        return io.BufferedReader(UpstreamDeadlineReader(raw, self.sock, self.deadline_ns))


class PaperUpstream:
    def __init__(self, host, port, origin, read_key, connection_factory=http.client.HTTPConnection):
        self.host, self.port, self.origin = host, port, origin
        self.read_key, self.connection_factory = read_key, connection_factory
        parsed = urlsplit(origin)
        if parsed.scheme != 'https' or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError('canonical HTTPS origin required')

    def exchange(self, method, target, body, public_headers, deadline_ns, *, identity=False):
        internal_target = '/__polygon__/identity?requestSchemaVersion=v1'
        if identity:
            if method != 'GET' or target != internal_target or body:
                raise InvalidRequest(404)
        elif not route_allowed(method, target):
            raise InvalidRequest(404)
        headers = request_headers(public_headers, self.origin, method, len(body))
        try:
            key = self.read_key()
        except Exception as exc:
            raise GatewayUnavailable('ingress key unavailable') from exc
        headers.update(signed_headers(key, method, target, body, deadline_ns))
        connection = self.connection_factory(self.host, self.port, timeout=remaining(deadline_ns))
        try:
            connection.connect()
            sock = connection.sock
            connection.response_class = lambda sock, **kwargs: http.client.HTTPResponse(
                ResponseSocket(sock, deadline_ns), **kwargs)
            original_send = connection.send
            def bounded_send(data):
                sock.settimeout(remaining(deadline_ns))
                result = original_send(data)
                remaining(deadline_ns)
                return result
            connection.send = bounded_send
            sock.settimeout(remaining(deadline_ns))
            connection.request(method, target, body=body, headers=headers)
            sock.settimeout(remaining(deadline_ns))
            response = connection.getresponse()
            remaining(deadline_ns)
            parts, total = [], 0
            while True:
                sock.settimeout(remaining(deadline_ns))
                chunk = response.read1(min(8192, MAX_REPLY + 1 - total))
                remaining(deadline_ns)
                if not chunk:
                    break
                parts.append(chunk)
                total += len(chunk)
                if total > MAX_REPLY:
                    raise GatewayUnavailable('upstream response too large')
            content_type = response.getheaders()
            if [v for k, v in content_type if k.lower() == 'content-type'] != ['application/json; charset=utf-8']:
                raise GatewayUnavailable('invalid upstream response type')
            diagnostics = {}
            for name in ('x-request-id', 'x-correlation-id'):
                values = [v for k, v in content_type if k.lower() == name]
                if len(values) > 1 or (values and not re.fullmatch(UUID, values[0])):
                    raise GatewayUnavailable('invalid upstream diagnostic header')
                if values:
                    diagnostics[name] = values[0]
            if 'x-request-id' not in diagnostics:
                raise GatewayUnavailable('missing upstream request id')
            return response.status, b''.join(parts), diagnostics
        except (OSError, http.client.HTTPException) as exc:
            raise GatewayUnavailable('paper upstream unavailable') from exc
        finally:
            connection.close()

    def map_identity(self, public_headers, deadline_ns):
        status, raw, _ = self.exchange('GET', '/__polygon__/identity?requestSchemaVersion=v1',
                                    b'', public_headers, deadline_ns, identity=True)
        try:
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('duplicate identity field')
                    result[key] = value
                return result
            value = json.loads(raw, object_pairs_hook=unique)
            if status != 200 or type(value) is not dict or set(value) != {'userId'} or not re.fullmatch(UUID, value['userId']):
                raise ValueError()
            return value['userId']
        except (TypeError, ValueError, UnicodeError):
            raise GatewayUnavailable('product identity mapping unavailable') from None
