"""Pure Data API maker row and CTF-v2 receipt checks; no reads or writes."""
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import re

from resolver import Skip, EXCHANGES, MATCH, FILL, decode, exact, hex_id, uint, q, sha

SOURCE='polymarket-data-api-maker-finalized-v1'
PROFILE='data-api-v2-trades-maker-seconds-v1'
ENDPOINT='https://data-api.polymarket.com/v2/trades'


def parse_row(raw):
    if not isinstance(raw,bytes) or not 0<len(raw)<=65536:raise Skip('MAKER_ROW_SIZE')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise Skip('DUPLICATE_JSON_KEY')
            result[key]=value
        return result
    try:
        row=json.loads(raw,parse_float=Decimal,object_pairs_hook=pairs,
                       parse_constant=lambda _:(_ for _ in ()).throw(Skip('INVALID_NUMBER')))
        stamp=row['timestamp']
        if type(stamp) is not int or not 0<=stamp<=((2**53-1)//1000):raise Skip('INVALID_SOURCE_TIME')
        token=row['token_id']
        if not isinstance(token,str) or not re.fullmatch('[1-9][0-9]{0,77}',token) or int(token)>=2**256:raise Skip('INVALID_TOKEN')
        if row['side']!='BUY':raise Skip('MAKER_BUY_ONLY')
        quantity,price=exact(row['size']),exact(row['price'])
        if quantity<=0 or not 0<price<1:raise Skip('INVALID_AMOUNT')
        return dict(transactionHash=hex_id(row['transaction_hash'],32),wallet=hex_id(row['proxy_wallet'],20),
                    marketId=hex_id(row['condition_id'],32),outcomeId=token,side='BUY',
                    sourceTimestampMs=stamp*1000,reportedQuantity=q(quantity),reportedPrice=q(price))
    except (KeyError,TypeError,ValueError,RecursionError):raise Skip('MAKER_ROW_INVALID') from None


def select_fill(receipt,reported):
    tx=reported['transactionHash']
    if not isinstance(receipt,dict) or receipt.get('status')!='0x1' or hex_id(receipt['transactionHash'],32)!=tx:
        raise Skip('RECEIPT_NOT_SUCCESSFUL')
    block,bh=uint(receipt['blockNumber']),hex_id(receipt['blockHash'],32)
    logs=receipt['logs']
    if not isinstance(logs,list) or not 1<=len(logs)<=4096:raise Skip('RECEIPT_LOGS_INVALID')
    fills=[];matched=[];previous=-1
    for ordinal,log in enumerate(logs):
        index=uint(log['logIndex'])
        if (index<=previous or log.get('removed') is True or hex_id(log['transactionHash'],32)!=tx or
            uint(log['blockNumber'])!=block or hex_id(log['blockHash'],32)!=bh):raise Skip('RECEIPT_LOG_IDENTITY')
        previous=index;exchange=hex_id(log['address'],20)
        if exchange not in EXCHANGES or not log.get('topics'):continue
        topic=log['topics'][0].lower()
        if topic==MATCH:
            topics,values=decode(log,4,3);matched.append((exchange,index,topics,values))
        elif topic==FILL:
            topics,values=decode(log,7,4);fills.append((ordinal,index,exchange,topics,values))
    candidates=[];identities=0;paired=0
    for ordinal,index,exchange,topics,values in fills:
        if ('0x'+topics[2][-40:],str(values[1]),values[0])!=(reported['wallet'],reported['outcomeId'],0):continue
        # OrderFilled also accompanies the taker OrdersMatched event. A field named
        # maker is the owner of the order, not proof of the liquidity role.
        if any(ex==exchange and mt[1:3]==topics[1:3] for ex,mi,mt,mv in matched):
            paired+=1;continue
        identities+=1;gross,quantity=values[2:4]
        if min(gross,quantity)<=0 or gross>=quantity:raise Skip('EVENT_AMOUNT_INVALID')
        if (q(Fraction(quantity,1_000_000)),q(Fraction(gross,quantity)))!=(reported['reportedQuantity'],reported['reportedPrice']):continue
        candidates.append(dict(chainId=137,exchange=exchange,transactionHash=tx,receiptOrdinal=ordinal,logIndex=index,
            wallet=reported['wallet'],marketId=reported['marketId'],outcomeId=reported['outcomeId'],side='BUY',
            quantity=q(Fraction(quantity,1_000_000)),gross=q(Fraction(gross,1_000_000)),matchingCount=1,
            orderHash=topics[1],role='maker'))
    details=dict(receiptSha256=sha(receipt),receiptLogsCount=len(logs),identityCandidateCount=identities,
                 exactCandidateCount=len(candidates),excludedPairedTakerFills=paired)
    if len(candidates)!=1:raise Skip('MAKER_FILL_NOT_FOUND' if not candidates else 'MAKER_FILL_AMBIGUOUS',details)
    return candidates[0],details


def identity(match):
    key=['polygon-maker-order-filled-v1',137,match['exchange'],match['transactionHash'],match['receiptOrdinal'],
         match['orderHash'],match['wallet'],match['marketId'],match['outcomeId'],match['side']]
    eid=sha(key)
    return eid,sha([eid,match['quantity'],match['gross']])
