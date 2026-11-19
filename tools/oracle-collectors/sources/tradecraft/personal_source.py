"""Bind a personal Activity row to the original, verified CTF receipt."""
from fractions import Fraction
from hashlib import sha256
import json
import re
from urllib.request import Request

import maker_provenance
from resolver import EXCHANGES, FILL, MATCH, Skip, decode, hex_id, sha, uint
import rtds_provenance
import source

STANDARD = '0xe111180000d2663c0091e4f400237545b87b996b'


def normalize_fill(log, receipt, wallet):
    exchange = hex_id(log['address'], 20)
    if (exchange not in EXCHANGES or log.get('removed') is not False
            or receipt.get('status') != '0x1'):
        raise Skip('PERSONAL_FILL_RECEIPT')
    topics, words = decode(log, 7, 4)
    side, token, maker, taker, fee, _, _ = words
    index = uint(log['logIndex'])
    if (topics[0] != FILL or '0x' + topics[2][26:] != wallet
            or topics[3][2:26] != '0' * 24 or side not in (0, 1)
            or any(log[key] != receipt[key] for key in ('transactionHash', 'blockHash', 'blockNumber'))
            or [entry for entry in receipt['logs'] if uint(entry['logIndex']) == index] != [log]):
        raise Skip('PERSONAL_FILL_IDENTITY')
    row = dict(transactionHash=hex_id(log['transactionHash'], 32), logIndex=str(index),
               blockNumber=str(uint(log['blockNumber'])), blockHash=hex_id(log['blockHash'], 32),
               orderHash=topics[1], owner=wallet, counterparty='0x' + topics[3][26:],
               side=('BUY', 'SELL')[side], tokenId=str(token), makerAmountFilledRaw=str(maker),
               takerAmountFilledRaw=str(taker), feeRaw=str(fee), builder=f'0x{words[5]:064x}',
               metadata=f'0x{words[6]:064x}', rawLogSha256=sha(log), receiptSha256=sha(receipt))
    if exchange != STANDARD:
        row['exchange'] = exchange
    return row


def pairs(values):
    result = dict(values)
    if len(result) != len(values):
        raise Skip('PERSONAL_GAMMA_DUPLICATE_KEY')
    return result


def market_binding(event, timeout):
    token = event['outcomeId']
    if not re.fullmatch(r'0|[1-9][0-9]{0,77}', token) or int(token) >= 2**256:
        raise Skip('PERSONAL_MARKET_TOKEN')
    if timeout <= 0:
        raise Skip('PERSONAL_MARKET_TIME')
    url = 'https://gamma-api.polymarket.com/markets?clob_token_ids=' + token
    request = Request(url, headers={'Accept': 'application/json'})
    with source.OPENER.open(request, timeout=min(2, timeout)) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise Skip('PERSONAL_MARKET_SIZE')
    records = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(records, list):
        raise Skip('PERSONAL_MARKET_SHAPE')
    matches = []
    for row in records:
        protocol = row.get('version')
        field = {'v1': 'clobTokenIds', 'v2': 'positionIds'}.get(protocol)
        if field is None:
            continue
        ids = row.get(field)
        ids = json.loads(ids) if isinstance(ids, str) else ids
        if isinstance(ids, list) and token in ids:
            matches.append((row, ids))
    if len(matches) != 1:
        raise Skip('PERSONAL_MARKET_AMBIGUOUS')
    row, ids = matches[0]
    labels = row['outcomes']
    labels = json.loads(labels) if isinstance(labels, str) else labels
    if (row['version'] != 'v1' or row['conditionId'] != event['marketId'] or len(ids) != 2
            or len(set(ids)) != 2 or not all(re.fullmatch(r'0|[1-9][0-9]{0,77}', x) and int(x) < 2**256 for x in ids)
            or not isinstance(labels, list) or len(labels) != 2):
        raise Skip('PERSONAL_MARKET_BINDING')
    title, label = row['question'], labels[ids.index(token)]
    for value, limit in ((title, 2048), (label, 256)):
        if not isinstance(value, str) or not 1 <= len(value) <= limit or re.search(r'[\x00-\x1f\x7f-\x9f]', value):
            raise Skip('PERSONAL_MARKET_TITLE')
    return dict(tokenId=token, conditionId=event['marketId'], marketTitle=title,
                outcome=label, protocol=row['version'], marketSha256=sha256(raw).hexdigest())


def normalized_candidate(event, estimate, now_ms):
    source = event['venueReceipt']
    if source['source'] == maker_provenance.SOURCE:
        validator = maker_provenance
    elif source['source'] == rtds_provenance.SOURCE:
        validator = rtds_provenance
    else:
        raise Skip('PERSONAL_SOURCE_PROFILE')
    validator.validate(event, now_ms)
    validator.validate_estimate(event, estimate)
    match = source['match']
    receipt = estimate['evidence']['sourceProof']['receipt']
    original = receipt['logs'][match['receiptOrdinal']]
    exchange = hex_id(original['address'], 20)
    if exchange != match['exchange'] or uint(original['logIndex']) != match['logIndex']:
        raise Skip('PERSONAL_MATCH_IDENTITY')
    if validator is maker_provenance:
        fill = original
    else:
        topics, words = decode(original, 4, 3)
        if topics[0] != MATCH:
            raise Skip('PERSONAL_MATCH_IDENTITY')
        candidates = []
        for log in receipt['logs']:
            if (hex_id(log['address'], 20) == exchange and log['topics']
                    and hex_id(log['topics'][0], 32) == FILL and uint(log['logIndex']) < match['logIndex']):
                fill_topics, fill_words = decode(log, 7, 4)
                if fill_topics[1:3] == topics[1:3] and fill_words[:4] == words:
                    candidates.append(log)
        if len(candidates) != 1:
            raise Skip('PERSONAL_TAKER_FILL_NOT_UNIQUE')
        fill = candidates[0]
    row = normalize_fill(fill, receipt, match['wallet'])
    if (row['side'] != 'BUY' or row['tokenId'] != match['outcomeId']
            or Fraction(int(row['makerAmountFilledRaw']), 1_000_000) != rtds_provenance.q(match['gross'])
            or Fraction(int(row['takerAmountFilledRaw']), 1_000_000) != rtds_provenance.q(match['quantity'])):
        raise Skip('PERSONAL_FILL_AMOUNTS')
    return row
