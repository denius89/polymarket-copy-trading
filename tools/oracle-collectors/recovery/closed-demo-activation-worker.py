"""Prepare closed demo runtimes through explicitly installed venue adapters."""
from argparse import ArgumentParser
from ipaddress import IPv4Address
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
from selectors import DefaultSelector, EVENT_READ
from subprocess import DEVNULL, PIPE, Popen, TimeoutExpired
from threading import Event
from time import monotonic
from uuid import UUID

from psycopg import OperationalError, connect


def operator_file(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Expected a private operator file")
        data = stream.read(16385)
        if len(data) > 16384:
            raise ValueError("Operator file is oversized")
    return json.loads(data)


def adapter_path(value):
    path = Path(value)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("Expected an exact adapter path")
    for candidate in (path, *path.parents):
        info = candidate.stat()
        if info.st_uid not in {0, os.getuid()} or info.st_mode & 0o022:
            raise ValueError("Expected an operator-controlled adapter path")
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("Expected an executable venue adapter")
    return path


def prepare(adapter, job):
    # The lease token stays inside PostgreSQL. The immutable C06 request ID
    # identifies the same runtime even if the caller disappears mid-launch.
    payload = {key: job[key] for key in ("requestId", "sessionId", "venue", "wallet", "traderRevisionId")}
    with Popen([adapter], stdin=PIPE, stdout=PIPE, stderr=DEVNULL, start_new_session=True) as process:
        try:
            deadline = monotonic() + 55
            process.stdin.write(json.dumps(payload).encode())
            process.stdin.close()
            response = bytearray()
            with DefaultSelector() as readable:
                readable.register(process.stdout, EVENT_READ)
                while readable.select(max(0, deadline-monotonic())):
                    chunk = os.read(process.stdout.fileno(), 1025-len(response))
                    if not chunk:
                        break
                    response.extend(chunk)
                    if len(response) > 1024:
                        raise ValueError("Venue adapter output exceeded its limit")
                else:
                    raise TimeoutExpired(adapter, 55)
            if process.wait(timeout=max(0, deadline-monotonic())) != 0:
                raise ValueError("Venue adapter did not confirm activation")
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    result = json.loads(response)
    if (not isinstance(result, dict) or set(result) != {"requestId", "instanceId"}
            or result["requestId"] != job["requestId"] or not isinstance(result["instanceId"], str)):
        raise ValueError("Venue adapter replied for a different request")
    identity = UUID(result["instanceId"])
    if identity.int == 0:
        raise ValueError("Venue adapter did not report a running instance")
    return identity


def broker_path(value):
    path = Path(value)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("Expected an exact runtime broker socket")
    info = path.stat()
    if info.st_uid != 0 or not stat.S_ISSOCK(info.st_mode):
        raise ValueError("Expected an operator-managed launch broker")
    for parent in path.parents:
        info = parent.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("Expected an operator-controlled broker directory")
    return path


def prepare_with_broker(address, job):
    payload = {key: job[key] for key in ("requestId", "token")}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(35)
        client.connect(str(address))
        client.sendall((json.dumps(payload)+"\n").encode())
        with client.makefile("rb") as stream:
            response = stream.readline(1025)
    if len(response) > 1024 or not response.endswith(b"\n"):
        raise ValueError("Invalid launch broker reply")
    result = json.loads(response)
    if (not isinstance(result, dict) or result.get("requestId") != job["requestId"]
            or not isinstance(result.get("instanceId"), str)):
        raise ValueError("The launch broker deferred this request")
    instance = UUID(result["instanceId"])
    if instance.int == 0:
        raise ValueError("The launch broker did not confirm an instance")
    return instance


def activate(database, adapters, brokers, job, stop):
    try:
        venue = job["venue"]
        if venue in brokers:
            instance = prepare_with_broker(brokers[venue], job)
        else:
            instance = prepare(adapters[venue], job)
    except (OSError, TypeError, ValueError, TimeoutExpired):
        database.execute("SELECT demo_delivery.defer_activation(%s,%s)", (job["requestId"], job["token"]))
        return "retry"
    # 55 seconds for the adapter, at most 15 seconds of SQL and three one-second waits.
    for _ in range(3):
        [activated] = database.execute("SELECT demo_delivery.finish_activation(%s,%s,%s)",
                                       (job["requestId"], job["token"], instance)).fetchone()
        if activated:
            return "active"
        if stop.wait(1):
            break
    database.execute("SELECT demo_delivery.defer_activation(%s,%s)", (job["requestId"], job["token"]))
    return "waiting_for_writer"


def observe(profile, stop):
    profile_fields = {"database", "serverAddress", "role", "service", "runId", "adapters"}
    if set(profile)-{"runtimeBrokers"} != profile_fields:
        raise ValueError("Unexpected activation profile fields")
    address = IPv4Address(profile["serverAddress"])
    role = profile["role"]
    if (not address.is_private or profile["database"] != "shadow_v00"
            or not re.fullmatch(r"demo_activation_[a-f0-9]{8}", role)):
        raise ValueError("Expected the private closed database and activation role")
    venues = set(profile["adapters"])
    brokers = profile.get("runtimeBrokers", {})
    if venues & brokers.keys() or venues | brokers.keys() != {"polymarket", "limitless"}:
        raise ValueError("Expected one activation route per venue")
    adapters = {venue: adapter_path(path) for venue, path in profile["adapters"].items()}
    brokers = {venue: broker_path(path) for venue, path in brokers.items()}
    while not stop.is_set():
        try:
            with connect(service=profile["service"], connect_timeout=3, autocommit=True,
                         application_name="shadow-closed-demo-activation",
                         options="-c statement_timeout=5000 -c lock_timeout=1000") as database:
                expected = ("shadow_v00", str(address), role, UUID(profile["runId"]))
                actual = database.execute(
                    "SELECT current_database(),host(inet_server_addr()),session_user,demo_delivery.activation_release()"
                ).fetchone()
                if actual != expected:
                    raise ValueError("Closed activation database identity mismatch")
                while not stop.is_set():
                    [job] = database.execute("SELECT demo_delivery.claim_activation()").fetchone()
                    if job is None:
                        stop.wait(2)
                        continue
                    status = activate(database, adapters, brokers, job, stop)
                    print(json.dumps({"venue": job["venue"], "status": status, "attempt": job["attempt"]}), flush=True)
        except OperationalError:
            stop.wait(5)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    stop = Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    observe(operator_file(parser.parse_args().config), stop)


if __name__ == "__main__":
    main()
