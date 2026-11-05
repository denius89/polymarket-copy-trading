import email.message
import hashlib
import hmac
import io
import struct
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import gateway_core as g

ORIGIN = 'https://localhost:18444'


def headers(*pairs):
    result = email.message.Message()
    result['Host'] = 'localhost:18444'
    for k, v in pairs:
        result[k] = v
    return result


class GatewayTests(unittest.TestCase):
    def test_hmac_wire_matches_independent_framing(self):
        key = bytes(range(32)); target = '/api/traders?requestSchemaVersion=v1&cursor=a%2Bb'
        result = g.signed_headers(key, 'GET', target, b'', 123456789)
        fields = ['GET', target, hashlib.sha256(b'').hexdigest(), '123456789']
        wire = b'shadow.polygon.ingress.v1\0' + b''.join(struct.pack('>I', len(v.encode())) + v.encode() for v in fields)
        import base64
        expected = base64.urlsafe_b64encode(hmac.digest(key, wire, 'sha256')).decode().rstrip('=')
        self.assertEqual(result[g.INTERNAL[2]], expected)
        self.assertNotEqual(result, g.signed_headers(key, 'GET', target.replace('%2B', '+'), b'', 123456789))

    def test_allowlist_includes_patch_excludes_internal_absolute_and_unknown(self):
        uid = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
        self.assertTrue(g.route_allowed('PATCH', '/api/demo/drafts/' + uid))
        for method, target in [('POST', '/api/sessions/current'), ('GET', '/__polygon__/identity'),
                               ('GET', '//localhost/api/traders'), ('GET', 'https://localhost/api/traders'),
                               ('GET', '/api/traders#fragment'), ('DELETE', '/api/traders')]:
            self.assertFalse(g.route_allowed(method, target), (method, target))

    def test_caller_internal_headers_never_forward(self):
        supplied = headers(('X-Shadow-Internal-Proof', 'forged'), ('X-Forwarded-Host', 'evil'),
                           ('X-Shadow-Actor-Id', 'forged'), ('Cookie', 'legitimate=value'))
        result = g.request_headers(supplied, ORIGIN, 'GET', 0)
        self.assertEqual(result['cookie'], 'legitimate=value')
        self.assertFalse(set(g.INTERNAL) & set(result))
        self.assertNotIn('x-forwarded-host', result)
        self.assertNotIn('x-shadow-actor-id', result)

    def test_ambiguous_framing_and_credentials_rejected(self):
        cases = [headers(('Host', 'localhost:18444')), headers(('Content-Length', '0'), ('Content-Length', '0')),
                 headers(('Transfer-Encoding', 'chunked')), headers(('Cookie', 'a'), ('Cookie', 'b')),
                 headers(('X-Shadow-Login-Id', 'a'), ('X-Shadow-Login-Id', 'b'))]
        for value in cases:
            with self.assertRaises(g.InvalidRequest):
                g.request_headers(value, ORIGIN, 'GET', 0)

    def test_post_origin_marker_and_media_checked_before_forward(self):
        valid = [('Content-Length', '2'), ('Origin', ORIGIN), ('Content-Type', 'application/json'), ('X-Shadow-Auth-Request', '1')]
        self.assertEqual(g.request_headers(headers(*valid), ORIGIN, 'POST', 2)['Content-Length'], '2')
        for pair in [('Origin', 'https://evil.example'), ('X-Shadow-Auth-Request', '0'), ('Content-Type', 'text/plain')]:
            changed = [p for p in valid if p[0] != pair[0]] + [pair]
            with self.assertRaises(g.InvalidRequest):
                g.request_headers(headers(*changed), ORIGIN, 'POST', 2)

    def test_slow_body_exhaustion_does_not_renew_budget(self):
        ticks = iter([100, 400, 500, 1100])
        stream = SimpleNamespace(read1=lambda n: b'x')
        timeouts = []
        connection = SimpleNamespace(settimeout=timeouts.append)
        with self.assertRaises(g.GatewayUnavailable):
            g.read_body(stream, 2, 1000, connection, lambda: next(ticks))
        self.assertEqual(timeouts, [900 / g.NS, 500 / g.NS])

    def test_empty_body_and_queued_expired_request_refused(self):
        with self.assertRaises(g.GatewayUnavailable):
            g.read_body(io.BytesIO(b''), 0, 100, SimpleNamespace(), lambda: 100)
        opened = []
        upstream = g.PaperUpstream('private-node', 19090, ORIGIN, lambda: bytes(32),
                                   lambda *a, **k: opened.append((a, k)))
        with self.assertRaises(g.GatewayUnavailable):
            upstream.exchange('GET', '/api/traders?requestSchemaVersion=v1', b'', headers(), 1)
        self.assertEqual(opened, [])

    def test_q01_cap_is_request_local_and_factory_time_is_charged(self):
        def make():
            return SimpleNamespace(deadline=time.monotonic() + 4.5)
        factory = g.bounded_runtime(make)
        limit = time.monotonic_ns() + g.NS
        baseline = factory().deadline
        with g.q01_budget(limit):
            self.assertLessEqual(factory().deadline, limit / g.NS)
        self.assertGreater(factory().deadline, limit / g.NS)
        self.assertGreater(baseline, limit / g.NS)

    def test_identity_failure_has_no_actor_fallback(self):
        upstream = g.PaperUpstream('private-node', 19090, ORIGIN, lambda: bytes(32))
        for reply in [(503, b'{}'), (200, b'{"actor_id":"legacy"}'), (200, b'{"userId":null}'), (200, b'{"userId":"aaaaaaaa-aaaa-1aaa-8aaa-aaaaaaaaaaaa"}'), (200, b'{"userId":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","userId":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"}')]:
            with patch.object(upstream, 'exchange', return_value=(*reply, {})):
                with self.assertRaises(g.GatewayUnavailable):
                    upstream.map_identity(headers(), time.monotonic_ns() + g.NS)

