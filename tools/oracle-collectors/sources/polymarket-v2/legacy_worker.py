"""Read-only venue adapters and a persistent shared virtual ledger."""
import concurrent.futures
import datetime as dt
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from sell import sale_fraction
import poly_v2_settlement
from follow_policy import NEW_LIMITLESS, label as follow_label

POLY = '0xed3bed3eafd729a26cdb20e927b8ed8ca8d251f2'
LIMITLESS = '0x0D6a4C42Efe6aF0a81632DcFe0e8D1e76D1D4ADA'
NAMES = {'polymarket':'0xed3bed…51f2', 'limitless':'SharpDownyLarch'}
WALLETS = {'polymarket':POLY, 'limitless':LIMITLESS}
LEGACY_WALLETS = {'polymarket':'0xde9f7f4e77a1595623ceb58e469f776257ccd43c',
                  'limitless':'0x3eda6446d3f458e8ce2b9c433c59d719e331fc28'}
START, BUY, DAILY, MARKET = 200_000_000, 10_000_000, 200_000_000, 100_000_000
CUT_OFF = dt.datetime(2026, 11, 16, 22, 59, tzinfo=dt.UTC).timestamp()
SCALE = D(1_000_000)
WARSAW = ZoneInfo('Europe/Warsaw')

class Skip(Exception):
    pass

def get(host, path, params=None):
    if params:
        path += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request('https://'+host+path, headers={
        'Accept':'application/json', 'Cache-Control':'no-cache', 'User-Agent':'Shadow-public-demo/1'})
    with urllib.request.urlopen(req, timeout=4) as response:
        return json.loads(response.read(2_000_001), parse_float=D)

def slug(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,250}', value):
        raise Skip('identity')
    return value

def qty(value):
    return int(D(str(value)).to_integral_value(rounding=ROUND_FLOOR))

def timestamp():
    return dt.datetime.now(dt.UTC).isoformat()

def event_trader(event):
    if event.get('wallet','').lower()==NEW_LIMITLESS:
        return follow_label(event['venue'],NEW_LIMITLESS)
    return NAMES[event['venue']]

def position_market(event):
    # Existing ledger rows use the original venue leader's unqualified market key.
    market=str(event.get('condition') or event['slug'])
    wallet=event['wallet'].lower()
    if wallet==LEGACY_WALLETS[event['venue']]:
        return market
    return f'{market}:{wallet}'

def group_signals(rows):
    grouped={}
    for row in rows:
        if row['side']!='SELL':
            yield row
            continue
        key=(row['tx'],row['condition'],row.get('token') or row['outcome'])
        if key in grouped:
            grouped[key]['reportedQuantity']+=row['reportedQuantity']
            continue
        row['id']='sell:'+':'.join(key)
        grouped[key]=row
    yield from grouped.values()

def poly_signals():
    rows=get('data-api.polymarket.com','/v2/trades',dict(user=POLY,taker_only='false',limit=80))['data']
    def adapt():
        for t in rows:
            side=t.get('side')
            if t.get('proxy_wallet','').lower()!=POLY or side not in ('BUY','SELL'):
                continue
            condition,token,tx=t['condition_id'],t['token_id'],t['transaction_hash']
            if not re.fullmatch(r'0x[0-9a-fA-F]{64}',condition) or not re.fullmatch(r'[0-9]{1,80}',token) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',tx):
                continue
            yield dict(venue='polymarket',id=tx+':'+token,at=int(t['timestamp']),slug=slug(t['slug']),
                       condition=condition,token=token,market=t['title'],outcome=t['outcome'],tx=tx,
                       side=side,wallet=POLY,reportedQuantity=qty(D(str(t['size']))*SCALE))
    return group_signals(adapt())

def limitless_signals(wallet=None):
    wallet = LIMITLESS if wallet is None else wallet
    rows=get('api.limitless.exchange','/portfolio/'+wallet+'/history',dict(limit=30))['data']
    def adapt():
        for t in rows:
            strategy=t.get('strategy')
            if strategy not in ('Limit Buy','Market Buy','Limit Sell','Market Sell') or t.get('outcomeIndex') not in (0,1):
                continue
            side='SELL' if strategy.endswith('Sell') else 'BUY'
            identity=t.get('tradeEventId')
            m=t.get('market') or {}
            condition=m.get('conditionId')
            tx=t.get('transactionHash')
            if not isinstance(identity,str) or not re.fullmatch(r'[0-9a-fA-F-]{36}',identity) or not m.get('id'):
                continue
            if not re.fullmatch(r'0x[0-9a-fA-F]{64}',condition or ''):
                continue
            if side=='SELL' and not re.fullmatch(r'0x[0-9a-fA-F]{64}',tx or ''):
                continue
            group=(m.get('group') or {}).get('title')
            title=m.get('title') or ''
            yield dict(venue='limitless',id=identity+':'+str(t['outcomeIndex']),at=int(t['blockTimestamp']),
                       slug=slug(m['slug']),market_id=str(m['id']),condition=condition,
                       market=f'{group} · {title}' if group else title,outcome=('YES','NO')[t['outcomeIndex']],
                       tx=tx,side=side,wallet=wallet,reportedQuantity=qty(D(str(t['outcomeTokenAmount']))*SCALE) if side=='SELL' else 0)
    return group_signals(adapt())

