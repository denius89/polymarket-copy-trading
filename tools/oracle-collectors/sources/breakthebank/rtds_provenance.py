"""Validate retained private resolver attestations; this is not an RPC client."""
from fractions import Fraction
import hashlib
import json
import re
import numeric_match

SOURCE='polymarket-rtds-finalized-v1'
PROFILE='polymarket-rtds-only-v1'
EXCHANGES=frozenset({'0xe111180000d2663c0091e4f400237545b87b996b','0xe2222d279d744050d28e00520010520000310f59'})

class ProvenanceError(Exception): pass


def fail(code): raise ProvenanceError(code)

def shape(v, fields):
    if not isinstance(v,dict) or set(v)!=set(fields.split()): fail('RTDS_PROVENANCE_SHAPE')

def integer(v):
    if type(v) is not int or not 0<=v<=2**53-1: fail('RTDS_INTEGER')
    return v

def text(v):
    if not isinstance(v,str) or not 1<=len(v)<=256 or any(ord(c)<32 for c in v): fail('RTDS_TEXT')
    return v

def hexvalue(v,size):
    if not isinstance(v,str) or not re.fullmatch('0x[0-9a-f]{'+str(size)+'}',v): fail('RTDS_HEX')
    return v

def sha(v):
    if not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v): fail('RTDS_EVIDENCE_HASH')

def ns(v):
    if not isinstance(v,str) or not re.fullmatch('0|[1-9][0-9]{0,29}',v): fail('RTDS_MONOTONIC')
    return int(v)

def q(v):
    shape(v,'n d')
    if not isinstance(v['n'],str) or not isinstance(v['d'],str) or not re.fullmatch('0|-?[1-9][0-9]{0,255}',v['n']) or not re.fullmatch('[1-9][0-9]{0,255}',v['d']): fail('RTDS_EXACT_NUMBER')
    x=Fraction(int(v['n']),int(v['d']))
    if {'n':str(x.numerator),'d':str(x.denominator)}!=v: fail('RTDS_EXACT_NUMBER')
    return x

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def identity(match):
    """receiptOrdinal is the zero-based index in receipt.logs, not global logIndex."""
    key=['polygon-orders-matched-v1',137,match['exchange'],match['transactionHash'],match['receiptOrdinal'],match['wallet'],match['marketId'],match['outcomeId'],match['side']]
    execution_id=digest(key)
    return execution_id,digest([execution_id,match['quantity'],match['gross']])