class HandlerTests(unittest.TestCase):
    def make_handler(self, upstream):
        from gateway_handler import paper_gateway_handler
        class Base:
            def reply(self, status, body, headers=(), fault=None):
                self.observed = status, body, headers, fault
            def dispatch(self):
                self.called_base = True
                self.reply(200, {'authenticated': True, 'user': {'userId': 'legacy-actor', 'locale': 'en'}},
                           [('X-Shadow-Login-Id', 'selected')])
        app = SimpleNamespace(bridge=SimpleNamespace(transaction=lambda: SimpleNamespace(deadline=time.monotonic() + 4.5)))
        Handler = paper_gateway_handler(Base, app, upstream)
        handler = Handler()
        handler.command = 'GET';handler.path = '/api/me?requestSchemaVersion=v1'
        handler._paper_deadline_ns = time.monotonic_ns() + g.NS
        handler.headers = headers()
        return handler

    def test_mapping_replaces_only_product_id_and_preserves_login_header(self):
        upstream = SimpleNamespace(map_identity=lambda h, d: 'product-user')
        handler = self.make_handler(upstream);handler.dispatch()
        self.assertEqual(handler.observed[1]['user'], {'userId': 'product-user', 'locale': 'en'})
        self.assertEqual(handler.observed[2], [('X-Shadow-Login-Id', 'selected')])

    def test_mapping_failure_never_emits_legacy_actor_or_success(self):
        def fail(h, d):raise g.GatewayUnavailable()
        handler = self.make_handler(SimpleNamespace(map_identity=fail));handler.dispatch()
        self.assertEqual(handler.observed[0], 503)
        self.assertNotIn('user', handler.observed[1])
        self.assertEqual(handler.observed[2], ())

    def test_public_internal_bridge_never_reaches_base_or_upstream(self):
        handler = self.make_handler(SimpleNamespace())
        handler.path = '/__polygon__/identity?requestSchemaVersion=v1';handler.dispatch()
        self.assertEqual(handler.observed[0], 404)
        self.assertFalse(hasattr(handler, 'called_base'))

    def test_expired_q01_never_calls_real_auth_or_mapping(self):
        handler = self.make_handler(SimpleNamespace());handler._paper_deadline_ns = 1
        handler.dispatch()
        self.assertFalse(hasattr(handler, 'observed'))
        self.assertTrue(handler.close_connection)
        self.assertFalse(hasattr(handler, 'called_base'))


