"""Combine complete venue snapshots without refreshing unchanged or older state."""
from collections import Counter, deque
from dataclasses import replace
import json
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request
from uuid import uuid4

from book_engine import GateSkip, NS, levels, rational
from route import RtdsBookGate
import source


def snapshot_time(value):
    text = str(value)
    if len(text) != 13 or not text.isascii() or not text.isdecimal():
        raise GateSkip('BOOK_SOURCE_TIME')
    return int(text)


class HybridBookGate(RtdsBookGate):
    def __init__(self, *, fetch=None, **kwargs):
        super().__init__(**kwargs)
        self.fetch = fetch or http_book
        self.slots = threading.BoundedSemaphore(1)
        self.key = self.generation = self.market = self.params = None
        self.last_stamp = self.delta_stamp = self.window_start_ms = 0
        self.window = None
        self.terminal = False
        self.counts = Counter()
        self.observations = deque(maxlen=12)

    def configure(self, market, policy, baseline):
        with self.changed:
            key = (market.venue, market.market, market.token)
            params = (rational(policy['priceTick']), rational(policy['minimumQuantity']), baseline['neg_risk'])
            if key == self.key and params == self.params and not self.terminal:
                return self.generation
            if self.key:
                self.invalidate(*self.key, disconnected=True)
            self.key, self.market, self.params = key, market, params
            self.generation = uuid4().hex
            self.last_stamp = self.delta_stamp = 0
            self.terminal = False
            self.window = None
            try:
                self.publish_rest(baseline, self.generation, None)
            except (KeyError, TypeError, ValueError, ArithmeticError, GateSkip) as error:
                self.counts[getattr(error, 'reason', 'BOOK_BASELINE_INVALID')] += 1
            return self.generation

    def publish_rest(self, payload, generation, window, *, received=None):
        if (payload['market'], payload['asset_id']) != self.key[1:]:
            raise GateSkip('BOOK_REST_IDENTITY')
        tick, minimum, neg_risk = self.params
        if (rational(payload['tick_size']) != tick or rational(payload['min_order_size']) != minimum
                or payload.get('neg_risk') is not neg_risk or payload.get('version') is not None):
            raise GateSkip('BOOK_REST_MARKET_PARAMETERS')
        stamp = snapshot_time(payload['timestamp'])
        frame = source.book_message(self.market, generation, stamp, payload, digest=payload['hash'])
        frame['evidenceRef'] = f'polymarket:rest:{generation}:{payload["hash"]}'
        return self.publish(frame, generation, 'REST' if window else 'REST_BASELINE', window, received=received)

    def publish(self, frame, generation, transport, window=None, *, received=None):
        received_ns, received_ms = received or (self.clock(), self.utc())
        stamp = snapshot_time(frame['sourceTimestamp'])
        with self.changed:
            key = (frame['venue'], frame['market'], frame['token'])
            if generation != self.generation or key != self.key or self.terminal:
                return False
            if window and (self.window != window or received_ns > window.deadline_ns):
                return False
            reason = 'BOOK_' + transport
            self.observations.append({'transport': transport, 'snapshotAtMs': stamp,
                                      'receivedAtMs': received_ms, 'receivedMonotonicNs': str(received_ns)})
            if stamp > received_ms:
                self.counts[reason + '_FUTURE'] += 1
                return False
            if stamp < self.last_stamp or stamp < self.delta_stamp:
                self.counts[reason + '_OLDER'] += 1
                return False
            if window and stamp <= self.window_start_ms:
                self.counts[reason + '_PRE_WINDOW'] += 1
                return False
            previous = self.books.get(key)
            frame = dict(frame, connectionId=generation)
            if previous and previous.bids == levels(frame['bids'], True) and previous.asks == levels(frame['asks']):
                self.last_stamp = max(self.last_stamp, stamp)
                self.counts[reason + '_UNCHANGED'] += 1
                return False
            if previous and stamp == self.last_stamp:
                self.invalidate(*key)
                self.counts[reason + '_TIME_CONFLICT'] += 1
                return False
            book = self.feed_book(frame)
            self.last_stamp = max(self.last_stamp, stamp)
            if previous is not None and book.revision == previous.revision:
                self.counts[reason + '_UNCHANGED'] += 1
                return False
            self.books[key] = replace(book, received_ns=received_ns, received_ms=received_ms,
                                      eligible=book.eligible and transport != 'REST_BASELINE')
            self.counts[reason + '_SNAPSHOT'] += 1
            self.changed.notify_all()
            return book.eligible and transport != 'REST_BASELINE'

    def ws_invalidated(self, generation, *, stamp=None, terminal=False, disconnected=False):
        with self.changed:
            if generation != self.generation:
                return
            if stamp is not None and stamp < self.last_stamp:
                return
            if stamp is not None:
                self.delta_stamp = max(self.delta_stamp, stamp)
            if disconnected:
                self.last_stamp = self.delta_stamp = 0
            self.terminal |= terminal
            self.invalidate(*self.key, disconnected=disconnected)

    def begin(self, signal, delay_ms, delay_evidence):
        with self.changed:
            window = super().begin(signal, delay_ms, delay_evidence)
            signal_deadline = signal.first_ns + 30 * NS - signal.age_ms * 1_000_000
            window = replace(window, deadline_ns=min(window.deadline_ns, signal_deadline))
            self.window, self.window_start_ms = window, self.utc()
            self.observations.clear()
            if self.slots.acquire(blocking=False):
                threading.Thread(target=self.read_rest, args=(window, self.generation, self.market), daemon=True).start()
            else:
                self.counts['BOOK_REST_BUSY'] += 1
            return window

    def read_rest(self, window, generation, market):
        try:
            for _ in range(3):
                remaining = (window.deadline_ns - self.clock()) / NS
                if remaining <= 0:
                    return
                with self.changed:
                    if self.window != window or self.key != window.signal.key or self.generation != generation:
                        return
                    self.counts['BOOK_REST_REQUEST'] += 1
                try:
                    payload, received = self.fetch(market, remaining)
                    with self.changed:
                        if generation != self.generation or self.window != window:
                            return
                        if self.publish_rest(payload, generation, window, received=received):
                            return
                except HTTPError as error:
                    with self.changed:
                        self.counts[f'BOOK_REST_HTTP_{error.code}'] += 1
                    return
                except (OSError, KeyError, ValueError, TypeError, ArithmeticError, GateSkip) as error:
                    with self.changed:
                        self.counts[getattr(error, 'reason', 'BOOK_REST_TRANSPORT_OR_FORMAT')] += 1
                    return
                with self.changed:
                    if self.window != window:
                        return
                    self.changed.wait(timeout=min(.25, max(0, (window.deadline_ns - self.clock()) / NS)))
        finally:
            self.slots.release()

    def candidate(self, window, *, recompute=False):
        with self.changed:
            if self.terminal or self.key != window.signal.key or self.window != window:
                raise GateSkip('BOOK_MARKET_CHANGED')
            book = super().candidate(window, recompute=False)
            if book.source_time <= self.window_start_ms:
                raise GateSkip('BOOK_WAITING')
            return book

    def wait_candidate(self, window, *, recompute=False):
        return super().wait_candidate(window, recompute=False)

    def finish(self):
        with self.changed:
            self.window = None
            self.changed.notify_all()


def http_book(market, timeout):
    query = urlencode({'token_id': market.token})
    request = Request(f'{source.POLY_CLOB}/book?{query}', headers={
        'Accept': 'application/json', 'Content-Type': 'application/json',
        'User-Agent': 'Shadow-closed-demo-read-only/1', 'Cache-Control': 'no-cache',
    })
    with source.OPENER.open(request, timeout=timeout) as response:
        raw = response.read(source.MAX_MESSAGE + 1)
        received = time.monotonic_ns(), time.time_ns() // 1_000_000
    if len(raw) > source.MAX_MESSAGE:
        raise ValueError('oversized CLOB snapshot')
    return json.loads(raw), received
