"""Bounded, read-only market inputs for the isolated Shadow acceptance run."""
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
import select
import socket
import ssl
import struct
import time
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

POLY_WS = 'ws-subscriptions-clob.polymarket.com'
LIMITLESS_WS = 'ws.limitless.exchange'
POLY_TRADES = 'https://data-api.polymarket.com/v2/trades'
POLY_CLOB = 'https://clob.polymarket.com'
POLY_MARKETS = 'https://gamma-api.polymarket.com'
LIMITLESS_API = 'https://api.limitless.exchange'
POLY_MARKET_DOC = 'https://docs.polymarket.com/api-reference/markets/get-clob-market-info'
POLY_ORDER_DOC = 'https://docs.polymarket.com/trading/place-orders'
LIMITLESS_ORDER_DOC = 'https://docs.limitless.exchange/api-reference/trading/create-order'
LIMITLESS_FEE_DOC = 'https://docs.limitless.exchange/developers/migrate-to-new-trading-venues'
RPC = ('https://base.drpc.org', 'https://mainnet.base.org')
MATCH = '0x363a587c4640b524767666acd46b6600a7308a3692b1c11c2f5a930318e04866'
FEE_MODULES = {
    '0x01b7df643247b377d5c39fcc40b9c28b4a827524',
    '0x7b6ffe5ba8b5ec7afb0aabae629d12da5bc62565',
}
CTF = '0xc9c98965297bc527861c898329ee280632b76e18'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
SINGLE = '0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62'
BATCH = '0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb'
SCALE = 1_000_000
MAX_MESSAGE = 1_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args):
        return None


OPENER = build_opener(NoRedirect())


@dataclass(frozen=True)
class Market:
    venue: str
    market: str
    token: str
    wallet: str
    slug: str = ''
    fee_module: str = ''
    side: str = 'BUY'

    def __post_init__(self):
        if self.venue not in {'polymarket', 'limitless'} or self.side not in {'BUY', 'SELL'}:
            raise ValueError('unsupported venue or side')
        int(self.market, 16)
        if len(self.market) != 66 or not self.market.startswith('0x'):
            raise ValueError('market condition must be a 32-byte hex value')
        int(self.wallet, 16)
        if len(self.wallet) != 42 or not self.wallet.startswith('0x'):
            raise ValueError('wallet must be a 20-byte hex value')
        if not self.token.isascii() or not self.token.isdecimal() or not 0 < int(self.token) < 2**256:
            raise ValueError('token must be a positive uint256 decimal string')
        if self.venue == 'limitless' and (not self.slug or self.fee_module not in FEE_MODULES):
            raise ValueError('Limitless requires a verified market slug and collateral fee module')


def json_read(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=data, headers={
        'Accept': 'application/json', 'Content-Type': 'application/json',
        'User-Agent': 'Shadow-closed-demo-read-only/1',
    })
    with OPENER.open(request, timeout=3) as response:
        body = response.read(MAX_MESSAGE + 1)
    if len(body) > MAX_MESSAGE:
        raise ValueError('oversized source response')
    return json.loads(body, parse_float=Decimal)


