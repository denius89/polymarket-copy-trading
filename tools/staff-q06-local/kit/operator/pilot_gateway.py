"""Opt-in pilot staff edge adapter. No listeners or runtime changes on import."""
import base64
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
import hashlib
import hmac
import http.client
import ipaddress
import json
import re
import time
from urllib.parse import urlsplit

from gateway_core import (GatewayUnavailable, InvalidRequest, ResponseSocket, UUID,
                          read_body, remaining, request_headers)

MAX_BODY = 8192
MAX_FRAME = 32768
MAX_REPLY = 65536
PEER_PATH = '/internal/pilot-staff/v1'
AUTH_ROOT = '/api/admin/pilot/auth/contexts'
LOGOUT_ROOT = '/api/admin/auth/logout-contexts'
ROUTES = (
    ('POST', AUTH_ROOT, 'context'),
    ('POST', rf'{AUTH_ROOT}/({UUID})/login', 'login'),
    ('GET', rf'{AUTH_ROOT}/({UUID})/operations/({UUID})', 'outcome'),
    ('POST', rf'{AUTH_ROOT}/({UUID})/operations/({UUID})/cookie', 'recover'),
    ('GET', '/api/admin/pilot/sessions', 'list'),
    ('GET', rf'/api/admin/sessions/({UUID})', 'session'),
    ('GET', rf'/api/admin/pilot/sessions/({UUID})/events', 'events'),
    ('GET', '/api/admin/me', 'me'),
    ('POST', LOGOUT_ROOT, 'logout_prepare'),
    ('POST', LOGOUT_ROOT + '/continue', 'logout_continue'),
    ('POST', '/api/admin/auth/logout', 'logout_execute'),
    ('GET', rf'{LOGOUT_ROOT}/({UUID})/operations/({UUID})', 'logout_read'),
)
AUTH = {'context', 'login', 'outcome', 'recover'}
LOGIN_PROOF = {'list', 'session', 'events', 'me', 'logout_prepare', 'logout_continue'}
COOKIE_TAIL = '; Path=/; Secure; HttpOnly; SameSite=Strict; '
NAV = {'nextAction', 'nextActionParams'}
SUCCESS = {
    'context': {201}, 'login': {200}, 'outcome': {200, 202}, 'recover': {200},
    'list': {200}, 'session': {200}, 'events': {200}, 'me': {200},
    'logout_prepare': {201}, 'logout_continue': {201}, 'logout_execute': {204},
    'logout_read': {200, 202},
}
ERROR_STATUS = {400, 401, 403, 404, 409, 413, 415, 429, 500, 503}


def select(method, target):
    if (not target.startswith('/api/admin/') or len(target) > 2048
            or re.search(r'[\\#\x00-\x20\x7f-\uffff]', target) or not target.isascii()):
        raise InvalidRequest(404)
    path, sep, query = target.partition('?')
    for verb, pattern, name in ROUTES:
        match = re.fullmatch(pattern, path)
        if method == verb and match:
            if ((method == 'GET' and query != 'requestSchemaVersion=v1')
                    or (method == 'POST' and sep)):
                raise InvalidRequest()
            return name, match.groups()
    raise InvalidRequest(404)


def json_object(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError('nonstandard JSON constant')

    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid_constant)
    if type(value) is not dict:
        raise ValueError('JSON object required')
    return value


def uuid(value):
    return isinstance(value, str) and re.fullmatch(UUID, value) is not None


def canonical_secret(value):
    return (isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', value) is not None
            and base64.urlsafe_b64encode(base64.urlsafe_b64decode(value + '=')).decode()[:-1] == value)


def valid_key(key):
    if type(key) is not bytes or len(key) != 32:
        raise GatewayUnavailable('invalid pilot ingress key')
    return key


