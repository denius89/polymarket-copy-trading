from dataclasses import dataclass
from decimal import Decimal
import json, re, select, socket, ssl, threading, time
from queue import Empty, Full, Queue
from urllib.error import HTTPError
from urllib.request import Request
from uuid import uuid4
import rtds_provenance
import source
from book_engine import GateSkip, q
from hybrid_book import snapshot_time
from market_policy import load_market, verify_observed_fee
from numeric_match import price_key
from resolver import Resolver, Skip
from route import execute_resolved
SESSION = 'polymarket'
OWNER = 'shared-demo'

RTDS = 'ws-live-data.polymarket.com'

RPC = 'https://polygon.drpc.org'

ADDRESS = re.compile(r'0x[0-9a-fA-F]{40}')

HASH = re.compile(r'0x[0-9a-fA-F]{64}')

SLUG = re.compile(r'[a-zA-Z0-9_-]{1,180}')

BUY_BUDGET = q(10)

FIRST_LIMIT_NS = 30_000_000_000

RTDS_IDLE_SECONDS = 90

RTDS_IDLE_RECONNECT_LIMIT = 2

@dataclass(frozen=True)
class Frame:
    raw: bytes
    connection: str
    first_mono: int
    first_utc: int
    wallet: str
    market: str
    token: str
    slug: str
    event_key: tuple
    source_ms: int
    exact_price: Decimal

def capture_frame(raw, connection, first_mono, first_utc, wallets, *, frame=None):
    if frame is None:
        frame = json.loads(raw, parse_float=Decimal)
    if frame.get('topic') != 'activity' or frame.get('type') != 'orders_matched':
        return None
    payload = frame['payload']
    wallet = payload['proxyWallet'].lower()
    if wallet not in wallets:
        return None
    if payload['side'] != 'BUY':
        raise Skip('OUTSIDE_BUY_SCOPE')
    market, token, slug = payload['conditionId'].lower(), payload['asset'], payload['slug']
    transaction = payload['transactionHash'].lower()
    stamp = payload['timestamp']
    if (not HASH.fullmatch(market) or not HASH.fullmatch(transaction) or not isinstance(token, str)
            or not re.fullmatch('[1-9][0-9]{0,77}', token) or int(token) >= 2**256
            or not SLUG.fullmatch(slug) or type(stamp) is not int):
        raise Skip('INVALID_FRAME')
    amounts = payload['price'], payload['size']
    if any(type(value) not in (int, Decimal) for value in amounts):
        raise Skip('INVALID_AMOUNT')
    price, size = (Decimal(value) for value in amounts)
    if (any(not value.is_finite() or len(str(value)) > 160 or abs(value.as_tuple().exponent) > 100
            for value in (price, size)) or not 0 < price < 1 or size <= 0):
        raise Skip('INVALID_AMOUNT')
    key = transaction, wallet, market, token, 'BUY', price_key(price), size
    return Frame(raw, connection, first_mono, first_utc, wallet, market, token,
                 slug, key, stamp * 1000, price)

class Registry:
    def __init__(self):
        self.lock = threading.RLock()
        self.seen = {}
        self.conflicts = {}

    def register(self, frame):
        with self.lock:
            if frame.event_key not in self.seen:
                self.seen[frame.event_key] = frame.source_ms, frame.exact_price
                return None
            observed_time, observed_price = self.seen[frame.event_key]
            reason = ('SOURCE_TIME_CONFLICT' if observed_time != frame.source_ms else
                      'SOURCE_PRICE_CONFLICT' if observed_price != frame.exact_price else None)
            if reason:
                self.conflicts.setdefault(frame.event_key, reason)
                return reason.lower()
            return 'duplicate_frames'

