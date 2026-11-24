"""Share one immutable, venue-timestamped Polymarket snapshot per pilot signal."""
import argparse
from concurrent.futures import Future
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import re
import socket
from socketserver import StreamRequestHandler, ThreadingUnixStreamServer
import threading
import time

from book_engine import Book, GateSkip, NS, q, rational
from hybrid_book import BOOK_WAIT_NS, HybridBookGate
from market_policy import prepare_market
from route import RtdsBookGate, Signal
from rtds_operator import ActiveBook
from source import Market

MAX_WIRE = 1_100_000
MAX_SIGNALS = 128
MAX_MARKETS = 24
MARKET_TTL = 3
CLOCK_MARGIN_NS = 50_000_000


def read_message(stream):
    raw = stream.readline(MAX_WIRE + 1)
    if not raw or len(raw) > MAX_WIRE or not raw.endswith(b'\n'):
        raise GateSkip('BOOK_BROKER_PROTOCOL')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise GateSkip('BOOK_BROKER_PROTOCOL')
    return value


def write_message(stream, value):
    def decimal_string(value):
        if isinstance(value, Decimal) and value.is_finite():
            return str(value)
        raise TypeError('unsupported book value')

    raw = json.dumps(value, separators=(',', ':'), allow_nan=False, default=decimal_string).encode()
    if len(raw) >= MAX_WIRE:
        raise GateSkip('BOOK_BROKER_PROTOCOL')
    stream.write(raw + b'\n')
    stream.flush()


def market_wire(market):
    return {name: getattr(market, name) for name in ('venue','market','token','wallet','slug','side')}


def book_wire(book):
    return dict(key=list(book.key), connection=book.connection, revision=book.revision,
                identity=book.identity, source_time=book.source_time, received_ns=book.received_ns,
                received_ms=book.received_ms, levels_hash=book.levels_hash, evidence_ref=book.evidence_ref,
                eligible=book.eligible,
                bids=[[q(p), q(s)] for p, s in book.bids], asks=[[q(p), q(s)] for p, s in book.asks])


def decode_book(wire):
    wire = dict(wire, key=tuple(wire['key']))
    for side in ('bids', 'asks'):
        wire[side] = tuple((rational(p), rational(s)) for p, s in wire[side])
    return Book(**wire)


