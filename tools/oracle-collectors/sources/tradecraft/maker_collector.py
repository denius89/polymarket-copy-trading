"""Discover current Polymarket maker buys without changing the followed wallet."""
from collections import Counter
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from queue import Empty, Full, Queue
import re
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from book_engine import GateSkip, rational
from collectors import PolymarketWriter
from hybrid_book import HybridBookGate
from market_policy import VERIFIED_FLOOR, load_market, verify_observed_fee
from route import execute_resolved
import rtds_operator as poly
import source

ENDPOINT = 'https://data-api.polymarket.com/v2/trades'
LIMIT = 50
MAX_RESPONSE = 500_000
OBSERVATION = 'maker-timestamp-observation.json'
WHITE = re.compile(r'[ \t\r\n]*')


def pairs(values):
    result = dict(values)
    if len(result) != len(values):
        raise ValueError('duplicate provider JSON key')
    return result


def document_rows(raw):
    """Keep exact raw bytes of each admitted source row instead of re-encoding numbers."""
    text = raw.decode('utf-8')
    decoder = json.JSONDecoder(parse_float=Decimal,object_pairs_hook=pairs)

    def space(index):
        return WHITE.match(text,index).end()

    def consume(index, expected):
        here = space(index)
        if not text.startswith(expected,here):
            raise ValueError('invalid provider JSON envelope')
        return space(here+len(expected))

    gathered, envelope = [], {}
    index = consume(0,'{')
    while not text.startswith('}',index):
        key,index = decoder.raw_decode(text,index)
        if type(key) is not str or key in envelope:
            raise ValueError('invalid provider JSON key')
        index = consume(index,':')
        if key == 'data':
            index = consume(index,'[')
            while not text.startswith(']',index):
                row, end = decoder.raw_decode(text,index)
                if not isinstance(row,dict) or len(gathered)>=LIMIT:
                    raise ValueError('invalid size or shape of provider page')
                gathered.append((row,text[index:end].encode('utf-8')))
                index = space(end)
                if text.startswith(']',index):
                    break
                index = consume(index,',')
                if text.startswith(']',index):
                    raise ValueError('invalid provider array delimiter')
            index = consume(index,']')
            envelope[key] = True
        else:
            envelope[key],index = decoder.raw_decode(text,index)
            index = space(index)
        if text.startswith('}',index):
            break
        index = consume(index,',')
        if text.startswith('}',index):
            raise ValueError('invalid provider object delimiter')
    if consume(index,'}') != len(text) or envelope.get('data') is not True:
        raise ValueError('missing provider rows')
    pagination = envelope.get('pagination')
    if not isinstance(pagination,dict) or type(pagination.get('has_more')) is not bool:
        raise ValueError('invalid provider pagination')
    cursor = pagination.get('next_cursor')
    if pagination['has_more'] and (not isinstance(cursor,str) or not 1<=len(cursor)<=2048):
        raise ValueError('invalid provider cursor')
    return gathered,cursor if pagination['has_more'] else None


def fetch_page(wallet, start, cursor):
    query = {'user':wallet,'taker_only':'false','side':'BUY','start':start,'limit':LIMIT}
    if cursor:
        query['cursor'] = cursor
    request = Request(ENDPOINT+'?'+urlencode(query),headers={
        'Accept':'application/json','Cache-Control':'no-cache','User-Agent':'Shadow-public-demo/1',
    })
    with source.OPENER.open(request,timeout=3) as response:
        raw=response.read(MAX_RESPONSE+1)
        mono,utc=source.observe()
    if len(raw)>MAX_RESPONSE:
        raise ValueError('oversized public maker page')
    return raw,mono,utc


def candidate(row, raw, wallet, request_ref, first_ns, first_ms, armed_ms):
    if row.get('proxy_wallet','').lower()!=wallet or row.get('side')!='BUY':
        raise ValueError('provider returned another wallet or side')
    tx,condition,token,slug = (row[k].lower() if k in {'transaction_hash','condition_id'} else row[k]
                              for k in ('transaction_hash','condition_id','token_id','slug'))
    stamp, price, quantity = (row[k] for k in ('timestamp','price','size'))
    if (type(stamp) is not int or not poly.HASH.fullmatch(tx) or not poly.HASH.fullmatch(condition)
            or not poly.SLUG.fullmatch(slug) or not re.fullmatch('[1-9][0-9]{0,77}',token) or int(token)>=2**256):
        raise ValueError('invalid public maker identity')
    if any(type(value) not in (int,Decimal) or not Decimal(value).is_finite()
           or abs(Decimal(value).as_tuple().exponent)>100 or len(str(value))>160 for value in (price,quantity)):
        raise ValueError('invalid public maker amount')
    if not 0<price<1 or quantity<=0:
        raise ValueError('invalid public maker amount range')
    source_ms=stamp*1000
    if source_ms<armed_ms or not 0<=first_ms-source_ms<=30_000:
        return None
    event_key=(tx,wallet,condition,token,'BUY',Fraction(price),Fraction(quantity))
    return poly.Frame(raw,request_ref,first_ns,first_ms,wallet,condition,token,slug,event_key,source_ms,Decimal(price))


