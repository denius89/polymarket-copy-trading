"""Run the two verified collector routes for one enrolled personal subscription."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import fcntl
import json
import os
from pathlib import Path
import re
import signal
from threading import Event
from time import monotonic
from uuid import UUID

from collectors import run_polymarket
from guarded_source import FollowScope, SessionCollectorAdapter, exact
from maker_collector import run_makers
from personal_pg import IdleIngestCanceled, PgTransport, UnresolvedResult
from personal_range import timestamp, utc_ms
from resolver import Skip
from rtds_operator import BoundedRPC

WALLETS = {
    '0xf0318c32136c2db7fec88b84869aee6a1106c80c',
    '0xde9f7f4e77a1595623ceb58e469f776257ccd43c',
}
APPROVED_UNTIL = '2026-11-20T23:00:00Z'
WRITE_DRAIN_SECONDS = 5


class CopyWindow:
    def __init__(self, until, stop):
        if until != APPROVED_UNTIL:
            raise ValueError('Unexpected personal copying cutoff')
        self.cutoff_ms = int(timestamp(until).timestamp() * 1000)
        self.deadline = monotonic() + (self.cutoff_ms - utc_ms()) / 1000
        self.stop = stop

    def remaining(self):
        return min(self.deadline - monotonic(), (self.cutoff_ms - utc_ms()) / 1000)

    def check_write(self):
        if self.stop.is_set() or self.remaining() <= WRITE_DRAIN_SECONDS:
            raise Skip('PERSONAL_WINDOW_CLOSING')


def private_config(path):
    details = path.stat()
    if path.is_symlink() or not path.is_file() or details.st_uid != os.getuid() or details.st_mode & 0o077:
        raise ValueError('Expected an owner-only operator config')
    config = json.loads(path.read_bytes())
    if (set(config) != {'sessionId', 'publicWallet', 'writerService', 'issuerService'}
            or str(UUID(config['sessionId'])) != config['sessionId'] or config['publicWallet'] not in WALLETS
            or config['writerService'] == config['issuerService']
            or any(re.fullmatch(r'personal_[a-z0-9_]{1,50}', config[k]) is None
                   for k in ('writerService', 'issuerService'))):
        raise ValueError('Invalid personal operator config')
    return config


def report(item):
    # Source proof and auth data remain outside stdout. Report only fixed fields.
    row = {key: item[key] for key in ('stage', 'status', 'reason') if key in item}
    if 'reason' in row and (not isinstance(row['reason'], str) or not re.fullmatch('[A-Z_0-9]{1,100}', row['reason'])):
        row['reason'] = 'CHECK_REFUSED'
    print(json.dumps(row, separators=(',', ':')), flush=True)


def advance(transport, scope, stop, deadline):
    while monotonic() < deadline and not stop.is_set():
        try:
            transport.advance_idle(scope)
        except (OSError, TimeoutError, Skip) as error:
            report({'stage': 'personal-range', 'reason': getattr(error, 'reason', 'READ_UNAVAILABLE')})
        stop.wait(2)


def run(args):
    stop = Event()
    window = CopyWindow(args.until, stop) if args.until is not None else None
    if window is not None and window.remaining() <= WRITE_DRAIN_SECONDS:
        report({'stage': 'personal-window', 'status': 'closed'})
        return 4
    config = private_config(args.config)
    transport = PgTransport(BoundedRPC(), config['writerService'], config['issuerService'], window)
    cursor = transport.cursor(config['sessionId'])
    wallet, budget = config['publicWallet'], exact(cursor['fixedBudget'])
    if (cursor['sessionId'], cursor['wallet'], budget) != (config['sessionId'], wallet, 20):
        raise ValueError('Personal enrollment mismatch')
    scope = FollowScope(cursor['sessionId'], cursor['streamId'], cursor['settingsId'],
                        wallet, int(timestamp(cursor['boundAt']).timestamp() * 1000), budget)
    if args.lookup:
        row = transport.lookup(scope, {'executionId': args.lookup})
        report({'stage': 'personal-lookup', 'status': 'recorded' if row else 'unresolved'})
        return 0 if row else 3
    transport.scoped(scope, cursor)
    start = cursor['personalStart']
    if start and int(start['number']) - int(cursor['checkpoint']['number']) > 64:
        report({'stage': 'personal-scope-preflight', 'status': 'blocked_historical_gap'})
        return 4
    if args.check:
        report({'stage': 'personal-scope-preflight', 'status': 'pass'})
        return 0
    for name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(name, lambda *_: stop.set())
    lock_path = args.config.parent / (scope.session_id + '.worker.lock')
    with os.fdopen(os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        deadline = window.deadline if window is not None else monotonic() + args.seconds
        adapter = SessionCollectorAdapter(scope, transport)
        failures = []
        with ThreadPoolExecutor(3) as pool:
            workers = [pool.submit(fn, adapter, wallet, stop, deadline, report, buy_budget=budget,
                                   start_ms=scope.started_at_ms) for fn in (run_polymarket, run_makers)]
            workers.append(pool.submit(advance, transport, scope, stop, deadline))
            if window is None:
                wait(workers, return_when=FIRST_COMPLETED)
                ended_early = monotonic() + 1 < deadline and not stop.is_set()
            else:
                while not stop.is_set() and window.remaining() > 0:
                    done, _ = wait(workers, timeout=min(1, max(0, window.remaining())), return_when=FIRST_COMPLETED)
                    if done:
                        break
                ended_early = window.remaining() > 1 and not stop.is_set()
            stop.set()
            for worker in workers:
                try:
                    worker.result()
                except Exception as error:
                    failures.append(error)
        if ended_early and not failures:
            failures.append(RuntimeError('A personal source worker stopped early'))
        unknown = next((error for error in failures if isinstance(error, UnresolvedResult)), None)
        if window is not None:
            status = 'reconciliation_required' if unknown else 'source_unavailable' if failures else 'stopped'
            if unknown:
                report_unknown(unknown)
            elif failures and all(isinstance(error, IdleIngestCanceled) for error in failures):
                print(json.dumps({'stage': 'personal-ingest', 'status': 'canceled_before_commit',
                                  'operationId': failures[0].args[0], 'sqlstate': '57014'}), flush=True)
                status = 'stopped'
            transport.finish(scope, status, window.cutoff_ms)
            report({'stage': 'personal-window', 'status': status})
            if unknown:
                return 3
        if failures:
            raise unknown or failures[0]
    return 0


def report_unknown(error):
    if error.kind == 'purchase':
        details = {'stage': 'personal-commit', 'executionId': error.args[0]}
    else:
        details = {'stage': 'personal-' + error.kind, 'operationId': error.args[0]}
    print(json.dumps({'status': 'unresolved', **details}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--lookup')
    mode.add_argument('--seconds', type=int)
    mode.add_argument('--until', choices=[APPROVED_UNTIL])
    args = parser.parse_args()
    if args.lookup is not None and not re.fullmatch('[0-9a-f]{64}', args.lookup):
        parser.error('Invalid original execution key')
    if args.seconds is not None and not 15 <= args.seconds <= 900:
        parser.error('This trial must run between 15 and 900 seconds')
    try:
        return run(args)
    except UnresolvedResult as error:
        report_unknown(error)
        return 3
    except Exception as error:
        row = {'stage': 'personal-worker', 'status': 'stopped', 'type': type(error).__name__}
        state = getattr(error, 'sqlstate', None)
        if isinstance(state, str) and re.fullmatch('[A-Z0-9]{5}', state):
            row['sqlstate'] = state
        print(json.dumps(row), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
