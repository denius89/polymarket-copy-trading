"""Run a venue release with the financial identity of a closed demo profile."""
from argparse import ArgumentParser, Namespace
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from fractions import Fraction
from ipaddress import IPv4Address
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import sys
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic
from uuid import UUID

from psycopg import connect


PROFILE_KEYS = {
    "requestId", "sessionId", "ownerId", "traderRevisionId", "settingsRevisionId",
    "venue", "wallet", "runId", "fixedDebit", "sessionExpiresAt", "writerRole",
}


def read_operator(path):
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("Expected an exact installed runtime file")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("Expected an operator-owned runtime file")
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("Runtime file exceeded its size limit")
    return json.loads(raw)


def validated_profile(value):
    if set(value) != PROFILE_KEYS or value["venue"] not in {"polymarket","limitless"}:
        raise ValueError("Unexpected closed financial profile fields")
    for field in ("requestId","sessionId","ownerId","traderRevisionId","settingsRevisionId","runId"):
        if str(UUID(value[field])) != value[field]:
            raise ValueError("Expected canonical closed runtime identifiers")
    prefix = "polygon_live_writer" if value["venue"]=="polymarket" else "limitless_buy_writer"
    if not re.fullmatch(prefix+r"_[a-f0-9]{32}",value["writerRole"]):
        raise ValueError("Invalid venue writer role")
    if not re.fullmatch(r"0x[a-f0-9]{40}",value["wallet"]):
        raise ValueError("Invalid canonical trader wallet")
    debit=value["fixedDebit"]
    if set(debit)!={"n","d"} or any(not re.fullmatch(r"[1-9][0-9]{0,17}",debit[k]) for k in ("n","d")):
        raise ValueError("Invalid fixed debit")
    amount=Fraction(int(debit["n"]),int(debit["d"]))
    expires=datetime.fromisoformat(value["sessionExpiresAt"])
    if expires.tzinfo is None:
        raise ValueError("The runtime requires a UTC deadline")
    return amount, expires


def connection_policy(policy, profile):
    expected={"venue","runId","serverAddress","pgServiceFile","writerServices","seconds"}
    if set(policy) != expected or (policy["venue"],policy["runId"]) != (profile["venue"],profile["runId"]):
        raise ValueError("Runtime belongs to another venue or release")
    address=IPv4Address(policy["serverAddress"])
    if not address.is_private:
        raise ValueError("Expected a private PostgreSQL endpoint")
    service_file=Path(policy["pgServiceFile"])
    if not service_file.is_absolute() or service_file.resolve(strict=True)!=service_file:
        raise ValueError("Expected a private PostgreSQL service file")
    info=service_file.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid not in {0,os.getuid()} or info.st_mode & 0o077:
        raise ValueError("The service profile must be private")
    os.environ["PGSERVICEFILE"]=str(service_file)
    scoped=policy["writerServices"][profile["writerRole"]]
    fields={"writer","issuer"} if profile["venue"]=="polymarket" else {
        "writer","discoveryBlock","allowNo","checkpointFile"
    }
    if set(scoped)!=fields:
        raise ValueError("Invalid scoped credential configuration")
    for key in ("writer","issuer"):
        if key in scoped and not re.fullmatch(r"[a-z][a-z0-9_]{1,59}",scoped[key]):
            raise ValueError("Invalid local PostgreSQL service name")
    with connect(service=scoped["writer"],connect_timeout=3,autocommit=True) as database:
        identity=database.execute("SELECT current_database(),host(inet_server_addr()),session_user").fetchone()
        if identity!=("shadow_v00",str(address),profile["writerRole"]):
            raise ValueError("Closed runtime writer does not match the financial profile")
    return str(address),scoped


def ready(venue):
    destination=os.environ.get("NOTIFY_SOCKET")
    if destination:
        if destination.startswith("@"):
            destination="\0"+destination[1:]
        with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as notice:
            notice.sendto(b"READY=1",destination)
    print(json.dumps({"stage":"closed-live-runtime","venue":venue,"status":"scope_verified"}),flush=True)


def polymarket(profile, address, scoped, amount, seconds, check):
    from personal_worker import run

    config={
        "sessionId":profile["sessionId"],"publicWallet":profile["wallet"],"writerService":scoped["writer"],
        "issuerService":scoped["issuer"],"settingsId":profile["settingsRevisionId"],
        "fixedBudget":{"n":str(amount.numerator),"d":str(amount.denominator)},
        "database":"shadow_v00","serverAddress":address,"runId":profile["runId"],
    }
    with TemporaryDirectory(prefix="shadow-pm-profile-") as temporary:
        path=Path(temporary)/"assignment.json"
        with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"w") as output:
            json.dump(config,output)
        args=Namespace(config=path,closed_configured_wallet=True,seconds=seconds,until=None,
                       data_taker=True,lookup=None,check=check,stop_after_first=False,
                       require_activation_anchor=True)
        return run(args,on_ready=lambda:ready("polymarket"))


