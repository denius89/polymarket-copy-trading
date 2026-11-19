"""Actual public REST maker discovery -> exact unpaired Fill -> finalized Polygon."""
import base64
import hashlib
import time
from fractions import Fraction

from resolver import Resolver, Observation, Resolved, Skip, sha, uint, hex_id
from maker_core import SOURCE, PROFILE, ENDPOINT, parse_row, select_fill, identity


class MakerResolver(Resolver):
    def __init__(self,rpc,*,endpoint_id,binding,timestamp_evidence,mono=time.monotonic_ns,utc=None,wait=time.sleep):
        if not isinstance(timestamp_evidence,str) or not timestamp_evidence:raise Skip('TIMESTAMP_UNITS_UNPROVEN')
        super().__init__(rpc,endpoint_id=endpoint_id,binding=binding,timestamp_unit='seconds',
                         timestamp_evidence=timestamp_evidence,mono=mono,utc=utc,wait=wait)

    def observe(self,raw,request_ref,*,first_seen_ms,first_ns):
        if (type(first_seen_ms) is not int or type(first_ns) is not int or first_seen_ms<0 or first_ns<0 or
            first_seen_ms>self.utc() or first_ns>self.mono()):raise Skip('INVALID_OBSERVATION_TIME')
        if not isinstance(request_ref,str) or not 0<len(request_ref)<=256:raise Skip('INVALID_REQUEST_REF')
        p=parse_row(raw)
        if not self.binding.get('evidenceRef') or (p['wallet'],p['marketId'],p['outcomeId'])!=(
            self.binding['wallet'].lower(),self.binding['marketId'].lower(),self.binding['outcomeId']):raise Skip('MARKET_OR_ACTOR_MISMATCH')
        quantity=Fraction(int(p['reportedQuantity']['n']),int(p['reportedQuantity']['d']))
        price=Fraction(int(p['reportedPrice']['n']),int(p['reportedPrice']['d']))
        key=(p['transactionHash'],p['wallet'],p['marketId'],p['outcomeId'],'BUY',quantity,price)
        if key in self.rejected:raise Skip(self.rejected[key])
        prior=self.seen.get(key)
        if prior is not None:
            if prior.source_ms!=p['sourceTimestampMs']:
                self.rejected[key]='SOURCE_TIME_CONFLICT';raise Skip('SOURCE_TIME_CONFLICT')
            return prior
        o=Observation(raw,request_ref,'v2_trades_maker',hashlib.sha256(raw).hexdigest(),p['sourceTimestampMs'],
            first_seen_ms,first_ns,p['transactionHash'],p['wallet'],p['marketId'],p['outcomeId'],'BUY',quantity,price,key,False)
        self.seen[key]=o
        if not 0<=first_seen_ms-o.source_ms<=30000:
            self.rejected[key]='SOURCE_TIME_FUTURE' if o.source_ms>first_seen_ms else 'SIGNAL_EXPIRED'
            raise Skip(self.rejected[key])
        self.remaining(o)
        return o

    def _resolve(self,o):
        p=parse_row(o.raw);polls=0
        def pending(reason):
            nonlocal polls
            if polls>=20:raise Skip(reason)
            if self.remaining(o)<=500_000_000:raise Skip('SIGNAL_EXPIRED')
            polls+=1;self.wait(.5);self.remaining(o)
        if self.call(o,'eth_chainId',[])!='0x89':raise Skip('CHAIN_MISMATCH')
        receipt=self.call(o,'eth_getTransactionReceipt',[o.tx])
        while receipt is None:
            pending('RECEIPT_UNAVAILABLE');receipt=self.call(o,'eth_getTransactionReceipt',[o.tx])
        match,diagnostic=select_fill(receipt,p);self.diagnostics[o.key]=diagnostic
        block,bh=uint(receipt['blockNumber']),hex_id(receipt['blockHash'],32)
        canonical=self.call(o,'eth_getBlockByNumber',[hex(block),False])
        if not canonical or uint(canonical['number'])!=block or hex_id(canonical['hash'],32)!=bh:raise Skip('CANONICAL_BLOCK_MISMATCH')
        block_ms=uint(canonical['timestamp'])*1000
        if block_ms!=o.source_ms:raise Skip('MAKER_SOURCE_BLOCK_TIME_MISMATCH')
        finalized=self.call(o,'eth_getBlockByNumber',['finalized',False])
        while finalized is None or uint(finalized['number'])<block:
            pending('FINALITY_NOT_REACHED');finalized=self.call(o,'eth_getBlockByNumber',['finalized',False])
        fn,fh=uint(finalized['number']),hex_id(finalized['hash'],32)
        if fn==block and fh!=bh:raise Skip('FINALIZED_BLOCK_MISMATCH')
        if self.call(o,'eth_getBlockByNumber',[hex(block),False])!=canonical or self.call(o,'eth_getTransactionReceipt',[o.tx])!=receipt:raise Skip('INCLUSION_CHANGED')
        checked,checked_ns=self.utc(),self.mono();self.remaining(o)
        if block_ms>checked:raise Skip('BLOCK_TIME_FUTURE_AT_FINALITY')
        proof=dict(rawRowBase64=base64.b64encode(o.raw).decode(),endpoint=ENDPOINT,requestRef=o.connection,
                   timestampUnit='seconds',timestampEvidence=self.unit_evidence,marketBinding=self.binding,
                   rpcEndpoint=self.endpoint,receipt=receipt,canonicalBlock=canonical,finalizedBlock=finalized)
        discovery=dict(profile=PROFILE,endpoint=ENDPOINT,requestRef=o.connection,rowSha256=o.payload_sha,
                       firstSeenMs=o.first_ms,firstSeenMonotonicNs=str(o.first_ns),**p)
        finality=dict(receiptStatus=1,receiptSha256=sha(receipt),blockNumber=block,blockHash=bh,blockTimestampMs=block_ms,
            canonicalBlockHash=bh,finalizedBlockNumber=fn,finalizedBlockHash=fh,checkedAtMs=checked,
            checkedMonotonicNs=str(checked_ns),rpcEvidenceRef=self.endpoint)
        eid,fp=identity(match)
        event=dict(executionId=eid,fingerprint=fp,venue='polymarket',marketId=o.market,outcomeId=o.token,side='BUY',
            signalAtMs=o.source_ms,firstSeenMs=o.first_ms,chain=None,
            venueReceipt=dict(source=SOURCE,evidenceRef=sha(proof),discovery=discovery,match=match,finality=finality))
        return Resolved(event,o.first_ns,o.first_ms-o.source_ms,sha(event),proof)