def read_rtds(wallets, queue, stop, deadline, counts, registry):
    context = ssl.create_default_context()
    while not stop.is_set() and time.monotonic() < deadline:
        connection = uuid4().hex
        try:
            with socket.create_connection((RTDS, 443), timeout=3) as raw:
                with context.wrap_socket(raw, server_hostname=RTDS) as conn, conn.makefile('rb', buffering=0) as stream:
                    source.upgrade(conn, stream, RTDS, '/')
                    source.send_frame(conn, b'{"action":"subscribe","subscriptions":[{"topic":"activity","type":"orders_matched"}]}')
                    counts['connections'] += 1
                    last_activity = time.monotonic()
                    ping = last_activity + 5
                    while not stop.is_set() and time.monotonic() < deadline:
                        now = time.monotonic()
                        if now - last_activity >= RTDS_IDLE_SECONDS:
                            counts['RTDS_ACTIVITY_IDLE'] += 1
                            if counts['RTDS_IDLE_RECONNECT'] >= RTDS_IDLE_RECONNECT_LIMIT:
                                # A long-running app retains its registry and queue;
                                # only the public transport reconnects, at a bounded rate.
                                counts['RTDS_IDLE_BACKOFF'] += 1
                                stop.wait(min(30, max(0, deadline - time.monotonic())))
                                break
                            counts['RTDS_IDLE_RECONNECT'] += 1
                            break
                        if now >= ping:
                            source.send_frame(conn, b'PING')
                            ping = time.monotonic() + 5
                        if not conn.pending() and not select.select([conn], [], [], .2)[0]:
                            continue
                        raw_text = source.read_frame(conn, stream)
                        mono, utc = time.monotonic_ns(), time.time_ns() // 1_000_000
                        if raw_text == 'PONG':
                            counts['rtds_pongs'] += 1
                            continue
                        if not raw_text:
                            continue
                        counts['public_frames'] += 1
                        try:
                            frame = json.loads(raw_text, parse_float=Decimal)
                            if frame.get('topic') == 'activity' and frame.get('type') == 'orders_matched':
                                last_activity = mono / 1_000_000_000
                                counts['rtds_activity_frames'] += 1
                            captured = capture_frame(raw_text.encode(), connection, mono, utc, wallets, frame=frame)
                        except Skip as error:
                            counts[error.reason] += 1
                            continue
                        except (KeyError, TypeError, AttributeError, ValueError, ArithmeticError):
                            counts['FORMAT_UNPROVEN'] += 1
                            continue
                        if captured is None:
                            continue
                        reason = registry.register(captured)
                        if reason:
                            counts[reason] += 1
                            continue
                        counts['unique_followed_buys'] += 1
                        age = utc - captured.source_ms
                        if not 0 <= age <= 30_000:
                            counts['SOURCE_TIME_FUTURE' if age < 0 else 'SIGNAL_EXPIRED'] += 1
                            continue
                        try:
                            queue.put_nowait(captured)
                        except Full:
                            counts['QUEUE_CAPACITY'] += 1
        except (OSError, EOFError, ValueError) as error:
            counts['RTDS_' + type(error).__name__] += 1
            stop.wait(5)

def remaining(captured):
    return FIRST_LIMIT_NS - (captured.first_utc - captured.source_ms) * 1_000_000 - (
        time.monotonic_ns() - captured.first_mono)

class BoundedRPC:
    """Share one rate-limit pause across the private worker's RPC clients."""
    rate_limit_lock = threading.Lock()
    rate_limit_until = 0.0
    def __init__(self):
        self.slots = threading.BoundedSemaphore(2)

    def __call__(self, method, params, timeout_seconds):
        if (method, len(params)) not in {('eth_chainId', 0), ('eth_getTransactionReceipt', 1),
                                         ('eth_getBlockByNumber', 2), ('eth_getLogs', 1)}:
            raise ValueError('unexpected Polygon RPC request')
        timeout = min(3, timeout_seconds)
        if timeout <= 0 or not self.slots.acquire(blocking=False):
            raise TimeoutError('Polygon RPC budget unavailable')
        packet = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
        result = Queue(maxsize=1)

        def request():
            try:
                with BoundedRPC.rate_limit_lock:
                    if time.monotonic() < BoundedRPC.rate_limit_until:
                        raise TimeoutError('Polygon RPC cooling down after 429')
                request = Request(RPC, data=packet, headers={
                    'Content-Type': 'application/json', 'Accept': 'application/json',
                    'User-Agent': 'Shadow-closed-demo-read-only/1',
                })
                with source.OPENER.open(request, timeout=timeout) as response:
                    body = response.read(source.MAX_MESSAGE + 1)
                if len(body) > source.MAX_MESSAGE:
                    raise ValueError('oversize RPC response')
                data = json.loads(body)
                if data.get('id') != 1 or 'error' in data or 'result' not in data:
                    raise ValueError('invalid RPC response envelope')
                result.put((True, data['result']))
            except HTTPError as error:
                if error.code == 429:
                    retry_after = (error.headers or {}).get('Retry-After', '')
                    pause = max(60, int(retry_after)) if re.fullmatch(r'[0-9]{1,9}', retry_after) else 60
                    with BoundedRPC.rate_limit_lock:
                        BoundedRPC.rate_limit_until = max(BoundedRPC.rate_limit_until, time.monotonic() + pause)
                    error.close()
                    result.put((False, TimeoutError('Polygon RPC rate limited (429)')))
                else:
                    result.put((False, error))
            except (OSError, ValueError, TypeError, KeyError) as error:
                result.put((False, error))
            finally:
                self.slots.release()

        threading.Thread(target=request, daemon=True).start()
        try:
            ok, value = result.get(timeout=timeout)
        except Empty:
            raise TimeoutError('bounded Polygon RPC timed out') from None
        if not ok:
            raise value
        return value

