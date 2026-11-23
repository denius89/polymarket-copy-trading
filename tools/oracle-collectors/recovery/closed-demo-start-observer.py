"""Register confirmed closed-demo sessions independently of browser state."""
from argparse import ArgumentParser
from pathlib import Path
from threading import Event
import ipaddress
import json
import os
import re
import signal

from psycopg import OperationalError, connect


def run(profile, stop, statement):
    address = ipaddress.IPv4Address(profile["serverAddress"])
    if not address.is_private or profile["database"] != "shadow_v00":
        raise ValueError("Expected a private closed PostgreSQL address")
    role = profile["role"]
    if not re.fullmatch(r"demo_start_observer_[a-f0-9]{8}", role):
        raise ValueError("Expected the closed start observer role")
    options = "-c statement_timeout=5000 -c lock_timeout=1000"
    failure = None
    delay = 1
    while not stop.is_set():
        try:
            with connect(service=profile["service"], connect_timeout=3, autocommit=True,
                         application_name="shadow-closed-start-observer", options=options) as database:
                identity = database.execute(
                    "SELECT current_database(),host(inet_server_addr()),session_user"
                ).fetchone()
                if identity != ("shadow_v00", str(address), role):
                    raise ValueError("Closed PostgreSQL identity mismatch")
                delay = 1
                failure = None
                previous = None
                while not stop.is_set():
                    [outcome] = database.execute(statement).fetchone()
                    if previous is None:
                        print(json.dumps({"status": "ready"}), flush=True)
                    if outcome["subscribed"] or outcome.get("writers") or (any(outcome.values()) and outcome != previous):
                        print(json.dumps(outcome), flush=True)
                    previous = outcome
                    stop.wait(2)
        except OperationalError as error:
            reason = error.sqlstate or "connection_unavailable"
            if reason != failure:
                print(json.dumps({"status": "waiting", "reason": reason}), flush=True)
            failure = reason
            stop.wait(delay)
            delay = min(delay * 2, 30)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--with-financial-bindings", action="store_true")
    args = parser.parse_args()
    path = args.config
    info = path.stat()
    if path.is_symlink() or not path.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Expected owner-only observer config")
    profile = json.loads(path.read_text())
    if set(profile) != {"database", "serverAddress", "role", "service"}:
        raise ValueError("Unexpected observer config fields")
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    statement = "SELECT demo_delivery.consume_confirmed_starts()"
    if args.with_financial_bindings:
        statement = "SELECT demo_delivery.consume_ready_demo_sessions()"
    run(profile, stop, statement)


if __name__ == "__main__":
    main()