def limitless(profile, address, scoped, amount, seconds, check):
    from book_engine import q
    from closed_limitless_checkpoint import Checkpoint
    from personal_limitless_worker import PersonalLimitless, PersonalScope, finalize_buys, run_limitless
    from source import BASE_DISCOVERY_FALLBACK, RPC, rpc

    micros=amount*1_000_000
    if micros.denominator!=1 or micros<=0:
        raise ValueError("Limitless requires an exact positive micro-unit cap")
    cursor,allow_no=scoped["discoveryBlock"],scoped["allowNo"]
    if type(cursor) is not int or not 0<cursor<2**53 or type(allow_no) is not bool:
        raise ValueError("Expected the known saved Limitless discovery block")
    scope=PersonalScope(*(UUID(profile[k]) for k in ("sessionId","ownerId","traderRevisionId","settingsRevisionId")),
                        profile["wallet"],int(micros))
    def db():
        session=connect(service=scoped["writer"],connect_timeout=3,application_name="shadow-closed-limitless-runtime")
        try:
            identity=session.execute("SELECT current_database(),host(inet_server_addr()),session_user").fetchone()
            if identity!=("shadow_v00",address,profile["writerRole"]):
                raise ValueError("Closed Limitless connection scope changed")
            session.rollback()
            return session
        except Exception:
            session.close()
            raise

    with db() as database:
        database.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        [current] = database.execute(
            "SELECT polygon.closed_limitless_runtime_scope(%s::uuid)", (profile["sessionId"],)
        ).fetchone()
    if not isinstance(current,dict) or not isinstance(current.get("activatedAt"),str):
        raise ValueError("Limitless writer did not return its activation time")
    started=datetime.fromisoformat(current.pop("activatedAt"))
    if started.tzinfo is None:
        raise ValueError("Limitless activation time requires a timezone")
    identity={key:profile[key] for key in ("sessionId","ownerId","traderRevisionId","settingsRevisionId","wallet","runId")}
    if current != identity | {"maxBuyDebitMicros":str(int(micros))}:
        raise ValueError("Limitless assignment differs from the financial profile")
    waiting,stop=Event(),Event()
    adapter=PersonalLimitless(scope,db,waiting)
    if adapter.pending():
        waiting.set()
    for signum in (signal.SIGINT,signal.SIGTERM):
        signal.signal(signum,lambda *_:stop.set())

    def report(entry):
        safe={key:entry[key] for key in ("stage","status","state","reason","scannedThrough") if key in entry}
        print(json.dumps(safe),flush=True)

    def checkpoint_witness(method,*params):
        # Base finality for funds continues to use the financial adapter's pair.
        # Coverage is verified independently against two block-only providers.
        with ThreadPoolExecutor(max_workers=2) as pool:
            requests=[pool.submit(rpc,method,*params,endpoint=endpoint)
                      for endpoint in (RPC[1],BASE_DISCOVERY_FALLBACK)]
            return tuple(request.result() for request in requests)

    progress=Checkpoint(Path(scoped["checkpointFile"]),identity,cursor,checkpoint_witness,report)
    with progress.lock():
        for attempt in range(4):
            try:
                cursor=progress.resume(persist_seed=not check)
                break
            except OSError:
                if attempt==3 or stop.wait(4):
                    raise
                report({"stage":"limitless-checkpoint-witness","status":"waiting"})
        ready("limitless")
        if check:
            return 0
        with ThreadPoolExecutor(max_workers=3) as pool:
            checkpoint_task=pool.submit(progress.maintain,stop)
            workers=(
                pool.submit(run_limitless,adapter,scope.wallet,stop,monotonic()+seconds,report,
                            buy_budget=q(amount),allow_no=allow_no,discovery_cursor=cursor,
                            discovery_hash=progress.digest,started_ms=int(started.timestamp()*1000),
                            range_processed=progress.complete),
                pool.submit(finalize_buys,adapter,stop,report,stop_after_first=False),
            )
            finished,_=wait((*workers,checkpoint_task),return_when=FIRST_COMPLETED)
            stop.set()
            for worker in (*finished,checkpoint_task):
                worker.result()
    return 0


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("profile",type=Path)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    script=Path(__file__).resolve()
    profile=read_operator(args.profile)
    amount,expires=validated_profile(profile)
    policy=read_operator(script.with_name("venue-runtime.json"))
    maximum=policy["seconds"]
    if type(maximum) is not int or not 15<=maximum<=21600:
        raise ValueError("Expected a bounded closed runtime window")
    remaining=min(maximum,int((expires-datetime.now(timezone.utc)).total_seconds()))
    if remaining<15:
        raise ValueError("Demo session has insufficient time left")
    address,scoped=connection_policy(policy,profile)
    venue=profile["venue"]
    runner=polymarket if venue=="polymarket" else limitless
    return runner(profile,address,scoped,amount,remaining,args.check)


if __name__=="__main__":
    raise SystemExit(main())