def poly_fee_rate(market):
    schedule=market.get('feeSchedule') or {}
    if market.get('feesEnabled') is False:
        return D(0)
    if schedule.get('exponent')==1 and 'rate' in schedule:
        return D(str(schedule['rate']))
    raise Skip('fee')

def poly_quote(s, before_book=None):
    m=get('gamma-api.polymarket.com','/markets/slug/'+s['slug'])
    ids=m.get('clobTokenIds')
    if isinstance(ids,str): ids=json.loads(ids)
    if m.get('conditionId')!=s['condition'] or not isinstance(ids,list) or s['token'] not in ids:
        raise Skip('identity')
    if m.get('acceptingOrders') is not True or m.get('closed') is True:
        raise Skip('closed')
    delay=m.get('secondsDelay')
    if delay is None:
        info=get('clob.polymarket.com','/clob-markets/'+s['condition'])
        delay=info.get('sd')
    if type(delay) is not int or not 0<=delay<=5:
        raise Skip('delay')
    if before_book:
        before_book(s)
    time.sleep(delay)
    b=get('clob.polymarket.com','/book',dict(token_id=s['token']))
    if b.get('asset_id')!=s['token'] or b.get('market')!=s['condition']:
        raise Skip('identity')
    observed_age=time.time()-int(b['timestamp'])/1000
    if not 0<=observed_age<=2:
        raise Skip('book_age')
    rate=poly_fee_rate(m)
    return [(D(str(x['price'])),qty(D(str(x['size']))*SCALE)) for x in b['bids' if before_book else 'asks']],qty(D(str(b['min_order_size']))*SCALE),rate

def limitless_quote(s, before_book=None):
    m=get('api.limitless.exchange','/markets/'+s['slug'])
    if str(m.get('id'))!=s['market_id'] or not s['condition'] or m.get('conditionId')!=s['condition']:
        raise Skip('identity')
    if m.get('tradeType')!='clob':
        raise Skip('book')
    if m.get('status') not in ('CREATED','FUNDED') or m.get('expired') is not False:
        raise Skip('closed')
    tokens=m.get('tokens') or {}
    if not tokens.get('yes') or not tokens.get('no'):
        raise Skip('identity')
    s['token']=tokens[s['outcome'].lower()]
    if before_book:
        before_book(s)
    b=get('api.limitless.exchange','/markets/'+s['slug']+'/orderbook')
    if b.get('tokenId')!=tokens['yes']:
        raise Skip('identity')
    if (m.get('venue') or {}).get('feeModuleType')!='COLLATERAL':
        raise Skip('fee')
    rows=b['bids'] if (s['outcome']=='YES')==bool(before_book) else b['asks']
    levels=[(D(str(x['price'])) if s['outcome']=='YES' else 1-D(str(x['price'])),qty(x['size'])) for x in rows]
    return levels,qty(b['minSize']),D('.05')

def estimate(levels, minimum, rate):
    levels=sorted((p,q) for p,q in levels if p.is_finite() and 0<p<1 and q>0)
    if not levels or minimum<=0 or not D(0)<=rate<=D(1):
        raise Skip('depth')
    max_price=levels[0][0]*D('1.02')
    left=D(BUY)
    notional=fee=D(0)
    shares=0
    for p,available in levels:
        if p>max_price: break
        per_share_fee=rate*p*(1-p)
        take=min(available,qty(left/(p+per_share_fee)))
        if not take:break
        shares+=take
        notional+=take*p
        fee+=take*per_share_fee
        left=D(BUY)-notional-fee
    if left>1:
        raise Skip('depth')
    if shares<minimum:
        raise Skip('minimum')
    cost=int(notional.to_integral_value(rounding=ROUND_CEILING))
    expense=int(fee.to_integral_value(rounding=ROUND_CEILING))
    if cost+expense>BUY:
        cost=int(notional.to_integral_value(rounding=ROUND_FLOOR))
    if not 0 < cost <= BUY-expense:
        raise Skip('depth')
    return dict(quantity=shares,cost=cost,fee=expense,price=str(notional/shares))

def evaluate(s):
    if not 0<=time.time()-s['at']<=30:
        return {'reason':'signal_age'}
    try:
        quote=(poly_quote if s['venue']=='polymarket' else limitless_quote)(s)
        if time.time()-s['at']>30:
            raise Skip('signal_age')
        return estimate(*quote)
    except Skip as e:
        return {'reason':str(e)}
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
        return {'reason':'book'}

def evaluate_sell(event):
    try:
        adapter=poly_quote if event['venue']=='polymarket' else limitless_quote
        proof=None
        def verify(signal):
            nonlocal proof
            try:
                proof=sale_fraction(signal)
            except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as failure:
                raise Skip('sell_basis') from failure
        levels,minimum,rate=adapter(event,before_book=verify)
        fraction,sequence=proof
        if not 0<=time.time()-event['at']<=30:
            return {'reason':'signal_age'}
        return dict(levels=levels,minimum=minimum,rate=rate,fraction=fraction,sequence=sequence,
                    readAt=time.monotonic())
    except Skip as failure:
        return {'reason':str(failure)}
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError):
        return {'reason':'book'}

