"""Private isolated-estimated coordinator; no venue writes or production fallback."""
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
import json
import re
import threading
import time

PROFILE = 'isolated-estimated'
LABEL = 'Виртуальная сделка по оценочной цене'
NS = 1_000_000_000


class GateSkip(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def rational(value):
    if isinstance(value, F):
        return value
    if type(value) is int:
        return F(value)
    if isinstance(value, str) and re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', value):
        return F(value)
    if isinstance(value, dict) and set(value) == {'n', 'd'}:
        if all(isinstance(v, str) and re.fullmatch(r'-?[0-9]+', v) for v in value.values()):
            return F(int(value['n']), int(value['d']))
    raise GateSkip('INVALID_EXACT_NUMBER')


def q(value):
    value = rational(value)
    return {'n': str(value.numerator), 'd': str(value.denominator)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def levels(rows, reverse=False):
    if not isinstance(rows, list) or len(rows) > 20000:
        raise GateSkip('BOOK_INVALID')
    result = {}
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise GateSkip('BOOK_INVALID')
        price, raw = rational(row[0]), row[1]
        if not 0 < price < 1 or type(raw) is not int or raw <= 0 or price in result:
            raise GateSkip('BOOK_INVALID')
        result[price] = F(raw, 1_000_000)
    return tuple(sorted(result.items(), reverse=reverse))


@dataclass(frozen=True)
class Book:
    key: tuple
    connection: str
    revision: int
    identity: object
    source_time: object
    received_ns: int
    received_ms: int
    bids: tuple
    asks: tuple
    levels_hash: str
    evidence_ref: str
    eligible: bool


@dataclass(frozen=True)
class Signal:
    event: dict
    key: tuple
    first_ns: int
    age_ms: int
    validated_ns: int


@dataclass(frozen=True)
class Window:
    signal: Signal
    start_ns: int
    deadline_ns: int


class BookGate:
    def __init__(self, monotonic_ns=time.monotonic_ns, utc_ms=None):
        self.clock = monotonic_ns
        self.utc = utc_ms or (lambda: time.time_ns() // 1_000_000)
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.books = {}
        self.connections = {}
        self.revisions = {}
        self.signals = {}
        self.invalidated = set()

    def feed_book(self, frame):
        # Reception is stamped before taking the publication lock, never at quote time.
        received, utc = self.clock(), self.utc()
        key = (frame['venue'], frame['market'], frame['token'])
        if key[0] not in ('polymarket', 'limitless') or not all(isinstance(v, str) and v for v in key):
            raise GateSkip('BOOK_IDENTITY')
        connection = frame.get('connectionId')
        if not isinstance(connection, str) or not connection or not frame.get('evidenceRef'):
            raise GateSkip('BOOK_IDENTITY')
        bids, asks = levels(frame['bids'], True), levels(frame['asks'])
        if bids and asks and bids[0][0] > asks[0][0]:
            raise GateSkip('BOOK_CROSSED')
        identity = frame.get('hash') if key[0] == 'polymarket' else frame.get('version')
        if key[0] == 'polymarket':
            if not isinstance(identity, str) or not re.fullmatch(r'(?:0x)?[a-fA-F0-9]{8,128}', identity):
                raise GateSkip('BOOK_HASH')
        elif type(identity) is not int or identity < 0:
            raise GateSkip('BOOK_VERSION')
        if frame.get('sourceTimestamp') is None:
            raise GateSkip('BOOK_SOURCE_TIME')
        state_hash = digest([[q(p), q(size)] for p, size in bids] + ['asks'] +
                            [[q(p), q(size)] for p, size in asks])
        with self.changed:
            old = self.books.get(key)
            if self.connections.get(key) != connection:
                old = None
                self.connections[key] = connection
            if old and key[0] == 'limitless' and identity < old.identity:
                return None  # No refresh on out-of-order frames.
            if old and identity == old.identity:
                if state_hash != old.levels_hash:
                    self.invalidated.add(key)
                    self.changed.notify_all()
                    raise GateSkip('BOOK_IDENTITY_CONFLICT')
                return old  # Duplicate leaves reception time and eligibility unchanged.
            if old and state_hash == old.levels_hash:
                # Version movement with identical levels cannot extend freshness.
                self.invalidated.add(key)
                old = Book(key, connection, old.revision, identity, old.source_time,
                           old.received_ns, old.received_ms, bids, asks, state_hash,
                           old.evidence_ref, False)
                self.books[key] = old
                self.changed.notify_all()
                return old
            revision = self.revisions.get(key, 0) + 1
            self.revisions[key] = revision
            book = Book(key, connection, revision, identity, frame['sourceTimestamp'],
                        received, utc, bids, asks, state_hash, frame['evidenceRef'],
                        old is not None and (key[0] != 'limitless' or identity > 0))
            self.books[key] = book
            self.invalidated.discard(key)
            self.changed.notify_all()
            return book

    def invalidate(self, venue, market, token, connection_id=None, disconnected=False):
        key = (venue, market, token)
        with self.changed:
            if connection_id is not None and self.connections.get(key) != connection_id:
                return
            self.invalidated.add(key)
            if disconnected:
                self.connections.pop(key, None)
                self.books.pop(key, None)
            self.changed.notify_all()

    def accept_signal(self, event, first_observed_ns, age_at_first_ms):
        now = self.clock()
        if type(first_observed_ns) is not int or not 0 <= first_observed_ns <= now:
            raise GateSkip('SIGNAL_CLOCK')
        if type(age_at_first_ms) is not int or not 0 <= age_at_first_ms <= 30000:
            raise GateSkip('SIGNAL_AGE')
        key = (event['venue'], event['marketId'], event['outcomeId'])
        if event['side'] not in ('BUY', 'SELL') or key[0] not in ('polymarket', 'limitless'):
            raise GateSkip('SIGNAL_IDENTITY')
        if not re.fullmatch('[a-f0-9]{64}', event.get('fingerprint', '')):
            raise GateSkip('SIGNAL_IDENTITY')
        chain = event['chain']
        if key[0] == 'limitless':
            if chain['rpcBlockHashes'] != [chain['blockHash'], chain['blockHash']]:
                raise GateSkip('SIGNAL_RPC_DISAGREEMENT')
        elif chain is None:
            receipt = event.get('venueReceipt', {})
            if receipt.get('source') != 'polymarket-data-api-v2' or not receipt.get('evidenceRef'):
                raise GateSkip('VENUE_RECEIPT_UNPROVEN')
        elif not chain.get('rpcBlockHashes') or any(h != chain['blockHash'] for h in chain['rpcBlockHashes']):
            raise GateSkip('SIGNAL_RPC_DISAGREEMENT')
        identity = (event['venue'], event['executionId'])
        with self.lock:
            previous = self.signals.get(identity)
            if previous:
                if previous.event['fingerprint'] != event['fingerprint']:
                    raise GateSkip('SIGNAL_IDENTITY_CONFLICT')
                # Original age survives re-reading and a new block inclusion.
                first_observed_ns, age_at_first_ms = previous.first_ns, previous.age_ms
                event = dict(event, firstSeenMs=previous.event['firstSeenMs'],
                             signalAtMs=previous.event['signalAtMs'])
            signal = Signal(json.loads(json.dumps(event)), key, first_observed_ns, age_at_first_ms, now)
            self.check_age(signal)
            self.signals[identity] = signal
            return signal

    def check_age(self, signal):
        elapsed = self.clock() - signal.first_ns
        if elapsed < 0 or elapsed + signal.age_ms * 1_000_000 > 30 * NS:
            raise GateSkip('SIGNAL_AGE')

    def begin(self, signal, delay_ms, delay_evidence):
        if type(delay_ms) is not int or not 0 <= delay_ms <= 30000 or not delay_evidence:
            raise GateSkip('EXECUTION_DELAY_UNPROVEN')
        self.check_age(signal)
        start = self.clock()
        if start < signal.validated_ns + delay_ms * 1_000_000:
            raise GateSkip('EXECUTION_DELAY_NOT_ELAPSED')
        return Window(signal, start, start + NS)

    def candidate(self, window, *, recompute=False):
        self.check_age(window.signal)
        now = self.clock()
        with self.lock:
            book = self.books.get(window.signal.key)
            if (book is None or not book.eligible or book.key in self.invalidated or
                    book.received_ns <= window.start_ns or
                    (not recompute and book.received_ns > window.deadline_ns)):
                raise GateSkip('BOOK_WAIT_TIMEOUT' if not recompute and now >= window.deadline_ns else 'BOOK_WAITING')
            if not 0 <= now - book.received_ns <= 2 * NS:
                raise GateSkip('BOOK_AGE')
            return book

    def wait_candidate(self, window, *, recompute=False):
        deadline = self.clock() + NS if recompute else window.deadline_ns
        with self.changed:
            while True:
                try:
                    return self.candidate(window, recompute=recompute)
                except GateSkip as error:
                    if error.reason != 'BOOK_WAITING':
                        raise
                    remaining = deadline - self.clock()
                    if remaining <= 0:
                        raise GateSkip('BOOK_WAIT_TIMEOUT')
                    self.changed.wait(remaining / NS)

    def guard(self, window, book):
        gate = self

        class CommitGuard:
            commit_lock = gate.lock

            def __call__(self, event, estimate):
                gate.check_age(window.signal)
                with gate.lock:
                    if gate.books.get(book.key) != book or book.key in gate.invalidated:
                        raise GateSkip('BOOK_CHANGED')
                    if not 0 <= gate.clock() - book.received_ns <= 2 * NS:
                        raise GateSkip('BOOK_AGE')
                    if event != window.signal.event or estimate['book']['revision'] != book.revision:
                        raise GateSkip('COMMIT_IDENTITY')
                    return True

        return CommitGuard()


def quote(book, side, policy, *, budget=None, sell_quantity=None):
    """Exact quantities/cash; policy is installed by the private verified source driver."""
    required = {'profile', 'priceTick', 'quantityStep', 'minimumQuantity', 'minimumNotional',
                'feeModel', 'feeRate', 'feeRounding', 'evidenceRef', 'orderShape'}
    if not required <= policy.keys() or policy['profile'] != PROFILE or not policy['evidenceRef']:
        raise GateSkip('MARKET_PARAMETERS_UNPROVEN')
    tick, step = rational(policy['priceTick']), rational(policy['quantityStep'])
    minimum, min_cash = rational(policy['minimumQuantity']), rational(policy['minimumNotional'])
    rate = rational(policy['feeRate'])
    if not 0 < tick < 1 or step <= 0 or minimum < 0 or min_cash < 0 or not 0 <= rate <= 1:
        raise GateSkip('MARKET_PARAMETERS_INVALID')
    if not policy['orderShape']:
        raise GateSkip('ORDER_SHAPE_UNPROVEN')
    if policy['feeModel'].startswith('limitless-') and book.key[0] != 'limitless':
        raise GateSkip('FEE_FAMILY_MISMATCH')
    if policy['feeModel'].startswith('polymarket-') and book.key[0] != 'polymarket':
        raise GateSkip('FEE_FAMILY_MISMATCH')
    rows = book.asks if side == 'BUY' else book.bids if side == 'SELL' else ()
    if not rows or any(p % tick for p, _ in rows):
        raise GateSkip('BOOK_DEPTH_OR_TICK')
    best = rows[0][0]
    boundary = (best * F(102, 100) // tick) * tick if side == 'BUY' else -(-best * F(98, 100) // tick) * tick
    allowed = [(p, size) for p, size in rows if (p <= boundary if side == 'BUY' else p >= boundary)]
    total = sum((size for _, size in allowed), F(0))

    def fill(amount):
        left, fills = amount, []
        for price, available in allowed:
            take = min(left, available)
            if take:
                fills.append((take, price))
                left -= take
            if not left:
                break
        if left or not fills:
            raise GateSkip('BOOK_DEPTH')
        gross = sum((size * p for size, p in fills), F(0))
        if policy['feeModel'] == 'verified-zero' and rate == 0:
            fee = F(0)
        elif policy['feeModel'] == 'limitless-collateral-single-match':
            fee = rate * gross * (amount - gross) / amount
        elif policy['feeModel'] == 'polymarket-v2-single-match':
            fee = sum((rate * size * p * (1 - p) for size, p in fills), F(0))
        else:
            raise GateSkip('FEE_UNPROVEN')
        quantum = F(1, 100000)
        if policy['feeRounding'] == 'floor-5dp':
            fee = (fee // quantum) * quantum
        elif policy['feeRounding'] == 'half-up-5dp':
            fee = ((fee + quantum / 2) // quantum) * quantum
        elif fee != 0 or policy['feeRounding'] != 'exact-zero':
            raise GateSkip('FEE_ROUNDING_UNPROVEN')
        return fills, gross, fee

    if side == 'BUY':
        budget = rational(budget)
        if budget <= 0 or total <= 0:
            raise GateSkip('BUDGET')
        _, max_cost, max_fee = fill(total)
        if max_cost + max_fee < budget:
            raise GateSkip('BOOK_DEPTH')  # Full budget coverage before quantity rounding.
        low, high = 0, int(total // step)
        while low < high:
            mid = (low + high + 1) // 2
            _, cash, fee = fill(mid * step)
            if cash + fee <= budget:
                low = mid
            else:
                high = mid - 1
        amount = low * step
    else:
        amount = rational(sell_quantity)
        if amount % step:
            raise GateSkip('QUANTITY_STEP')
    if amount <= 0 or amount < minimum:
        raise GateSkip('ORDER_MINIMUM')
    fills, gross, fee = fill(amount)
    if side == 'BUY':
        # Tighten the rounded quantity to a representable collateral amount. This only
        # reduces an estimate after full-depth coverage; it never fills a shallow book.
        for _ in range(1000):
            if (gross * 1_000_000).denominator == 1 and (amount * 1_000_000).denominator == 1:
                break
            amount -= step
            if amount <= 0 or amount < minimum:
                raise GateSkip('ORDER_MINIMUM')
            fills, gross, fee = fill(amount)
    if len(fills) > 128:
        raise GateSkip('FILL_COUNT_LIMIT')
    # Exact token precision is a venue constraint, independent of the internal rational ledger.
    if ((gross * 1_000_000).denominator != 1 or (amount * 1_000_000).denominator != 1):
        raise GateSkip('RAW_AMOUNT_PRECISION')
    if gross < min_cash or (side == 'SELL' and gross <= fee):
        raise GateSkip('ORDER_MINIMUM')
    wire = [{'quantity': q(size), 'price': q(price), 'cashFee': q(fee if i == len(fills)-1 else 0)}
            for i, (size, price) in enumerate(fills)]
    return {'fills': wire,
            'book': {'venue': book.key[0], 'market': book.key[1], 'token': book.key[2],
                     'connectionId': book.connection, 'revision': book.revision,
                     'hashOrVersion': book.identity, 'levelsHash': book.levels_hash,
                     'sourceTimestamp': book.source_time, 'receivedAtMs': book.received_ms,
                     'receivedMonotonicNs': str(book.received_ns), 'evidenceRef': book.evidence_ref},
            'evidence': {'profile': PROFILE, 'label': LABEL, 'policy': policy,
                         'display': {'marketTitle': policy.get('marketTitle'),
                                     'outcomeTitle': policy.get('outcomeTitle')},
                         'priceLimit': q(boundary), 'side': side, 'quantity': q(amount),
                         'gross': q(gross), 'cashFee': q(fee),
                         'publisherClockBoundMs': None, 'publicationDelayMs': None}}


class Coordinator:
    def __init__(self, gate, ledger, db, session_id, owner_id):
        self.gate, self.ledger, self.db = gate, ledger, db
        self.session_id, self.owner_id = session_id, owner_id

    def execute(self, command_id, window, policy, **sizing):
        previous = self.ledger.lookup_command(self.db, self.session_id, self.owner_id, command_id,
                                              event=window.signal.event)
        if previous is not None:
            return previous
        book = self.gate.wait_candidate(window)
        while True:
            estimate = quote(book, window.signal.event['side'], policy, **sizing)
            estimate['evidence'].update(waitStartedMonotonicNs=str(window.start_ns),
                                        firstObservedMonotonicNs=str(window.signal.first_ns),
                                        ageAtFirstObservationMs=window.signal.age_ms)
            try:
                return self.ledger.submit(self.db, self.session_id, self.owner_id,
                    command_id, window.signal.event, estimate, self.gate.guard(window, book))
            except GateSkip as error:
                # Only a gate rejection from a rolled-back DB transaction permits recomputation.
                if error.reason != 'BOOK_CHANGED':
                    raise
                book = self.gate.wait_candidate(window, recompute=True)
