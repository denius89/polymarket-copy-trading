"""Relay the isolated guest gateway to the local built-in browser."""
import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import subprocess

HOST = "127.0.0.1:52486"
HEADERS = ("Cookie", "Content-Type", "Origin", "Sec-Fetch-Site",
           "X-Shadow-Auth-Request", "X-Shadow-Login-Id", "Accept")


def serve(command):
    class Handler(BaseHTTPRequestHandler):
        def relay(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if not 0 <= size <= 65536 or self.headers.get("Host") != HOST:
                self.send_error(400)
                return
            if self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            request = {
                "method": self.command,
                "path": self.path,
                "body": base64.b64encode(self.rfile.read(size)).decode(),
                "headers": {key: self.headers[key] for key in HEADERS if key in self.headers},
                "loopbackOrigin": f"http://{HOST}",
            }
            try:
                peer = subprocess.run(command, input=json.dumps(request), text=True,
                                      capture_output=True, timeout=18, check=True)
                response = json.loads(peer.stdout)
                body = base64.b64decode(response["body"], validate=True)
            except (OSError, ValueError, subprocess.SubprocessError):
                self.send_error(502, "Isolated gateway unavailable")
                return
            self.send_response(response["status"])
            for key, value in response["headers"]:
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

        do_GET = do_POST = relay

    with ThreadingHTTPServer(("127.0.0.1", 52486), Handler) as server:
        print(f"Staff Q06 browser relay ready at http://{HOST}/admin/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transport", nargs="+", help="Command that invokes relay-guest.py in the disposable guest")
    args = parser.parse_args()
    serve(args.transport)