def sale_proceeds(levels,target,rate):
    if not 0<=rate<=1:
        raise Skip('fee')
    bids=sorted(((p,q) for p,q in levels if p.is_finite() and 0<p<1 and q>0),reverse=True)
    if not bids:
        raise Skip('depth')
    floor=bids[0][0]*D('.98')
    left=target
    gross=fee=D(0)
    for price,size in bids:
        if price<floor:
            break
        part=min(size,left)
        gross+=price*part
        fee+=rate*price*(1-price)*part
        left-=part
        if not left:
            break
    if left:
        raise Skip('depth')
    gross_units=qty(gross)
    fee_units=int(fee.to_integral_value(rounding=ROUND_CEILING))
    if gross_units<=fee_units:
        raise Skip('minimum')
    return gross_units,fee_units,format(gross/target,'f')

def midpoint(book):
    def prices(side):
        return [p for row in book[side] if D(str(row['size']))>0
                and (p:=D(str(row['price']))).is_finite() and 0<p<1]
    bid,ask=max(prices('bids'),default=None),min(prices('asks'),default=None)
    if bid is None or ask is None:
        return None
    if bid>ask:
        raise Skip('book')
    return (bid+ask)/2

def position_sale(quote, shares, basis, fees):
    if quote is None:
        return None
    levels,minimum,rate,at=quote
    if minimum<=0 or shares<minimum:
        return None
    try:
        gross,fee,price=sale_proceeds(levels,shares,rate)
    except (Skip,ValueError,ArithmeticError):
        return None
    return dict(net=gross-fee,fee=fee,price=price,at=at,pnl=gross-fee-basis-fees)

CTF = '0x4d97dcd97ec945f40cf65f87097ace5ea0476045'
NEG_RISK_ADAPTER = '0xd91e80cf2e7be2e162c6513ced06f1dd0da35296'
USDC_E = '0x2791bca1f2de4661ed88a30c99a7a9449aa84174'


def ctf_rpc(method, *params):
    body = json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode()
    req = urllib.request.Request('https://polygon-bor-rpc.publicnode.com', data=body,
                                 headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=4) as response:
        result = json.loads(response.read(1_000_001)).get('result')
    if result is None:
        raise Skip('ctf_unavailable')
    return result


@lru_cache(maxsize=8)
def ctf_signature(signature):
    return ctf_rpc('web3_sha3', '0x'+signature.encode().hex())


def ctf_call(contract, signature, *words):
    calldata = ctf_signature(signature)[:10]+''.join(f'{word:064x}' for word in words)
    result = ctf_rpc('eth_call', {'to':contract,'data':calldata}, 'finalized')
    if not isinstance(result,str) or not re.fullmatch(r'0x[0-9a-f]{64}',result):
        raise Skip('ctf_identity')
    return int(result,16)


@lru_cache(maxsize=512)
def ctf_block(height):
    return ctf_rpc('eth_getBlockByNumber',hex(height),False)


def ctf_block_at(timestamp, finalized_height):
    lower, upper = 0, finalized_height
    for _ in range(32):
        if upper-lower<=1:
            return upper
        middle = (lower+upper)//2
        if int(ctf_block(middle)['timestamp'],16)<timestamp:
            lower=middle
        else:
            upper=middle
    raise Skip('ctf_resolution_window')


def ctf_decode_resolution(log):
    data=log['data'][2:]
    if len(data)!=64*5 or len(log['topics'])!=4:
        raise Skip('ctf_payout')
    words=[int(data[i:i+64],16) for i in range(0,len(data),64)]
    if words[:3] != [2,64,2] or sum(words[3:])<=0:
        raise Skip('ctf_payout')
    return tuple(words[3:])


