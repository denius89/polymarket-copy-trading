"""Read-only Polymarket PositionManager payout for an existing demo position."""
import datetime as dt
from dataclasses import dataclass
import re
import time

MANAGER = '0x006f54f7f9a22e0000cc2ab60031000000ae9fef'
MODULES = {
    1: '0x1000008dd9001b968442c1000017eae6e0da00ba',
    2: '0x200000900045e3b6259600682756002200028933',
    3: '0x30000034706c7d8e12009dab006be20000c031a8',
}

# First four bytes of Ethereum Keccak-256 for the published ABI signatures.
MODULE_BY_ID = '0x4d51cdf1'
IS_CONDITION_PREPARED = '0x741055b4'
GET_PAYOUT = '0x4c619e4c'


@dataclass(frozen=True)
class Payout:
    shares: int
    micros: int
    evidence: dict


def position_id(condition, token):
    if not isinstance(condition, str) or not re.fullmatch(r'0x[0-9a-fA-F]{62}(?:00)?', condition):
        raise ValueError('Invalid V2 condition ID')
    if not isinstance(token, str) or not re.fullmatch(r'[1-9][0-9]{0,77}', token):
        raise ValueError('Invalid V2 position ID')
    condition_word = int(condition[2:].ljust(64, '0'), 16)
    position = int(token)
    module = position >> 248
    if module not in MODULES or position & 255 not in (0, 1) or position & ~255 != condition_word:
        raise ValueError('V2 position does not belong to the condition')
    return position, module


def word(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}', value):
        raise ValueError('Invalid Polygon ABI word')
    return int(value, 16)


def header(block):
    number, timestamp, block_hash = block['number'], block['timestamp'], block['hash']
    if not re.fullmatch(r'0x[0-9a-fA-F]{64}', block_hash):
        raise ValueError('Invalid Polygon block hash')
    for value in (number, timestamp):
        if not re.fullmatch(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)', value):
            raise ValueError('Invalid Polygon block quantity')
    return int(number, 16), int(timestamp, 16), block_hash.lower()


def quote(event, *, rpc, allowed_modules=(1, 2, 3)):
    position, module = position_id(event['condition'], event['token'])
    shares = event['_settlementShares']
    if module not in allowed_modules or type(shares) is not int or not 0 < shares < 2**63:
        raise ValueError('Invalid settlement amount or module')
    if rpc('eth_chainId') != '0x89':
        raise ValueError('Wrong Polygon chain')
    height, seconds, block_hash = header(rpc('eth_getBlockByNumber', 'finalized', False))
    if not 0 < seconds <= time.time():
        raise ValueError('Invalid finalized block time')
    selector = {'blockHash': block_hash, 'requireCanonical': True}

    def call(contract, function_selector, *args):
        calldata = function_selector + ''.join(f'{arg:064x}' for arg in args)
        return word(rpc('eth_call', {'to': contract, 'data': calldata}, selector))

    module_address = MODULES[module]
    if call(MANAGER, MODULE_BY_ID, module) != int(module_address, 16):
        raise ValueError('Unexpected Polygon payout module')
    if module == 3 and call(module_address, IS_CONDITION_PREPARED, position & ~255) != 1:
        raise ValueError('Unprepared Combo condition')
    payout = call(MANAGER, GET_PAYOUT, position, shares)
    if payout > shares:
        raise ValueError('Payout exceeds collateral bound')
    if header(rpc('eth_getBlockByNumber', hex(height), False)) != (height, seconds, block_hash):
        raise ValueError('Finalized block no longer matches canonical chain')
    block_time = dt.datetime.fromtimestamp(seconds, dt.UTC).isoformat()
    evidence = dict(source='polygon-position-manager', chainId=137, positionManager=MANAGER,
                    module=module_address, moduleId=module, positionId=str(position),
                    blockNumber=height, blockHash=block_hash, finalizedBlockTime=block_time)
    return Payout(shares, payout, evidence), 'payout', block_time, None
