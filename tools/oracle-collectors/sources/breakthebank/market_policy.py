"""Read a Polymarket BUY policy and bind its fees to the observed CTF form."""
from decimal import Decimal
from urllib.parse import urlencode

import source
from book_engine import rational
from published_delay import MarketParameterError, delay_for_market
from resolver import FILL, MATCH, decode, uint

FEE_DOC = 'https://docs.polymarket.com/trading/fees'
BOOK_DOC = 'https://docs.polymarket.com/api-reference/market-data/get-order-book'
CTF_EXCHANGES = {
    False: '0xe111180000d2663c0091e4f400237545b87b996b',
    True: '0xe2222d279d744050d28e00520010520000310f59',
}
SPORTS_FEE_SHA = 'c9aafd8ef9f35c5c589701bd657c9d4f622d3e32ed4afd5f8f8ef071f2dac33e'
SPORTS_CONTRACT_SHA = '6a53abd5a28115cf542766536de12eb3e4bc73f4bbf65d6ac2d68c856634017b'
STANDARD_FEE_SHA = '0f077a7636335478d6bd605d68a3ef3f29c14ec031199fb8f0a090b5b1a6478c'
STANDARD_CONTRACT_SHA = '535168ae633a78d77129b50d4ee58998d6c661fefcdf36d00b38ab2dabeb46fe'
# Standard CTF, Polygon block 97709619, OrdersMatched log 269.
STANDARD_CRYPTO_001_FEE_SHA = '41ed6e544c8f2cb62a69e0ba7059519a4648fd6dc48edded27d63a8b8a9e2448'
VERIFIED_FLOOR = {
    (CTF_EXCHANGES[False], rational('0.01')): (STANDARD_CRYPTO_001_FEE_SHA, STANDARD_CONTRACT_SHA),
    (CTF_EXCHANGES[True], rational('0.05')): (SPORTS_FEE_SHA, SPORTS_CONTRACT_SHA),
    (CTF_EXCHANGES[False], rational('0.07')): (STANDARD_FEE_SHA, STANDARD_CONTRACT_SHA),
}
QUANTITY_PRECISION = {'0.1': 3, '0.01': 4, '0.005': 5, '0.0025': 6, '0.001': 5, '0.0001': 6}


def load_market(market):
    details = source.json_read(f'{source.POLY_MARKETS}/markets?{urlencode({"slug": market.slug})}')
    detail = next((row for row in details if row.get('conditionId') == market.market), None)
    if (not detail or detail.get('slug') != market.slug or detail.get('active') is not True
            or detail.get('acceptingOrders') is not True or detail.get('closed') is not False):
        raise MarketParameterError('MARKET_IDENTITY_OR_TRADABILITY_UNPROVEN')
    info = source.json_read(f'{source.POLY_CLOB}/clob-markets/{market.market}')
    outcomes = [row for row in info['t'] if row['t'] == market.token]
    if len(outcomes) != 1:
        raise MarketParameterError('MARKET_IDENTITY_OR_TRADABILITY_UNPROVEN')
    token = urlencode({'token_id': market.token})
    book = source.json_read(f'{source.POLY_CLOB}/book?{token}')
    if book.get('market') != market.market or book.get('asset_id') != market.token:
        raise MarketParameterError('MARKET_BOOK_IDENTITY_UNPROVEN')
    delay, delay_ref = delay_for_market(detail, info)
    tick, minimum = Decimal(str(info['mts'])), Decimal(str(info['mos']))
    tick_text = format(tick, 'f')
    if (tick_text not in QUANTITY_PRECISION or not minimum.is_finite() or minimum <= 0
            or Decimal(str(book['tick_size'])) != tick or Decimal(str(book['min_order_size'])) != minimum):
        raise MarketParameterError('MARKET_TICK_OR_MINIMUM_UNPROVEN')
    neg_risk = book.get('neg_risk')
    if (type(neg_risk) is not bool or detail.get('negRisk') is not neg_risk
            or book.get('version') is not None or market.side != 'BUY'):
        raise MarketParameterError('MARKET_CONTRACT_SHAPE_UNPROVEN')
    curve = info.get('fd') or {}
    rate = Decimal(str(curve.get('r', '0')))
    token_base = source.json_read(f'{source.POLY_CLOB}/fee-rate?{token}').get('base_fee')
    free = detail.get('feesEnabled') is False and rate == 0 and type(token_base) is int and token_base == 0
    paid = (detail.get('feesEnabled') is True and rate.is_finite() and 0 < rate <= 1
            and type(curve.get('e')) is int and curve['e'] == 1 and curve.get('to') is True
            and type(token_base) is int and token_base == 1000 and type(info.get('tbf')) is int
            and info['tbf'] == token_base)
    if not (free or paid):
        raise MarketParameterError('MARKET_FEE_PROFILE_UNPROVEN')
    policy = {'profile': 'isolated-estimated', 'priceTick': tick_text,
              'quantityStep': format(Decimal(10) ** -QUANTITY_PRECISION[tick_text], 'f'),
              'minimumQuantity': format(minimum, 'f'), 'minimumNotional': '0',
              'feeModel': 'verified-zero' if free else 'polymarket-v2-single-match',
              'feeRate': '0' if free else format(rate, 'f'),
              'feeRounding': 'exact-zero' if free else 'floor-5dp',
              'orderShape': 'polymarket-market-fak', 'marketTitle': detail['question'],
              'outcomeTitle': outcomes[0]['o'], 'evidenceRef': [source.POLY_MARKET_DOC, FEE_DOC, BOOK_DOC]}
    return delay, delay_ref, policy, book, CTF_EXCHANGES[neg_risk]