@lru_cache(maxsize=256)
def ctf_resolution(condition, tokens, neg_risk, anchors):
    if int(ctf_rpc('eth_chainId'),16)!=137:
        raise Skip('ctf_network')
    condition_word=int(condition,16)
    collateral=int(USDC_E,16)
    if neg_risk:
        if ctf_call(NEG_RISK_ADAPTER,'ctf()')!=int(CTF,16):
            raise Skip('ctf_identity')
        collateral=ctf_call(NEG_RISK_ADAPTER,'wcol()')
        if not 0<collateral<2**160:
            raise Skip('ctf_identity')
    expected_tokens=[]
    for singleton in (1,2):
        collection=ctf_call(CTF,'getCollectionId(bytes32,bytes32,uint256)',0,condition_word,singleton)
        expected_tokens.append(str(ctf_call(CTF,'getPositionId(address,bytes32)',collateral,collection)))
    if tuple(expected_tokens)!=tokens:
        raise Skip('ctf_identity')

    denominator=ctf_call(CTF,'payoutDenominator(bytes32)',condition_word)
    if denominator<=0:
        raise Skip('ctf_not_resolved')
    numerators=tuple(ctf_call(CTF,'payoutNumerators(bytes32,uint256)',condition_word,i) for i in range(2))
    if sum(numerators)!=denominator:
        raise Skip('ctf_payout')

    finalized=ctf_rpc('eth_getBlockByNumber','finalized',False)
    height=int(finalized['number'],16)
    final_time=int(finalized['timestamp'],16)
    topic=ctf_signature('ConditionResolution(bytes32,address,bytes32,uint256,uint256[])')
    centers=[ctf_block_at(anchor,height) for anchor in anchors if anchor<=final_time]
    if not centers:
        centers=[height]
    matched={}
    for radius in (300,2400):
        for center in centers:
            lower,upper=max(center-radius,0),min(center+radius,height)
            for start in range(lower,upper+1,600):
                query={'address':CTF,'topics':[topic,condition],
                       'fromBlock':hex(start),'toBlock':hex(min(start+599,upper))}
                for log in ctf_rpc('eth_getLogs',query):
                    matched[(log['transactionHash'],log['logIndex'])]=log
            if matched:
                break
        if matched:
            break
    if len(matched)!=1:
        raise Skip('ctf_resolution_window')
    log=next(iter(matched.values()))
    block_number=int(log['blockNumber'],16)
    block=ctf_block(block_number)
    receipt=ctf_rpc('eth_getTransactionReceipt',log['transactionHash'])
    if (log.get('removed') or log['address'].lower()!=CTF or log['topics'][:2]!=[topic,condition]
        or block_number>height or block['hash']!=log['blockHash'] or receipt['status']!='0x1'
        or receipt['blockHash']!=block['hash'] or receipt['transactionHash']!=log['transactionHash']
        or log not in receipt['logs'] or ctf_decode_resolution(log)!=numerators):
        raise Skip('ctf_confirmation')
    if neg_risk and int(log['topics'][2],16)!=int(NEG_RISK_ADAPTER,16):
        raise Skip('ctf_identity')
    when=dt.datetime.fromtimestamp(int(block['timestamp'],16),dt.UTC).isoformat()
    return numerators,denominator,when


def ctf_fallback(market, tokens, condition, token, resolution):
    version=market.get('version')
    if (version not in (None,'v1') or type(market.get('negRisk')) is not bool
        or not re.fullmatch(r'0x[0-9a-f]{64}',condition) or len(tokens)!=2
        or len(set(tokens))!=2):
        raise Skip('ctf_identity')
    anchors=[]
    for value in (market.get('closedTime'),resolution.get('resolved_at'),resolution.get('last_update_timestamp'),market.get('endDate')):
        if not value:
            continue
        try:
            if isinstance(value,str) and not value.isdecimal():
                parsed=dt.datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    continue
                seconds=int(parsed.timestamp())
            else:
                seconds=int(value)
        except (ValueError,TypeError,OverflowError):
            continue
        if seconds>0 and all(abs(seconds-anchor)>300 for anchor in anchors):
            anchors.append(seconds)
    numerators,denominator,resolved_at=ctf_resolution(condition,tuple(tokens),market['negRisk'],tuple(anchors))
    return Fraction(numerators[tokens.index(token)],denominator),'payout',resolved_at,None