class SharedPolygonBookGate(RtdsBookGate):
    """Use the same local route and fee rules with a pinned remote book."""

    def __init__(self, path, participant, **kwargs):
        super().__init__(**kwargs)
        self.path, self.participant = str(path), participant
        self.market = None

    @contextmanager
    def exchange(self, operation, fields, timeout):
        request = dict(operation=operation, participant=self.participant, **fields)
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(max(.01, timeout))
                sock.connect(self.path)
                with sock.makefile('rwb') as stream:
                    write_message(stream, request)
                    response = read_message(stream)
                    if response.get('ok') is not True:
                        raise GateSkip(response.get('reason', 'BOOK_BROKER_PROTOCOL'))
                    yield stream, response
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise GateSkip('BOOK_WAIT_TIMEOUT') from error

    def prepare_market(self, market):
        with self.exchange('market', {'market': market_wire(market)}, 4) as (_, response):
            return response['parameters'], response['elapsedMs']

    def configure(self, market, policy, baseline):
        if (market.venue != 'polymarket' or (baseline['market'], baseline['asset_id']) != (market.market, market.token)
                or rational(baseline['tick_size']) != rational(policy['priceTick'])
                or rational(baseline['min_order_size']) != rational(policy['minimumQuantity'])):
            raise GateSkip('BOOK_REST_MARKET_PARAMETERS')
        self.market = market

    def begin(self, signal, delay_ms, delay_evidence):
        window = super().begin(signal, delay_ms, delay_evidence)
        signal_deadline = signal.first_ns + 30 * NS - signal.age_ms * 1_000_000
        return replace(window, deadline_ns=min(window.start_ns + BOOK_WAIT_NS, signal_deadline))

    def wait_candidate(self, window, *, recompute=False):
        # An immutable pin never switches books halfway through fanout.
        if recompute:
            raise GateSkip('BOOK_WAIT_TIMEOUT')
        self.check_age(window.signal)
        event = window.signal.event
        if self.market is None or window.signal.key != (self.market.venue, self.market.market, self.market.token):
            raise GateSkip('BOOK_MARKET_CHANGED')
        deadline = min(window.deadline_ns, self.clock() + BOOK_WAIT_NS)
        request = {
            'market': market_wire(self.market), 'execution': event['executionId'], 'fingerprint': event['fingerprint'],
            'sourceAtMs': event['signalAtMs'], 'startNs': window.start_ns, 'deadlineNs': deadline,
        }
        if self.clock() >= deadline:
            raise GateSkip('BOOK_WAIT_TIMEOUT')
        with self.exchange('book', request, (deadline - self.clock()) / NS) as (_, response):
            book = decode_book(response['book'])
        if (book.key != window.signal.key or book.received_ns <= window.start_ns
                or book.received_ns > window.deadline_ns or not book.eligible):
            raise GateSkip('BOOK_BROKER_PROTOCOL')
        if not 0 <= self.clock() - book.received_ns <= 2 * NS or not 0 <= self.utc() - book.source_time <= 2000:
            raise GateSkip('BOOK_AGE')
        return book

    def guard(self, window, book):
        gate = self

        class CommitGuard:
            stream = None

            @contextmanager
            def hold(self):
                fields = {'execution': window.signal.event['executionId'], 'book': book.evidence_ref}
                with gate.exchange('lease', fields, 2) as (stream, _):
                    self.stream = stream
                    try:
                        yield
                    finally:
                        self.stream = None

            @property
            def commit_lock(self):
                return self.hold()

            def __call__(self, event, estimate):
                gate.check_age(window.signal)
                if (event != window.signal.event or estimate['book']['revision'] != book.revision
                        or estimate['book']['evidenceRef'] != book.evidence_ref):
                    raise GateSkip('COMMIT_IDENTITY')
                if not 0 <= gate.clock() - book.received_ns <= 2 * NS or not 0 <= gate.utc() - book.source_time <= 2000:
                    raise GateSkip('BOOK_AGE')
                if self.stream is None:
                    raise GateSkip('BOOK_BROKER_PROTOCOL')
                try:
                    write_message(self.stream, {'operation': 'check'})
                    result = read_message(self.stream)
                except (OSError, TypeError, ValueError) as error:
                    raise GateSkip('BOOK_AGE') from error
                if result.get('ok') is not True:
                    raise GateSkip(result.get('reason', 'BOOK_BROKER_PROTOCOL'))
                return True

        return CommitGuard()

    def finish(self):
        pass


class MarketFeed:
    def __init__(self, market, deadline):
        self.market = market
        self.gate = HybridBookGate()
        self.books = ActiveBook(self.gate, deadline)
        self.preparation = Future()
        self.acquisition = threading.Lock()
        self.expires = 0
        self.books.prepare(market)

    def load(self, pending, market):
        try:
            parameters, elapsed = prepare_market(market)
            _, _, policy, baseline, _ = parameters
            self.books.follow(market, policy, baseline)
            self.expires = time.monotonic() + MARKET_TTL
            pending.set_result((parameters, elapsed))
        except (OSError, EOFError, KeyError, ValueError, TypeError, ArithmeticError, GateSkip):
            pending.set_exception(GateSkip('MARKET_PARAMETERS_UNPROVEN'))


class PendingBook:
    def __init__(self, identity, feed, expires):
        self.identity, self.feed, self.expires = identity, feed, expires
        self.waiting = {}
        self.failed = False
        self.pinned = None


