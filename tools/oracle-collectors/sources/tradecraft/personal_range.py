"""Build the existing canonical-range ingest envelope for one personal stream."""
from datetime import datetime, timezone
from time import monotonic, time_ns

from personal_source import normalize_fill
from resolver import EXCHANGES, FILL, Skip, hex_id, sha, uint


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def utc_ms():
    return time_ns() // 1_000_000


def wire_time(ms):
    return datetime.fromtimestamp(ms // 1000, timezone.utc).replace(
        microsecond=(ms % 1000) * 1000).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def header(block):
    return dict(number=str(uint(block['number'])), hash=hex_id(block['hash'], 32),
                parentHash=hex_id(block['parentHash'], 32), timestampSeconds=str(uint(block['timestamp'])))


def checkpoint(block):
    return {key: block[key] for key in ('number', 'hash')}


def identity(log):
    return log['transactionHash'], log['logIndex']


def read_range(rpc, cursor, *, target_number=None, deadline):
    """Check the whole finalized prefix. The trade receipt never substitutes for eth_getLogs."""
    def read(method, params):
        left = deadline - monotonic()
        if left <= 0:
            raise Skip('PERSONAL_RANGE_TIME')
        return rpc(method, params, left)

    def block_at(number):
        block = header(read('eth_getBlockByNumber', [hex(number), False]))
        if int(block['number']) != number:
            raise Skip('PERSONAL_RANGE_HEADER')
        return block

    if uint(read('eth_chainId', [])) != 137:
        raise Skip('PERSONAL_RANGE_CHAIN')
    base, previous = cursor['baseline'], cursor['checkpoint']
    if block_at(int(base['number'])) != base:
        raise Skip('PERSONAL_BASELINE_CHANGED')
    if checkpoint(block_at(int(previous['number']))) != previous:
        raise Skip('PERSONAL_CHECKPOINT_CHANGED')
    final = header(read('eth_getBlockByNumber', ['finalized', False]))
    start = int(previous['number']) + 1
    end = target_number if target_number is not None else min(int(final['number']), start + 63)
    if target_number is not None and (end < start or end > int(final['number']) or end >= start + 64):
        raise Skip('PERSONAL_TARGET_OUTSIDE_RANGE')
    if int(final['number']) < start - 1:
        if target_number is None and previous == checkpoint(base):
            return None
        raise Skip('PERSONAL_FINALITY_REGRESSED')
    if end < start:
        return None
    owner = '0x' + '0' * 24 + cursor['wallet'][2:]
    # Fetch the bounded log set first. For idle progress a fresh BUY holds the
    # entire block for its RTDS/maker assessment instead of advancing past it.
    logs, fetched = {}, {}
    for exchange in sorted(EXCHANGES):
        logs_found = read('eth_getLogs', [dict(address=exchange, fromBlock=hex(start), toBlock=hex(end),
                                               topics=[FILL, None, owner])])
        if not isinstance(logs_found, list) or len(logs) + len(logs_found) > 128:
            raise Skip('PERSONAL_RANGE_LOG_LIMIT')
        for raw in logs_found:
            if hex_id(raw['address'], 20) != exchange:
                raise Skip('PERSONAL_RANGE_LOG_ADDRESS')
            tx = hex_id(raw['transactionHash'], 32)
            if tx not in fetched:
                fetched[tx] = read('eth_getTransactionReceipt', [tx])
            row = normalize_fill(raw, fetched[tx], cursor['wallet'])
            key = identity(row)
            if key in logs or not start <= int(row['blockNumber']) <= end:
                raise Skip('PERSONAL_RANGE_LOG_IDENTITY')
            logs[key] = row
    headers, chain = {}, previous
    for n in range(start, end + 1):
        block = final if n == int(final['number']) else block_at(n)
        if block['parentHash'] != chain['hash']:
            raise Skip('PERSONAL_RANGE_PARENT')
        headers[n], chain = block, block
    if block_at(end) != headers[end]:
        raise Skip('PERSONAL_RANGE_END_CHANGED')
    personal_start = cursor['personalStart']
    if personal_start:
        boundary = headers.get(int(personal_start['number']))
        if boundary and boundary['hash'] != personal_start['hash']:
            raise Skip('PERSONAL_START_ANCHOR_CHANGED')
    for row in logs.values():
        if row['blockHash'] != headers[int(row['blockNumber'])]['hash']:
            raise Skip('PERSONAL_RANGE_LOG_BLOCK')
    return headers, sorted(logs.values(), key=lambda row: (int(row['blockNumber']), int(row['logIndex'])))


def ingest_envelope(cursor, chain_range, operation_id, *, quote=None, binding=None, now_ms):
    headers, logs = chain_range
    target = quote['normalizedLog'] if quote else None
    armed_at = timestamp(cursor['armedAt']).timestamp()
    personal_start = cursor['personalStart']
    if target and personal_start and int(target['blockNumber']) <= int(personal_start['number']):
        raise Skip('PERSONAL_BEFORE_ACTIVATION')
    evaluations = []
    for log in logs:
        number = int(log['blockNumber'])
        block_time = int(headers[number]['timestampSeconds'])
        if block_time <= armed_at:
            continue
        if personal_start and number <= int(personal_start['number']):
            evidence = dict(schemaVersion='paper-buy-evidence-v1', kind='skip',
                            reason='before_personal_activation',
                            evidenceSha256=personal_start['evidenceSha256'], binding=None)
        elif log == target:
            evidence = dict(schemaVersion='paper-buy-pending-v1', kind='candidate',
                            admissionId=quote['reserveId'], binding=binding,
                            evidenceSha256=quote['event']['venueReceipt']['evidenceRef'])
        elif log['side'] == 'SELL':
            evidence = dict(schemaVersion='paper-buy-evidence-v1', kind='skip',
                            reason='not_buy', evidenceSha256=sha(log), binding=None)
        else:
            # A chain timestamp alone cannot establish the time of a trade signal.
            # A separate verified evaluation is required before this BUY is closed.
            if quote:
                raise Skip('PERSONAL_RANGE_UNCLASSIFIED_BUY')
            headers = {k: v for k, v in headers.items() if k < number}
            logs = [entry for entry in logs if int(entry['blockNumber']) < number]
            evaluations = [value for value in evaluations if value['blockNumber'] < number]
            break
        evaluations.append(dict(transactionHash=log['transactionHash'], logIndex=log['logIndex'],
                                evidence=evidence, blockNumber=number))
    if not headers:
        return None
    if target and not any(entry['evidence']['kind'] == 'candidate' for entry in evaluations):
        raise Skip('PERSONAL_TARGET_PREARM')
    for value in evaluations:
        del value['blockNumber']
    batch = dict(runId=cursor['runId'], operationId=operation_id, sessionId=cursor['sessionId'],
                 previous=cursor['checkpoint'], baselineCanonicalHash=cursor['baseline']['hash'],
                 finalized=next(reversed(headers.values())), headers=list(headers.values()),
                 observedAt=wire_time(now_ms), logs=logs)
    batch['evidenceSha256'] = sha(batch)
    return dict(session_id=cursor['sessionId'], request=dict(
        ingest=batch, expectedSnapshotVersion=cursor['version'], evaluations=evaluations))
