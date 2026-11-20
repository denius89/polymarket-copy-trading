"""Read two Polygon providers and verify a common finalized block."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import time
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.error import URLError
from urllib.parse import urlsplit


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')


def numeric(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x(?:0|[1-9a-f][0-9a-f]{0,15})', value):
        raise ValueError('Invalid block quantity')
    return int(value, 16)


def hash_value(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-f]{64}', value):
        raise ValueError('Invalid block hash')
    return value


def header(value):
    if not isinstance(value, dict):
        raise ValueError('Missing block')
    return {
        'number': numeric(value.get('number')),
        'hash': hash_value(value.get('hash')),
        'parentHash': hash_value(value.get('parentHash')),
        'timestamp': numeric(value.get('timestamp')),
    }


def rpc(origin, method, parameters):
    body = canonical({'id': 1, 'jsonrpc': '2.0', 'method': method, 'params': parameters})
    request = Request(origin, body, {'Content-Type': 'application/json', 'Accept': 'application/json',
                                    'User-Agent':'Shadow-demo-anchor-read-only/1'})
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=6) as response:
        raw = response.read(65_537)
    if len(raw) > 65_536:
        raise ValueError('Oversize response')
    response = json.loads(raw)
    if not isinstance(response, dict) or response.get('id') != 1 or 'error' in response or 'result' not in response:
        raise ValueError('Invalid RPC response')
    return response['result']


def finalized(origin):
    if numeric(rpc(origin, 'eth_chainId', [])) != 137:
        raise ValueError('Unexpected Polygon chain')
    return header(rpc(origin, 'eth_getBlockByNumber', ['finalized', False]))


def anchor(origins):
    with ThreadPoolExecutor(max_workers=2) as pool:
        tips = tuple(pool.map(finalized, origins))
        height = min(tip['number'] for tip in tips)
        blocks = tuple(pool.map(lambda origin: header(rpc(origin, 'eth_getBlockByNumber', [hex(height), False])), origins))
    if blocks[0] != blocks[1] or blocks[0]['number'] != height:
        raise ValueError('Finalized providers disagree on the canonical header')
    for tip in tips:
        if tip['number'] == height and tip != blocks[0]:
            raise ValueError('The provider changed its finalized header')
    observed_at = time.time()
    if not 0 <= observed_at - blocks[0]['timestamp'] <= 300:
        raise ValueError('Finalized anchor is outside the observation window')
    return {'chainId': 137, 'observedAt': datetime.fromtimestamp(observed_at, timezone.utc).isoformat(timespec='milliseconds'),
            'provenance': [{'origin': origin, 'finalized': block} for origin, block in zip(origins, tips)],
            'commonFinalized': blocks[0]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rpc', nargs=2, required=True, metavar=('PRIMARY', 'SECONDARY'))
    parser.add_argument('--checkpoint', action='append', default=[], metavar='NAME=BLOCK')
    args = parser.parse_args()
    parsed = [urlsplit(value) for value in args.rpc]
    if any(p.scheme != 'https' or not p.hostname or p.username or p.password or p.query or p.fragment for p in parsed):
        parser.error('Use two HTTPS RPC URLs without credentials')
    if parsed[0].hostname == parsed[1].hostname:
        parser.error('Use two distinct RPC providers')
    checkpoints = {}
    for item in args.checkpoint:
        match = re.fullmatch(r'([a-zA-Z0-9_-]+)=(0|[1-9][0-9]{0,18})', item)
        if not match or match[1] in checkpoints:
            parser.error('Checkpoints must have unique NAME=BLOCK values')
        checkpoints[match[1]] = int(match[2])
    try:
        result = anchor(args.rpc)
    except (ValueError, TimeoutError, URLError) as error:
        parser.exit(1, f'Anchor not confirmed: {error}\n')
    height = result['commonFinalized']['number']
    if any(number > height for number in checkpoints.values()):
        raise SystemExit('A saved checkpoint is ahead of the shared finalized anchor')
    result['intervals'] = {
        name: {'after': number, 'through': height, 'blockCount': height-number}
        for name, number in checkpoints.items()
    }
    output = {'observation': result, 'sha256': sha256(canonical(result)).hexdigest()}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