def network_digest(addr, key):
    if '%' in addr:
        raise ValueError('scoped IP address')
    ip = ipaddress.ip_address(addr)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    prefix = 32 if ip.version == 4 else 64
    network = ipaddress.ip_network((ip, prefix), strict=False)
    wire = bytes((ip.version, prefix)) + network.network_address.packed
    return hmac.new(valid_key(key), b'shadow.pilot.network.v1\0' + wire, hashlib.sha256).hexdigest()


def credentials(headers, route, ids, body):
    selected = headers.get('x-shadow-login-id') if route in LOGIN_PROOF | {'logout_execute'} else None
    if selected is not None and not uuid(selected):
        raise InvalidRequest()
    if route == 'context':
        return None, None
    if route in LOGIN_PROOF:
        prefix, scope = 'staff-login', selected
    elif route in {'logout_execute', 'logout_read'}:
        prefix = 'stafflogoutctx'
        scope = body.get('logoutContextId') if route == 'logout_execute' else ids[0]
        if not uuid(scope):
            raise InvalidRequest()
    else:
        prefix, scope = 'pilotctx', ids[0]
    if scope is None:
        raise InvalidRequest(401)
    name = f'__Host-shadow-{prefix}-{scope}'
    matches = [value.strip() for item in headers.get('cookie', '').split(';')
               for key, sep, value in (item.strip().partition('='),) if key.strip() == name]
    if len(matches) > 1:
        raise InvalidRequest()
    if not matches or not canonical_secret(matches[0]):
        raise InvalidRequest(401)
    return selected, matches[0]


def stamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z', value):
        raise ValueError('invalid timestamp')
    return datetime.fromisoformat(value[:-1] + '+00:00')


def one(headers, name):
    values = [value for key, value in headers if key.lower() == name]
    if len(values) > 1:
        raise ValueError('duplicate private header')
    return values[0] if values else None