def market_parameters(market, *, btc_single_price=False):
    """Return an evidenced test policy or fail closed before observing a trade."""
    if market.venue == 'limitless':
        detail = json_read(f'{LIMITLESS_API}/markets/{quote(market.slug, safe="")}')
        venue, tokens = detail['venue'], detail['tokens']
        enabled = detail['metadata']['fee']
        if (detail['conditionId'] != market.market or detail['slug'] != market.slug
                or detail['tradeType'] != 'clob' or detail['expired'] is not False
                or detail['status'] not in {'CREATED', 'FUNDED'} or tokens['yes'] != market.token
                or venue['feeModuleType'] != 'COLLATERAL' or venue['feeModule'].lower() != market.fee_module
                or type(enabled) is not bool or detail['collateralToken']['decimals'] != 6):
            raise ValueError('Limitless market parameters or YES-side book identity unproven')
        policy = {'profile': 'isolated-estimated', 'priceTick': '0.001', 'quantityStep': '0.000001',
                  'minimumQuantity': '0' if market.side == 'BUY' else '0.0001',
                  'minimumNotional': '0.0001' if market.side == 'BUY' else '0',
                  'feeModel': 'limitless-collateral-single-match' if enabled else 'verified-zero',
                  'feeRate': '0.05' if enabled else '0',
                  'feeRounding': 'half-up-5dp' if enabled else 'exact-zero',
                  'orderShape': 'limitless-collateral-fak', 'marketTitle': detail['title'], 'outcomeTitle': 'Yes',
                  'marketExpiresAtMs': detail.get('expirationTimestamp'),
                  'evidenceRef': [LIMITLESS_ORDER_DOC, LIMITLESS_FEE_DOC]}
        return 0, 'https://docs.limitless.exchange/user-guide/market-orders', policy

    # HTTP metadata is used only for policy, never as the live execution book.
    if not market.slug:
        raise ValueError('Polymarket exact market slug required for market policy')
    details = json_read(f'{POLY_MARKETS}/markets?{urlencode({"slug": market.slug})}')
    detail = next((item for item in details if item.get('conditionId') == market.market), None)
    info = json_read(f'{POLY_CLOB}/clob-markets/{market.market}')
    book = json_read(f'{POLY_CLOB}/book?{urlencode({"token_id": market.token})}')
    if (not detail or detail['acceptingOrders'] is not True or detail['closed'] is True
            or book['market'] != market.market or book['asset_id'] != market.token
            or not any(row['t'] == market.token for row in info['t'])):
        raise ValueError('Polymarket market identity or tradability unproven')
    delay = info.get('itode', False)
    seconds = detail.get('secondsDelay')
    # A different published delay must be reconciled instead of silently selecting one.
    if type(delay) is not bool or seconds not in (None, 0):
        raise ValueError('Polymarket execution delay unproven')
    tick = Decimal(str(info['mts']))
    minimum = Decimal(str(info['mos']))
    precisions = {'0.1': 3, '0.01': 4, '0.005': 5, '0.0025': 6, '0.001': 5, '0.0001': 6}
    if (format(tick, 'f') not in precisions or minimum <= 0
            or Decimal(str(book['tick_size'])) != tick or Decimal(str(book['min_order_size'])) != minimum):
        raise ValueError('Polymarket tick or order minimum unproven')
    curve = info.get('fd') or {}
    curve_rate = Decimal(str(curve.get('r', '0')))
    rate = json_read(f'{POLY_CLOB}/fee-rate?{urlencode({"token_id": market.token})}')
    free = detail.get('feesEnabled') is False and curve_rate == 0 and rate.get('base_fee') == 0
    # The reference BUY receipts came from the documented CTF exchanges, whose book omits version.
    ctf_book = (book.get('version') is None and type(book.get('neg_risk')) is bool
                and detail.get('negRisk', book['neg_risk']) == book['neg_risk'])
    verified_btc = (btc_single_price and market.side == 'BUY' and market.slug.startswith('btc-updown-15m-')
                    and ctf_book and detail.get('feesEnabled') is not False
                    and curve_rate == Decimal('0.07') and curve.get('e') == 1 and curve.get('to') is True
                    and info.get('tbf') == rate.get('base_fee') == 1000 and delay is True)
    if not (free or verified_btc):
        raise ValueError('Polymarket fee parameters or tested rounding are unproven')
    step = Decimal('0.01') if market.side == 'SELL' else Decimal(10) ** -precisions[format(tick, 'f')]
    outcome = next(row['o'] for row in info['t'] if row['t'] == market.token)
    policy = {'profile': 'isolated-estimated', 'priceTick': format(tick, 'f'), 'quantityStep': format(step, 'f'),
              'minimumQuantity': format(minimum, 'f'), 'minimumNotional': '0',
              'feeModel': 'verified-zero' if free else 'polymarket-v2-single-match',
              'feeRate': '0' if free else '0.07', 'feeRounding': 'exact-zero' if free else 'floor-5dp',
              'orderShape': 'polymarket-market-fak', 'marketTitle': detail['question'], 'outcomeTitle': outcome,
              'evidenceRef': [POLY_MARKET_DOC, POLY_ORDER_DOC, 'https://docs.polymarket.com/trading/fees']}
    if market.slug.startswith('btc-updown-15m-'):
        policy['marketExpiresAtMs'] = (int(market.slug.rsplit('-', 1)[1]) + 900) * 1000
    if verified_btc:
        policy['evidenceRef'].append('observed-polymarket-btc15m-buy:sha256:0f077a7636335478d6bd605d68a3ef3f29c14ec031199fb8f0a090b5b1a6478c')
    return (250 if delay else 0), POLY_MARKET_DOC, policy


