"""Identify BUY events in the closed Polygon spool and publish to existing session queues."""
import argparse
from contextlib import closing, contextmanager
import fcntl
import json
from pathlib import Path
import socket
import sqlite3
from time import sleep

from psycopg import InterfaceError, OperationalError
from psycopg.types.json import Jsonb

from closed_polygon_ingress import BATCH_BLOCKS, spool_connection, wake_path
from closed_polygon_source import connection
from personal_range import timestamp, utc_ms, wire_time
from personal_worker import private_config
from polygon_queue_wakeup import SOURCE_READY


def dispatchable(row, wallet):
    number, encoded_header, encoded_logs, received_ms = row
    header, logs = json.loads(encoded_header), json.loads(encoded_logs)
    occurred_ms = int(header['timestampSeconds']) * 1000
    if str(number) != header['number'] or occurred_ms > received_ms + 5000:
        raise ValueError('Bad Polygon spool header or clock')
    events = []
    for log in sorted(logs, key=lambda value: int(value['logIndex'])):
        if log['side'] != 'BUY' or log['owner'] != wallet:
            continue
        index = int(log['logIndex'])
        if (log['blockHash'], log['blockNumber']) != (header['hash'], header['number']):
            raise ValueError('Bad Polygon spool log identity')
        events.append({
            'logIndex': index,
            'executionKey': f"137:{log['transactionHash']}:{index}",
            'occurredAt': wire_time(occurred_ms),
            'firstReceivedAt': wire_time(received_ms),
            'expiresAt': wire_time(occurred_ms + 30_000),
            'payload': {'kind': 'polygon-finalized-buy', 'header': header, 'log': log},
        })
    return {'header': header, 'events': events}


@contextmanager
def wake_receiver(spool):
    path = wake_path(spool)
    with spool.with_suffix('.lock').open('a') as lock, socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as wake:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path.unlink(missing_ok=True)
        wake.bind(str(path))
        wake.settimeout(0.4)
        try:
            yield wake
        finally:
            path.unlink(missing_ok=True)


def checkpoint(config):
    with connection(config) as db:
        current, = db.execute('SELECT demo_delivery.closed_trader_checkpoint(%s)', (config['sessionId'],)).fetchone()
    if not current or (current['wallet'], current['runId']) != (config['publicWallet'], config['runId']):
        raise ValueError('Polygon dispatcher scope mismatch')
    return int(current['height'])


def deliver(db, config, rows):
    batch = [dispatchable(row, config['publicWallet']) for row in rows]
    result, = db.execute('SELECT demo_delivery.dispatch_closed_trader_range(%s,%s)',
                         (config['sessionId'], Jsonb(batch))).fetchone()
    if int(result['height']) != rows[-1][0]:
        raise ValueError('Polygon dispatcher did not advance to the submitted block')
    if result['enqueued']:
        db.execute("SELECT pg_notify(%s,'')", (SOURCE_READY,))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    parser.add_argument('spool', type=Path)
    parser.add_argument('--until', required=True)
    args = parser.parse_args()
    config = private_config(args.config, closed=True)
    cutoff = int(timestamp(args.until).timestamp() * 1000)
    while not args.spool.is_file() and utc_ms() < cutoff:
        sleep(0.1)
    with closing(spool_connection(args.spool)) as spool, wake_receiver(args.spool) as wake:
        height = None
        while utc_ms() < cutoff:
            try:
                if height is None:
                    height = checkpoint(config)
                rows = spool.execute('SELECT height,header,logs,received_ms FROM ingress_blocks '
                                     'WHERE height>? ORDER BY height LIMIT ?', (height, BATCH_BLOCKS)).fetchall()
                if rows:
                    with connection(config) as db:
                        result = deliver(db, config, rows)
                    height = int(result['height'])
                    print(json.dumps({'stage': 'polygon-trader-range', 'fromBlock': rows[0][0],
                                      **result}), flush=True)
                else:
                    try:
                        wake.recv(1)
                    except TimeoutError:
                        pass
            except (OperationalError, InterfaceError, sqlite3.OperationalError) as error:
                # After a lost commit reply, re-read the DB cursor before consuming again.
                height = None
                print(json.dumps({'stage': 'polygon-trader-retry', 'error': type(error).__name__}), flush=True)
                sleep(0.2)


if __name__ == '__main__':
    main()
