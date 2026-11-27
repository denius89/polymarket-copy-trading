"""Consume the isolated queue's canonical fills without venue trade discovery."""
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import json
import os
from time import monotonic, monotonic_ns
from types import SimpleNamespace

from book_engine import GateSkip
from collectors import PolymarketWriter
from hybrid_book import HybridBookGate
from maker_collector import fee_for_copy
from maker_core import identity as maker_identity
from market_policy import prepare_market, verify_observed_fee
from personal_pg import read_call
from personal_range import header, utc_ms
from personal_source import market_binding, normalize_fill
from polygon_deferred_frames import QUEUE_WAIT_REASONS
from resolver import FILL, MATCH, Resolved, Skip, decode, hex_id, q, sha, uint
from route import execute_resolved
import rtds_operator as poly
import source

SOURCE = 'polymarket-polygon-finalized-queue-v1'
READ_HEAD = 'SELECT demo_delivery.read_polygon_buy_head(%s::uuid,%s::bigint)'


def match_fill(log, receipt, market):
    """Recover the exact queued fill, preserving existing Maker/Taker identities."""
    index = int(log['logIndex'])
    logs = receipt['logs']
    if not isinstance(logs, list) or not 1 <= len(logs) <= 4096:
        raise Skip('POLYGON_DIRECT_RECEIPT_LOGS')
    candidates = [(ordinal, row) for ordinal, row in enumerate(logs) if uint(row['logIndex']) == index]
    if len(candidates) != 1 or sha(receipt) != log['receiptSha256']:
        raise Skip('POLYGON_DIRECT_RECEIPT_IDENTITY')
    ordinal, fill = candidates[0]
    if normalize_fill(fill, receipt, log['owner']) != log or log['side'] != 'BUY':
        raise Skip('POLYGON_DIRECT_FILL_IDENTITY')
    exchange = hex_id(fill['address'], 20)
    topics, words = decode(fill, 7, 4)
    if topics[0] != FILL or not 0 < words[2] < words[3]:
        raise Skip('POLYGON_DIRECT_FILL_AMOUNTS')
    matches = []
    for number, row in enumerate(logs):
        if row['address'].lower() == exchange and row['topics'] and row['topics'][0].lower() == MATCH:
            mt, mw = decode(row, 4, 3)
            if mt[1:3] == topics[1:3]:
                if mw != words[:4] or number <= ordinal:
                    raise Skip('POLYGON_DIRECT_TAKER_MISMATCH')
                matches.append((number, uint(row['logIndex'])))
    if len(matches) > 1:
        raise Skip('POLYGON_DIRECT_TAKER_AMBIGUOUS')
    role = 'taker' if matches else 'maker'
    if matches:
        ordinal, index = matches[0]
        # The established Taker identity must name one exact OrderFilled.
        duplicates = 0
        for row in logs[:ordinal]:
            if row['address'].lower() == exchange and row['topics'] and row['topics'][0].lower() == FILL:
                ft, fw = decode(row, 7, 4)
                duplicates += ft[1:3] == topics[1:3] and fw[:4] == words[:4]
        if duplicates != 1:
            raise Skip('POLYGON_DIRECT_TAKER_FILL_AMBIGUOUS')
    return dict(chainId=137, exchange=exchange, transactionHash=log['transactionHash'],
                receiptOrdinal=ordinal, logIndex=index, wallet=log['owner'], marketId=market,
                outcomeId=log['tokenId'], side='BUY', quantity=q(Fraction(words[3], 1_000_000)),
                gross=q(Fraction(words[2], 1_000_000)), matchingCount=1, orderHash=topics[1], role=role)


def identity(match):
    if match['role'] == 'maker':
        return maker_identity(match)
    eid = sha(['polygon-orders-matched-v1', 137, match['exchange'], match['transactionHash'],
               match['receiptOrdinal'], match['wallet'], match['marketId'], match['outcomeId'], 'BUY'])
    return eid, sha([eid, match['quantity'], match['gross']])


def checked_headers(required, canonical, finalized):
    block, head = header(canonical), header(finalized)
    if block != required or int(head['number']) < int(block['number']) or (
            head['number'] == block['number'] and head['hash'] != block['hash']):
        raise Skip('POLYGON_DIRECT_FINALITY')
    return block, head


