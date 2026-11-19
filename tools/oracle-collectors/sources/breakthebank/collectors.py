"""Read-only venue collectors for the existing shared demo writer."""
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
from queue import Empty, Queue
import threading
import time

import rtds_operator as polymarket
from book_engine import BookGate, GateSkip, q, quote
from hybrid_book import HybridBookGate
from pooled import Books
import source
import trader_limitless as limitless
from trader_address_probe import base_logs

BUYS = {'polymarket': q(10), 'limitless': q(10)}
SOURCE_ERRORS = (OSError, ValueError, KeyError, TypeError, ArithmeticError)


def estimate_metadata(venue, wallet, slug, event, policy):
    return {'venue': venue, 'wallet': wallet.lower(), 'slug': slug, 'condition': event['marketId'],
            'token': event['outcomeId'], 'marketTitle': policy['marketTitle'],
            'outcomeTitle': policy['outcomeTitle'], 'sourceTimestampMs': event['signalAtMs']}


class PolymarketWriter:
    def __init__(self, adapter, captured, registry):
        self.adapter, self.captured, self.registry = adapter, captured, registry

    def lookup_command(self, *args, event):
        return self.adapter.lookup_command(*args, event=event)

    def submit(self, db, session, owner, command, event, estimate, guard):
        policy = estimate['evidence']['policy']
        if policy['feeModel'] == 'polymarket-v2-single-match' and len(estimate['fills']) != 1:
            raise GateSkip('FEE_QUOTE_MULTIPLE_PRICE_LEVELS')
        metadata = estimate_metadata('polymarket', self.captured.wallet, self.captured.slug, event, policy)
        captured, registry = self.captured, self.registry

        @contextmanager
        def commit_locks():
            with guard.commit_lock, registry.lock:
                yield

        class CommitGuard:
            commit_lock = commit_locks()

            def __call__(self, expected, computed):
                with registry.lock:
                    if captured.event_key in registry.conflicts:
                        raise GateSkip(registry.conflicts[captured.event_key])
                    return guard(expected, computed)

        return self.adapter.bind(metadata).submit(db, session, owner, command, event, estimate, CommitGuard())


