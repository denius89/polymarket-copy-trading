"""Private REST-maker proof validator. Old RTDS attestations keep their own rules."""
import base64
import hashlib
from fractions import Fraction

import rtds_provenance as common
from resolver import Skip, uint, hex_id
from maker_core import SOURCE, PROFILE, ENDPOINT, parse_row, select_fill, identity

ProvenanceError=common.ProvenanceError
shape,integer,text,hexvalue,sha,ns,q,digest,fail=(getattr(common,k) for k in ('shape','integer','text','hexvalue','sha','ns','q','digest','fail'))


def validate(event,at_ms):
    receipt=event.get('venueReceipt')
    shape(receipt,'source evidenceRef discovery match finality')
    if receipt['source']!=SOURCE or event.get('venue')!='polymarket' or event.get('chain') is not None:fail('MAKER_SOURCE')
    sha(receipt['evidenceRef'])
    d,m,f=(receipt[k] for k in ('discovery','match','finality'))
    shape(d,'profile endpoint requestRef rowSha256 sourceTimestampMs firstSeenMs firstSeenMonotonicNs transactionHash wallet marketId outcomeId side reportedQuantity reportedPrice')
    shape(m,'chainId exchange transactionHash receiptOrdinal logIndex wallet marketId outcomeId side quantity gross matchingCount orderHash role')
    shape(f,'receiptStatus receiptSha256 blockNumber blockHash blockTimestampMs canonicalBlockHash finalizedBlockNumber finalizedBlockHash checkedAtMs checkedMonotonicNs rpcEvidenceRef')
    if d['profile']!=PROFILE or d['endpoint']!=ENDPOINT or m['role']!='maker':fail('MAKER_PROFILE')
    text(d['requestRef']);sha(d['rowSha256'])
    if type(m['chainId']) is not int or m['chainId']!=137 or type(m['matchingCount']) is not int or m['matchingCount']!=1:fail('MAKER_MATCH')
    integer(m['receiptOrdinal']);integer(m['logIndex']);hexvalue(m['exchange'],40);hexvalue(m['orderHash'],64)
    if m['exchange'] not in common.EXCHANGES:fail('MAKER_EXCHANGE')
    for field in ('transactionHash','wallet','marketId','outcomeId','side'):
        if d[field]!=m[field]:fail('MAKER_BINDING')
    for field in ('marketId','outcomeId','side'):
        text(m[field])
        if event.get(field)!=m[field]:fail('MAKER_EVENT_BINDING')
    if m['side']!='BUY':fail('MAKER_BUY_ONLY')
    hexvalue(m['transactionHash'],64);hexvalue(m['wallet'],40);hexvalue(m['marketId'],64)
    qty,gross,reported,price=q(m['quantity']),q(m['gross']),q(d['reportedQuantity']),q(d['reportedPrice'])
    if qty<=0 or gross<=0 or not 0<price<1 or reported!=qty or gross!=qty*price:fail('MAKER_AMOUNT_BINDING')
    if identity(m)!=(event.get('executionId'),event.get('fingerprint')):fail('MAKER_EXECUTION_IDENTITY')
    source,first,checked,bt=(integer(x) for x in (d['sourceTimestampMs'],d['firstSeenMs'],f['checkedAtMs'],f['blockTimestampMs']))
    first_ns,checked_ns=ns(d['firstSeenMonotonicNs']),ns(f['checkedMonotonicNs'])
    if source!=event.get('signalAtMs') or first!=event.get('firstSeenMs'):fail('MAKER_ORIGINAL_TIME')
    if bt!=source:fail('MAKER_SOURCE_BLOCK_TIME_MISMATCH')
    if not source<=first<=checked<=at_ms or bt>checked or at_ms-source>30000:fail('MAKER_SIGNAL_TIME')
    if not 0<=checked_ns-first_ns<=30_000_000_000:fail('MAKER_MONOTONIC_AGE')
    if type(f['receiptStatus']) is not int or f['receiptStatus']!=1:fail('MAKER_RECEIPT_FAILED')
    sha(f['receiptSha256']);text(f['rpcEvidenceRef'])
    number,head=integer(f['blockNumber']),integer(f['finalizedBlockNumber'])
    for key in ('blockHash','canonicalBlockHash','finalizedBlockHash'):hexvalue(f[key],64)
    if f['canonicalBlockHash']!=f['blockHash'] or head<number or (head==number and f['finalizedBlockHash']!=f['blockHash']):fail('MAKER_FINALITY')
    return dict(transactionHash=m['transactionHash'],blockHash=f['blockHash'],blockNumber=number)


