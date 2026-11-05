"""Opt-in adapter around the existing polygon handler; no installation on import."""
import io
import re
import time
from urllib.parse import urlsplit

from gateway_core import (GatewayUnavailable, InvalidRequest, bounded_runtime,
                          q01_budget, read_body, remaining, request_headers, route_allowed)


def gateway_error(reason, *, auth=False, retry=False):
    detail = {'code': reason, 'params': {}}
    return {'reasonCode': reason, 'reasonDetails': detail if auth else [detail],
            'nextAction': 'retry_later' if retry and not auth else None, 'nextActionParams': {}}


class HeaderDeadlineReader(io.RawIOBase):
    """Absolute header-read bound, including slow trickles that reset idle timeouts."""
    def __init__(self, raw, handler):
        self.raw, self.handler = raw, handler

    def readable(self):
        return True

    def readinto(self, buffer):
        if self.handler._reading_headers:
            try:
                self.handler.connection.settimeout(remaining(self.handler._paper_deadline_ns))
            except GatewayUnavailable:
                raise TimeoutError('request headers exceeded original budget') from None
        count = self.raw.readinto(buffer)
        if self.handler._reading_headers:
            try:
                remaining(self.handler._paper_deadline_ns)
            except GatewayUnavailable:
                raise TimeoutError('request headers exceeded original budget') from None
        return count

    def close(self):
        try:
            self.raw.close()
        finally:
            super().close()


class GatewayServerMixin:
    def process_request(self, request, client_address):
        # Before ThreadingMixIn schedules a handler thread. First request includes
        # time spent waiting for that thread; subsequent keep-alive requests get
        # their own clock before parsing, not a budget inherited from request 1.
        request._shadow_gateway_accepted_ns = time.monotonic_ns()
        return super().process_request(request, client_address)


def paper_gateway_handler(base, app, upstream):
    """Call only when the reviewed profile explicitly enables paper.

    `base` is polygon_handler(app, origin) including the existing SPA overlay.
    The caller retains the disabled path verbatim; no optional connection means
    no gate auto-enablement. app.bridge.transaction must be the genuine factory.
    """
    app.bridge.transaction = bounded_runtime(app.bridge.transaction)

    class Handler(base):
        def setup(self):
            super().setup()
            self._reading_headers = False
            raw = self.rfile.detach()
            self.rfile = io.BufferedReader(HeaderDeadlineReader(raw, self))

        def parse_request(self):
            try:
                return super().parse_request()
            finally:
                self._reading_headers = False
                # Existing Auth uses its original processing/read rules after headers.
                self.connection.settimeout(5)

        def handle_one_request(self):
            self._paper_deadline_ns = getattr(self.connection, '_shadow_gateway_accepted_ns', None)
            if self._paper_deadline_ns is None:
                self._paper_deadline_ns = time.monotonic_ns()
            else:
                self.connection._shadow_gateway_accepted_ns = None
            self._paper_deadline_ns += 5_000_000_000
            self._reading_headers = True
            try:
                return super().handle_one_request()
            finally:
                self._reading_headers = False

        def reply(self, status, body, headers=(), fault=None):
            # The original app has already authenticated and committed real Q01.
            if (self.command == 'GET' and urlsplit(self.path).path == '/api/me'
                    and status == 200):
                try:
                    if (type(body) is not dict or body.get('authenticated') is not True
                            or type(body.get('user')) is not dict):
                        raise GatewayUnavailable('invalid Q01 projection')
                    product_id = upstream.map_identity(self.headers, self._paper_deadline_ns)
                    remaining(self._paper_deadline_ns)
                    body = body | {'user': body['user'] | {'userId': product_id}}
                except (GatewayUnavailable, InvalidRequest):
                    status, body, headers, fault = 503, gateway_error('SERVICE_UNAVAILABLE', auth=True), (), None
            return super().reply(status, body, headers, fault)

        def dispatch(self):
            try:
                target = urlsplit(self.path)
                if target.path.startswith('/__polygon__/'):
                    self.close_connection = True
                    return super().reply(404, gateway_error('RESOURCE_NOT_FOUND', auth=True))
                if self.command == 'GET' and target.path == '/api/me':
                    with q01_budget(self._paper_deadline_ns):
                        return super().dispatch()
                if not route_allowed(self.command, self.path):
                    # Includes unchanged Auth/static and their existing validation.
                    return super().dispatch()
                lengths = self.headers.get_all('Content-Length', [])
                if len(lengths) > 1 or any(not re.fullmatch(r'[0-9]+', x) for x in lengths):
                    raise InvalidRequest()
                length = int(lengths[0]) if lengths else 0
                request_headers(self.headers, upstream.origin, self.command, length)
                body = read_body(self.rfile, length, self._paper_deadline_ns, self.connection)
                status, raw, diagnostics = upstream.exchange(self.command, self.path, body, self.headers,
                                                self._paper_deadline_ns)
                remaining(self._paper_deadline_ns)
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                for name, value in diagnostics.items():
                    self.send_header(name, value)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except (ValueError, UnicodeError):
                self.close_connection = True
                return super().reply(400, gateway_error('INVALID_REQUEST'))
            except InvalidRequest as exc:
                self.close_connection = True
                reason = {403: 'ACCESS_DENIED', 413: 'REQUEST_TOO_LARGE',
                          415: 'UNSUPPORTED_MEDIA_TYPE'}.get(exc.status, 'INVALID_REQUEST')
                return super().reply(exc.status, gateway_error(reason))
            except (GatewayUnavailable, OSError):
                self.close_connection = True
                return super().reply(503, gateway_error('SERVICE_UNAVAILABLE', auth=urlsplit(self.path).path == '/api/me', retry=True))

        do_GET = dispatch
        do_POST = dispatch
        do_PATCH = dispatch

    return Handler