class ActiveBook:
    def __init__(self, gate, deadline):
        self.gate, self.deadline = gate, deadline
        self.worker = self.stop = self.key = None
        self.frames = self.errors = 0

    def follow(self, market, policy, baseline):
        generation = self.gate.configure(market, policy, baseline)
        key = market.market, market.token, generation
        if key == self.key and self.worker and self.worker.is_alive():
            return
        self.close()
        self.key = key
        self.stop = threading.Event()

        def feed(frame):
            received = self.gate.clock(), self.gate.utc()
            self.gate.publish(frame, generation, 'WS', received=received)
            self.frames += 1

        def invalidate(venue, condition, token, connection, *, stamp=None, terminal=False, disconnected=False):
            if (venue, condition, token) != ('polymarket', market.market, market.token):
                raise GateSkip('BOOK_IDENTITY')
            self.gate.ws_invalidated(generation, stamp=snapshot_time(stamp) if stamp is not None else None,
                                     terminal=terminal, disconnected=disconnected)

        def collect():
            try:
                source.stream_books(market, self.stop, self.deadline, feed, invalidate)
            except (OSError, EOFError, ValueError, KeyError, TypeError, GateSkip):
                self.errors += 1

        self.worker = threading.Thread(target=collect, daemon=True)
        self.worker.start()

    def close(self):
        if self.worker:
            self.stop.set()
            self.worker.join(timeout=4)
            if self.worker.is_alive():
                raise RuntimeError('book reader did not stop')
            self.worker = None

def process(captured, gate, books, rpc, db, stop, registry, deadline, *, writer_factory, buy_budget=BUY_BUDGET, on_refusal=None):
    if remaining(captured) <= 0:
        raise Skip('SIGNAL_EXPIRED')
    market = source.Market('polymarket', captured.market, captured.token, captured.wallet, captured.slug)
    try:
        delay, delay_evidence, policy, baseline, exchange = load_market(market)
    except HTTPError as error:
        raise Skip(f'MARKET_PARAMETERS_HTTP_{error.code}') from None
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as error:
        raise Skip(getattr(error, 'reason', 'MARKET_PARAMETERS_UNPROVEN')) from None
    if remaining(captured) <= 0:
        raise Skip('SIGNAL_EXPIRED')
    books.follow(market, policy, baseline)
    binding = {'wallet': captured.wallet, 'marketId': captured.market, 'outcomeId': captured.token,
               'evidenceRef': 'verified-active-clob-market-and-token:' + captured.market}
    observing = True
    resolver = Resolver.orders_matched_seconds(
        rpc, endpoint_id=RPC, binding=binding,
        mono=lambda: captured.first_mono if observing else time.monotonic_ns(),
        utc=lambda: captured.first_utc if observing else time.time_ns() // 1_000_000,
        wait=stop.wait)
    observed = resolver.observe(captured.raw, captured.connection)
    observing = False
    resolved = resolver.resolve(observed)
    try:
        verify_observed_fee(resolved, policy, exchange)
    except ValueError as error:
        reason = getattr(error, 'reason', 'FEE_EVIDENCE_UNPROVEN')
        if on_refusal is not None:
            on_refusal(resolved, reason)
        raise Skip(reason, getattr(error, 'details', None)) from None
    writer = writer_factory(registry, captured.event_key, deadline)
    try:
        receipt = execute_resolved(writer, rtds_provenance.validate, db, gate, resolved, session_id=SESSION,
                                   owner_id=OWNER, command_id='observed-execution', policy=policy,
                                   delay_ms=delay, delay_evidence=delay_evidence, budget=buy_budget, wait=stop.wait)
    except (Skip, GateSkip) as error:
        if on_refusal is not None:
            on_refusal(resolved, error.reason)
        raise
    finally:
        gate.finish()
    return resolved, receipt, delay
