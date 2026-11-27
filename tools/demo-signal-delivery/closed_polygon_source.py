"""Publish finalized Polygon ranges from the isolated personal collector's source."""
import argparse
from collections import defaultdict
from contextlib import contextmanager
import json
from pathlib import Path
from time import monotonic, sleep

from psycopg import InterfaceError, OperationalError, connect
from psycopg.errors import SerializationFailure
from psycopg.types.json import Jsonb

from personal_range import read_idle_range, timestamp, utc_ms, wire_time
from personal_worker import ClosedPgTransport, bound_scope, closed_services, private_config
from polygon_queue_wakeup import SOURCE_READY
from resolver import Skip
from rtds_operator import BoundedRPC, HISTORY_RPC


def block_batch(chain_range, received_at):
    headers, logs = chain_range
    grouped = defaultdict(list)
    for log in logs:
        if log['side'] == 'BUY':
            header = headers[int(log['blockNumber'])]
            occurred_at = int(header['timestampSeconds']) * 1000
            if occurred_at > received_at + 5000:
                raise ValueError('Polygon source clock skew')
            grouped[int(log['blockNumber'])].append({
                'logIndex': int(log['logIndex']),
                'executionKey': f"137:{log['transactionHash']}:{log['logIndex']}",
                'occurredAt': wire_time(occurred_at),
                'firstReceivedAt': wire_time(received_at),
                'expiresAt': wire_time(occurred_at + 30_000),
                'payload': {'kind': 'polygon-finalized-buy', 'header': header, 'log': log},
            })
    return [{'header': header, 'events': grouped[number]} for number, header in headers.items()]


@contextmanager
def connection(config):
    service = config['writerService']
    profile = closed_services(config)[service]
    with connect(service=service, connect_timeout=2, options='-c statement_timeout=5000 -c lock_timeout=1000') as db:
        identity = db.execute(
            'SELECT host(inet_server_addr()), inet_server_port(), current_database(), session_user'
        ).fetchone()
        address = config.get('serverAddress')
        port = int(profile['port']) if address else None
        if (identity != (address, port, profile['dbname'], profile['user'])
                or (db.info.host, db.info.port) != (profile['host'], int(profile['port']))):
            raise ValueError('Isolated PostgreSQL connection identity mismatch')
        yield db


def cycle(config, primary, backup, anchors, previous_finality):
    sid = config['sessionId']
    with connection(config) as db:
        scope, = db.execute('SELECT demo_delivery.closed_polygon_scope(%s)', (sid,)).fetchone()
    if not scope or (scope['wallet'], scope['runId']) != (config['publicWallet'], config['runId']):
        raise ValueError('Polygon queue scope mismatch')
    scope.update(anchors)

    started = monotonic()
    finality = {}
    try:
        chain_range, _, _ = read_idle_range(primary, backup, scope, deadline=started + 8, max_blocks=16,
                                            finality_observation=finality)
    except (KeyError, TypeError, ValueError):
        raise Skip('PERSONAL_RANGE_INVALID_PROVIDER_DATA') from None
    if chain_range is None:
        with connection(config) as db:
            completed, = db.execute('SELECT demo_delivery.reconcile_closed_polygon_results(%s,NULL,NULL)',
                                    (sid,)).fetchone()
        if completed:
            print(json.dumps({'stage': 'polygon-queue-recovered-outcomes', 'count': completed}), flush=True)
        return finality
    read_ms = round((monotonic() - started) * 1000)
    batches = block_batch(chain_range, utc_ms())
    started = monotonic()
    with connection(config) as db:
        receipt, _ = db.execute('''
            WITH published AS MATERIALIZED (
                SELECT demo_delivery.publish_closed_polygon_range(%s,%s) AS receipt
            )
            SELECT receipt, CASE WHEN (receipt->>'enqueued')::integer > 0
                                 THEN pg_notify(%s,'') END
            FROM published
        ''', (sid, Jsonb(batches), SOURCE_READY)).fetchone()
        completed, = db.execute('SELECT demo_delivery.reconcile_closed_polygon_results(%s,NULL,NULL)',
                                (sid,)).fetchone()
    publish_finished = monotonic()
    timing = {'stage': 'polygon-queue-range', 'fromBlock': int(scope['checkpoint']['number']) + 1,
              **receipt, 'reconciled': completed, 'readMs': read_ms,
              'commitMs': round((monotonic() - started) * 1000), 'finalizedHead': finality['head']}
    if receipt['enqueued']:
        timing['buyTiming'] = [
            buy_timing(batch['header'], finality, previous_finality, publish_finished)
            for batch in batches if batch['events']
        ]
    print(json.dumps(timing), flush=True)
    return finality


def buy_timing(block, finality, previous_finality, publish_finished):
    block_at = int(block['timestampSeconds']) * 1000
    observed = finality['observedAtMs']
    previous_read = None
    if (previous_finality is not None and previous_finality['usedBackup'] == finality['usedBackup']
            and previous_finality['head'] < int(block['number'])):
        previous_read = previous_finality['observedAtMs'] - block_at
    return {'block': block['number'], 'blockToObservedFinalityMs': observed - block_at,
            'blockToPreviousHeadReadMs': previous_read,
            'observedFinalityToPublishMs': round((publish_finished - finality['observedMono']) * 1000),
            'usedBackup': finality['usedBackup'], 'batchedAnchors': finality['batchedAnchors']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    parser.add_argument('--until', required=True)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    config = private_config(args.config, closed=True)
    cutoff = int(timestamp(args.until).timestamp() * 1000)
    primary, backup = BoundedRPC(), BoundedRPC(HISTORY_RPC)
    transport = ClosedPgTransport(primary, config, None)
    anchors = previous_finality = None
    while utc_ms() < cutoff:
        cycle_started = monotonic()
        pause = 3
        try:
            if anchors is None:
                cursor = transport.cursor(config['sessionId'], starting=True)
                transport.scoped(bound_scope(config, cursor, closed=True), cursor)
                anchors = {key: cursor.get(key) for key in ('personalStart', 'coverageGap')}
            previous_finality = cycle(config, primary, backup, anchors, previous_finality)
            pause = max(1, 3 - (monotonic() - cycle_started))
        except (OSError, Skip, OperationalError, InterfaceError, SerializationFailure) as error:
            print(json.dumps({'stage': 'polygon-queue-retry', 'error': type(error).__name__}), flush=True)
            if args.once:
                raise SystemExit(1) from None
        except Exception as error:
            print(json.dumps({'stage': 'polygon-queue-stopped', 'error': type(error).__name__}), flush=True)
            raise SystemExit(1) from None
        if args.once:
            return
        sleep(max(0, min(pause, (cutoff - utc_ms()) / 1000)))


if __name__ == '__main__':
    main()