def validate_reply(route, ids, request, selected, status, raw, headers, cutoff):
    content_type = one(headers, 'content-type')
    if content_type != 'application/json' or one(headers, 'cache-control') != 'no-store':
        raise ValueError('invalid peer media or cache control')
    cookie = one(headers, 'set-cookie')
    login = one(headers, 'x-shadow-login-id')
    value = json_object(raw) if raw else None
    if status in ERROR_STATUS:
        if (cookie or login or not value or set(value) != NAV | {'reasonCode', 'reasonDetails'}
                or not re.fullmatch(r'[A-Z][A-Z_0-9]{1,63}', value['reasonCode'])
                or value['reasonDetails'] != {'code': value['reasonCode'], 'params': {}}
                or value['nextAction'] is not None or value['nextActionParams'] != {}):
            raise ValueError('unsafe peer error')
        return {}
    if status not in SUCCESS[route]:
        raise ValueError('unexpected peer status')
    if route == 'logout_execute':
        match = re.fullmatch(rf'__Host-shadow-staff-login-({UUID})=' + re.escape(COOKIE_TAIL + 'Max-Age=0'), cookie or '')
        if raw or login or not match or selected and match[1] != selected:
            raise ValueError('invalid logout cookie')
        return {'Set-Cookie': cookie}
    if not value or not NAV <= set(value) or value['nextAction'] is not None or value['nextActionParams'] != {}:
        raise ValueError('invalid peer response')
    fields = {
        'context': {'staffContext', 'observedAt'}, 'login': {'completion', 'observedAt'},
        'recover': {'loginId', 'observedAt'}, 'me': {'staff', 'authenticated', 'observedAt'},
        'list': {'sessions', 'observedAt'}, 'session': {'session', 'restrictedGroups'},
        'events': {'events', 'sessionId', 'observedAt'}, 'logout_read': {'operationRef', 'status', 'confirmedAt', 'observedAt'},
        'logout_prepare': {'logoutContext', 'observedAt'}, 'logout_continue': {'logoutContext', 'observedAt'},
        'outcome': {'operationRef', 'status', 'observedAt'} | ({'result'} if status == 200 else set()),
    }
    if set(value) != fields[route] | NAV:
        raise ValueError('unexpected peer fields')
    observed = stamp(value['observedAt']) if 'observedAt' in value else None
    if observed and observed > cutoff:
        raise ValueError('peer observation after cutoff')
    if route == 'session':
        if ((value['session'].get('sessionId') if value['session'].get('schemaVersion') == 'live-buy-session-v1' else value['session']['summary']['sessionId']) != ids[0]
                or value['restrictedGroups'] != ['user.minimal_context']):
            raise ValueError('wrong session projection')
    if route == 'events' and value['sessionId'] != ids[0]:
        raise ValueError('wrong session events')
    if route == 'outcome' and (value['operationRef'] != {'contextId': ids[0], 'operationId': ids[1]}
                               or value['status'] != ('resolved' if status == 200 else 'unresolved')):
        raise ValueError('wrong login operation')
    if route == 'logout_read':
        ref = value['operationRef']
        if (ref.get('logoutContextId') != ids[0] or ref.get('authOperationId') != ids[1]
                or ref.get('commandType') != 'C07' or not uuid(ref.get('loginId'))):
            raise ValueError('wrong logout operation')
    expected = None
    output = {}
    if route == 'context':
        ctx = value['staffContext']
        expected = ('pilotctx', ctx['contextId'], stamp(ctx['expiresAt']), timedelta(minutes=10))
    elif route in {'logout_prepare', 'logout_continue'}:
        ctx = value['logoutContext']
        created = stamp(ctx['createdAt'])
        expires = stamp(ctx['expiresAt'])
        if created > min(observed, datetime.now(timezone.utc)) or expires - created != timedelta(minutes=15):
            raise ValueError('invalid logout context lifetime')
        expected = ('stafflogoutctx', ctx['logoutContextId'], expires, timedelta(minutes=15))
        if not uuid(ctx.get('loginId')) or ctx.get('realm') != 'staff':
            raise ValueError('invalid logout context')
        if route == 'logout_continue':
            if ctx.get('sourceLogoutContextId') != request.get('sourceLogoutContextId'):
                raise ValueError('logout continuation source mismatch')
            if request.get('authorizationMode') not in {'original_login', 'current_staff'}:
                raise ValueError('invalid logout authorization mode')
        if (route == 'logout_prepare' or request.get('authorizationMode') == 'original_login') and ctx['loginId'] != selected:
            raise ValueError('logout context bound to different login')
    elif route in {'login', 'recover'}:
        completion = value['completion'] if route == 'login' else value
        if route == 'login' and (completion.get('contextId') != ids[0] or completion.get('realm') != 'staff'
                                 or completion.get('operationId') != request.get('operationId')):
            raise ValueError('wrong login completion')
        login_id = completion['loginId']
        if not uuid(login_id) or login != login_id:
            raise ValueError('login header mismatch')
        anchor = stamp(completion['completedAt']) if route == 'login' else observed
        if anchor > observed:
            raise ValueError('invalid login completion time')
        expected = ('staff-login', login_id, None, anchor + timedelta(hours=8) - observed)
        output['X-Shadow-Login-Id'] = login
    elif route == 'me':
        if login != selected or value['authenticated'] is not True or not uuid(value['staff'].get('staffId')):
            raise ValueError('wrong selected login')
        output['X-Shadow-Login-Id'] = login
    if login is not None and 'X-Shadow-Login-Id' not in output:
        raise ValueError('unexpected login header')
    if expected:
        prefix, scope, expires, max_age = expected
        if not uuid(scope):
            raise ValueError('bad cookie scope')
        match = re.fullmatch(re.escape(f'__Host-shadow-{prefix}-{scope}=')
                             + r'([A-Za-z0-9_-]{43})' + re.escape(COOKIE_TAIL + 'Expires=')
                             + r'([^;\r\n]+)', cookie or '')
        if not match or not canonical_secret(match[1]):
            raise ValueError('invalid cookie attributes')
        expiration = parsedate_to_datetime(match[2])
        # A logout context cannot grant access. Its fixed expiry may outlast
        # the window, but exchange still refuses all traffic at cutoff.
        upper = cutoff + max_age if prefix == 'stafflogoutctx' else cutoff
        if (expiration.tzinfo != timezone.utc or format_datetime(expiration, usegmt=True) != match[2]
                or not observed.replace(microsecond=0) < expiration <= min(upper, observed + max_age)
                or expires is not None and expiration != expires.replace(microsecond=0)):
            raise ValueError('cookie expiration mismatch')
        output['Set-Cookie'] = cookie
    elif cookie is not None:
        raise ValueError('unexpected cookie')
    return output


