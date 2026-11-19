"""Prepare and activate the versioned shared-demo release on Oracle."""
from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import backup
import edge
import storage

RELEASE = Path(__file__).resolve().parent
STATE = backup.LEDGER.parent
UNIT = 'shadow-paper-e99162d8-app-buy-v1.service'
OLD_UNIT = 'shadow-paper-e99162d8-public-demo-v3.service'
LEDGER_SHA = '553cf25c79b6c5d191864bac3c2eceee652e4da90f3ead4a746f92008741dbf7'
BACKUP_SHA = '47fdcdff4ba72830c91cdc6c160430f7f8d2df49f4212ee17838fa149f2c1cd5'
FEED_SHA = '1e4be86a91652d9ec53b5d3da5ac0f5b533a87c4ddaa137bd3514e7f5346d45c'
BASELINE = json.loads((RELEASE/'BASELINE-SCHEMA.json').read_text())['schema']
POLICY = {'opening':200_000_000,'daily':200_000_000,'market':100_000_000}
BOOTSTRAP = backup.ROOT/'integration-backups/prebuy20261117/ledger.sqlite'
WINDOW_END = int(datetime(2026,11,21,0,0,tzinfo=ZoneInfo('Europe/Warsaw')).timestamp())


def report(stage, **evidence):
    print(json.dumps({'stage':stage, **evidence},ensure_ascii=False,separators=(',',':')),flush=True)


def unit(property_name, name):
    return edge.run('systemctl','show',f'--property={property_name}','--value',name).decode().strip()


def baseline():
    if unit('ActiveState', OLD_UNIT) != 'inactive' or unit('ActiveState', UNIT) != 'inactive':
        raise RuntimeError('another shared-ledger writer is active')
    if unit('ActiveState','shadow-paper-e99162d8-edge-friday.timer') != 'active':
        raise RuntimeError('existing edge access timer no longer active')
    if time.time() >= WINDOW_END:
        raise RuntimeError('edge access window expired')
    backup.assert_stopped_ledger_writers()
    pins = ((backup.LEDGER,LEDGER_SHA),(BOOTSTRAP,BACKUP_SHA),(backup.FEED,FEED_SHA),
            (edge.DIST/'index.html',edge.INDEX_SHA),(edge.CONFIG,edge.EDGE_SHA))
    if any(not path.is_file() or edge.sha(path.read_bytes())!=wanted for path,wanted in pins):
        raise RuntimeError('Oracle preimage changed')
    report('baseline-pinned',ledger=LEDGER_SHA,feed=FEED_SHA,edge=edge.EDGE_SHA)


def rehearse():
    with tempfile.TemporaryDirectory(prefix='app-buy-restore-',dir=backup.ROOT/'integration-backups') as folder:
        scratch = Path(folder)/'ledger.sqlite'
        with closing(backup.read_only(BOOTSTRAP)) as source, closing(sqlite3.connect(scratch)) as copy:
            source.backup(copy)
            before = storage.audit(copy,POLICY)
            storage.install(copy,BASELINE,POLICY)
            after = storage.audit(copy)
            if before!=after:
                raise RuntimeError('migration changed historical holdings')
        with closing(sqlite3.connect(scratch)) as foreign:
            try:
                foreign.execute("INSERT INTO settings VALUES('rehearsal-unauthorized',0)")
            except sqlite3.DatabaseError:
                foreign.rollback()
            else:
                foreign.rollback()
                raise RuntimeError('legacy SQLite writer bypasses the fence')
        with closing(sqlite3.connect(scratch)) as candidate:
            writer = storage.claim_writer(candidate,'restore-rehearsal',0)
            writer.stop_admissions()
            if writer.pending_operations():
                raise RuntimeError('rehearsal unexpectedly introduced pending records')
            writer.fence()
            if storage.audit(candidate)!=before:
                raise RuntimeError('admission check changed restored holdings')
    report('restored-copy-rehearsal',available=before['available'],positions=len(before['positions']),
           history=before['legacy'],legacyBypassBlocked=True,admissionsStopped=True)


def activate(run):
    baseline()
    rehearse()
    baseline()
    if RELEASE.name != run or not run.isascii() or not run.isalnum():
        raise ValueError('unexpected release path')
    rollback = backup.ROOT/'integration-backups'/('edge-'+run)
    rollback.mkdir(mode=0o700)
    with closing(sqlite3.connect(backup.LEDGER.as_uri()+'?mode=rw',uri=True,timeout=3)) as db:
        before = storage.audit(db,POLICY)
        storage.install(db,BASELINE,POLICY)
        if storage.audit(db)!=before:
            raise RuntimeError('migration changed application balances or history')
    report('storage-installed-closed',available=before['available'],positions=len(before['positions']))
    version = RELEASE/'ui'
    assets = {path.name.encode():path.read_bytes() for path in (version/'assets').iterdir() if path.is_file()}
    report('app-ui-verified',proof=edge.install((version/'index.html').read_bytes(),assets,rollback))
    owner = 'shared-demo-'+run
    options = ['systemd-run','--quiet','--unit='+UNIT.removesuffix('.service'),
        '--property=User=ubuntu','--property=Group=ubuntu','--property=NoNewPrivileges=yes',
        '--property=ProtectSystem=strict','--property=ProtectHome=yes','--property=PrivateTmp=yes',
        '--property=RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6','--property=UMask=0077',
        '--property=Restart=no','--property=TimeoutStopSec=70s',
        '--property=ReadWritePaths='+str(STATE)+' '+str(backup.FEED.parent),
        '/usr/bin/python3','-B',str(RELEASE/'app_run.py'),str(backup.LEDGER),str(backup.FEED),owner,'0',str(WINDOW_END)]
    edge.run(*options)
    for _ in range(32):
        if unit('ActiveState',UNIT) in {'failed','inactive'}:
            break
        with closing(backup.read_only(backup.LEDGER)) as db:
            record = db.execute('SELECT epoch,owner,admissions FROM app_buy_control WHERE id=1').fetchone()
        if record in ((1,owner,1),(1,owner,0)):
            report('single-writer-active',unit=UNIT,epoch=1,admissions=bool(record[2]));return
        time.sleep(.25)
    raise RuntimeError('writer readiness unknown; inspect once without a replacement attempt')


if __name__=='__main__':
    os.umask(0o077)
    action,*args=sys.argv[1:]
    if action=='rehearse' and not args:
        baseline();rehearse()
    elif action=='activate' and len(args)==1:
        lock=backup.ROOT/'integration-release.lock'
        descriptor=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
            activate(args[0])
        finally:
            os.close(descriptor)
    else:
        raise SystemExit('expected rehearse or activate with run ID')
