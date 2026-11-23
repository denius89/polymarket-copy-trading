"""Launch one approved closed demo process per leased confirmation."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from fcntl import LOCK_EX, LOCK_NB, flock
from hashlib import sha256
from ipaddress import IPv4Address
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import socket
import stat
import struct
from subprocess import DEVNULL, TimeoutExpired, check_output, run
from time import monotonic, sleep
from uuid import UUID

from psycopg import connect

SYSTEMCTL = "/usr/bin/systemctl"
PROPERTIES = "ActiveState,SubState,InvocationID,MainPID,User,WorkingDirectory,ExecStart,Type,NotifyAccess"


def root_file(path):
    if path.resolve(strict=True) != path or not path.is_absolute():
        raise ValueError("Expected a canonical protected file")
    for target in (path, *path.parents):
        info = target.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("Expected a root-managed configuration path")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Expected a regular operator file")
        body = stream.read(65537)
    if len(body) > 65536:
        raise ValueError("Operator configuration is too large")
    return body


def authorize(config, request, token):
    ip = IPv4Address(config["serverAddress"])
    role = config["role"]
    release = UUID(config["runId"])
    if not ip.is_private or not re.fullmatch(r"demo_activation_[a-f0-9]{8}", role):
        raise ValueError("Expected an exact scoped login on private Oracle")
    with connect(service=config["service"], autocommit=True, connect_timeout=3,
                 options="-c statement_timeout=5000 -c lock_timeout=1000") as database:
        expected = ("shadow_v00", str(ip), role, release)
        identity = database.execute(
            "SELECT current_database(),host(inet_server_addr()),session_user,demo_delivery.activation_release()"
        ).fetchone()
        if identity != expected:
            raise ValueError("Closed runtime database identity mismatch")
        [profile] = database.execute(
            "SELECT demo_delivery.activation_runtime_profile(%s,%s)", (request, token)
        ).fetchone()
        if profile is None or profile["requestId"] != str(request):
            raise ValueError("Activation lease has no bound runtime profile")
    return profile


def save(config, request, profile, account):
    directory = Path(config["profileDirectory"])
    if not directory.is_absolute() or directory.resolve(strict=True) != directory:
        raise ValueError("Expected a canonical closed runtime directory")
    for target in (directory, *directory.parents):
        info = target.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("Expected a root-managed profile directory")
    encoded = (json.dumps(profile, sort_keys=True, separators=(",", ":")) + "\n").encode()
    destination = directory / (str(request) + ".json")
    temporary = directory / ("." + str(request) + "." + os.urandom(8).hex())
    try:
        with temporary.open("xb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        os.chown(temporary, 0, account.pw_gid)
        temporary.chmod(0o640)
        try:
            os.link(temporary, destination, follow_symlinks=False)
            parent = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        except FileExistsError:
            if root_file(destination) != encoded:
                raise ValueError("A different financial profile already exists for this request") from None
    finally:
        temporary.unlink(missing_ok=True)
    return destination, sha256(encoded).hexdigest()


def read_unit(unit):
    output = check_output([SYSTEMCTL, "--system", "show", "--all", "--no-pager",
                           "--property=" + PROPERTIES, unit], text=True, timeout=4)
    return dict(line.split("=", 1) for line in output.splitlines() if "=" in line)


def same_definition(info, argv, owner, working_directory):
    expected_argv = shlex.split(info.get("ExecStart", "").partition("argv[]=")[2].partition(" ;")[0])
    return (expected_argv == argv and info.get("User") == owner and info.get("WorkingDirectory") == working_directory
            and (info.get("Type"), info.get("NotifyAccess")) == ("notify", "main"))


def ready(unit, argv, owner, working_directory):
    info = read_unit(unit)
    if info.get("ActiveState") != "active" or info.get("SubState") != "running":
        return None
    pid = info.get("MainPID", "")
    invocation = info.get("InvocationID", "")
    if (not same_definition(info, argv, owner, working_directory)
            or not re.fullmatch(r"[1-9][0-9]*", pid) or not re.fullmatch(r"[a-f0-9]{32}", invocation)):
        raise ValueError("Existing unit is not the approved process for this request")
    command = (Path("/proc") / pid / "cmdline").read_bytes().rstrip(b"\0").decode().split("\0")
    if command != argv:
        raise ValueError("Running process differs from the approved runtime")
    return str(UUID(hex=invocation))


def launch(config, request, token, profile):
    policy = config["venues"][profile["venue"]]
    account = pwd.getpwnam(policy["user"])
    if account.pw_uid == 0 or not 15 <= policy["seconds"] <= 21600:
        raise ValueError("The runtime must be bounded and unprivileged")
    program = Path(policy["program"])
    if sha256(root_file(program)).hexdigest() != policy["programSha256"]:
        raise ValueError("The venue runtime differs from the approved release")
    runtime, fingerprint = save(config, request, profile, account)
    working_directory = str(program.parent)
    unit = "shadow-closed-demo-" + str(request) + ".service"
    argv = ["/usr/bin/python3", "-B", str(program), str(runtime)]
    lock = os.open(str(runtime)+".lock", os.O_NOFOLLOW | os.O_CREAT | os.O_RDWR, 0o600)
    try:
        flock(lock, LOCK_EX | LOCK_NB)
        instance = start_authorized(config, request, token, profile, unit, argv, account.pw_name,
                                    working_directory, policy["seconds"])
    finally:
        os.close(lock)
    return {"requestId": str(request), "instanceId": instance, "profileSha256": fingerprint}


def start_authorized(config, request, token, profile, unit, argv, owner, working_directory, maximum_seconds):
    instance = ready(unit, argv, owner, working_directory)
    if instance is None:
        if authorize(config, request, token) != profile:
            raise ValueError("The authorized runtime profile changed before launch")
        window = datetime.fromisoformat(profile["sessionExpiresAt"]) - datetime.now(timezone.utc)
        runtime_seconds = min(maximum_seconds, int(window.total_seconds()))
        if runtime_seconds < 15:
            raise ValueError("The allowed demo window is ending")
    attempted = instance is None
    try:
        if attempted:
            # A timeout is ambiguous: systemd might have received the start.
            # Reconcile the exact unit before either returning or unwinding it.
            try:
                run(["/usr/bin/systemd-run", "--quiet", "--no-block", "--unit", unit, "--uid", owner,
                     "--property", "NoNewPrivileges=yes", "--property", "Restart=no",
                     "--property", "Type=notify", "--property", "NotifyAccess=main",
                     "--property", "TimeoutStartSec=8", "--property", f"RuntimeMaxSec={runtime_seconds}",
                     "--property", "WorkingDirectory=" + working_directory, *argv],
                    check=False, stdout=DEVNULL, stderr=DEVNULL, timeout=6)
            except TimeoutExpired:
                pass
            deadline = monotonic()+9
            while instance is None and monotonic()<deadline:
                sleep(.25)
                instance = ready(unit, argv, owner, working_directory)
        if instance is None:
            raise RuntimeError("The closed runtime did not reach running")
        if authorize(config, request, token) != profile:
            raise ValueError("The authorized runtime profile changed during launch")
    except Exception:
        if attempted and same_definition(read_unit(unit), argv, owner, working_directory):
            run([SYSTEMCTL, "--system", "stop", unit], check=True, timeout=6,
                stdout=DEVNULL, stderr=DEVNULL)
        raise
    return instance


def serve(config, address):
    if not address.is_absolute() or address.parent.resolve(strict=True) != address.parent:
        raise ValueError("Expected a canonical broker socket directory")
    for parent in (address.parent, *address.parent.parents):
        info = parent.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("The launch broker directory must be operator-managed")
    caller = pwd.getpwnam(config["activationUser"])
    if caller.pw_uid == 0:
        raise ValueError("Expected an unprivileged activation user")
    lock = os.open(str(address)+".lock", os.O_NOFOLLOW | os.O_CREAT | os.O_RDWR, 0o600)
    try:
        flock(lock, LOCK_EX | LOCK_NB)
        if address.exists():
            info = address.lstat()
            if info.st_uid != 0 or not stat.S_ISSOCK(info.st_mode):
                raise ValueError("Unexpected file at the private broker socket")
            address.unlink()
        run_broker(config, address, caller)
    finally:
        os.close(lock)


def run_broker(config, address, caller):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as broker:
        broker.bind(str(address))
        os.chown(address, 0, caller.pw_gid)
        address.chmod(0o660)
        broker.listen(4)
        try:
            while True:
                client, _ = broker.accept()
                with client:
                    client.settimeout(3)
                    try:
                        _, uid, _ = struct.unpack("3i", client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                        if uid != caller.pw_uid:
                            raise ValueError("Inactive broker caller")
                        with client.makefile("rb") as stream:
                            packet = stream.readline(513)
                        if len(packet) > 512 or not packet.endswith(b"\n"):
                            raise ValueError("Invalid launch request length")
                        payload = json.loads(packet)
                        if set(payload) != {"requestId", "token"}:
                            raise ValueError("Invalid launch request")
                        request, token = UUID(payload["requestId"]), UUID(payload["token"])
                        profile = authorize(config, request, token)
                        result = launch(config, request, token, profile)
                    except Exception as error:
                        result = {"status": "deferred", "reason": type(error).__name__}
                    try:
                        client.sendall((json.dumps(result)+"\n").encode())
                    except OSError:
                        pass  # The caller can reconcile the same request and process.
        finally:
            address.unlink()


def main():
    args = ArgumentParser(description=__doc__)
    args.add_argument("configuration", type=Path)
    args.add_argument("request", type=UUID, nargs="?")
    args.add_argument("lease_file", type=Path, nargs="?")
    args.add_argument("--socket", type=Path)
    value = args.parse_args()
    if os.geteuid() != 0:
        raise ValueError("Use the isolated host operator for system services")
    config = json.loads(root_file(value.configuration))
    if value.socket is not None:
        if value.request is not None or value.lease_file is not None:
            args.error("Supply either a broker socket or one exact lease")
        serve(config, value.socket)
        return
    if value.request is None or value.lease_file is None:
        args.error("The request and private lease file are required")
    token = UUID(root_file(value.lease_file).decode().strip())
    profile = authorize(config, value.request, token)
    print(json.dumps(launch(config, value.request, token, profile)))


if __name__ == "__main__":
    main()