class BookBroker:
    def __init__(self, participants, deadline):
        self.participants = frozenset(participants)
        self.deadline = deadline
        self.changed = threading.Condition()
        self.markets, self.signals = {}, {}

    def prepare(self, market):
        if market.venue != 'polymarket' or market.side != 'BUY':
            raise GateSkip('BOOK_MARKET_CHANGED')
        key = market.market, market.token
        with self.changed:
            now = time.monotonic()
            managed = self.markets.get(key)
            if managed is not None and managed.market != market:
                raise GateSkip('BOOK_MARKET_CHANGED')
            created = managed is None
            if created:
                if len(self.markets) >= MAX_MARKETS:
                    evictable = [(feed.expires, name, feed) for name, feed in self.markets.items()
                                 if feed.expires <= now and feed.preparation.done() and not feed.acquisition.locked()
                                 and not any(record.feed is feed and not record.failed and record.expires > now
                                             for record in self.signals.values())]
                    if not evictable:
                        raise GateSkip('BOOK_WAIT_TIMEOUT')
                    _, name, oldest = min(evictable)
                    oldest.books.close()
                    del self.markets[name]
                managed = self.markets[key] = MarketFeed(market, self.deadline)
            refresh = not created and managed.expires <= now and managed.preparation.done()
            if refresh:
                managed.preparation = Future()
            pending = managed.preparation
        if created or refresh:
            managed.load(pending, market)
        return pending.result(timeout=3.5)

    def pin(self, participant, market, request):
        execution, fingerprint = request['execution'], request['fingerprint']
        start, deadline, source_at = request['startNs'], request['deadlineNs'], request['sourceAtMs']
        now_ns, now_ms = time.monotonic_ns(), time.time_ns() // 1_000_000
        if (not all(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value)
                    for value in (execution, fingerprint))
                or not all(type(value) is int for value in (start, deadline, source_at))
                or not 0 <= start <= now_ns < deadline <= start + BOOK_WAIT_NS
                or not 0 <= now_ms - source_at < 30_000):
            raise GateSkip('BOOK_WAIT_TIMEOUT')
        identity = fingerprint, market, source_at
        with self.changed:
            now = time.monotonic()
            self.signals = {key: value for key, value in self.signals.items() if value.expires > now}
            managed = self.markets.get((market.market, market.token))
            if managed is None or market != managed.market or not managed.preparation.done():
                raise GateSkip('BOOK_MARKET_CHANGED')
            record = self.signals.get(execution)
            if record is None:
                if len(self.signals) >= MAX_SIGNALS:
                    raise GateSkip('BOOK_WAIT_TIMEOUT')
                record = self.signals[execution] = PendingBook(identity, managed, now + (30_000 - now_ms + source_at) / 1000)
            if record.identity != identity or record.feed is not managed:
                raise GateSkip('BOOK_IDENTITY_CONFLICT')
            if participant in record.waiting:
                # Overlapping requests from the same worker cannot move the agreed clock boundary.
                raise GateSkip('BOOK_WAIT_TIMEOUT')
            record.waiting[participant] = (start, deadline)
            elected = not record.failed and record.waiting.keys() == self.participants
            if not elected:
                while not record.failed and record.pinned is None and time.monotonic_ns() < deadline:
                    self.changed.wait(max(0, (deadline - time.monotonic_ns()) / NS))
                if record.pinned is None:
                    record.failed = True
                    self.changed.notify_all()
                    raise GateSkip('BOOK_WAIT_TIMEOUT')
                return record.pinned
            common_deadline = min(finish for _, finish in record.waiting.values())

        try:
            book = self.acquire(managed, source_at, common_deadline)
        except (GateSkip, ValueError, KeyError, TypeError, OSError, ArithmeticError):
            with self.changed:
                record.failed = True
                self.changed.notify_all()
            raise
        with self.changed:
            if record.failed:
                raise GateSkip('BOOK_WAIT_TIMEOUT')
            record.pinned = book
            self.changed.notify_all()
        print(json.dumps({'stage': 'shared-polygon-book', 'executionId': execution,
                          'bookHash': book.identity, 'levelsHash': book.levels_hash,
                          'evidenceRef': book.evidence_ref, 'sourceTimestampMs': book.source_time,
                          'receivedAtMs': book.received_ms, 'receivedMonotonicNs': str(book.received_ns),
                          'participants': len(record.waiting)}), flush=True)
        return book

    @staticmethod
    def acquire(feed, source_at, deadline_ns):
        remaining = (deadline_ns - time.monotonic_ns() - CLOCK_MARGIN_NS) / NS
        if remaining <= 0 or not feed.acquisition.acquire(timeout=remaining):
            raise GateSkip('BOOK_WAIT_TIMEOUT')
        gate = feed.gate
        try:
            signal = Signal({}, (feed.market.venue, feed.market.market, feed.market.token), gate.clock(),
                            gate.utc() - source_at, gate.clock())
            # Both participants registered before the venue acquisition window opened.
            # This also preserves the original rule that a baseline alone is never a quote.
            window = gate.begin(signal, 0, 'closed-shared-book-rendezvous')
            with gate.changed:
                while True:
                    if gate.clock() >= deadline_ns - CLOCK_MARGIN_NS:
                        raise GateSkip('BOOK_WAIT_TIMEOUT')
                    try:
                        book = gate.candidate(window)
                        if 0 <= gate.utc() - book.source_time <= 2000:
                            return book
                    except GateSkip as error:
                        if error.reason not in ('BOOK_WAITING', 'BOOK_AGE'):
                            raise
                    gate.changed.wait(max(0, (deadline_ns - CLOCK_MARGIN_NS - gate.clock()) / NS))
        finally:
            gate.finish()
            feed.acquisition.release()

    @contextmanager
    def lease(self, participant, execution, evidence_ref):
        with self.changed:
            record = self.signals.get(execution)
            if record is None or participant not in record.waiting or record.pinned is None:
                raise GateSkip('BOOK_WAIT_TIMEOUT')
            book = record.pinned
            if book.evidence_ref != evidence_ref:
                raise GateSkip('BOOK_IDENTITY_CONFLICT')
        gate = record.feed.gate

        def check():
            if (gate.books.get(book.key) != book or book.key in gate.invalidated
                    or gate.terminal or book.source_time < gate.delta_stamp):
                raise GateSkip('BOOK_WAIT_TIMEOUT')
            if not 0 <= gate.clock() - book.received_ns <= 2 * NS or not 0 <= gate.utc() - book.source_time <= 2000:
                raise GateSkip('BOOK_AGE')

        timeout = min(2 - (gate.clock() - book.received_ns) / NS,
                      (2000 - gate.utc() + book.source_time) / 1000)
        if timeout <= 0 or not gate.lock.acquire(timeout=timeout):
            raise GateSkip('BOOK_AGE')
        try:
            check()
            yield check
        finally:
            gate.lock.release()