def position_quote(event):
    token,condition=event['token'],event['condition']
    if event['venue']=='polymarket':
        try:
            _, module = poly_v2_settlement.position_id(condition, token)
        except ValueError:
            module = None
        if module == 3:
            return poly_v2_settlement.quote(event, rpc=ctf_rpc, allowed_modules=(3,))
        market_slug=slug(event['slug'])
        market=get('gamma-api.polymarket.com','/markets/slug/'+market_slug)
        if market.get('version') == 'v2':
            position, module = poly_v2_settlement.position_id(condition, token)
            tokens = market['positionIds']
            if (module not in (1, 2) or not isinstance(tokens, list) or len(tokens) != 2
                    or tokens != [str(position & ~255), str(position | 1)]
                    or poly_v2_settlement.position_id(market['conditionId'], token)[0] != position):
                raise Skip('v2_identity')
            try:
                return poly_v2_settlement.quote(event, rpc=ctf_rpc, allowed_modules=(1, 2))
            except (Skip, OSError, ValueError, KeyError, TypeError, ArithmeticError):
                if market.get('closed') is True:
                    raise
        else:
            tokens=market['clobTokenIds']
        tokens=json.loads(tokens) if isinstance(tokens,str) else tokens
        if market.get('version') != 'v2' and (market.get('conditionId')!=condition or token not in tokens):
            raise Skip('identity')
        if market.get('closed') is True:
            if market.get('umaResolutionStatus')!='resolved':
                raise Skip('closed')
            try:
                resolution=get('data-api.polymarket.com','/v2/resolutions',dict(condition=condition)).get('data')
            except (OSError,ValueError):
                resolution=None
            if not isinstance(resolution,list) or not resolution:
                return ctf_fallback(market,tokens,condition,token,{})
            if len(resolution)!=1:
                raise Skip('payout')
            result=resolution[0]
            if result.get('condition_id')!=condition or result.get('status')!='resolved':
                raise Skip('payout')
            payouts=result.get('payouts')
            if payouts is None or not result.get('resolved_at'):
                return ctf_fallback(market,tokens,condition,token,result)
            if (result.get('condition_id')!=condition or result.get('status')!='resolved'
                or not result.get('resolved_at') or not isinstance(payouts,list)
                or len(payouts)!=len(tokens) or len(set(tokens))!=len(tokens)
                or any(type(n) is not int or n<0 for n in payouts) or sum(payouts)!=1_000_000):
                raise Skip('payout')
            prices=market['outcomePrices']
            prices=json.loads(prices) if isinstance(prices,str) else prices
            if [D(str(price)) for price in prices]!=[D(payout)/SCALE for payout in payouts]:
                raise Skip('payout')
            return D(payouts[tokens.index(token)])/SCALE,'payout',result['resolved_at'],None
        if market.get('acceptingOrders') is not True:
            raise Skip('closed')
        book=get('clob.polymarket.com','/book',dict(token_id=token))
        if book.get('market')!=condition or book.get('asset_id')!=token:
            raise Skip('identity')
        book_time=int(book['timestamp'])/1000
        if not 0<=time.time()-book_time<=120:
            raise Skip('book_age')
        at=dt.datetime.fromtimestamp(book_time,dt.UTC).isoformat()
        try:
            rate=poly_fee_rate(market)
            levels=[(D(str(x['price'])),qty(D(str(x['size']))*SCALE)) for x in book['bids']]
            closing=(levels,qty(D(str(book['min_order_size']))*SCALE),rate,at)
        except (Skip,KeyError,TypeError,ValueError,ArithmeticError):
            closing=None
        return midpoint(book),'book',at,closing
    market_slug=slug(event['slug'])
    market=get('api.limitless.exchange','/markets/'+market_slug)
    tokens=market['tokens']
    outcome=event['outcome'].lower()
    # The chain-backed BUY events identify the market by condition and outcome token.
    # Older events additionally carry the numeric market ID from the trading API.
    if market.get('conditionId')!=condition or tokens.get(outcome)!=token:
        raise Skip('identity')
    if 'market_id' in event and str(market.get('id'))!=event['market_id']:
        raise Skip('identity')
    if market.get('status')=='RESOLVED':
        index=('yes','no').index(outcome)
        winner=market.get('winningOutcomeIndex')
        if type(winner) is int and winner in (0,1):
            return D(int(index==winner)),'payout',timestamp(),None
        payouts=[D(str(n)) for n in market['payoutNumerators']]
        if len(payouts)!=2 or min(payouts)<=0:
            raise Skip('payout')
        return payouts[index]/sum(payouts),'payout',timestamp(),None
    if market.get('status') not in ('CREATED','FUNDED') or market.get('expired') is not False or market.get('tradeType')!='clob':
        raise Skip('closed')
    book=get('api.limitless.exchange','/markets/'+market_slug+'/orderbook')
    if book.get('tokenId')!=tokens['yes']:
        raise Skip('identity')
    price=midpoint(book)
    if price is not None and outcome=='no':
        price=1-price
    at=timestamp()
    closing=None
    if (market.get('venue') or {}).get('feeModuleType')=='COLLATERAL':
        try:
            rows=book['asks' if outcome=='no' else 'bids']
            levels=[(1-D(str(x['price'])) if outcome=='no' else D(str(x['price'])),qty(x['size'])) for x in rows]
            closing=(levels,qty(book['minSize']),D('.05'),at)
        except (KeyError,TypeError,ValueError,ArithmeticError):
            pass
    return price,'book',at,closing

class PositionQuotes:
    def __init__(self,pool):
        self.pool=pool
        self.jobs={}
        self.cache={}

    def read(self,key,event):
        now=time.monotonic()
        job=self.jobs.get(key)
        if job is not None and job.done():
            del self.jobs[key]
            try:
                quote=job.result()
            except (Skip,OSError,ValueError,IndexError,KeyError,TypeError,ArithmeticError):
                quote=None
            self.cache[key]=(now,quote)
        checked,quote=self.cache.get(key,(float('-inf'),None))
        if quote is not None and quote[1]=='payout':
            payout = quote[0]
            if not isinstance(payout, poly_v2_settlement.Payout) or payout.shares == event.get('_settlementShares'):
                return quote
            self.cache.pop(key, None)
            checked, quote = float('-inf'), None
        if key not in self.jobs and now-checked>=30:
            self.jobs[key]=self.pool.submit(position_quote,event)
        if quote is not None and now-checked<=45:
            if (event['venue']=='polymarket' and
                (dt.datetime.now(dt.UTC)-dt.datetime.fromisoformat(quote[2])).total_seconds()>120):
                return None
            return quote
        return None