class FeeEvidenceError(MarketParameterError):
    def __init__(self, reason, **details):
        super().__init__(reason)
        self.details = details


def verify_observed_fee(resolved, policy, exchange):
    """Bind the virtual fee model to an attested contract and rate."""
    match = resolved.event['venueReceipt']['match']
    if match['exchange'] != exchange:
        raise FeeEvidenceError('FEE_CONTRACT_MISMATCH', observedExchange=match['exchange'], expectedExchange=exchange)
    rate = rational(policy['feeRate'])
    known = VERIFIED_FLOOR.get((exchange, rate))
    if policy['feeModel'] == 'polymarket-v2-single-match' and known:
        policy['evidenceRef'].extend('observed-polymarket-ctf-buy:sha256:' + sha for sha in known)
        return
    logs = resolved.evidence['receipt']['logs']
    ordinal = match['receiptOrdinal']
    matching_log = logs[ordinal]
    if matching_log['topics'][0].lower() != MATCH or uint(matching_log['logIndex']) != match['logIndex']:
        raise FeeEvidenceError('FEE_EVENT_IDENTITY', receiptOrdinal=ordinal)
    match_topics, match_values = decode(matching_log, 4, 3)
    order_fills = []
    for log in reversed(logs[:ordinal]):
        if log['address'].lower() != exchange or not log.get('topics'):
            continue
        topic = log['topics'][0].lower()
        if topic == MATCH:
            break
        if topic == FILL:
            order_fills.append(decode(log, 7, 4))
    if policy['feeModel'] == 'verified-zero':
        takers = [fields for topics, fields in order_fills
                  if topics[1:3] == match_topics[1:3] and fields[:4] == match_values]
        if len(takers) != 1 or takers[0][4] != 0:
            raise FeeEvidenceError('FEE_ZERO_UNPROVEN', takerFillCount=len(takers))
        return
    if len(order_fills) != 2:
        raise FeeEvidenceError('FEE_OBSERVED_FILL_COUNT_UNSUPPORTED', orderFillCount=len(order_fills))
    (taker_topics, taker), (maker_topics, maker) = order_fills
    if (taker_topics[1:3] != match_topics[1:3] or taker[:4] != match_values or taker[0] != 0
            or maker_topics[1] == taker_topics[1] or maker[:4] != [1, taker[1], taker[3], taker[2]]
            or maker[4] != 0):
        raise FeeEvidenceError('FEE_OBSERVED_FILL_FORM_UNSUPPORTED', takerMatches=taker[:4] == match_values,
                               makerSide=maker[0], makerTokenMatches=maker[1] == taker[1],
                               reversedAmounts=maker[2:4] == taker[2:4][::-1], makerFeeZero=maker[4] == 0)
    shares, gross = rational(match['quantity']), rational(match['gross'])
    price = gross / shares
    raw_fee = shares * rate * price * (1 - price) * 1_000_000
    floor = (raw_fee // 10) * 10
    if not 0 < price < 1 or taker[4] != floor:
        raise FeeEvidenceError('FEE_ROUNDING_UNPROVEN', observedFeeRaw=taker[4], floorFeeRaw=floor)
    if floor == ((raw_fee + 5) // 10) * 10:
        raise FeeEvidenceError('FEE_ROUNDING_INDETERMINATE', observedFeeRaw=taker[4], floorFeeRaw=floor)
    policy['evidenceRef'].append('observed-ctf-taker-fee:' + resolved.event['venueReceipt']['evidenceRef'])