class AdditionalBoundaryTests(unittest.TestCase):
    def test_parallel_q01_contexts_do_not_share_deadlines(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barrier = Barrier(2)
        factory = g.bounded_runtime(lambda: SimpleNamespace(deadline=time.monotonic() + 4.5))
        def worker(seconds):
            limit = time.monotonic_ns() + int(seconds * g.NS)
            with g.q01_budget(limit):
                barrier.wait(timeout=2)
                actual = factory().deadline
                self.assertLessEqual(actual, limit / g.NS)
                self.assertAlmostEqual(actual, limit / g.NS, places=6)
                return actual
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(worker, 0.5), pool.submit(worker, 2)
            self.assertGreater(b.result() - a.result(), 1)
        self.assertIsNone(g._q01_deadline.get())

    def test_invalid_key_is_technical_refusal_before_connection(self):
        def broken():raise ValueError('bad key file')
        upstream = g.PaperUpstream('private-node', 19090, ORIGIN, broken,
                                   lambda *a, **k: self.fail('connection must not open'))
        with self.assertRaises(g.GatewayUnavailable):
            upstream.exchange('GET', '/api/traders', b'', headers(), time.monotonic_ns() + g.NS)

    def test_slow_header_absolute_deadline_prevents_next_read(self):
        from gateway_handler import HeaderDeadlineReader
        state = SimpleNamespace(_reading_headers=True, _paper_deadline_ns=1,
                                connection=SimpleNamespace(settimeout=lambda x: None))
        class Raw(io.RawIOBase):
            def readinto(self, b):raise AssertionError('expired header may not continue reading')
        reader = HeaderDeadlineReader(Raw(), state)
        with self.assertRaises(TimeoutError):reader.readinto(bytearray(8))
        reader.close()


class SocketHandlerTests(unittest.TestCase):
    """Actual HTTP parsing over socketpair; legacy app/upstream are explicit stubs."""
    def run_request(self, wire, *, accepted_age=0, await_limit=1, response_bytes=0, upstream_delay=0):
        import socket
        import threading
        from http.server import BaseHTTPRequestHandler
        from gateway_handler import paper_gateway_handler
        calls = []
        class Legacy(BaseHTTPRequestHandler):
            def log_message(self, *_):pass
            def reply(self, status, body, headers=(), fault=None):
                raw = __import__('json').dumps(body).encode()
                self.send_response(status)
                for k, v in headers:self.send_header(k, v)
                self.send_header('Content-Length', str(len(raw)));self.end_headers();self.wfile.write(raw)
            def dispatch(self):
                calls.append('auth')
                self.reply(200, {'authenticated': True, 'user': {'userId': 'legacy'}}, [('X-Shadow-Login-Id', 'selected')])
        product = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
        class Upstream:
            origin = ORIGIN
            def map_identity(self, headers, deadline):
                calls.append('mapping');g.remaining(deadline);return product
            def exchange(self, method, target, body, headers, deadline):
                calls.append((method, target, body));time.sleep(upstream_delay);g.remaining(deadline)
                return 200, (b'x' * response_bytes if response_bytes else b'{"saved":true}'), {'x-request-id': product}
        class MarkedSocket(socket.socket):pass
        a, client = socket.socketpair()
        server = MarkedSocket(fileno=a.detach())
        if response_bytes:server.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
        server._shadow_gateway_accepted_ns = time.monotonic_ns() - int(accepted_age * g.NS)
        app = SimpleNamespace(bridge=SimpleNamespace(transaction=lambda: None))
        Handler = paper_gateway_handler(Legacy, app, Upstream())
        failures = []
        def work():
            try:Handler(server, ('local', 0), SimpleNamespace())
            except BaseException as exc:failures.append(exc)
            finally:server.close()
        thread = threading.Thread(target=work, daemon=True)
        client.sendall(wire);thread.start()
        thread.join(await_limit)
        finished = not thread.is_alive()
        client.settimeout(.5)
        output = b''
        if finished:
            while True:
                chunk = client.recv(8192)
                if not chunk:break
                output += chunk
        client.close();thread.join(.5)
        self.assertEqual(failures, [])
        return finished, output, calls

    def test_actual_q01_mapping_occurs_after_auth(self):
        done, raw, calls = self.run_request(b'GET /api/me?requestSchemaVersion=v1 HTTP/1.1\r\nHost: localhost:18444\r\n\r\n')
        self.assertTrue(done);self.assertIn(b'200 OK', raw)
        self.assertEqual(calls, ['auth', 'mapping']);self.assertNotIn(b'legacy', raw)

    def test_actual_private_bridge_404_has_no_auth_or_mapping(self):
        done, raw, calls = self.run_request(b'GET /__polygon__/identity HTTP/1.1\r\nHost: localhost:18444\r\n\r\n')
        self.assertTrue(done);self.assertIn(b'404', raw);self.assertEqual(calls, [])

    def test_actual_patch_preserves_body_and_diagnostic_id(self):
        wire = (b'PATCH /api/demo/drafts/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa HTTP/1.1\r\n'
                b'Host: localhost:18444\r\nOrigin: https://localhost:18444\r\nContent-Type: application/json\r\n'
                b'X-Shadow-Auth-Request: 1\r\nContent-Length: 2\r\n\r\n{}')
        done, raw, calls = self.run_request(wire)
        self.assertTrue(done);self.assertIn(b'x-request-id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', raw)
        self.assertEqual(calls[0][0], 'PATCH');self.assertEqual(calls[0][2], b'{}')

    def test_actual_headers_use_remaining_wallclock(self):
        done, raw, calls = self.run_request(b'GET /api/traders HTTP/1.1\r\nHost: local', accepted_age=4.8, await_limit=.7)
        self.assertTrue(done, 'header read renewed an idle budget');self.assertEqual(calls, [])

    def test_actual_body_uses_remaining_wallclock(self):
        wire = (b'POST /api/demo/drafts HTTP/1.1\r\nHost: localhost:18444\r\nOrigin: https://localhost:18444\r\n'
                b'Content-Type: application/json\r\nX-Shadow-Auth-Request: 1\r\nContent-Length: 2\r\n\r\n{')
        done, raw, calls = self.run_request(wire, accepted_age=4.8, await_limit=.7)
        self.assertTrue(done, 'body read renewed an idle budget');self.assertNotIn(b'200 OK', raw);self.assertEqual(calls, [])

    def test_actual_expired_dispatch_never_authenticates(self):
        done, raw, calls = self.run_request(b'GET /api/me HTTP/1.1\r\nHost: localhost:18444\r\n\r\n', accepted_age=6)
        self.assertTrue(done);self.assertEqual(calls, [])


    def test_actual_downstream_backpressure_keeps_deadline_and_one_response(self):
        wire = b'GET /api/traders?requestSchemaVersion=v1 HTTP/1.1\r\nHost: localhost:18444\r\n\r\n'
        done, raw, calls = self.run_request(wire, accepted_age=4.6, await_limit=.8,
                                            response_bytes=65536, upstream_delay=.15)
        self.assertTrue(done, 'downstream body renewed its socket budget')
        self.assertEqual(raw.count(b'HTTP/1.0'), 1)
        self.assertNotIn(b'503 Service', raw)
        self.assertLess(len(raw), 65536)


class UpstreamResponseTests(unittest.TestCase):
    def exchange(self, diagnostics):
        class Response:
            status = 200
            def __init__(self):self.stream = io.BytesIO(b'{}')
            def read1(self, n):return self.stream.read(n)
            def getheaders(self):return [('Content-Type', 'application/json; charset=utf-8'), *diagnostics]
        class Connection:
            def __init__(self, *a, **k):self.sock = SimpleNamespace(settimeout=lambda t: None)
            def connect(self):pass
            def send(self, data):pass
            def request(self, *a, **k):pass
            def getresponse(self):return Response()
            def close(self):pass
        upstream = g.PaperUpstream('private-node', 19090, ORIGIN, lambda: bytes(32), Connection)
        return upstream.exchange('GET', '/api/traders', b'', headers(), time.monotonic_ns() + g.NS)

    def test_diagnostic_whitelist_preserves_only_valid_ids(self):
        uid = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
        status, raw, diagnostics = self.exchange([('X-Request-Id', uid), ('X-Correlation-Id', uid),
                                                  ('Set-Cookie', 'must-never-forward'), ('Connection', 'close')])
        self.assertEqual(diagnostics, {'x-request-id': uid, 'x-correlation-id': uid})

    def test_ambiguous_or_missing_diagnostics_refuse_response(self):
        uid = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
        for values in [[], [('X-Request-Id', 'invalid')], [('X-Request-Id', uid), ('x-request-id', uid)],
                       [('X-Request-Id', uid), ('X-Correlation-Id', 'invalid')]]:
            with self.assertRaises(g.GatewayUnavailable):self.exchange(values)


class ActualUpstreamDeadlineTests(unittest.TestCase):
    def test_slow_upstream_headers_cannot_reset_idle_timeout(self):
        import socket
        import threading
        client, server = socket.socketpair()
        def peer():
            try:
                server.settimeout(1)
                request = b''
                while b'\r\n\r\n' not in request:request += server.recv(4096)
                server.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nX-Slow: ')
                for _ in range(20):
                    time.sleep(.03);server.sendall(b'a')
            except OSError:pass
            finally:server.close()
        thread = threading.Thread(target=peer, daemon=True);thread.start()
        class Connection(__import__('http.client', fromlist=['HTTPConnection']).HTTPConnection):
            def connect(self):self.sock = client
        upstream = g.PaperUpstream('unused-private', 19090, ORIGIN, lambda: bytes(32), Connection)
        start = time.monotonic()
        try:
            with self.assertRaises(g.GatewayUnavailable):
                upstream.exchange('GET', '/api/traders', b'', headers(), time.monotonic_ns() + 200_000_000)
            self.assertLess(time.monotonic() - start, .5)
        finally:
            client.close();thread.join(1)


if __name__ == '__main__':
    unittest.main()