def prepare_settlements(db):
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS settlements(
            venue TEXT NOT NULL, market TEXT NOT NULL, token TEXT NOT NULL,
            payout INTEGER NOT NULL CHECK(payout>=0), pnl INTEGER NOT NULL, body TEXT NOT NULL,
            PRIMARY KEY(venue,market,token))""")

def prepare_sales(db):
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS sales(
            venue TEXT NOT NULL, id TEXT NOT NULL, market TEXT NOT NULL, token TEXT NOT NULL,
            quantity INTEGER NOT NULL, cost_exact TEXT NOT NULL, fee_exact TEXT NOT NULL,
            credit INTEGER NOT NULL CHECK(credit>=0), body TEXT NOT NULL,
            PRIMARY KEY(venue,id))""")
        db.execute("""CREATE TABLE IF NOT EXISTS sell_targets(
            venue TEXT NOT NULL, market TEXT NOT NULL, token TEXT NOT NULL,
            remainder TEXT NOT NULL, block INTEGER NOT NULL, tx_index INTEGER NOT NULL,
            PRIMARY KEY(venue,market,token))""")

def remaining(db,venue,market,token,quantity,cost,fee):
    sold=0
    cost,fee=Fraction(cost),Fraction(fee)
    for shares,basis,expense in db.execute(
            'SELECT quantity,cost_exact,fee_exact FROM sales WHERE venue=? AND market=? AND token=?',
            (venue,market,token)):
        sold+=shares
        cost-=Fraction(basis)
        fee-=Fraction(expense)
    if sold>quantity or cost<0 or fee<0:
        raise RuntimeError('sale ledger does not reconcile')
    return quantity-sold,cost,fee

def projected(number):
    return (2*number.numerator+number.denominator)//(2*number.denominator)

def cash_credits(db):
    return db.execute("""SELECT (SELECT COALESCE(SUM(payout),0) FROM settlements)+
        (SELECT COALESCE(SUM(credit),0) FROM sales)""").fetchone()[0]

def record_sell(db,event,result):
    venue,market,token=event['venue'],position_market(event),event['token']
    last=db.execute('SELECT remainder,block,tx_index FROM sell_targets WHERE venue=? AND market=? AND token=?',
                    (venue,market,token)).fetchone()
    block,index=result['sequence']
    if last and (block,index)<=last[1:]:
        raise Skip('sell_order')
    if db.execute('SELECT 1 FROM settlements WHERE venue=? AND market=? AND token=?',(venue,market,token)).fetchone():
        raise Skip('closed')
    shares,cost,fee,latest=db.execute("""SELECT COALESCE(SUM(quantity),0),COALESCE(SUM(cost),0),
        COALESCE(SUM(fee),0),MAX(CAST(json_extract(body,'$.at') AS INTEGER))
        FROM events WHERE venue=? AND market=? AND token=? AND debit>0""",(venue,market,token)).fetchone()
    if latest is not None and latest>=event['at']:
        raise Skip('sell_order')
    shares,cost,fee=remaining(db,venue,market,token,shares,cost,fee)
    if not shares:
        raise Skip('no_position')
    carried=min(Fraction(last[0]),shares) if last else Fraction()
    target=carried+result['fraction']*(shares-carried)
    # Virtual quantity is recorded in microshares. Keep the uneconomic remainder
    # for a later confirmed leader exit, with the exchange minimum checked again.
    whole=int(target)
    minimum=result['minimum']
    if minimum<=0:
        raise Skip('minimum')
    sold=0
    if whole>=minimum:
        if not 0<=time.time()-event['at']<=30 or time.monotonic()-result['readAt']>2:
            raise Skip('signal_age')
        gross,exit_fee,price=sale_proceeds(result['levels'],whole,result['rate'])
        sold=whole
        basis=cost*Fraction(sold,shares)
        entry=fee*Fraction(sold,shares)
        # Projection uses differences of rounded balances; durable allocation remains rational.
        basis_display=projected(cost)-projected(cost-basis)
        entry_display=projected(fee)-projected(fee-entry)
        credit=gross-exit_fee
        row=dict(kind='sale',id=event['id'],venue=venue,trader=event_trader(event),at=int(time.time()),
                 market=event['market'],outcome=event['outcome'],condition=event['condition'],quantity=sold,
                 gross=gross,payout=credit,cost=basis_display,fee=entry_display,exitFee=exit_fee,
                 pnl=credit-basis_display-entry_display,price=price,remaining=shares-sold)
        db.execute('INSERT INTO sales VALUES(?,?,?,?,?,?,?,?,?)',
                   (venue,event['id'],market,token,sold,str(basis),str(entry),credit,json.dumps(row,ensure_ascii=False)))
    db.execute("""INSERT INTO sell_targets VALUES(?,?,?,?,?,?) ON CONFLICT(venue,market,token)
        DO UPDATE SET remainder=excluded.remainder,block=excluded.block,tx_index=excluded.tx_index""",
        (venue,market,token,str(target-sold),block,index))
    return {'reason':'minimum'} if not sold else {}