def run_polymarket(adapter, wallet, stop, deadline, report, *, buy_budget=polymarket.BUY_BUDGET, start_ms=0):
    gate, counts = HybridBookGate(), Counter()
    books = polymarket.ActiveBook(gate, deadline)
    registry, queue = polymarket.Registry(), adapter.source_queue(maxsize=12)
    armed_ms = max(start_ms, time.time_ns() // 1_000_000)
    halt = threading.Event()
    reader = threading.Thread(target=polymarket.read_rtds,
                              args=({wallet.lower()}, queue, halt, deadline, counts, registry), daemon=True)
    reader.start()
    rpc = polymarket.BoundedRPC()
    heartbeat = 0
    try:
        while not stop.is_set() and time.monotonic() < deadline:
            if time.monotonic() >= heartbeat:
                report({'stage':'polymarket-monitor','source':dict(counts),'bookFrames':books.frames})
                heartbeat = time.monotonic()+60
            try:
                captured = queue.get(timeout=.25)
            except Empty:
                if not reader.is_alive() and time.monotonic() < deadline:
                    raise RuntimeError('Polymarket public stream stopped')
                continue
            try:
                if captured.source_ms < armed_ms:
                    continue
                try:
                    _, result, _ = polymarket.process(captured, gate, books, rpc, None, stop, registry, deadline,
                        writer_factory=lambda reg, key, end: PolymarketWriter(adapter, captured, reg),
                        buy_budget=buy_budget, on_refusal=adapter.remember_rejection)
                except (polymarket.Skip, GateSkip) as error:
                    report({'stage':'polymarket-skip','reason':error.reason,'proof':getattr(error,'details',None)})
                    continue
                if result['status'] == 'recorded':
                    report({'stage':'app-venue-admission','venue':'polymarket','status':'recorded'})
            finally:
                queue.complete(captured)
    finally:
        halt.set()
        reader.join(timeout=5)
        books.close()
        if reader.is_alive():
            raise RuntimeError('Polymarket reader did not stop')


def limit_estimate(item, subscriptions, gate, adapter, stop, started_ms):
    log, wallet, token, observed = item
    try:
        market = limitless.market_for(log, subscriptions, wallet, token)
        delay, evidence, policy = source.market_parameters(market)
        expiry = policy.get('marketExpiresAtMs')
        now = source.observe()[1]
        if type(expiry) is not int or expiry <= now:
            raise GateSkip('MARKET_EXPIRY_UNPROVEN_OR_PASSED')
        subscriptions.follow(market, expiry, now)
        matches = list(source.limitless_signals(market, started_ms, {}, [log], observed))
    except SOURCE_ERRORS as error:
        raise GateSkip('LIMITLESS_SOURCE_' + type(error).__name__) from error
    if len(matches) != 1:
        raise GateSkip('BASE_RECEIPT_OR_SIGNAL_UNPROVEN')
    match = matches[0]
    event = source.ledger_event(match)
    scoped = adapter.bind(estimate_metadata('limitless', wallet, market.slug, event, policy))
    command = event['executionId']
    cached = scoped.lookup_command(None, 'limitless', 'shared-demo', command, event=event)
    if cached is not None:
        return cached
    signal = gate.accept_signal(event, match['firstObservedMonotonicNs'], match['ageAtFirstObservationMs'])
    if stop.wait(delay / 1000):
        return None
    window = gate.begin(signal, delay, evidence)
    book = gate.wait_candidate(window)
    while True:
        estimate = quote(book, 'BUY', policy, budget=BUYS['limitless'])
        estimate['evidence'].update(waitStartedMonotonicNs=str(window.start_ns),
                                    firstObservedMonotonicNs=str(signal.first_ns),
                                    ageAtFirstObservationMs=signal.age_ms,
                                    sourceProof={'sourceLog': match['sourceLog'], 'sourceReceipt': match['sourceReceipt']})
        book_guard = gate.guard(window, book)

        class Guard:
            commit_lock = book_guard.commit_lock

            def __call__(self, expected, computed):
                if source.observe()[1] >= expiry:
                    raise GateSkip('MARKET_EXPIRED')
                return book_guard(expected, computed)

        try:
            return scoped.submit(None, 'limitless', 'shared-demo', command, event, estimate, Guard())
        except GateSkip as error:
            if error.reason != 'BOOK_CHANGED':
                raise
            book = gate.wait_candidate(window, recompute=True)


def run_limitless(adapter, wallet, stop, deadline, report):
    wallet = wallet.lower()
    gate = BookGate()
    books = Books(gate, deadline)
    subscriptions = limitless.Subscriptions(books)
    counters, seen = Counter(), {}
    started_ms = source.observe()[1]
    refresh = heartbeat = 0
    try:
        while not stop.is_set() and time.monotonic() < deadline:
            if time.monotonic() >= refresh:
                try:
                    subscriptions.prewarm(limitless.warm_hints((wallet,)), source.observe()[1])
                except SOURCE_ERRORS as error:
                    report({'stage':'limitless-warm','reason':type(error).__name__})
                refresh = time.monotonic() + limitless.REFRESH_S
            subscriptions.sync(source.observe()[1])
            try:
                head = int(source.rpc('eth_getBlockByNumber', 'latest', False)['number'], 16)
                logs = base_logs(head - 15, head, (wallet,))
                stamps = source.observe()
                candidates = list(limitless.collect(logs, {wallet}, stamps, seen, counters))
            except SOURCE_ERRORS as error:
                report({'stage':'limitless-read','reason':type(error).__name__})
                stop.wait(5)
                continue
            if time.monotonic() >= heartbeat:
                report({'stage':'limitless-monitor','head':head,'seen':len(seen),'source':dict(counters),
                        'bookFrames':sum(books.frames.values())})
                heartbeat = time.monotonic()+60
            for item in candidates:
                if stop.is_set() or time.monotonic() >= deadline:
                    break
                try:
                    result = limit_estimate(item, subscriptions, gate, adapter, stop, started_ms)
                except GateSkip as error:
                    report({'stage':'limitless-skip','reason':error.reason})
                    continue
                if result and result['status'] == 'recorded':
                    report({'stage':'app-venue-admission','venue':'limitless','status':'recorded'})
            stop.wait(limitless.POLL_S)
    finally:
        books.close()


def run_limitless_finalizer(adapter, stop, report):
    while not stop.is_set():
        for pending in adapter.pending_limitless():
            if stop.is_set():
                return
            try:
                state, evidence = base_evidence(pending)
            except SOURCE_ERRORS as error:
                report({'stage':'limitless-finality-read','reason':type(error).__name__})
                continue
            if state == 'pending':
                continue
            result = adapter.resolve_limitless(pending['executionId'], state, evidence,
                                               operation_id=pending['operationId'])
            operation = result.get('operation') or {}
            if (result.get('status')!='recorded' or operation.get('state')!=state
                    or operation.get('operationId')!=pending['operationId']):
                raise RuntimeError('Limitless terminal write did not return the same committed operation')
            report({'stage':'limitless-finality','state':state,'blockNumber':pending['sourceEvent']['blockNumber'],
                    'finalizedBlockNumbers':evidence['finalizedHeights']})
        stop.wait(6)


def base_evidence(pending, witness=None):
    witness = witness or source.witness
    observed = {}

    def record(method, *params):
        results = witness(method, *params)
        observed[method, params] = results
        return results

    locator = pending['sourceEvent']
    state, hashes, heights = source.base_state(locator, query=record)
    if state == 'pending':
        return state, None
    receipts = observed[('eth_getTransactionReceipt', (locator['transaction'],))]
    original_log = pending['sourceProof']['sourceLog']
    matches = []
    for receipt in receipts:
        selected = [log for log in (receipt or {}).get('logs', []) if int(log['logIndex'], 16) == locator['logIndex']]
        matches.append(len(selected) == 1 and all(selected[0][key] == original_log[key]
                       for key in ('address', 'topics', 'data', 'blockHash', 'transactionHash')))
    if state == 'finalized' and matches != [True, True]:
        return 'pending', None
    digest = hashlib.sha256(json.dumps([(method, params, value) for (method, params), value in sorted(observed.items())],
                                       sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    present = [receipt is not None for receipt in receipts]
    return state, {'rpcBlockHashes':hashes,'finalizedHeights':heights,'receiptMatchesOriginal':all(matches),
                   'receiptPresent':any(present),'receiptMatchesByProvider':matches,'receiptPresentByProvider':present,
                   'providers':list(source.RPC),'checkedAtMs':source.observe()[1],
                   'evidenceRef':'base-public-rpc:sha256:'+digest}
