"""Capture and rehearse restoring the current shared SQLite ledger on Oracle."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile

ROOT = Path('/var/lib/shadow-e99162d8-public-paper-ledger')
LEDGER = ROOT / 'state/ledger.sqlite'
FEED = Path('/opt/shadow-polygon/.browser-e2e.e99162d8/gateway/distributions/app/demo-venue-data/snapshot.json')
TABLES = ('events', 'sales', 'sell_targets', 'settings', 'settlements')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_only(path):
    return sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=3)


def project(db):
    rows = {}
    for name in TABLES:
        digests = [hashlib.sha256(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode()).digest()
                   for row in db.execute(f'SELECT * FROM {name}')]
        rows[name] = {'count': len(digests), 'rowSetSha256': sha(b''.join(sorted(digests)))}
    spent = db.execute('SELECT COALESCE(SUM(debit),0) FROM events').fetchone()[0]
    settled = db.execute('SELECT COALESCE(SUM(payout),0) FROM settlements').fetchone()[0]
    sales = db.execute('SELECT COALESCE(SUM(credit),0) FROM sales').fetchone()[0]
    return {'tables': rows, 'debits': spent, 'settlementCredits': settled, 'salesCredits': sales,
            'available': 200_000_000 - spent + settled + sales}


def assert_stopped_ledger_writers():
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            handles = list((process / 'fd').iterdir())
        except (FileNotFoundError, PermissionError):
            continue
        for handle in handles:
            try:
                destination = os.readlink(handle)
            except (FileNotFoundError, PermissionError):
                continue
            if destination == str(LEDGER) or destination.startswith(str(LEDGER) + '-'):
                raise RuntimeError('ledger file is open by another process')


def main(run, ledger_sha, feed_sha):
    assert run.isascii() and run.isalnum() and 8 <= len(run) <= 24
    assert os.geteuid() == 0
    os.umask(0o077)
    assert_stopped_ledger_writers()
    for source in (LEDGER, FEED):
        assert stat.S_ISREG(source.lstat().st_mode)
    feed_bytes = FEED.read_bytes()
    assert sha(LEDGER.read_bytes()) == ledger_sha and sha(feed_bytes) == feed_sha
    state = json.loads(feed_bytes)
    assert state['schema'] == 1 and state['opening'] == 200_000_000
    folder = ROOT / 'integration-backups'
    folder.mkdir(mode=0o700, exist_ok=True)
    assert stat.S_ISDIR(folder.lstat().st_mode) and folder.stat().st_uid == 0
    assert folder.stat().st_mode & 0o077 == 0
    target = folder / run
    target.mkdir(mode=0o700)
    backup = target / 'ledger.sqlite'
    with closing(read_only(LEDGER)) as source, closing(sqlite3.connect(backup)) as dest:
        before = project(source)
        assert state['available'] == before['available']
        source.backup(dest)
        assert dest.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert before == project(dest)
    assert_stopped_ledger_writers()
    assert sha(LEDGER.read_bytes()) == ledger_sha and sha(FEED.read_bytes()) == feed_sha
    (target / 'snapshot.json').write_bytes(feed_bytes)
    with tempfile.TemporaryDirectory(prefix='restore-', dir=target) as directory:
        scratch = Path(directory) / 'ledger.sqlite'
        with closing(read_only(backup)) as source, closing(sqlite3.connect(scratch)) as restore:
            source.backup(restore)
            assert restore.execute('PRAGMA quick_check').fetchone() == ('ok',)
            assert project(restore) == before
    for path in (backup, target / 'snapshot.json'):
        with path.open('rb') as handle:
            os.fsync(handle.fileno())
    proof = {'path': str(backup), 'ledgerSha256': ledger_sha, 'backupSha256': sha(backup.read_bytes()),
             'feedSha256': feed_sha, 'restoreVerified': True, **before}
    with (target / 'proof.json').open('x') as handle:
        json.dump(proof, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    for directory in (target, folder):
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