class PilotPrivateHttp:
    def __init__(self, host, port, read_key, connection_factory=http.client.HTTPConnection):
        self.host, self.port, self.read_key = host, port, read_key
        self.connection_factory = connection_factory

    def call(self, data, signature, deadline):
        connection = self.connection_factory(self.host, self.port, timeout=remaining(deadline))
        try:
            connection.connect()
            sock = connection.sock
            connection.response_class = lambda socket, **kw: http.client.HTTPResponse(
                ResponseSocket(socket, deadline), **kw)
            send = connection.send

            def bounded_send(value):
                sock.settimeout(remaining(deadline))
                send(value)
                remaining(deadline)

            connection.send = bounded_send
            connection.request('POST', PEER_PATH, body=data, headers={
                'Content-Type': 'application/json', 'Content-Length': str(len(data)),
                'X-Pilot-Signature': signature, 'Connection': 'close'})
            response = connection.getresponse()
            parts, size = [], 0
            while True:
                part = response.read1(min(8192, MAX_REPLY + 1 - size))
                remaining(deadline)
                if not part:
                    break
                parts.append(part)
                size += len(part)
                if size > MAX_REPLY:
                    raise GatewayUnavailable('pilot reply exceeds limit')
            return response.status, b''.join(parts), response.getheaders()
        except (OSError, http.client.HTTPException) as exc:
            raise GatewayUnavailable('pilot peer unavailable') from exc
        finally:
            connection.close()


class PilotEdge:
    def __init__(self, origin, pin, peers, read_network_key, enabled, cutoff, clock=time.monotonic_ns):
        parsed = urlsplit(origin)
        if (set(peers) != {'auth', 'reader'} or not re.fullmatch(r'[a-f0-9]{64}', pin)
                or parsed.scheme != 'https' or not parsed.hostname
                or origin != f'https://{parsed.netloc}' or parsed.username or parsed.password
                or cutoff.tzinfo != timezone.utc):
            raise ValueError('invalid pilot edge configuration')
        self.origin, self.pin, self.peers = origin, pin, dict(peers)
        self.read_network_key, self.enabled, self.cutoff, self.clock = read_network_key, enabled, cutoff, clock

    def exchange(self, method, target, headers, body, trusted_ip, deadline):
        route, ids = select(method, target)
        if not self.enabled() or datetime.now(timezone.utc) >= self.cutoff:
            raise GatewayUnavailable('pilot disabled')
        if len(body) > MAX_BODY:
            raise InvalidRequest(413)
        h = request_headers(headers, self.origin, method, len(body))
        if method == 'GET' and (h.get('origin', self.origin) != self.origin
                                or h.get('sec-fetch-site', 'none') not in ('none', 'same-origin')):
            raise InvalidRequest(403)
        if method == 'POST' and not headers.get_all('Content-Length', []):
            raise InvalidRequest()
        try:
            request = json_object(body) if method == 'POST' else {}
        except (ValueError, UnicodeError, RecursionError):
            raise InvalidRequest() from None
        selected, proof = credentials(h, route, ids, request)
        role = 'auth' if route in AUTH else 'reader'
        if not 0 < deadline - self.clock() <= 5_000_000_000:
            raise GatewayUnavailable('invalid original deadline')
        try:
            network = network_digest(trusted_ip, self.read_network_key()) if route == 'context' else None
            frame = dict(version='pilot-staff-peer-v1', role=role, deploymentDigest=self.pin,
                         method=method, target=target, deadlineNs=str(deadline),
                         bodyBase64=base64.b64encode(body).decode(), selectedLoginId=selected,
                         proof=proof, networkDigest=network)
            wire = json.dumps(frame, separators=(',', ':')).encode('ascii')
            if len(wire) > MAX_FRAME:
                raise InvalidRequest(413)
            peer = self.peers[role]
            signature = hmac.new(valid_key(peer.read_key()), b'shadow.pilot.ingress.v1\0' + wire,
                                 hashlib.sha256).hexdigest()
            remaining(deadline, self.clock)
            status, raw, private_headers = peer.call(wire, signature, deadline)
            remaining(deadline, self.clock)
            if not self.enabled() or datetime.now(timezone.utc) >= self.cutoff:
                raise GatewayUnavailable('pilot disabled')
            public_headers = validate_reply(route, ids, request, selected, status, raw, private_headers, self.cutoff)
            return status, raw, public_headers
        except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError, RecursionError):
            raise GatewayUnavailable('pilot exchange refused') from None