def rpc(method, *params, endpoint=RPC[0]):
    if method not in {'eth_getBlockByNumber', 'eth_getLogs', 'eth_getTransactionReceipt'} or endpoint not in RPC:
        raise ValueError('unsupported RPC operation')
    response = json_read(endpoint, {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    if response.get('id') != 1 or 'error' in response or 'result' not in response:
        raise ValueError('invalid RPC response')
    return response['result']


def witness(method, *params):
    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(rpc, method, *params, endpoint=RPC[0])
        right = pool.submit(rpc, method, *params, endpoint=RPC[1])
        return left.result(), right.result()


def send_frame(conn, data, opcode=1):
    if len(data) > 65535:
        raise ValueError('oversized outbound frame')
    size = bytes([128 + len(data)]) if len(data) < 126 else b'\xfe' + struct.pack('!H', len(data))
    mask = os.urandom(4)
    conn.sendall(bytes([128 + opcode]) + size + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(data)))


def read_exact(stream, size):
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            raise EOFError('truncated websocket frame')
        data.extend(chunk)
    return bytes(data)


def read_frame(conn, stream):
    first, second = read_exact(stream, 2)
    size = second & 127
    if size >= 126:
        size = int.from_bytes(read_exact(stream, 2 if size == 126 else 8), 'big')
    if first & 112 or not first & 128 or second & 128 or size > MAX_MESSAGE:
        raise ValueError('unsupported websocket frame')
    opcode = first & 15
    if opcode not in (1, 8, 9, 10) or (opcode >= 8 and size > 125):
        raise ValueError('unsupported websocket opcode')
    data = read_exact(stream, size)
    if opcode == 8:
        raise EOFError('websocket closed')
    if opcode == 9:
        send_frame(conn, data, 10)
    return data.decode('utf-8') if opcode == 1 else None


def upgrade(conn, stream, host, path):
    key = base64.b64encode(os.urandom(16)).decode()
    conn.sendall((
        f'GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n'
        f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
    ).encode())
    status = stream.readline(4096).decode().split()
    headers = {}
    for _ in range(40):
        line = stream.readline(4096)
        if line == b'\r\n':
            break
        name, value = line.decode().split(':', 1)
        headers[name.lower()] = value.strip()
    else:
        raise ValueError('oversized websocket upgrade headers')
    expected = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
    if status[:2] != ['HTTP/1.1', '101'] or headers.get('sec-websocket-accept') != expected:
        raise ValueError('invalid websocket upgrade')


def levels(rows, *, polymarket, bids):
    if not isinstance(rows, list):
        raise ValueError('incomplete book')
    result = {}
    for row in rows:
        price = Decimal(str(row['price']))
        size = Decimal(str(row['size'])) * (SCALE if polymarket else 1)
        if not 0 < price < 1 or not 0 < size <= 2**63 - 1 or size != size.to_integral_value() or price in result:
            raise ValueError('invalid level in complete book')
        result[price] = int(size)
    return [[format(price, 'f'), result[price]] for price in sorted(result, reverse=bids)]


def book_message(market, connection, timestamp, book, version=None, digest=None):
    return {
        'venue': market.venue, 'market': market.market, 'token': market.token, 'connectionId': connection,
        'version': version, 'hash': digest, 'sourceTimestamp': timestamp,
        'bids': levels(book['bids'], polymarket=market.venue == 'polymarket', bids=True),
        'asks': levels(book['asks'], polymarket=market.venue == 'polymarket', bids=False),
        'evidenceRef': f'{market.venue}:ws:{connection}:{version if version is not None else digest}',
    }


def poly_books(message, market, connection, book, invalidate):
    if message == 'PONG':
        return
    events = json.loads(message, parse_float=Decimal)
    for event in events if isinstance(events, list) else [events]:
        if event.get('market') != market.market:
            continue
        event_type = event.get('event_type')
        token = event.get('asset_id')
        if event_type == 'price_change' and any(change.get('asset_id') == market.token for change in event['price_changes']):
            invalidate(market.venue, market.market, market.token, connection, stamp=int(event['timestamp']))
        elif event_type in {'tick_size_change', 'market_resolved'} and (
            token == market.token or market.token in event.get('assets_ids', [])
        ):
            invalidate(market.venue, market.market, market.token, connection, terminal=True)
            raise ValueError('market parameters changed during scenario')
        elif event_type == 'book' and token == market.token:
            stamp, digest = str(event['timestamp']), event['hash']
            if len(stamp) != 13 or not stamp.isdecimal() or not isinstance(digest, str) or not digest:
                raise ValueError('invalid Polymarket book identity')
            book(book_message(market, connection, int(stamp), event, digest=digest))


def limitless_books(message, market, connection, send, book):
    if message.startswith('0'):
        send(b'40/markets,')
    elif message.startswith('40/markets,'):
        send(('42/markets,' + json.dumps(['subscribe_market_prices', {'marketSlugs': [market.slug]}])).encode())
    elif message.startswith('2'):
        send(('3' + message[1:]).encode())
    elif message.startswith(('41/markets,', '44/markets,')):
        raise ValueError('Limitless market subscription closed')
    elif message.startswith('42/markets,'):
        event, data = json.loads(message.split(',', 1)[1], parse_float=Decimal)
        if event != 'orderbookUpdate' or data.get('marketSlug') != market.slug:
            return
        orderbook = data['orderbook']
        if str(orderbook.get('tokenId')) != market.token:
            return
        version = data['version']
        timestamp = datetime.fromisoformat(data['timestamp'])
        if type(version) is not int or version < 0 or timestamp.tzinfo is None:
            raise ValueError('invalid Limitless book identity')
        book(book_message(market, connection, data['timestamp'], orderbook, version=version))


def stream_books(market, stop, deadline, book, invalidate):
    """Keep the subscription open during source polling and decision commit."""
    host, path = ((POLY_WS, '/ws/market') if market.venue == 'polymarket'
                  else (LIMITLESS_WS, '/socket.io/?EIO=4&transport=websocket'))
    connection = uuid4().hex
    try:
        with socket.create_connection((host, 443), timeout=3) as raw:
            with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as conn:
                with conn.makefile('rb', buffering=0) as stream:
                    upgrade(conn, stream, host, path)
                    if market.venue == 'polymarket':
                        send_frame(conn, json.dumps({'assets_ids': [market.token], 'type': 'market'}).encode())
                    ping = time.monotonic() + 8
                    while not stop.is_set() and time.monotonic() < deadline:
                        now = time.monotonic()
                        if market.venue == 'polymarket' and now >= ping:
                            send_frame(conn, b'PING')
                            ping = now + 8
                        if not conn.pending() and not select.select([conn], [], [], 0.1)[0]:
                            continue
                        message = read_frame(conn, stream)
                        if message is None:
                            continue
                        if market.venue == 'polymarket':
                            poly_books(message, market, connection, book, invalidate)
                        else:
                            limitless_books(message, market, connection, lambda data: send_frame(conn, data), book)
    finally:
        invalidate(market.venue, market.market, market.token, connection, disconnected=True)


def utc_ms(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds')


def signal(market, tx, source_ms, observation, **metadata):
    mono_ns, utc = observation
    age = utc - source_ms
    if not 0 <= age <= 30_000:
        return None
    return {
        'venue': market.venue, 'market': market.market, 'token': market.token,
        'wallet': market.wallet, 'side': market.side, 'transaction': tx,
        'firstObservedMonotonicNs': mono_ns, 'firstObservedUtc': utc_ms(utc), 'firstSeenMs': utc,
        'sourceOccurredUtc': utc_ms(source_ms), 'sourceTimestampMs': source_ms,
        'ageAtFirstObservationMs': age,
        'evidenceRef': f'{market.venue}:match:{tx}', **metadata,
    }


def observe():
    return time.monotonic_ns(), time.time_ns() // 1_000_000


def poly_trade_page(condition, *, side='BUY'):
    query = urlencode({'condition': condition, 'taker_only': 'true', 'side': side, 'limit': 30})
    return json_read(f'{POLY_TRADES}?{query}')['data']


def poly_signals(market, started_ms, rows=None, observation=None):
    if rows is None:
        rows = poly_trade_page(market.market, side=market.side)
        observation = observe()
    for row in sorted(rows, key=lambda item: item.get('timestamp', 0)):
        txn = row.get('transaction_hash')
        stamp = row.get('timestamp')
        if (row.get('condition_id') != market.market or str(row.get('token_id')) != market.token
                or str(row.get('proxy_wallet', '')).lower() != market.wallet.lower()
                or row.get('side') != market.side or type(stamp) is not int or stamp * 1000 < started_ms
                or not isinstance(txn, str) or len(txn) != 66):
            continue
        amount, price = Decimal(str(row['size'])), Decimal(str(row['price']))
        if not amount.is_finite() or not price.is_finite() or not 0 < price < 1 or amount <= 0:
            continue
        # This feed has no documented log index. Keep the platform field when present.
        event_fields = [txn, market.market, market.token, market.wallet.lower(), market.side, stamp,
                        str(amount.normalize()), str(price.normalize())]
        execution_id = hashlib.sha256(json.dumps(event_fields, separators=(',', ':')).encode()).hexdigest()
        if out := signal(market, txn.lower(), stamp * 1000, observation, executionId=execution_id,
                         fingerprint=execution_id,
                         logIndex=row.get('log_index'), chainId=137,
                         sourcePrice=format(price, 'f'), sourceShares=format(amount, 'f')):
            yield out


def words(data):
    if not data.startswith('0x') or (len(data) - 2) % 64:
        raise ValueError('invalid ABI words')
    return [int(data[i:i + 64], 16) for i in range(2, len(data), 64)]


def address_topic(wallet):
    return '0x' + wallet.lower()[2:].zfill(64)


def transfer_qty(log, token):
    values = words(log['data'])
    if log['topics'][0] == SINGLE:
        token_id, amount = values
        return amount if token_id == token else 0
    ids, amounts = (v // 32 for v in values[:2])
    count = values[ids]
    if count != values[amounts] or count > 256 or max(ids, amounts) + count >= len(values):
        raise ValueError('invalid ERC-1155 batch transfer')
    return sum(value for asset, value in zip(values[ids + 1:ids + 1 + count],
               values[amounts + 1:amounts + 1 + count]) if asset == token)


def receipt_matches(log, receipt, market):
    if (not receipt or receipt.get('status') != '0x1' or receipt.get('blockHash') != log['blockHash']
            or receipt.get('transactionHash') != log['transactionHash']
            or receipt.get('blockNumber') != log['blockNumber']):
        return False
    matches = [item for item in receipt['logs'] if item['logIndex'] == log['logIndex']]
    if len(matches) != 1 or any(matches[0].get(field) != log[field] for field in ('address', 'topics', 'data')):
        return False
    wallet = address_topic(market.wallet)
    token = int(market.token)
    side, _fill, notional, shares, fee, *_ = words(log['data'])
    share_delta = cash_delta = 0
    for item in receipt['logs']:
        topics = item['topics']
        if item['address'].lower() == CTF and len(topics) == 4 and topics[0] in {SINGLE, BATCH}:
            direction = (topics[3].lower() == wallet) - (topics[2].lower() == wallet)
            if direction:
                share_delta += transfer_qty(item, token) * direction
        elif item['address'].lower() == USDC and len(topics) == 3 and topics[0] == TRANSFER:
            direction = (topics[2].lower() == wallet) - (topics[1].lower() == wallet)
            if direction:
                cash_delta += int(item['data'], 16) * direction
    expected = (shares, -notional - fee) if side == 0 else (-shares, notional - fee)
    return (share_delta, cash_delta) == expected


def limitless_signals(market, started_ms, seen, logs=None, observation=None):
    expected_side = 0 if market.side == 'BUY' else 1
    topics = [MATCH, None, address_topic(market.wallet), f'0x{int(market.token):064x}']
    if logs is None:
        head = rpc('eth_getBlockByNumber', 'latest', False)
        high = int(head['number'], 16)
        logs = rpc('eth_getLogs', {'address': market.fee_module, 'topics': topics,
                                  'fromBlock': hex(max(0, high - 15)), 'toBlock': hex(high)})
        observation = observe()
    for log in logs:
        tx, index, block_hash = (log[key] for key in ('transactionHash', 'logIndex', 'blockHash'))
        if log.get('removed') or log['address'].lower() != market.fee_module:
            continue
        log_topics = log['topics']
        values = words(log['data'])
        if (len(log_topics) != 4 or log_topics[0] != MATCH or log_topics[2:] != topics[2:]
                or len(values) != 8 or values[0] != expected_side or min(values[2:4]) <= 0):
            continue
        key = (market.fee_module, log_topics[1], tx)
        # Transient witnesses may recover; preserve the first read time on subsequent polls.
        first = seen.setdefault(key, observation)
        if observation[0] - first[0] > 30_000_000_000:
            continue
        with ThreadPoolExecutor(max_workers=2) as pool:
            consensus = pool.submit(witness, 'eth_getBlockByNumber', log['blockNumber'], False)
            lookup = pool.submit(rpc, 'eth_getTransactionReceipt', tx)
            blocks, receipt = consensus.result(), lookup.result()
        if not all(block and block.get('hash') == block_hash for block in blocks):
            continue
        stamps = [int(block['timestamp'], 16) * 1000 for block in blocks]
        if stamps[0] != stamps[1] or stamps[0] < started_ms or not receipt_matches(log, receipt, market):
            continue
        fingerprint_fields = [tx, log_topics[1], market.fee_module, market.wallet.lower(),
                              market.market, market.token, market.side, *values[:5]]
        fingerprint = hashlib.sha256(json.dumps(fingerprint_fields, separators=(',', ':')).encode()).hexdigest()
        if out := signal(market, tx, stamps[0], first, logIndex=int(index, 16), chainId=8453,
                         executionId=f'base:8453:{tx}:{log_topics[1]}', fingerprint=fingerprint,
                         blockNumber=int(log['blockNumber'], 16), blockHash=block_hash,
                         rpcEvidence={'agree': True, 'receiptVerified': True, 'providers': list(RPC),
                                      'blockHashes': [block['hash'] for block in blocks]},
                         sourceLog=log, sourceReceipt=receipt,
                         sourceTakerNotionalMicros=values[2], sourceTakerSharesMicros=values[3],
                         sourceTakerFeeMicros=values[4]):
            yield out


def wait_for_signal(market, stop, deadline, started_ms):
    """Return one new eligible signal, or None at the bounded deadline."""
    seen = {}
    while not stop.is_set() and time.monotonic() < deadline:
        candidates = (poly_signals(market, started_ms) if market.venue == 'polymarket'
                      else limitless_signals(market, started_ms, seen))
        for match in candidates:
            if not stop.is_set() and time.monotonic() < deadline:
                return match
        stop.wait(min(2, max(0, deadline - time.monotonic())))
    return None


def ledger_event(match):
    event = {'executionId': match['executionId'], 'fingerprint': match['fingerprint'],
             'venue': match['venue'], 'marketId': match['market'], 'outcomeId': match['token'],
             'side': match['side'], 'signalAtMs': match['sourceTimestampMs'],
             'firstSeenMs': match['firstSeenMs'], 'chain': None}
    if match['venue'] == 'limitless':
        event['chain'] = {
            'chainId': match['chainId'], 'blockNumber': match['blockNumber'], 'blockHash': match['blockHash'],
            'transactionHash': match['transaction'], 'logIndex': match['logIndex'],
            'rpcBlockHashes': match['rpcEvidence']['blockHashes'],
        }
    else:
        event['venueReceipt'] = {
            'source': 'polymarket-data-api-v2', 'evidenceRef': match['evidenceRef'],
            'transactionHash': match['transaction'], 'wallet': match['wallet'],
            'sourceTimestamp': match['sourceTimestampMs'] // 1000,
            'reportedQuantity': match['sourceShares'], 'reportedPrice': match['sourcePrice'],
        }
    return event


def base_state(event, query=witness):
    """Read-only comparison for the same accepted Base execution."""
    tx, number, original = (event[k] for k in ('transaction', 'blockNumber', 'blockHash'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        canonical = pool.submit(query, 'eth_getBlockByNumber', hex(number), False)
        finalized = pool.submit(query, 'eth_getBlockByNumber', 'finalized', False)
        receipts = pool.submit(query, 'eth_getTransactionReceipt', tx)
        blocks, final_heads, results = canonical.result(), finalized.result(), receipts.result()
    hashes = [block.get('hash') if block else None for block in blocks]
    receipt_blocks = [result.get('blockHash') if result else None for result in results]
    final_numbers = [int(head['number'], 16) if head else None for head in final_heads]
    if hashes == [original, original] and receipt_blocks == [original, original]:
        matches = [log for log in results[0]['logs'] if int(log['logIndex'], 16) == event['logIndex']]
        peer = [log for log in results[1]['logs'] if int(log['logIndex'], 16) == event['logIndex']]
        if len(matches) == 1 and matches == peer and all(r['status'] == '0x1' for r in results):
            if all(height is not None and height >= number for height in final_numbers):
                return 'finalized', hashes, final_numbers
    if hashes[0] and hashes[0] == hashes[1] and hashes[0] != original and receipt_blocks == [None, None]:
        return 'reverted', hashes, final_numbers
    return 'pending', hashes, final_numbers