def validate(event, at_ms):
    wire = event['venueReceipt']
    m, f = wire['match'], wire['finality']
    source_at, first_at = event['signalAtMs'], event['firstSeenMs']
    if (wire['source'] != SOURCE or event['venue'] != 'polymarket' or event['side'] != 'BUY'
            or (m['marketId'], m['outcomeId'], m['side']) != (event['marketId'], event['outcomeId'], 'BUY')
            or (event['executionId'], event['fingerprint']) != identity(m)
            or not source_at == f['blockTimestampMs'] <= first_at <= f['checkedAtMs'] <= at_ms
            or at_ms - source_at > 30_000 or f['receiptStatus'] != 1
            or f['blockHash'] != f['canonicalBlockHash'] or f['finalizedBlockNumber'] < f['blockNumber']
            or (f['finalizedBlockNumber'] == f['blockNumber']
                and f['finalizedBlockHash'] != f['blockHash'])):
        raise Skip('POLYGON_DIRECT_PROVENANCE')
    if len(wire['evidenceRef']) != 64:
        raise Skip('POLYGON_DIRECT_PROOF_IDENTITY')


def validate_estimate(event, estimate):
    wire = event['venueReceipt']
    f = wire['finality']
    proof, book = estimate['evidence']['sourceProof'], estimate['book']
    block, head = checked_headers(proof['header'], proof['canonicalBlock'], proof['finalizedBlock'])
    binding = proof['marketBinding']
    if ((binding['conditionId'], binding['tokenId']) != (event['marketId'], event['outcomeId'])
            or not event['signalAtMs'] <= proof['publishedAtMs'] <= event['firstSeenMs']
            or sha(proof) != wire['evidenceRef'] or sha(proof['receipt']) != f['receiptSha256']
            or match_fill(proof['log'], proof['receipt'], event['marketId']) != wire['match']
            or (proof['log']['blockHash'], int(proof['log']['blockNumber'])) != (block['hash'], int(block['number']))
            or (block['hash'], int(block['number']), int(block['timestampSeconds']) * 1000)
                != (f['blockHash'], f['blockNumber'], f['blockTimestampMs'])
            or (head['hash'], int(head['number'])) != (f['finalizedBlockHash'], f['finalizedBlockNumber'])
            or (book['venue'], book['market'], book['token']) != ('polymarket', event['marketId'], event['outcomeId'])
            or book['receivedAtMs'] < f['checkedAtMs']
            or int(book['receivedMonotonicNs']) <= int(f['checkedMonotonicNs'])):
        raise Skip('POLYGON_DIRECT_ESTIMATE_PROOF')


def build_resolution(job, rpc, binding, first_at, first_ns):
    packet = job['payload']
    log, required = packet['log'], packet['header']
    market = binding['conditionId']
    block_at = int(required['timestampSeconds']) * 1000
    deadline = monotonic() + min(3, (block_at + 30_000 - utc_ms()) / 1000)

    def read(method, params):
        left = deadline - monotonic()
        if left <= 0:
            raise Skip('SIGNAL_EXPIRED')
        return rpc(method, params, left)

    finalized = read('eth_getBlockByNumber', ['finalized', False])
    receipt = read('eth_getTransactionReceipt', [log['transactionHash']])
    canonical = read('eth_getBlockByNumber', [hex(int(required['number'])), False])
    block, head = checked_headers(required, canonical, finalized)
    match = match_fill(log, receipt, market)
    checked_at, checked_ns = utc_ms(), monotonic_ns()
    proof = dict(log=log, header=required, receipt=receipt, canonicalBlock=canonical, finalizedBlock=finalized,
                 marketBinding=binding, signalId=job['signalId'], publishedAtMs=job['publishedAtMs'])
    eid, fp = identity(match)
    finality = dict(receiptStatus=1, receiptSha256=log['receiptSha256'], blockNumber=int(block['number']),
                    blockHash=block['hash'], blockTimestampMs=block_at, canonicalBlockHash=block['hash'],
                    finalizedBlockNumber=int(head['number']), finalizedBlockHash=head['hash'],
                    checkedAtMs=checked_at, checkedMonotonicNs=str(checked_ns), rpcEvidenceRef=poly.RPC)
    event = dict(executionId=eid, fingerprint=fp, venue='polymarket', marketId=market, outcomeId=log['tokenId'],
                 side='BUY', signalAtMs=block_at, firstSeenMs=first_at, chain=None,
                 venueReceipt=dict(source=SOURCE, evidenceRef=sha(proof), match=match, finality=finality))
    validate(event, checked_at)
    return Resolved(event, first_ns, first_at - block_at, sha(event), proof)


