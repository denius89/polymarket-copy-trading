"""Narrow price representation proof; never use binary64 for financial arithmetic."""
import base64
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import struct
import sys

PROFILE = 'rtds-price-binary64-shortest-v1'
COMPARISON = dict(profile=PROFILE, identityCandidateCount=1)


def q(value):
    value = Fraction(value)
    return dict(n=str(value.numerator), d=str(value.denominator))


def fraction_q(value):
    if not isinstance(value, dict) or set(value) != {'n', 'd'}:
        raise ValueError('INVALID_Q')
    result = Fraction(int(value['n']), int(value['d']))
    if q(result) != value:
        raise ValueError('NONCANONICAL_Q')
    return result


def binary(value):
    if (sys.float_info.radix, sys.float_info.mant_dig, sys.float_info.max_exp) != (2, 53, 1024):
        raise ValueError('BINARY64_UNAVAILABLE')
    value = Fraction(value)
    if not 0 < value < 1:
        raise ValueError('PRICE_RANGE')
    result = float(value)
    if not 0 < result < 1 or not math.isfinite(result):
        raise ValueError('PRICE_REPRESENTATION_RANGE')
    return result


def price_key(value):
    """Normalize spellings for original-time discovery only, NOT execution identity."""
    value = Fraction(value)
    if not 0 < value < 1: raise ValueError('PRICE_RANGE')
    return float(value).hex()


def price_evidence(exact_price, reported_price):
    """None unless decimal equals shortest roundtrip and rational proves RN-even cell."""
    exact_price, reported_price = Fraction(exact_price), Fraction(reported_price)
    try:
        value = binary(exact_price)
        # repr is shortest roundtrip on supported Python; compare decimal VALUES,
        # so equivalent exponent/trailing-zero JSON spellings are not rejected.
        shortest = repr(value)
        if Fraction(Decimal(shortest)) != reported_price:
            return None
        center = Fraction.from_float(value)
        lower = (Fraction.from_float(math.nextafter(value, -math.inf)) + center) / 2
        upper = (center + Fraction.from_float(math.nextafter(value, math.inf))) / 2
        even = struct.unpack('>Q', struct.pack('>d', value))[0] & 1 == 0
        if not (lower < exact_price < upper or even and exact_price in (lower, upper)):
            return None
        return dict(binary64Hex=value.hex(), shortestDecimal=shortest,
                    lowerMidpoint=q(lower), upperMidpoint=q(upper), tiesIncluded=even)
    except (ValueError, OverflowError):
        return None


def valid_comparison(value):
    return (isinstance(value, dict) and value == COMPARISON and
            type(value.get('identityCandidateCount')) is int)


def raw_comparison(proof, rtds, comparison):
    """Check private raw numeric fields/bindings. Receipt uniqueness is resolver-owned."""
    if not valid_comparison(comparison) or proof.get('amountComparison') != comparison:
        raise ValueError('COMPARISON_PROFILE')
    encoded = proof.get('rawFrameBase64')
    if not isinstance(encoded, str) or len(encoded) > 1_333_336:
        raise ValueError('RAW_FRAME_SIZE')
    raw = base64.b64decode(encoded, validate=True)
    if not 0 < len(raw) <= 1_000_000 or hashlib.sha256(raw).hexdigest() != rtds['payloadSha256']:
        raise ValueError('RAW_FRAME_HASH')
    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out: raise ValueError('DUPLICATE_JSON_KEY')
            out[key] = value
        return out
    def constant(value): raise ValueError('NONFINITE_JSON')
    frame = json.loads(raw, parse_float=Decimal, object_pairs_hook=pairs, parse_constant=constant)
    payload = frame['payload']
    if frame['topic'] != rtds['topic'] or frame['type'] != rtds['type'] or frame['type'] != 'orders_matched':
        raise ValueError('RAW_TOPIC')
    for key, target in (('transactionHash', 'transactionHash'), ('proxyWallet', 'wallet'),
                        ('conditionId', 'marketId')):
        if payload[key].lower() != rtds[target]: raise ValueError('RAW_IDENTITY')
    if payload['asset'] != rtds['outcomeId'] or payload['side'] != rtds['side']:
        raise ValueError('RAW_IDENTITY')
    if type(payload['timestamp']) is not int or proof.get('timestampUnit') != 'seconds' or payload['timestamp']*1000 != rtds['sourceTimestampMs']:
        raise ValueError('RAW_TIME')
    for source, target in (('price', 'reportedPrice'), ('size', 'reportedQuantity')):
        value = payload[source]
        if type(value) not in (int, Decimal): raise ValueError('RAW_NOT_NUMERIC')
        if isinstance(value, Decimal) and (not value.is_finite() or len(str(value)) > 160 or abs(value.as_tuple().exponent) > 100):
            raise ValueError('RAW_NUMERIC_LIMIT')
        if Fraction(value) != fraction_q(rtds[target]): raise ValueError('RAW_AMOUNT')
    return True