def validate(event,at_ms):
    receipt=event.get('venueReceipt')
    shape(receipt,'source evidenceRef rtds match finality' + (' amountComparison' if isinstance(receipt,dict) and 'amountComparison' in receipt else ''))
    if receipt['source']!=SOURCE or event.get('venue')!='polymarket' or event.get('chain') is not None: fail('RTDS_SOURCE')
    text(receipt['evidenceRef'])
    r,m,f=(receipt[k] for k in ('rtds','match','finality'))
    shape(r,'topic type payloadSha256 connectionId sourceTimestampMs firstSeenMs firstSeenMonotonicNs transactionHash wallet marketId outcomeId side reportedQuantity reportedPrice')
    shape(m,'chainId exchange transactionHash receiptOrdinal logIndex wallet marketId outcomeId side quantity gross matchingCount')
    shape(f,'receiptStatus receiptSha256 blockNumber blockHash blockTimestampMs canonicalBlockHash finalizedBlockNumber finalizedBlockHash checkedAtMs checkedMonotonicNs rpcEvidenceRef')
    if r['topic']!='activity' or r['type'] not in ('trades','orders_matched'): fail('RTDS_TOPIC')
    if type(m['chainId']) is not int or m['chainId']!=137 or type(m['matchingCount']) is not int or m['matchingCount']!=1: fail('RTDS_AMBIGUOUS_MATCH')
    integer(m['receiptOrdinal']);integer(m['logIndex']);hexvalue(m['exchange'],40)
    if m['exchange'] not in EXCHANGES:fail('RTDS_EXCHANGE_NOT_ALLOWED')
    for field in ('transactionHash','wallet','marketId','outcomeId','side'):
        if r[field]!=m[field]: fail('RTDS_MATCH_BINDING')
    for field in ('marketId','outcomeId','side'):
        text(m[field])
        if event.get(field)!=m[field]: fail('RTDS_EVENT_BINDING')
    if m['side'] not in ('BUY','SELL'): fail('RTDS_SIDE')
    hexvalue(m['transactionHash'],64);hexvalue(m['wallet'],40)
    quantity,gross,reported_quantity,price=q(m['quantity']),q(m['gross']),q(r['reportedQuantity']),q(r['reportedPrice'])
    if quantity<=0 or gross<=0 or gross>quantity or not 0<price<=1 or quantity!=reported_quantity: fail('RTDS_AMOUNT_BINDING')
    if 'amountComparison' not in receipt:
        if gross!=quantity*price: fail('RTDS_AMOUNT_BINDING')
    else:
        comparison=receipt['amountComparison']
        if not numeric_match.valid_comparison(comparison) or gross==quantity*price: fail('RTDS_AMOUNT_COMPARISON_INVALID')
        if numeric_match.price_evidence(gross/quantity,price) is None: fail('RTDS_AMOUNT_BINDING')
    if identity(m)!=(event.get('executionId'),event.get('fingerprint')): fail('RTDS_EXECUTION_IDENTITY')
    sha(r['payloadSha256']);sha(f['receiptSha256']);text(r['connectionId']);text(f['rpcEvidenceRef'])
    source,first,checked,block_time=(integer(v) for v in (r['sourceTimestampMs'],r['firstSeenMs'],f['checkedAtMs'],f['blockTimestampMs']))
    first_ns,checked_ns=ns(r['firstSeenMonotonicNs']),ns(f['checkedMonotonicNs'])
    # Trade time is anchored to original observation; settlement to actual finality verification.
    if source>first or block_time>checked: fail('RTDS_FUTURE_TIMESTAMP')
    if source!=event.get('signalAtMs') or first!=event.get('firstSeenMs'): fail('RTDS_ORIGINAL_TIME_BINDING')
    if not first<=checked<=at_ms or at_ms-min(source,first)>30000: fail('RTDS_SIGNAL_EXPIRED')
    if not 0<=checked_ns-first_ns<=30_000_000_000: fail('RTDS_MONOTONIC_AGE')
    if type(f['receiptStatus']) is not int or f['receiptStatus']!=1: fail('RTDS_RECEIPT_FAILED')
    block_number=integer(f['blockNumber']);head_number=integer(f['finalizedBlockNumber'])
    for k in ('blockHash','canonicalBlockHash','finalizedBlockHash'):hexvalue(f[k],64)
    if f['canonicalBlockHash']!=f['blockHash'] or head_number<block_number: fail('RTDS_FINALITY_NOT_PROVEN')
    if head_number==block_number and f['finalizedBlockHash']!=f['blockHash']: fail('RTDS_FINALITY_NOT_PROVEN')
    return {'transactionHash':m['transactionHash'],'blockHash':f['blockHash'],'blockNumber':block_number}


def validate_estimate(event,estimate):
    f=event['venueReceipt']['finality'];book=estimate.get('book')
    if not isinstance(book,dict):fail('RTDS_POST_FINALITY_BOOK_REQUIRED')
    if (book.get('venue'),book.get('market'),book.get('token'))!=(event['venue'],event['marketId'],event['outcomeId']): fail('RTDS_BOOK_BINDING')
    if integer(book.get('receivedAtMs'))<f['checkedAtMs'] or ns(book.get('receivedMonotonicNs'))<=ns(f['checkedMonotonicNs']): fail('RTDS_POST_FINALITY_BOOK_REQUIRED')
    evidence=estimate.get('evidence')
    proof=evidence.get('sourceProof') if isinstance(evidence,dict) else None
    if not isinstance(proof,dict):fail('RTDS_SOURCE_PROOF_MISSING')
    if digest(proof)!=event['venueReceipt']['evidenceRef']:fail('RTDS_SOURCE_PROOF_HASH')

    if 'amountComparison' in event['venueReceipt']:
        comparison=event['venueReceipt']['amountComparison']
        if not numeric_match.valid_comparison(proof.get('amountComparison')): fail('RTDS_RAW_AMOUNT_PROOF')
        try:
            numeric_match.raw_comparison(proof,event['venueReceipt']['rtds'],comparison)
        except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError,RecursionError):
            fail('RTDS_RAW_AMOUNT_PROOF')
