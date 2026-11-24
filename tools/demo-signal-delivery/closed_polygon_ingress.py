"""Durably spool the closed pilot's finalized Polygon RPC feed without session credentials."""
import argparse
from collections import defaultdict
from contextlib import closing
import json
from pathlib import Path
import re
import socket
import sqlite3
from time import monotonic, sleep

from personal_range import read_idle_range, timestamp, utc_ms
from resolver import Skip
from rtds_operator import BoundedRPC, HISTORY_RPC

MAX_BLOCKS = 4096
BATCH_BLOCKS = 16
MAX_BYTES = 262144


def wake_path(path):
    return path.with_suffix('.sock')


def spool_connection(path, *, create=False):
    if not path.is_absolute() or path.parent.stat().st_mode & 0o077 or path.is_symlink():
        raise ValueError('Expected a private run-local spool')
    return sqlite3.connect(path.as_uri() + ('?mode=rwc' if create else '?mode=rw'), uri=True, timeout=2)


def initialize(db, wallet, anchor):
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    with db:
        db.execute('''CREATE TABLE IF NOT EXISTS ingress_cursor (
            singleton INTEGER PRIMARY KEY CHECK (singleton=1), wallet TEXT NOT NULL,
            anchor_hash TEXT NOT NULL, anchor_height INTEGER NOT NULL,
            height INTEGER NOT NULL, hash TEXT NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS ingress_blocks (
            height INTEGER PRIMARY KEY, header TEXT NOT NULL, logs TEXT NOT NULL,
            received_ms INTEGER NOT NULL)''')
        seed = int(anchor['number'])
        db.execute('INSERT OR IGNORE INTO ingress_cursor VALUES(1,?,?,?,?,?)',
                   (wallet, anchor['hash'], seed, seed, anchor['hash']))
        actual = db.execute('SELECT wallet,anchor_hash,anchor_height FROM ingress_cursor').fetchone()
        if actual != (wallet, anchor['hash'], seed):
            raise ValueError('Spool belongs to a different Polygon feed')


def anchor_header(path):
    with path.open() as handle:
        evidence = json.load(handle)
    head, parent = evidence['head'], evidence['parent']
    for block in (head, parent):
        if (set(block) != {'number', 'hash', 'parentHash', 'timestampSeconds'}
                or not all(re.fullmatch(r'0|[1-9][0-9]{0,12}', block[k]) for k in ('number', 'timestampSeconds'))
                or not all(re.fullmatch(r'0x[0-9a-f]{64}', block[k]) for k in ('hash', 'parentHash'))):
            raise ValueError('Invalid finalized Polygon anchor')
    if (int(head['number']) != int(parent['number']) + 1 or head['parentHash'] != parent['hash']
            or len(set(evidence['endpoints'])) < 2):
        raise ValueError('Finalized Polygon witnesses disagree')
    return head


def append(db, chain_range, before, received_ms):
    headers, logs = chain_range
    grouped = defaultdict(list)
    for event in logs:
        number = int(event['blockNumber'])
        if number not in headers:
            raise ValueError('Polygon log outside its verified range')
        grouped[number].append(event)
    rows = []
    current = before
    for number, header in headers.items():
        if number != current[0] + 1 or header['parentHash'] != current[1]:
            raise ValueError('Polygon spool checkpoint changed')
        payload = json.dumps(grouped[number], separators=(',', ':'))
        if len(payload.encode()) > MAX_BYTES:
            raise ValueError('Polygon spool block too large')
        rows.append((number, json.dumps(header, separators=(',', ':')), payload, received_ms))
        current = number, header['hash']
    with db:
        db.execute('BEGIN IMMEDIATE')
        checkpoint = db.execute('SELECT height,hash,anchor_height FROM ingress_cursor').fetchone()
        if checkpoint[:2] != before or current[0] - checkpoint[2] > MAX_BLOCKS:
            raise ValueError('Polygon spool checkpoint changed or scope exhausted')
        db.executemany('INSERT INTO ingress_blocks VALUES(?,?,?,?)', rows)
        db.execute('UPDATE ingress_cursor SET height=?,hash=? WHERE singleton=1', current)
    return current[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('anchor', type=Path)
    parser.add_argument('spool', type=Path)
    parser.add_argument('--until', required=True)
    parser.add_argument('--wallet', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'0x[0-9a-f]{40}', args.wallet):
        raise ValueError('Invalid watched Polygon wallet')
    anchor = anchor_header(args.anchor)
    cutoff = int(timestamp(args.until).timestamp() * 1000)
    primary, backup = BoundedRPC(), BoundedRPC(HISTORY_RPC)
    with closing(spool_connection(args.spool, create=True)) as db, socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as wake:
        initialize(db, args.wallet, anchor)
        wake.setblocking(False)
        while utc_ms() < cutoff:
            started = monotonic()
            before = db.execute('SELECT height,hash FROM ingress_cursor').fetchone()
            scope = {'wallet': args.wallet, 'baseline': anchor, 'personalStart': None,
                     'checkpoint': {'number': str(before[0]), 'hash': before[1]}}
            finality = {}
            try:
                chain_range, _, _ = read_idle_range(primary, backup, scope, deadline=started + 8,
                                                    max_blocks=BATCH_BLOCKS, finality_observation=finality)
            except (OSError, Skip) as error:
                print(json.dumps({'stage': 'polygon-ingress-retry', 'error': type(error).__name__}), flush=True)
            else:
                if chain_range is not None:
                    height = append(db, chain_range, before, utc_ms())
                    print(json.dumps({'stage': 'polygon-ingress-range', 'height': height,
                                      'observations': len(chain_range[1]),
                                      'finalizedHead': finality['head']}), flush=True)
                    try:
                        wake.sendto(b'1', str(wake_path(args.spool)))
                    except (FileNotFoundError, ConnectionRefusedError, BlockingIOError):
                        pass  # The dispatcher also reads the durable spool on its timeout.
            sleep(max(0, min(max(0.1, 1.0 - (monotonic() - started)), (cutoff - utc_ms()) / 1000)))


if __name__ == '__main__':
    main()
