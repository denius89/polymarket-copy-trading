#!/usr/bin/python3 -B
"""Attach a confirmed closed-demo request to its approved systemd runtime."""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import stat
from subprocess import SubprocessError, check_output, run
import sys
from uuid import UUID


FIELDS = {"requestId", "sessionId", "venue", "wallet", "traderRevisionId"}
PROPERTIES = ("Id", "LoadState", "ActiveState", "SubState", "User",
              "InvocationID", "MainPID", "FragmentPath", "DropInPaths", "NeedDaemonReload",
              "WorkingDirectory", "ExecStart")
SYSTEMCTL = "/usr/bin/systemctl"


def load_registry(path):
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("The runtime registry path must be absolute and canonical")
    for parent in path.parents:
        info = parent.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("The runtime registry must be in an operator-controlled directory")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("The runtime registry must be operator-owned")
        data = stream.read(65537)
    if len(data) > 65536:
        raise ValueError("The runtime registry is too large")
    return json.loads(data)


def read_request(stream):
    data = stream.read(2049)
    if len(data) > 2048:
        raise ValueError("Activation request is too large")
    request = json.loads(data)
    if (not isinstance(request, dict) or set(request) != FIELDS
            or request["venue"] not in {"polymarket", "limitless"}
            or not re.fullmatch(r"0x[0-9a-f]{40}", request["wallet"])):
        raise ValueError("Invalid activation request")
    for key in ("requestId", "sessionId", "traderRevisionId"):
        if str(UUID(request[key])) != request[key]:
            raise ValueError("Invalid activation identity")
    return request


def approved_service(registry, request):
    entries = registry["sessions"]
    units = [entry["unit"] for entry in entries.values()]
    if len(units) != len(set(units)):
        raise ValueError("A runtime must belong to only one session")
    entry = entries.get(request["sessionId"])
    if not isinstance(entry, dict) or set(entry) != FIELDS | {
            "unit", "mode", "user", "entrypoint", "fragment", "workingDirectory", "argvSha256",
            "profilePath", "profileSha256"}:
        raise ValueError("No approved runtime is available for this session")
    if any(entry[name] != request[name] for name in FIELDS):
        raise ValueError("The activation request differs from the approved runtime")
    unit = entry["unit"]
    if entry["mode"] == "start-user":
        expected = "shadow-closed-demo-" + request["requestId"] + ".service"
        if unit != expected or entry["user"] != "":
            raise ValueError("Expected a dedicated request-derived user service")
    elif entry["mode"] == "adopt-system":
        if not re.fullmatch(r"shadow-[a-f0-9]{8}-[a-z0-9-]{1,48}\.service", unit):
            raise ValueError("Expected an isolated operator-managed service")
    else:
        raise ValueError("Invalid runtime mode")
    if (not all(re.fullmatch(r"[a-f0-9]{64}", entry[field]) for field in ("argvSha256", "profileSha256"))
            or not all(Path(entry[field]).is_absolute() for field in ("fragment", "entrypoint",
                                                                    "workingDirectory", "profilePath"))):
        raise ValueError("The runtime definition was not pinned")
    return entry


def inspect(systemctl, entry):
    output = check_output(systemctl + ["show", "--all", "--no-pager", "--property=" + ",".join(PROPERTIES), entry["unit"]],
                          text=True, timeout=5)
    props = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    argv = props.get("ExecStart", "").partition("argv[]=")[2].partition(" ;")[0]
    if (props.get("Id") != entry["unit"] or props.get("LoadState") != "loaded"
            or props.get("User") != entry["user"] or props.get("FragmentPath") != entry["fragment"]
            or props.get("WorkingDirectory") != entry["workingDirectory"]
            or props.get("DropInPaths") != "" or props.get("NeedDaemonReload") != "no"
            or not argv.startswith(entry["entrypoint"] + " ")
            or entry["profilePath"] not in shlex.split(argv)
            or sha256(argv.encode()).hexdigest() != entry["argvSha256"]):
        raise ValueError("The service definition differs from the approved runtime")
    profile = Path(entry["profilePath"])
    with profile.open("rb") as stream:
        body = stream.read(65537)
    if len(body) > 65536 or sha256(body).hexdigest() != entry["profileSha256"]:
        raise ValueError("The runtime profile differs from the approved one")
    props["argv"] = shlex.split(argv)
    return props


def activate(entry):
    systemctl = [SYSTEMCTL, "--user" if entry["mode"] == "start-user" else "--system"]
    status = inspect(systemctl, entry)
    if status.get("ActiveState") == "inactive" and entry["mode"] == "start-user":
        # systemd serializes start requests for one unit. The name is derived
        # from C06 and stays stable after a timeout or restart of the caller.
        run(systemctl + ["start", entry["unit"]], check=True, timeout=12,
            stdout=sys.stderr, stderr=sys.stderr)
        status = inspect(systemctl, entry)
    invocation = status.get("InvocationID", "")
    if (status.get("ActiveState"), status.get("SubState")) != ("active", "running") or not re.fullmatch(
            r"[a-f0-9]{32}", invocation):
        raise ValueError("The approved runtime is not running")
    pid = status.get("MainPID", "")
    if not re.fullmatch(r"[1-9][0-9]*", pid):
        raise ValueError("The approved runtime has no main process")
    process = Path("/proc") / pid
    command = (process / "cmdline").read_bytes().rstrip(b"\0").decode().split("\0")
    if command != status["argv"] or os.readlink(process / "cwd") != entry["workingDirectory"]:
        raise ValueError("The running command differs from the approved runtime")
    confirmed = inspect(systemctl, entry)
    if (confirmed.get("MainPID"), confirmed.get("InvocationID"), confirmed.get("ActiveState")) != (
            pid, invocation, "active"):
        raise ValueError("The runtime changed during verification")
    return str(UUID(hex=invocation))


def main():
    try:
        request = read_request(sys.stdin.buffer)
        registry = load_registry(Path(os.environ["SHADOW_CLOSED_RUNTIME_REGISTRY"]))
        print(json.dumps({"requestId": request["requestId"], "instanceId": activate(approved_service(registry, request))}))
    except (OSError, KeyError, TypeError, ValueError, AttributeError, SubprocessError) as error:
        # The parent receives no operator command line, environment or credentials.
        print(type(error).__name__, file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
