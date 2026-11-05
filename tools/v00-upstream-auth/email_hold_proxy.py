"""One exact /otp request accepted then discarded; no forwarding capability."""
import argparse
from http.server import ThreadingHTTPServer
import json
import os
import sys

from email_input import canonical_email
from hold_proxy import State, handler


class EmailState(State):
    def __init__(self, email, observer_token, hold_seconds):
        if canonical_email(email) != email:
            raise ValueError("canonical synthetic address required")
        # Reuse the one-shot/no-forward observer. The placeholder is only needed
        # by its old /verify constructor; no OTP is ever used in this profile.
        super().__init__(email, "000000", observer_token, hold_seconds)
        self._expected = json.dumps({"email": email, "create_user": False}, separators=(",", ":")).encode()

    def snapshot(self):
        return super().snapshot() | {"schema": "v00-email-no-forward-proxy-v1"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9998)
    parser.add_argument("--hold-seconds", type=float, default=7)
    args = parser.parse_args()
    if os.environ.get("V00_EMAIL_NO_FORWARD_ENABLED") != "1":
        raise SystemExit("email no-forward proxy disabled")
    value = json.loads(sys.stdin.readline())
    if type(value) is not dict or set(value) != {"email", "observer_token"}:
        raise ValueError("invalid private setup")
    state = EmailState(value["email"], value["observer_token"], args.hold_seconds)
    del value

    class Server(ThreadingHTTPServer):
        def handle_error(self, *_):
            print('{"event":"email_proxy_transport_error"}', flush=True)

    server = Server((args.bind, args.port), handler(state, path="/otp"))
    print('{"event":"email_no_forward_ready"}', flush=True)
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"event": "email_proxy_stopped", "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
