"""Local, resource-bounded supervisor for public read-only observation chunks.

Not an OS service: sleep, process loss and capture gaps remain data gaps.
No trading, credentials or modeled monetary outcomes are supported here.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def used_bytes(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def atomic_status(path, state):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2) + '\n')
    temp.replace(path)


def archive_chunk(directory):
    """Lossless container conversion; verify exact decoded hash before raw removal."""
    manifest=json.loads((directory/'manifest.json').read_text())
    raw=directory/'events.jsonl'
    if not raw.is_file() or not manifest.get('eventsSha256'):
        return False  # Interrupted/unfinalized data remains raw, with no repaired provenance.
    temp=directory/'events.jsonl.gz.tmp'
    compressed=directory/'events.jsonl.gz'
    if compressed.exists():
        raise ValueError('archive already exists; do not replace')
    with raw.open('rb') as source, gzip.open(temp,'wb',compresslevel=6) as target:
        shutil.copyfileobj(source,target)
    digest=hashlib.sha256()
    with gzip.open(temp,'rb') as source:
        for chunk in iter(lambda:source.read(1048576),b''):digest.update(chunk)
    if digest.hexdigest()!=manifest['eventsSha256']:
        temp.unlink();raise ValueError('archive roundtrip hash mismatch; raw retained')
    temp.replace(compressed)
    atomic_status(directory/'archive.json',dict(schemaVersion='forward-event-archive-v1',
                  file='events.jsonl.gz',uncompressedSha256=digest.hexdigest(),uncompressedBytes=raw.stat().st_size,
                  compressedSha256=hashlib.sha256(compressed.read_bytes()).hexdigest(),
                  compressedBytes=compressed.stat().st_size))
    raw.unlink()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=BASE/'observations')
    parser.add_argument('--hours', type=float, default=24)
    parser.add_argument('--chunk-seconds', type=int, default=1800)
    parser.add_argument('--max-bytes', type=int, default=268435456)
    args = parser.parse_args()
    if not 0 < args.hours <= 24*30 or not 30 <= args.chunk_seconds <= 86400:
        parser.error('hours must be 0..720 and chunk-seconds 30..86400')
    if not 1048576 <= args.max_bytes <= 1073741824:
        parser.error('max-bytes must be 1 MiB..1 GiB')
    args.root.mkdir(parents=True, exist_ok=True)
    with (args.root/'runner.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('another runner owns this capture root', file=sys.stderr)
            return 2
        # Freeze configuration for this launch; a restart is a new observed interval.
        config_bytes=args.config.read_bytes()
        json.loads(config_bytes)
        launch=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        frozen=args.root/('config-'+launch+'.json')
        frozen.write_bytes(config_bytes)
        frozen_collector=args.root/('collector-'+launch+'.py')
        frozen_collector.write_bytes((BASE/'collector.py').read_bytes())
        deadline_monotonic=time.monotonic()+args.hours*3600
        state=dict(schema='forward-runner-v1', launch_id=launch, pid=os.getpid(),
                   started_at=utc(), updated_at=utc(), status='starting',
                   deadline_epoch=time.time()+args.hours*3600,
                   config_sha256=hashlib.sha256(config_bytes).hexdigest(),
                   config_file=str(frozen.resolve()), max_bytes=args.max_bytes,
                   collector_file=str(frozen_collector.resolve()),
                   collector_sha256=hashlib.sha256(frozen_collector.read_bytes()).hexdigest(),
                   completed_chunks=0, failed_chunks=0, current_chunk=None,
                   continuous_coverage_guaranteed=False, real_money=False,
                   venue_binding_verified=False)
        stopping=False

        def stop(_signum, _frame):
            nonlocal stopping
            stopping=True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        child=None
        consecutive_failures=0
        try:
            while True:
                remaining=deadline_monotonic-time.monotonic()
                used=used_bytes(args.root)
                if stopping or (args.root/'STOP').exists():
                    state['status']='stopped_by_request'; break
                if remaining<1:
                    state['status']='deadline_reached'; break
                if args.max_bytes-used<1048576:
                    state['status']='storage_limit_reached'; break
                number=state['completed_chunks']+state['failed_chunks']+1
                output=args.root/('capture-'+launch+'-'+str(number).zfill(4))
                # Reserve room for both raw and lossless archive during conversion.
                chunk_bytes=min((args.max_bytes-used-131072)//2, 16*1048576)
                command=[sys.executable,str(frozen_collector),'capture','--config',str(frozen),
                         '--output',str(output),'--duration-seconds',str(max(1,int(min(remaining,args.chunk_seconds)))),
                         '--max-bytes',str(chunk_bytes)]
                state.update(status='collecting',current_chunk=str(output.resolve()),updated_at=utc())
                atomic_status(args.root/'runner-status.json',state)
                with (args.root/('chunk-'+launch+'-'+str(number)+'.log')).open('w') as log:
                    child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
                    while child.poll() is None:
                        if stopping or (args.root/'STOP').exists() or used_bytes(args.root)>=args.max_bytes-65536 or time.monotonic()>=deadline_monotonic:
                            child.terminate()
                            try:child.wait(timeout=20)
                            except subprocess.TimeoutExpired:child.kill();child.wait()
                            break
                        state.update(updated_at=utc(),bytes_used=used_bytes(args.root),child_pid=child.pid)
                        atomic_status(args.root/'runner-status.json',state)
                        time.sleep(2)
                    code=child.wait();child=None
                state['last_exit_code']=code
                if code==0:
                    try:
                        if not archive_chunk(output):
                            state.update(status='stopped_archive_incomplete',last_error='unfinalized capture retained raw')
                            break
                    except (ValueError,OSError) as exc:
                        state.update(status='stopped_archive_error',last_error=str(exc))
                        break
                    state['completed_chunks']+=1;consecutive_failures=0
                else:
                    state['failed_chunks']+=1;consecutive_failures+=1
                state.update(updated_at=utc(),bytes_used=used_bytes(args.root))
                atomic_status(args.root/'runner-status.json',state)
                if consecutive_failures>=3:
                    state['status']='stopped_after_three_failed_chunks';break
                # Chunk boundaries and retries are explicit capture gaps, never joined as continuous.
                for _ in range(5 if code==0 else 60):
                    if stopping or (args.root/'STOP').exists() or time.monotonic()>=deadline_monotonic:break
                    time.sleep(1)
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                try:child.wait(timeout=20)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            if state['status']=='collecting':state['status']='interrupted'
            state.update(updated_at=utc(),bytes_used=used_bytes(args.root),child_pid=None)
            atomic_status(args.root/'runner-status.json',state)
        print(json.dumps(state))
        return 1 if state['status'] in ('stopped_after_three_failed_chunks','stopped_archive_error','stopped_archive_incomplete') else 0


if __name__=='__main__':
    sys.exit(main())