def validate_estimate(event,estimate):
    receipt=event['venueReceipt'];d,m,f=(receipt[k] for k in ('discovery','match','finality'))
    book=estimate.get('book')
    if not isinstance(book,dict) or (book.get('venue'),book.get('market'),book.get('token'))!=('polymarket',event['marketId'],event['outcomeId']):fail('MAKER_BOOK_BINDING')
    if integer(book.get('receivedAtMs'))<f['checkedAtMs'] or ns(book.get('receivedMonotonicNs'))<=ns(f['checkedMonotonicNs']):fail('MAKER_POST_FINALITY_BOOK')
    evidence=estimate.get('evidence');proof=evidence.get('sourceProof') if isinstance(evidence,dict) else None
    if not isinstance(proof,dict) or digest(proof)!=receipt['evidenceRef']:fail('MAKER_RAW_PROOF_HASH')
    try:
        shape(proof,'rawRowBase64 endpoint requestRef timestampUnit timestampEvidence marketBinding rpcEndpoint receipt canonicalBlock finalizedBlock')
        if proof['endpoint']!=ENDPOINT or proof['requestRef']!=d['requestRef'] or proof['timestampUnit']!='seconds':fail('MAKER_RAW_SOURCE')
        text(proof['timestampEvidence'])
        if not isinstance(proof['rawRowBase64'],str) or len(proof['rawRowBase64'])>90000:fail('MAKER_RAW_ROW_SIZE')
        raw=base64.b64decode(proof['rawRowBase64'],validate=True);reported=parse_row(raw)
        if hashlib.sha256(raw).hexdigest()!=d['rowSha256'] or any(d[key]!=value for key,value in reported.items()):fail('MAKER_RAW_ROW_BINDING')
        binding=proof['marketBinding']
        if not binding.get('evidenceRef') or (binding['wallet'].lower(),binding['marketId'].lower(),binding['outcomeId'])!=(m['wallet'],m['marketId'],m['outcomeId']):fail('MAKER_MARKET_BINDING')
        matched,_=select_fill(proof['receipt'],reported)
        if matched!=m or digest(proof['receipt'])!=f['receiptSha256']:fail('MAKER_RAW_RECEIPT_BINDING')
        if (uint(proof['receipt']['blockNumber']),hex_id(proof['receipt']['blockHash'],32))!=(f['blockNumber'],f['blockHash']):fail('MAKER_RAW_RECEIPT_BLOCK_BINDING')
        canonical,finalized=proof['canonicalBlock'],proof['finalizedBlock']
        if (uint(canonical['number']),hex_id(canonical['hash'],32),uint(canonical['timestamp'])*1000)!=(f['blockNumber'],f['blockHash'],f['blockTimestampMs']):fail('MAKER_RAW_BLOCK_BINDING')
        if (uint(finalized['number']),hex_id(finalized['hash'],32))!=(f['finalizedBlockNumber'],f['finalizedBlockHash']):fail('MAKER_RAW_FINALITY_BINDING')
        if proof['rpcEndpoint']!=f['rpcEvidenceRef']:fail('MAKER_RPC_BINDING')
    except (Skip,ValueError,TypeError,KeyError,AttributeError,ArithmeticError,RecursionError):fail('MAKER_RAW_PROOF_INVALID')
