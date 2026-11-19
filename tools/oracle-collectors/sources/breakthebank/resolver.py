"""RTDS discovery -> unique CTF v2 execution -> finalized Polygon; no network client."""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import base64
import hashlib
import json
import re
import time
from numeric_match import COMPARISON, price_evidence, price_key

EXCHANGES = frozenset({'0xe111180000d2663c0091e4f400237545b87b996b',
                       '0xe2222d279d744050d28e00520010520000310f59'})
MATCH = '0x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c'
FILL = '0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee'
SOURCE = 'polymarket-rtds-finalized-v1'
ORDERS_MATCHED_PROFILE = 'activity-orders-matched-unix-seconds-20261117-v1'
TIMESTAMP_EVIDENCE = 'official-trade-timestamp+retained-sha256:9aa242f71d7af32c90a163aaf4a0ea0453bba6dea540c4623e760e4796eb95f8'


class Skip(Exception):
    def __init__(self, reason, details=None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def q(value):
    value = Fraction(value)
    return {'n': str(value.numerator), 'd': str(value.denominator)}


def hex_id(value, size):
    if not isinstance(value, str) or not re.fullmatch('0x[0-9a-fA-F]{'+str(size*2)+'}', value):
        raise Skip('INVALID_IDENTITY')
    return value.lower()


def uint(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)', value):
        raise Skip('INVALID_RPC_INTEGER')
    result = int(value, 16)
    if result >= 2**256:
        raise Skip('INVALID_RPC_INTEGER')
    return result


def exact(value):
    if type(value) not in (str, int, Decimal):
        raise Skip('LOSSY_NUMBER')
    try:
        number = Decimal(str(value))
        if (not number.is_finite() or len(str(value)) > 160 or
                abs(number.as_tuple().exponent) > 100 or not -80 <= number.adjusted() <= 78):
            raise ValueError()
        result = Fraction(number)
        if abs(result.numerator) >= 2**256 or result.denominator >= 2**256:
            raise ValueError()
        return result
    except (ValueError, ArithmeticError):
        raise Skip('INVALID_NUMBER') from None


def decode(log, word_count, topic_count):
    if not isinstance(log.get('topics'), list) or len(log['topics']) != topic_count:
        raise Skip('EVENT_ABI_MISMATCH')
    topics = [hex_id(v, 32) for v in log['topics']]
    data = log.get('data', '')
    if not re.fullmatch('0x[0-9a-fA-F]{'+str(64*word_count)+'}', data):
        raise Skip('EVENT_ABI_MISMATCH')
    if topics[2][2:26] != '0' * 24:
        raise Skip('EVENT_ABI_MISMATCH')
    values = [int(data[i:i+64], 16) for i in range(2, len(data), 64)]
    return topics, values


@dataclass(frozen=True)
class Observation:
    raw: bytes
    connection: str
    message_type: str
    payload_sha: str
    source_ms: int
    first_ms: int
    first_ns: int
    tx: str
    wallet: str
    market: str
    token: str
    side: str
    quantity: Fraction
    price: Fraction
    key: tuple
    numeric_amounts: bool


@dataclass(frozen=True)
class Resolved:
    event: dict
    first_ns: int
    age_at_first_ms: int
    event_sha: str
    evidence: dict


class Resolver:
    """rpc(method, params, timeout_seconds) is a bounded trusted read capability.

    The timestamp unit is an explicitly evidenced installation parameter, never guessed.
    The narrow orders_matched_seconds factory pins the retained observed profile.
    """
    def __init__(self, rpc, *, endpoint_id, binding, timestamp_unit=None, timestamp_evidence=None,
                 mono=time.monotonic_ns, utc=None, wait=time.sleep, message_types=None):
        self.rpc, self.endpoint = rpc, endpoint_id
        self.binding = binding
        self.unit, self.unit_evidence = timestamp_unit, timestamp_evidence
        self.mono, self.wait = mono, wait
        self.message_types = frozenset(message_types or ('trades', 'orders_matched'))
        self.utc = utc or (lambda: time.time_ns() // 1_000_000)
        self.seen, self.rejected, self.resolved = {}, {}, {}
        self.diagnostics = {}

    @classmethod
    def orders_matched_seconds(cls, rpc, *, endpoint_id, binding, mono=time.monotonic_ns,
                              utc=None, wait=time.sleep):
        return cls(rpc, endpoint_id=endpoint_id, binding=binding, timestamp_unit='seconds',
                   timestamp_evidence=ORDERS_MATCHED_PROFILE+':'+TIMESTAMP_EVIDENCE,
                   mono=mono, utc=utc, wait=wait, message_types=('orders_matched',))

    def observe(self, raw, connection):
        first_ns, first_ms = self.mono(), self.utc()
        if self.unit not in ('seconds', 'milliseconds') or not self.unit_evidence:
            raise Skip('TIMESTAMP_UNITS_UNPROVEN')
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 1_000_000 or not connection:
            raise Skip('INVALID_FRAME')
        def unique_pairs(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise Skip('DUPLICATE_JSON_KEY')
                obj[key] = value
            return obj
        try:
            frame = json.loads(raw, parse_float=Decimal, object_pairs_hook=unique_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(Skip('INVALID_NUMBER')))
            payload = frame['payload']
            if frame['topic'] != 'activity' or frame['type'] not in self.message_types:
                raise Skip('UNSUPPORTED_TOPIC')
            stamp = payload['timestamp']
            if type(stamp) is not int or not 0 <= stamp <= 2**53-1:
                raise Skip('INVALID_SOURCE_TIME')
            source_ms = stamp * (1000 if self.unit == 'seconds' else 1)
            tx, wallet = hex_id(payload['transactionHash'], 32), hex_id(payload['proxyWallet'], 20)
            market, token, side = hex_id(payload['conditionId'], 32), payload['asset'], payload['side']
            if not isinstance(token, str) or not re.fullmatch(r'[1-9][0-9]{0,77}', token) or int(token) >= 2**256:
                raise Skip('INVALID_TOKEN')
            if side not in ('BUY', 'SELL'):
                raise Skip('INVALID_SIDE')
            if not self.binding.get('evidenceRef') or (wallet, market, token) != (
                    self.binding['wallet'].lower(), self.binding['marketId'].lower(), self.binding['outcomeId']):
                raise Skip('MARKET_OR_ACTOR_MISMATCH')
            quantity, price = exact(payload['size']), exact(payload['price'])
            if quantity <= 0 or not 0 < price < 1:
                raise Skip('INVALID_AMOUNT')
        except (KeyError, TypeError, ValueError):
            raise Skip('INVALID_FRAME') from None
        # This discovery key preserves first observation; it is NOT a financial execution ID.
        key = (tx, wallet, market, token, side, quantity, price_key(price))
        if key in self.rejected:
            raise Skip(self.rejected[key])
        prior = self.seen.get(key)
        if prior is not None:
            # One economic notification arriving through two RTDS channels never resets time.
            if prior.source_ms != source_ms:
                self.rejected[key] = 'SOURCE_TIME_CONFLICT'
                raise Skip('SOURCE_TIME_CONFLICT')
            if prior.price != price:
                self.rejected[key] = 'SOURCE_PRICE_CONFLICT'
                raise Skip('SOURCE_PRICE_CONFLICT')
            return prior
        item = Observation(raw, connection, frame['type'], hashlib.sha256(raw).hexdigest(), source_ms,
                           first_ms, first_ns, tx, wallet, market, token, side, quantity, price, key,
                           all(type(payload[k]) in (int, Decimal) for k in ('price', 'size')))
        self.seen[key] = item
        if not 0 <= first_ms-source_ms <= 30000:
            self.rejected[key] = 'SOURCE_TIME_FUTURE' if source_ms > first_ms else 'SIGNAL_EXPIRED'
            raise Skip(self.rejected[key])
        return item

    def remaining(self, observation):
        elapsed = self.mono()-observation.first_ns
        age = observation.first_ms-observation.source_ms
        if elapsed < 0 or not 0 <= age <= 30000 or self.utc() < observation.first_ms:
            raise Skip('CLOCK_OR_SIGNAL_TIME_INVALID')
        remaining = 30_000_000_000 - age*1_000_000 - elapsed
        if remaining <= 0 or self.utc()-observation.source_ms > 30000:
            raise Skip('SIGNAL_EXPIRED')
        return remaining

    def call(self, observation, method, params):
        seconds = min(3, self.remaining(observation)/1_000_000_000)
        try:
            result = self.rpc(method, params, seconds)
        except Exception as error:
            if isinstance(error, Skip):
                raise
            raise Skip('RPC_UNAVAILABLE') from None
        self.remaining(observation)
        return result

    def resolve(self, observation):
        if observation.key in self.resolved:
            return self.resolved[observation.key]
        if observation.key in self.rejected:
            raise Skip(self.rejected[observation.key], self.diagnostics.get(observation.key))
        try:
            result = self._resolve(observation)
            self.resolved[observation.key] = result
            return result
        except Skip as error:
            # The same rejected notification is never made new by waiting or replaying.
            self.rejected[observation.key] = error.reason
            self.diagnostics[observation.key] = error.details or self.diagnostics.get(observation.key, {})
            error.details = self.diagnostics[observation.key]
            raise
        except (KeyError, TypeError, ValueError, ArithmeticError):
            self.rejected[observation.key] = 'MALFORMED_PROOF'
            raise Skip('MALFORMED_PROOF', self.diagnostics.get(observation.key)) from None

    def _resolve(self, o):
        diagnostic = dict(schemaVersion=1, payloadSha256=o.payload_sha,
            sourceTimestampMs=o.source_ms, firstSeenMs=o.first_ms,
            firstSeenMonotonicNs=str(o.first_ns), reportedQuantity=q(o.quantity),
            reportedPrice=q(o.price), candidates=[], candidateRowsTruncated=0)
        self.diagnostics[o.key] = diagnostic
        # One resolve owns one finite polling budget; never retry terminal outcomes.
        polls = 0
        def pending(reason):
            nonlocal polls
            if polls >= 20:
                raise Skip(reason)
            remaining = self.remaining(o)/1_000_000_000
            if remaining <= 0.5:
                raise Skip('SIGNAL_EXPIRED')
            polls += 1
            self.wait(0.5)
            self.remaining(o)

        if self.call(o, 'eth_chainId', []) != '0x89':
            raise Skip('CHAIN_MISMATCH')
        receipt = self.call(o, 'eth_getTransactionReceipt', [o.tx])
        while receipt is None:
            pending('RECEIPT_UNAVAILABLE')
            receipt = self.call(o, 'eth_getTransactionReceipt', [o.tx])
        diagnostic.update(receiptStatusSuccessful=isinstance(receipt,dict) and receipt.get('status')=='0x1',
                          receiptTransactionMatches=isinstance(receipt,dict) and isinstance(receipt.get('transactionHash'),str) and receipt['transactionHash'].lower()==o.tx)
        if not receipt or receipt.get('status') != '0x1' or hex_id(receipt['transactionHash'], 32) != o.tx:
            raise Skip('RECEIPT_NOT_SUCCESSFUL')
        block, block_hash = uint(receipt['blockNumber']), hex_id(receipt['blockHash'], 32)
        logs = receipt['logs']
        if not isinstance(logs, list) or not 1 <= len(logs) <= 4096:
            raise Skip('RECEIPT_LOGS_INVALID')
        diagnostic.update(receiptSha256=sha(receipt), receiptLogsCount=len(logs),
                          receiptBlockNumber=block, receiptBlockHash=block_hash)
        previous_index, candidates, identities = -1, [], []
        expected_side = 0 if o.side == 'BUY' else 1
        for ordinal, log in enumerate(logs):
            index = uint(log['logIndex'])
            log_checks = dict(logOrderValid=index>previous_index, notRemoved=log.get('removed') is not True,
                              transactionMatches=hex_id(log['transactionHash'],32)==o.tx,
                              blockNumberMatches=uint(log['blockNumber'])==block,
                              blockHashMatches=hex_id(log['blockHash'],32)==block_hash)
            if not all(log_checks.values()):
                diagnostic['failedReceiptLog'] = dict(receiptOrdinal=ordinal,logIndex=index,**log_checks)
                raise Skip('RECEIPT_LOG_IDENTITY', diagnostic)
            previous_index = index
            exchange = hex_id(log['address'], 20)
            if exchange not in EXCHANGES:
                diagnostic['unrecognizedExchangeLogs'] = diagnostic.get('unrecognizedExchangeLogs',0)+1
                continue
            if not log.get('topics') or log['topics'][0].lower() != MATCH:
                continue
            topics, values = decode(log, 4, 3)
            side, token, maker, taker = values
            gross, quantity = (maker, taker) if side == 0 else (taker, maker)
            actor_ok, token_ok, side_ok = ('0x'+topics[2][-40:] == o.wallet,
                                           str(token) == o.token, side == expected_side)
            row = dict(receiptOrdinal=ordinal, logIndex=index, actorMatches=actor_ok,
                       tokenMatches=token_ok, sideMatches=side_ok)
            if quantity > 0 and gross > 0:
                exact_quantity, exact_price = Fraction(quantity, 1_000_000), Fraction(gross, quantity)
                row.update(receiptQuantity=q(exact_quantity), receiptGross=q(Fraction(gross,1_000_000)),
                           receiptPrice=q(exact_price), quantityMatches=exact_quantity==o.quantity,
                           priceExactMatches=exact_price==o.price,
                           priceRepresentationMatches=price_evidence(exact_price,o.price) is not None)
            else:
                row['invalidReceiptAmounts'] = True
            if len(diagnostic['candidates']) < 16: diagnostic['candidates'].append(row)
            else: diagnostic['candidateRowsTruncated'] += 1
            if not (actor_ok and token_ok and side_ok): continue
            if quantity <= 0 or gross <= 0 or not 0 < exact_price < 1:
                raise Skip('EVENT_AMOUNT_INVALID', diagnostic)
            candidate = (ordinal, index, exchange, topics, values, gross, quantity)
            identities.append(candidate)
            if exact_quantity == o.quantity and exact_price == o.price:
                candidates.append(candidate)
        diagnostic.update(identityCandidateCount=len(identities), exactCandidateCount=len(candidates))
        comparison = None
        representation = None
        if not candidates and len(identities) == 1 and o.message_type == 'orders_matched' and o.numeric_amounts:
            choice = identities[0]
            gross, quantity = choice[-2:]
            if Fraction(quantity, 1_000_000) == o.quantity:
                representation = price_evidence(Fraction(gross, quantity), o.price)
                if representation is not None:
                    candidates.append(choice)
                    comparison = dict(COMPARISON)
        if len(candidates) != 1:
            raise Skip('MATCH_NOT_FOUND' if not candidates else 'MATCH_AMBIGUOUS', diagnostic)
        ordinal, index, exchange, topics, values, gross, quantity = candidates[0]
        diagnostic.update(selectedReceiptOrdinal=ordinal,
                          amountMode='binary64-shortest' if comparison else 'exact')
        fills = []
        for log in logs:
            if log['address'].lower() == exchange and log.get('topics') and log['topics'][0].lower() == FILL:
                ft, fv = decode(log, 7, 4)
                if ft[1:3] == topics[1:3] and fv[:4] == values and uint(log['logIndex']) < index:
                    fills.append(log)
        if len(fills) != 1:
            raise Skip('TAKER_FILL_NOT_UNIQUE')
        canonical_block = self.call(o, 'eth_getBlockByNumber', [hex(block), False])
        if not canonical_block or uint(canonical_block['number']) != block or hex_id(canonical_block['hash'], 32) != block_hash:
            raise Skip('CANONICAL_BLOCK_MISMATCH')
        block_ms = uint(canonical_block['timestamp'])*1000
        finalized = self.call(o, 'eth_getBlockByNumber', ['finalized', False])
        while finalized is None or uint(finalized['number']) < block:
            pending('FINALITY_NOT_REACHED')
            finalized = self.call(o, 'eth_getBlockByNumber', ['finalized', False])
        fn, fh = uint(finalized['number']), hex_id(finalized['hash'], 32)
        if fn == block and fh != block_hash:
            raise Skip('FINALIZED_BLOCK_MISMATCH')
        # Recheck the specific canonical inclusion after reading the finalized head.
        canonical_after = self.call(o, 'eth_getBlockByNumber', [hex(block), False])
        receipt_after = self.call(o, 'eth_getTransactionReceipt', [o.tx])
        if canonical_after != canonical_block or receipt_after != receipt:
            raise Skip('INCLUSION_CHANGED')
        checked_ms, checked_ns = self.utc(), self.mono()
        self.remaining(o)
        if block_ms > checked_ms:
            raise Skip('BLOCK_TIME_FUTURE_AT_FINALITY')
        match = dict(chainId=137, exchange=exchange, transactionHash=o.tx, receiptOrdinal=ordinal,
                     logIndex=index, wallet=o.wallet, marketId=o.market, outcomeId=o.token, side=o.side,
                     quantity=q(Fraction(quantity, 1_000_000)), gross=q(Fraction(gross, 1_000_000)), matchingCount=1)
        execution_id = sha(['polygon-orders-matched-v1',137,exchange,o.tx,ordinal,o.wallet,o.market,o.token,o.side])
        fingerprint = sha([execution_id, match['quantity'], match['gross']])
        evidence = dict(rawFrameBase64=base64.b64encode(o.raw).decode(), timestampUnit=self.unit,
                        timestampEvidence=self.unit_evidence, marketBinding=self.binding,
                        endpoint=self.endpoint, receipt=receipt, canonicalBlock=canonical_block,
                        finalizedBlock=finalized)
        if comparison:
            evidence.update(amountComparison=comparison, priceRepresentation=representation)
        provenance = dict(source=SOURCE, evidenceRef=sha(evidence),
            rtds=dict(topic='activity', type=o.message_type, payloadSha256=o.payload_sha,
                      connectionId=o.connection, sourceTimestampMs=o.source_ms, firstSeenMs=o.first_ms,
                      firstSeenMonotonicNs=str(o.first_ns), transactionHash=o.tx, wallet=o.wallet,
                      marketId=o.market, outcomeId=o.token, side=o.side,
                      reportedQuantity=q(o.quantity), reportedPrice=q(o.price)), match=match,
            finality=dict(receiptStatus=1, receiptSha256=sha(receipt), blockNumber=block, blockHash=block_hash,
                          blockTimestampMs=block_ms, canonicalBlockHash=block_hash,
                          finalizedBlockNumber=fn, finalizedBlockHash=fh, checkedAtMs=checked_ms,
                          checkedMonotonicNs=str(checked_ns), rpcEvidenceRef=self.endpoint))
        if comparison: provenance['amountComparison'] = comparison
        event = dict(executionId=execution_id, fingerprint=fingerprint, venue='polymarket', marketId=o.market,
                     outcomeId=o.token, side=o.side, signalAtMs=o.source_ms, firstSeenMs=o.first_ms,
                     chain=None, venueReceipt=provenance)
        return Resolved(event, o.first_ns, o.first_ms-o.source_ms, sha(event), evidence)