def position_snapshot(db, health, quotes):
    db.execute('BEGIN IMMEDIATE')
    try:
        positions=[]
        for v,market,token,shares,cost,fees,body in db.execute("""
            SELECT e.venue,e.market,e.token,SUM(e.quantity),SUM(e.cost),SUM(e.fee),MIN(e.body)
            FROM events e WHERE e.debit>0 AND NOT EXISTS (
              SELECT 1 FROM settlements s WHERE s.venue=e.venue AND s.market=e.market AND s.token=e.token
            ) GROUP BY e.venue,e.market,e.token ORDER BY e.venue,e.market,e.token""").fetchall():
            event=json.loads(body)
            shares,basis,entry=remaining(db,v,market,token,shares,cost,fees)
            if not shares:
                continue
            cost,fees=projected(basis),projected(entry)
            quote=quotes.read((v,market,token),dict(event, _settlementShares=shares))
            mark=closing=None
            if quote is not None:
                price,source,at,closing_quote=quote
                proof = price if isinstance(price, poly_v2_settlement.Payout) else None
                if proof is not None:
                    if source != 'payout' or proof.shares != shares:
                        raise Skip('v2_payout_scope')
                    price = Fraction(proof.micros, shares)
                    value = proof.micros
                    pnl = value-cost-fees
                elif price is not None:
                    if isinstance(price,Fraction):
                        value=projected(shares*price)
                    else:
                        value=int((shares*price).to_integral_value(rounding=ROUND_HALF_UP))
                    pnl=value-cost-fees
                if source=='payout':
                    row=dict(kind='settlement',id=market+':'+token,venue=v,market=event['market'],
                             condition=event['condition'],outcome=event['outcome'],trader=event['trader'],
                             at=int(time.time()),resolvedAt=at,quantity=shares,cost=cost,fee=fees,
                             price=format(D(price.numerator)/D(price.denominator),'f') if isinstance(price,Fraction) else format(price,'f'),payout=value,pnl=pnl)
                    if isinstance(price,Fraction):
                        row['payoutFraction']=str(price)
                    if proof is not None:
                        row['payoutEvidence'] = proof.evidence
                    db.execute('INSERT INTO settlements VALUES(?,?,?,?,?,?)',
                               (v,market,token,value,pnl,json.dumps(row,ensure_ascii=False)))
                    continue
                if price is not None:
                    mark=dict(price=format(price,'f'),source=source,at=at,value=value,pnl=pnl)
                closing=position_sale(closing_quote,shares,cost,fees)
            positions.append(dict(id=v+':'+market+':'+token,venue=v,market=event['market'],outcome=event['outcome'],
                                  condition=event['condition'],trader=event['trader'],
                                  quantity=shares,cost=cost,fee=fees,mark=mark,closing=closing))
        spent=db.execute('SELECT COALESCE(SUM(debit),0) FROM events').fetchone()[0]
        settlements=[json.loads(x[0]) for x in db.execute('SELECT body FROM settlements ORDER BY rowid DESC')]
        sales=[json.loads(x[0]) for x in db.execute('SELECT body FROM sales ORDER BY rowid DESC')]
        balance=START-spent+cash_credits(db)
        rows=[json.loads(x[0]) for x in db.execute('SELECT body FROM events ORDER BY seq DESC LIMIT 80')]
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return dict(schema=1,updatedAt=timestamp(),opening=START,available=balance,events=rows,
                positions=positions,settlements=settlements,sales=sales,health=health,leaders=NAMES)

def publish(db, path, health, quotes):
    state=position_snapshot(db,health,quotes)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False) as tmp:
        name=tmp.name
        json.dump(state,tmp,ensure_ascii=False)
        tmp.flush()
        os.fchmod(tmp.fileno(),0o644)
        os.fsync(tmp.fileno())
    try:
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)

def record(db,s,result):
    venue,identity=s['venue'],s['id']
    market=position_market(s)
    public_market=market.split(':',1)[0]
    wallet_scope_pattern=public_market+':*'
    day=dt.datetime.now(WARSAW).date().isoformat()
    db.execute('BEGIN IMMEDIATE')
    try:
        if db.execute('SELECT 1 FROM events WHERE venue=? AND id=? UNION ALL SELECT 1 FROM sales WHERE venue=? AND id=?',
                      (venue,identity,venue,identity)).fetchone():
            db.rollback()
            return
        total,daily,same=db.execute('''SELECT COALESCE(SUM(debit),0),
          COALESCE(SUM(CASE WHEN day=? THEN debit ELSE 0 END),0),
          COALESCE(SUM(CASE WHEN venue=? AND (market=? OR market GLOB ?) THEN debit ELSE 0 END),0)
          FROM events''',(day,venue,public_market,wallet_scope_pattern)).fetchone()
        if s.get('side')=='SELL':
            if 'reason' not in result:
                try:
                    result=record_sell(db,s,result)
                except Skip as failure:
                    result={'reason':str(failure)}
            if 'reason' not in result:
                db.commit()
                return
        if 'reason' not in result:
            paid=cash_credits(db)
            closed=db.execute('SELECT 1 FROM settlements WHERE venue=? AND market=? AND token=?',
                              (venue,market,s.get('token',''))).fetchone()
            if closed:
                result={'reason':'closed'}
            else:
                released=sum((Fraction(c)+Fraction(f) for c,f in db.execute(
                    'SELECT cost_exact,fee_exact FROM sales WHERE venue=? AND (market=? OR market GLOB ?)',
                    (venue,public_market,wallet_scope_pattern))),Fraction())
                if min(START-total+paid,DAILY-daily,MARKET-same+released)<result['cost']+result['fee']:
                    result={'reason':'limit'}
        debit=result.get('cost',0)+result.get('fee',0)
        body={**s,**result,'trader':event_trader(s),'recordedAt':timestamp()}
        db.execute('''INSERT INTO events(venue,id,day,market,token,debit,quantity,cost,fee,body)
                   VALUES(?,?,?,?,?,?,?,?,?,?)''',(venue,identity,day,market,s.get('token',''),debit,
                   result.get('quantity',0),result.get('cost',0),result.get('fee',0),json.dumps(body,ensure_ascii=False)))
        db.commit()
        print(json.dumps(dict(venue=venue,event=hashlib.sha256(identity.encode()).hexdigest()[:12],result=result.get('reason','filled'))),flush=True)
    except BaseException:
        db.rollback()
        raise