def pilot_handler(base, edge, trusted_client_ip):
    """Bind only behind an ingress that establishes the actual client IP."""
    class Handler(base):
        def _pilot(self):
            try:
                route, _ = select(self.command, self.path)
                declared = self.headers.get_all('Content-Length', [])
                if len(declared) > 1 or (declared and not re.fullmatch(r'0|[1-9][0-9]{0,4}', declared[0])):
                    raise InvalidRequest()
                size = int(declared[0]) if declared else 0
                if size > MAX_BODY:
                    raise InvalidRequest(413)
                request_headers(self.headers, edge.origin, self.command, size)
                deadline = self._paper_deadline_ns
                body = read_body(self.rfile, size, deadline, self.connection)
                addr = trusted_client_ip(self) if route == 'context' else None
                status, raw, headers = edge.exchange(self.command, self.path, self.headers, body, addr, deadline)
            except InvalidRequest as exc:
                code = {401: 'AUTH_REQUIRED', 403: 'ACCESS_DENIED', 404: 'RESOURCE_NOT_FOUND',
                        413: 'REQUEST_TOO_LARGE', 415: 'UNSUPPORTED_MEDIA_TYPE'}.get(exc.status, 'INVALID_REQUEST')
                return self.gateway_reply(exc.status, _error(code))
            except (ValueError, OSError, GatewayUnavailable):
                return self.gateway_reply(503, _error('SERVICE_UNAVAILABLE'))
            self._paper_reply_active = True
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if status != 204:
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            if raw:
                self.wfile.write(raw)

        def dispatch(self):
            # The outer mTLS handler calls super().dispatch() after checking
            # the pinned edge certificate. Do not bypass it via do_GET/do_POST.
            if self.path.startswith('/api/admin/'):
                return self._pilot()
            cookies = self.headers.get_all('Cookie', [])
            if len(cookies) == 1:
                keep = [entry.strip() for entry in cookies[0].split(';')
                        if not entry.strip().startswith(('__Host-shadow-pilotctx-', '__Host-shadow-staff'))]
                del self.headers['Cookie']
                if any(keep):
                    self.headers['Cookie'] = '; '.join(keep)
            return super().dispatch()

        do_GET = dispatch
        do_POST = dispatch
        do_PATCH = dispatch

    return Handler


def _error(code):
    return {'reasonCode': code, 'reasonDetails': {'code': code, 'params': {}},
            'nextAction': None, 'nextActionParams': {}}