class Handler(StreamRequestHandler):
    timeout = 4

    def handle(self):
        try:
            request = read_message(self.rfile)
            broker = self.server.broker
            participant = request['participant']
            if participant not in broker.participants:
                raise GateSkip('BOOK_BROKER_PROTOCOL')
            operation = request['operation']
            if operation == 'market':
                value, elapsed = broker.prepare(Market(**request['market']))
                write_message(self.wfile, {'ok': True, 'parameters': value, 'elapsedMs': elapsed})
            elif operation == 'book':
                book = broker.pin(participant, Market(**request['market']), request)
                write_message(self.wfile, {'ok': True, 'book': book_wire(book)})
            elif operation == 'lease':
                with broker.lease(participant, request['execution'], request['book']) as check:
                    write_message(self.wfile, {'ok': True})
                    while self.rfile.peek(1):
                        if read_message(self.rfile) != {'operation': 'check'}:
                            raise GateSkip('BOOK_BROKER_PROTOCOL')
                        check()
                        write_message(self.wfile, {'ok': True})
            else:
                raise GateSkip('BOOK_BROKER_PROTOCOL')
        except (OSError, TypeError, KeyError, ArithmeticError, ValueError, GateSkip) as error:
            try:
                write_message(self.wfile, {'ok': False, 'reason': getattr(error, 'reason', 'BOOK_WAIT_TIMEOUT')})
            except (OSError, GateSkip):
                pass


class BookingSocket(ThreadingUnixStreamServer):
    daemon_threads = True
    request_queue_size = 12
    slots = threading.BoundedSemaphore(16)

    def process_request(self, request, address):
        if self.slots.acquire(blocking=False):
            try:
                super().process_request(request, address)
            except BaseException:
                self.slots.release()
                raise
        else:
            self.shutdown_request(request)

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket', type=Path, required=True)
    parser.add_argument('--participant', action='append', required=True)
    parser.add_argument('--seconds', type=int, default=1800)
    args = parser.parse_args()
    if (len(args.participant) != 2 or len(set(args.participant)) != 2
            or not all(re.fullmatch('[A-Za-z0-9-]{1,64}', name) for name in args.participant)
            or not args.socket.is_absolute() or not 30 <= args.seconds <= 3600):
        parser.error('two distinct participants and a bounded local socket are required')
    with BookingSocket(str(args.socket), Handler) as server:
        args.socket.chmod(0o600)
        server.broker = BookBroker(args.participant, time.monotonic() + args.seconds)
        server.timeout = 1
        while time.monotonic() < server.broker.deadline:
            server.handle_request()


if __name__ == '__main__':
    main()