def main():
    path,dbpath=map(Path,sys.argv[1:])
    db=sqlite3.connect(dbpath)
    db.execute('PRAGMA synchronous=FULL')
    db.execute('''CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, venue TEXT, id TEXT, day TEXT,
        market TEXT, token TEXT, debit INTEGER, quantity INTEGER, cost INTEGER, fee INTEGER, body TEXT,
        UNIQUE(venue,id))''')
    db.execute('CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY, value INTEGER)')
    with db:
        db.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',('started',int(time.time())))
        started=db.execute("SELECT value FROM settings WHERE name='started'").fetchone()[0]
        start_by_venue={}
        for venue,wallet in WALLETS.items():
            if wallet.lower()==LEGACY_WALLETS[venue]:
                start_by_venue[venue]=started
                continue
            key=f'follow:{venue}:{wallet.lower()}'
            db.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',(key,int(time.time())))
            start_by_venue[venue]=db.execute('SELECT value FROM settings WHERE name=?',(key,)).fetchone()[0]
    prepare_settlements(db)
    prepare_sales(db)
    health={}
    with (concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool,
          concurrent.futures.ThreadPoolExecutor(max_workers=3) as quote_pool):
        quotes=PositionQuotes(quote_pool)
        publish(db,path,health,quotes)
        while time.time()<CUT_OFF:
            tick=time.monotonic()
            signals=[]
            calls=[(venue,pool.submit(lambda adapter:list(adapter()),adapter)) for venue,adapter in
                   [('polymarket',poly_signals),('limitless',limitless_signals)]]
            for venue,future in calls:
                try:
                    rows=future.result()
                    health[venue]='ok'
                    seen=set()
                    for s in reversed(rows):
                        if s['at']<start_by_venue[venue]:continue
                        if s['wallet'].lower()!=LEGACY_WALLETS[venue]:
                            s['id']=s['wallet'].lower()+':'+s['id']
                        if s['id'] in seen:continue
                        seen.add(s['id'])
                        if not db.execute('SELECT 1 FROM events WHERE venue=? AND id=? UNION ALL SELECT 1 FROM sales WHERE venue=? AND id=?',
                                          (venue,s['id'],venue,s['id'])).fetchone():
                            signals.append(s)
                except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as e:
                    health[venue]='unavailable'
                    print(venue,type(e).__name__,flush=True)
            fresh=[s for s in signals if 0<=time.time()-s['at']<=30]
            fresh.sort(key=lambda s:s['at'])
            fresh=[s for venue in NAMES for s in [row for row in fresh if row['venue']==venue][:2]]
            pending=[]
            for s in fresh:
                if s['side']=='BUY':
                    pending.append((s,pool.submit(evaluate,s)))
                    continue
                # Skip chain reads when there has never been a matching local buy.
                found=db.execute("""SELECT 1 FROM events WHERE venue=? AND market=? AND debit>0
                    AND json_extract(body,'$.outcome')=? LIMIT 1""",(s['venue'],position_market(s),s['outcome'])).fetchone()
                arriving=any(buy['side']=='BUY' and buy['venue']==s['venue'] and
                             position_market(buy)==position_market(s) and buy['outcome']==s['outcome'] and
                             buy['at']<=s['at'] for buy in signals)
                if found or arriving:
                    pending.append((s,pool.submit(evaluate_sell,s)))
                else:
                    record(db,s,{'reason':'no_position'})
            for s in signals:
                if time.time()-s['at']>30:
                    record(db,s,{'reason':'signal_age'})
            ready=[(s,future.result()) for s,future in pending]
            ready.sort(key=lambda pair:(pair[0]['at'],pair[1].get('sequence',(0,0))))
            for s,result in ready:
                if time.time()>=CUT_OFF:break
                record(db,s,result)
            publish(db,path,health,quotes)
            time.sleep(max(0,5-(time.monotonic()-tick)))

if __name__=='__main__':
    main()