def run_direct_polygon(adapter, wallet, stop, deadline, report, *, buy_budget, start_ms=0):
    transport = adapter.transport
    wake = transport.queue_wake
    rpc, registry = poly.BoundedRPC(), poly.Registry()
    socket = os.environ.get('CCT_CLOSED_SHARED_BOOK_SOCKET')
    if socket:
        from closed_shared_polygon_book import SharedPolygonBookGate
        gate = SharedPolygonBookGate(socket, os.environ['CCT_CLOSED_SHARED_BOOK_PARTICIPANT'])
        books = None
        load_parameters = gate.prepare_market
    else:
        gate = HybridBookGate()
        books = poly.ActiveBook(gate, deadline)
        load_parameters = prepare_market
    seen = 0
    prepared = None
    try:
        while not stop.is_set() and monotonic() < deadline:
            generation = wake.generation
            with transport.connection(transport.writer) as db:
                job = read_call(db, READ_HEAD, adapter.scope.session_id, seen)
            if job is None:
                wake.wait(generation, 0.5)
                continue
            signal = int(job['signalId'])
            packet = job['payload']
            log = packet['log']
            if log['owner'] != wallet or int(packet['header']['timestampSeconds']) * 1000 < start_ms:
                raise RuntimeError('Direct Polygon job does not match active scope')
            writer = None
            try:
                if prepared is None or prepared[0] != signal:
                    first_at, first_ns = utc_ms(), monotonic_ns()
                    binding = market_binding({'outcomeId': log['tokenId']}, 2, discover=True)
                    slug = binding['slug']
                    if not isinstance(slug, str) or not poly.SLUG.fullmatch(slug):
                        raise Skip('POLYGON_DIRECT_MARKET_SLUG')
                    market = source.Market('polymarket', binding['conditionId'], log['tokenId'], wallet, slug)
                    if books is not None:
                        books.prepare(market)
                    with ThreadPoolExecutor(1) as pool:
                        parameters = pool.submit(load_parameters, market)
                        resolved = build_resolution(job, rpc, binding, first_at, first_ns)
                        (delay, delay_ref, policy, baseline, exchange), _ = parameters.result()
                    if resolved.event['venueReceipt']['match']['role'] == 'maker':
                        fee_for_copy(resolved, policy, exchange)
                    else:
                        verify_observed_fee(resolved, policy, exchange)
                    if books is None:
                        gate.configure(market, policy, baseline)
                    else:
                        books.follow(market, policy, baseline)
                    prepared = (signal, resolved, market, policy, delay, delay_ref)
                    print(json.dumps({'stage': 'polygon-direct-signal', 'signalId': signal,
                                      'publishedMs': job['publishedAtMs'] - resolved.event['signalAtMs'],
                                      'firstSeenMs': first_at - resolved.event['signalAtMs'],
                                      'verifiedMs': (monotonic_ns() - first_ns) // 1_000_000,
                                      'role': resolved.event['venueReceipt']['match']['role']}), flush=True)
                _, resolved, market, policy, delay, delay_ref = prepared
                frame = SimpleNamespace(wallet=wallet, slug=market.slug, event_key=resolved.event['executionId'])
                writer = PolymarketWriter(adapter, frame, registry)
                result = execute_resolved(writer, validate, None, gate, resolved,
                                          session_id='polymarket', owner_id='shared-demo', command_id='polygon-direct',
                                          policy=policy, delay_ms=delay, delay_evidence=delay_ref,
                                          budget=buy_budget, wait=stop.wait)
            except (Skip, GateSkip, ValueError, OSError, KeyError, TypeError, ArithmeticError) as error:
                reason = getattr(error, 'reason', type(error).__name__)
                if reason in QUEUE_WAIT_REASONS:
                    wake.wait(generation, 0.25)
                    continue
                if writer is not None and reason in ('BOOK_AGE', 'BOOK_DEPTH'):
                    writer.finish_book_refusal(reason)
                print(json.dumps({'stage': 'polygon-direct-skip', 'signalId': signal, 'reason': reason,
                                  'bookTiming': getattr(error, 'book_timing', None)}), flush=True)
            else:
                if result['status'] == 'recorded':
                    report({'stage': 'app-venue-admission', 'venue': 'polymarket',
                            'source': 'finalized-polygon-queue', 'status': 'recorded'})
            finally:
                gate.finish()
            seen, prepared = signal, None
    finally:
        if books is not None:
            books.close()
