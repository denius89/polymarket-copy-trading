"""Operator-only pipe fault: discard REAL psql COMMIT confirmation.

Transparent only for this adapter's one-command-per-line protocol. It never
fabricates SQL output, database results or COMMIT success. Do not use for normal
traffic. No payload/proof/ciphertext is written to the optional private marker.
"""
import argparse
import json
import os
import stat
import subprocess
import sys


def mark(path, action):
    if path is None:
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError("private marker required")
        file.write(json.dumps({"fault": "commit_ack_pipe_loss", "action": action, "real_commit_tag_seen": True}) + "\n")
        file.flush()
        os.fsync(file.fileno())


def relay(action, args, marker=None):
    argv = json.loads(os.environ.get("V00_REAL_PSQL_COMMAND_JSON", '["psql"]'))
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise ValueError("invalid operator psql argv")
    child = subprocess.Popen(argv + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL)
    seen = False
    try:
        for command in sys.stdin.buffer:
            if command.startswith(("SELECT v00_session." + action + "(").encode()):
                seen = True
            child.stdin.write(command)
            child.stdin.flush()
            line = child.stdout.readline()
            if not line:
                return 2
            if seen and command.strip() == b"COMMIT;" and line.strip() == b"COMMIT":
                mark(marker, action)
                # DB has positively confirmed commit to this fault boundary. The
                # adapter receives EOF instead and cannot claim it saw COMMIT.
                return 97
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
        return 0
    finally:
        child.stdin.close()
        if child.poll() is None:
            child.terminate()
        child.wait(timeout=2)
        child.stdout.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("complete", "recover", "q01", "logout"), required=True)
    parser.add_argument("--marker", help="optional operator-only0600 evidence path")
    parser.add_argument("psql_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    flags = args.psql_args[1:] if args.psql_args[:1] == ["--"] else args.psql_args
    try:
        code = relay(args.action, flags, args.marker)
    except (OSError, ValueError, subprocess.SubprocessError):
        code = 2
    raise SystemExit(code)
