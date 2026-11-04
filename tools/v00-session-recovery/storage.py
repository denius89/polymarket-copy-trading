"""One psql process/transaction across crypto, with explicit COMMIT confirmation."""
import base64
import json
import os
import selectors
import subprocess
import time

from crypto import Unavailable

METHODS = frozenset(("lookup_result", "plan_completion", "complete", "recover", "q01",
                     "logout_prepare", "logout_continue", "logout", "logout_result"))


class Transaction:
    def __init__(self, command=None, budget=4.5):
        self.deadline = time.monotonic() + budget
        self.finished = False
        self.buffer = b""
        argv = command or json.loads(os.environ.get("V00_PSQL_COMMAND_JSON", '["psql"]'))
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise Unavailable("invalid psql argv")
        self.process = subprocess.Popen(argv + ["-XAt", "-v", "ON_ERROR_STOP=1"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=os.environ | {"PGOPTIONS": "-c statement_timeout=4000 -c lock_timeout=3000 -c idle_in_transaction_session_timeout=5000"})
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)

    def line(self):
        while b"\n" not in self.buffer:
            left = self.deadline - time.monotonic()
            if left <= 0 or not self.selector.select(left):
                raise Unavailable("transaction timeout")
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise Unavailable("transaction outcome unavailable")
            self.buffer += chunk
            if len(self.buffer) > 131072:
                raise Unavailable("unexpected transaction output")
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line.decode("utf-8")

    def send(self, sql):
        if time.monotonic() >= self.deadline:
            raise Unavailable("transaction budget exceeded")
        try:
            self.process.stdin.write(sql.encode("ascii") + b"\n")
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise Unavailable("transaction write failed") from exc

    def __enter__(self):
        try:
            self.send("BEGIN;")
            if self.line() != "BEGIN":
                raise Unavailable("transaction not begun")
            return self
        except BaseException:
            self.close()
            raise

    def call(self, method, fields):
        if method not in METHODS:
            raise Unavailable("unknown private method")
        encoded = base64.b64encode(json.dumps(fields, separators=(",", ":")).encode()).decode()
        self.send("SELECT v00_session." + method + "(convert_from(decode('" + encoded + "','base64'),'UTF8')::jsonb)::text;")
        try:
            result = json.loads(self.line())
            if not isinstance(result, dict) or type(result.get("http")) is not int:
                raise ValueError("invalid DB response")
            return result
        except (ValueError, TypeError) as exc:
            raise Unavailable("invalid private response") from exc

    def commit(self):
        self.send("COMMIT;")
        # psql may return ROLLBACK when COMMIT follows an aborted transaction.
        if self.line() != "COMMIT":
            raise Unavailable("commit not confirmed")
        self.finished = True

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=2)
        self.selector.close()
        self.process.stdin.close()
        self.process.stdout.close()

    def __exit__(self, *_):
        # Closing an uncommitted connection rolls back. Never auto-retry COMMIT.
        self.close()
