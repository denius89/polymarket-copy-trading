"""Move the existing writer to the maker-capable package without changing the UI."""
from contextlib import closing
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

import backup
import storage

PACKAGE = Path(__file__).resolve().parent
PUBLIC_LEDGER = backup.LEDGER
PUBLISH = backup.ROOT/'publish'
OLD_UNIT = 'shadow-paper-e99162d8-app-buy-v1.service'
NEW_UNIT = 'shadow-paper-e99162d8-app-buy-v2.service'
OLD_RUN = '5fd9a36ffadfd981'
END = int(datetime(2026,11,21,tzinfo=ZoneInfo('Europe/Warsaw')).timestamp())


def run(*command, timeout=15):
    return subprocess.run(command,check=True,capture_output=True,text=True,timeout=timeout).stdout.strip()


def unit(name, field):
    return run('systemctl','show','--value','--property='+field,name)


def report(stage, **values):
    print(json.dumps({'stage':stage,**values},ensure_ascii=False,separators=(',',':')),flush=True)


def control():
    with closing(backup.read_only(PUBLIC_LEDGER)) as db:
        return db.execute('SELECT epoch,owner,admissions FROM app_buy_control WHERE id=1').fetchone()


def safe_connection(path):
    db = backup.read_only(path)
    db.execute('PRAGMA query_only=ON')
    return db


def current_audit():
    with closing(safe_connection(PUBLIC_LEDGER)) as db:
        current = storage.audit(db)
    return {'available':current['available'],'reserved':current['reserved'],
            'positions':len(current['positions']),'history':current['legacy'],'states':current['journalStates']}


def handover(old_unit,new_unit,old_run,owner,old_epoch,new_owner,*,publish_ui=None,ready=None):
    if os.geteuid()!=0 or time.time()>=END:
        raise RuntimeError('release is outside the active Oracle window')
    old_pid=int(unit(old_unit,'MainPID'))
    if old_pid<1 or unit(old_unit,'ActiveState')!='active' or unit(new_unit,'MainPID')!='0':
        raise RuntimeError('unexpected process ownership before handover')
    cmdline=(Path('/proc')/str(old_pid)/'cmdline').read_bytes().split(b'\0')
    expected=backup.ROOT/'releases'/old_run/'app_run.py'
    if str(expected).encode() not in cmdline or control()!=(old_epoch,owner,1):
        raise RuntimeError('prior writer pin differs')
    next_epoch=old_epoch+1
    rollback = backup.ROOT/'integration-backups'/('handover-'+PACKAGE.name)
    rollback.mkdir(mode=0o700)
    retained = rollback/'ledger.sqlite'
    info=storage.consistent_backup(PUBLIC_LEDGER,retained)
    with closing(safe_connection(retained)) as copy:
        audit=storage.audit(copy)
    if audit['conservation'] is not True:
        raise RuntimeError('package rejected the restored ledger')
    report('restore-compatible',backupSha256=info['sha256'],available=audit['available'],
           reserved=audit['reserved'],states=audit['journalStates'])
    if publish_ui is not None:
        report('app-ui-verified',proof=publish_ui(rollback))
    run('systemctl','kill','--kill-who=main','--signal=USR1',old_unit)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        if control()==(old_epoch,owner,0):break
        time.sleep(.2)
    else:
        raise RuntimeError('previous owner did not close admissions')
    report('prior-admissions-closed',epoch=old_epoch)
    run('systemctl','stop',old_unit,timeout=75)
    if int(unit(old_unit,'MainPID'))!=0 or control()!=(next_epoch,None,0):
        raise RuntimeError('previous writer did not drain and fence')
    report('prior-writer-drained',**current_audit())
    old_feed=backup.sha(backup.FEED.read_bytes())
    run('systemd-run','--quiet','--unit='+new_unit.removesuffix('.service'),
        '--property=User=ubuntu','--property=Group=ubuntu','--property=NoNewPrivileges=yes',
        '--property=ProtectSystem=strict','--property=ProtectHome=yes','--property=PrivateTmp=yes',
        '--property=RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6','--property=UMask=0077',
        '--property=ReadWritePaths='+str(PUBLIC_LEDGER.parent)+' '+str(PUBLISH),
        '--property=BindPaths='+str(backup.FEED.parent)+':'+str(PUBLISH),
        '--property=Restart=no','--property=TimeoutStopSec=70s','/usr/bin/python3','-B',
        str(PACKAGE/'app_run.py'),str(PUBLIC_LEDGER),str(PUBLISH/backup.FEED.name),new_owner,str(next_epoch),str(END))
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        if (control()==(next_epoch+1,new_owner,1) and unit(new_unit,'ActiveState')=='active'
                and backup.sha(backup.FEED.read_bytes())!=old_feed):
            if ready is None or ready():
                report('writer-publishing',epoch=next_epoch+1,unit=new_unit);return
        time.sleep(.25)
    raise RuntimeError('writer readiness unknown; do not repeat')


def under_release_lock(callback):
    os.umask(0o077)
    descriptor=os.open(backup.ROOT/'integration-release.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        callback()
    finally:
        os.close(descriptor)


if __name__=='__main__':
    under_release_lock(lambda:handover(OLD_UNIT,NEW_UNIT,OLD_RUN,'shared-demo-'+OLD_RUN+'-mount',3,
                                      'shared-demo-maker-'+PACKAGE.name))
