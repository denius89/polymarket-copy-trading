"""Explicit operator entry; does not apply migrations, seed or enable database gates."""
import ipaddress
import os
import re
import ssl
from http.server import ThreadingHTTPServer

import polygon_serve as baseline
from gateway_core import PaperUpstream
from gateway_handler import GatewayServerMixin, paper_gateway_handler


def serve():
    if os.environ.get('V00_POLYGON_PAPER_ENABLED') != '1':
        # Disabled means the existing service, without reading paper configuration.
        return baseline.serve()
    config = baseline.private_json(os.environ['POLYGON_API_GATEWAY_CONFIG'])
    expected = {'format', 'upstreamHost', 'upstreamPort', 'ingressKeyFile'}
    if type(config) is not dict or set(config) != expected or config['format'] != 'polygon-gateway-v1':
        raise SystemExit('invalid gateway configuration')
    address = ipaddress.ip_address(config['upstreamHost'])
    if (not (address.is_private or address.is_loopback) or address.is_unspecified
            or address.is_multicast or type(config['upstreamPort']) is not int
            or not 1024 <= config['upstreamPort'] <= 65535):
        raise SystemExit('private paper upstream required')
    if os.path.realpath(config['ingressKeyFile']) == os.path.realpath(os.environ['V00_KEY_FILE']):
        raise SystemExit('independent paper ingress key required')

    def read_key():
        value = baseline.private_json(config['ingressKeyFile'])
        if (type(value) is not dict or set(value) != {'format', 'hex'}
                or value['format'] != 'polygon-ingress-hmac-v1'
                or type(value['hex']) is not str or not re.fullmatch('[0-9a-f]{64}', value['hex'])):
            raise ValueError('invalid ingress key')
        return bytes.fromhex(value['hex'])

    read_key()
    app, origin = baseline.make_app(), os.environ['V00_ORIGIN']
    upstream = PaperUpstream(str(address), config['upstreamPort'], origin, read_key)
    Handler = paper_gateway_handler(baseline.polygon_handler(app, origin), app, upstream)

    class Server(GatewayServerMixin, ThreadingHTTPServer):
        daemon_threads = True
        def handle_error(self, *_):
            print('{"event":"polygon_transport_error"}', flush=True)

    server = Server((os.environ.get('V00_BIND_HOST', '127.0.0.1'),
                     int(os.environ.get('PORT', '8443'))), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(os.environ['V00_TLS_CERT_FILE'], os.environ['V00_TLS_KEY_FILE'])
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    print('{"service":"shadow-polygon","scope":"synthetic-paper-gateway"}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    serve()