def read_makers(wallet, queue, stop, deadline, armed_ms, registry, counts):
    while not stop.is_set() and time.monotonic()<deadline:
        cursor = None
        start = max((armed_ms+999)//1000,int(time.time())-30)
        try:
            for _ in range(3):
                if stop.is_set():return
                raw, first_ns, first_ms = fetch_page(wallet,start,cursor)
                request_ref = 'data-api-v2-maker:sha256:'+hashlib.sha256(raw).hexdigest()
                rows, next_cursor = document_rows(raw)
                counts['pages'] += 1
                for row, schema_bytes in rows:
                    try:
                        frame = candidate(row,schema_bytes,wallet,request_ref,first_ns,first_ms,armed_ms)
                    except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError):
                        counts['invalid_row'] += 1
                        continue
                    if frame is None:
                        counts['stale_or_preexisting'] += 1
                        continue
                    reason = registry.register(frame)
                    if reason:
                        counts[reason] += 1
                        continue
                    counts['unique_candidates'] += 1
                    try:queue.put_nowait(frame)
                    except Full:counts['queue_full'] += 1
                if not next_cursor:break
                if next_cursor==cursor:raise ValueError('provider cursor repeated')
                cursor = next_cursor
            else:
                counts['page_limit'] += 1
        except HTTPError as error:
            counts[f'http_{error.code}'] += 1
            stop.wait(5)
        except (OSError,ValueError,TypeError) as error:
            counts[type(error).__name__] += 1
            stop.wait(4)
        stop.wait(2)


def fee_for_copy(resolved, policy, exchange):
    if resolved.event['venueReceipt']['match']['exchange'] != exchange:
        raise GateSkip('FEE_CONTRACT_MISMATCH')
    if policy['feeModel'] == 'verified-zero':
        return
    if (exchange,rational(policy['feeRate'])) not in VERIFIED_FLOOR:
        raise GateSkip('TAKER_FEE_PROFILE_UNPROVEN_FOR_MAKER_SOURCE')
    verify_observed_fee(resolved,policy,exchange)


def run_makers(adapter, wallet, stop, deadline, report, *, buy_budget=poly.BUY_BUDGET, start_ms=0):
    from maker_resolver import MakerResolver
    import maker_provenance

    wallet=wallet.lower()
    gate=HybridBookGate()
    books=poly.ActiveBook(gate,deadline)
    registry,queue,counts,halt=poly.Registry(),Queue(maxsize=12),Counter(),threading.Event()
    reference = (Path(__file__).resolve().parent/OBSERVATION).read_bytes()
    timestamp_evidence = 'data-api-v2-maker-timestamp:sha256:'+hashlib.sha256(reference).hexdigest()
    armed_ms=max(start_ms, source.observe()[1])
    reader=threading.Thread(target=read_makers,args=(wallet,queue,halt,deadline,armed_ms,registry,counts),daemon=True)
    reader.start()
    rpc=poly.BoundedRPC()
    heartbeat=0
    try:
        while not stop.is_set() and time.monotonic()<deadline:
            if time.monotonic()>=heartbeat:
                report({'stage':'polymarket-maker-monitor','source':dict(counts),'bookFrames':books.frames})
                heartbeat=time.monotonic()+60
            try:
                captured=queue.get(timeout=.25)
            except Empty:
                if not reader.is_alive() and time.monotonic()<deadline:
                    raise RuntimeError('public maker reader stopped')
                continue
            if poly.remaining(captured)<=0:
                counts['signal_expired'] += 1
                continue
            market=source.Market('polymarket',captured.market,captured.token,wallet,captured.slug)
            try:
                delay,delay_evidence,policy,baseline,exchange=load_market(market)
            except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as error:
                report({'stage':'polymarket-maker-skip','reason':getattr(error,'reason','MARKET_PARAMETERS_UNPROVEN')})
                continue
            try:
                books.follow(market,policy,baseline)
                binding={'wallet':wallet,'marketId':captured.market,'outcomeId':captured.token,
                         'evidenceRef':'verified-active-clob-market-and-token:'+captured.market}
                resolver=MakerResolver(rpc,endpoint_id=poly.RPC,binding=binding,timestamp_evidence=timestamp_evidence,
                                      mono=time.monotonic_ns,utc=lambda:time.time_ns()//1_000_000,wait=stop.wait)
                observed=resolver.observe(captured.raw,captured.connection,first_seen_ms=captured.first_utc,
                                           first_ns=captured.first_mono)
                resolved=resolver.resolve(observed)
                fee_for_copy(resolved,policy,exchange)
                writer=PolymarketWriter(adapter,captured,registry)
                result=execute_resolved(writer,maker_provenance.validate,None,gate,resolved,
                                        session_id='polymarket',owner_id='shared-demo',command_id='observed-maker',
                                        policy=policy,delay_ms=delay,delay_evidence=delay_evidence,
                                        budget=buy_budget,wait=stop.wait)
            except (GateSkip,poly.Skip) as error:
                report({'stage':'polymarket-maker-skip','reason':error.reason,'proof':getattr(error,'details',None)})
                continue
            finally:
                gate.finish()
            if result['status']=='recorded':
                report({'stage':'app-venue-admission','venue':'polymarket','source':'public-v2-maker','status':'recorded'})
    finally:
        halt.set()
        reader.join(timeout=6)
        books.close()
        if reader.is_alive():raise RuntimeError('public maker reader did not stop')
