"""Operator-only psql17 pipe fault, scoped to one fixture context and method.

Relays the existing three-line bound-call protocol. Only after observing a real
COMMIT tag does it atomically create a private one-shot marker and suppress that
tag. It never fabricates DB output, retries SQL, or logs bound input/results.
"""
import argparse
import base64
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import sys
import uuid


SELECT = re.compile(rb"SELECT v00_upstream\.([a-z_]+)\(convert_from\(decode\(\$1,'base64'\),'UTF8'\)::jsonb\)::text\n")
BIND = re.compile(rb"\\bind '([A-Za-z0-9+/=]+)'\n")


def canonical(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError("invalid source identifier")
    return value


def mark_once(path, method, source):
    value = {"schema": "v00-upstream-commit-gap-v1", "method": method,
             "source": source, "real_commit_tag_seen": True,
             "observed_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")}
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as output:
        output.write(json.dumps(value) + "\n")
        output.flush()
        os.fsync(output.fileno())
    return True


def relay(method, context_id, marker, flags, source_input=None, sink=None):
    if os.environ.get("V00_COMMIT_GAP_ENABLED") != "1":
        raise ValueError("operator fault disabled")
    if method not in {"seal_email", "complete"}:
        raise ValueError("unsupported fault boundary")
    canonical(context_id)
    argv = json.loads(os.environ["V00_REAL_PSQL_COMMAND_JSON"])
    if type(argv) is not list or not argv or not all(type(v) is str for v in argv):
        raise ValueError("invalid private psql command")
    incoming, outgoing = source_input or sys.stdin.buffer, sink or sys.stdout.buffer
    child = subprocess.Popen(argv + flags, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL)
    selected = None
    try:
        while True:
            line = incoming.readline(131073)
            if not line:
                return 0
            if len(line) > 131072:
                raise ValueError("oversized command")
            match = SELECT.fullmatch(line)
            fields = None
            if match:
                bound, execute = incoming.readline(131073), incoming.readline(16)
                binding = BIND.fullmatch(bound)
                if not binding or len(bound) > 131072 or execute != b"\\g\n":
                    raise ValueError("unexpected bound call")
                fields = json.loads(base64.b64decode(binding[1], validate=True))
                if type(fields) is not dict:
                    raise ValueError("unexpected call shape")
                child.stdin.write(line + bound + execute)
            elif line not in {b"BEGIN;\n", b"COMMIT;\n", b"ROLLBACK;\n"}:
                raise ValueError("unsupported command protocol")
            else:
                child.stdin.write(line)
            child.stdin.flush()
            result = child.stdout.readline(131073)
            if not result or len(result) > 131072:
                return 2
            if match and match[1].decode() == method and fields.get("context_id") == context_id:
                value = json.loads(result)
                # A final replay must not re-arm a lost seal acknowledgement.
                actual = (value.get("dispatch_allowed") is True if method == "seal_email"
                          else value.get("http") == 200 and value.get("result", {}).get("kind") == "login_completed")
                if actual:
                    selected = {"context_id": context_id, "operation_id": canonical(fields["operation_id"]),
                                "action": fields["action"]}
                    if selected["action"] not in {"C02", "AUTH_TOTP_VERIFY"}:
                        raise ValueError("unsupported source action")
            if line == b"COMMIT;\n" and result == b"COMMIT\n" and selected:
                if mark_once(marker, method, selected):
                    return 97
            outgoing.write(result)
            outgoing.flush()
            if line in {b"COMMIT;\n", b"ROLLBACK;\n"}:
                selected = None
    finally:
        child.stdin.close()
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=2)
        child.stdout.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("seal_email", "complete"), required=True)
    parser.add_argument("--context-id", required=True)
    parser.add_argument("--marker", required=True, help="new marker in an operator-owned private directory")
    parser.add_argument("psql_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    flags = args.psql_args[1:] if args.psql_args[:1] == ["--"] else args.psql_args
    try:
        code = relay(args.method, args.context_id, args.marker, flags)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        code = 2
    raise SystemExit(code)
