#!/usr/bin/env python3
"""Operator-only directory loader. Never executed by the DB chat against Oracle."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys


def private_json(path):
    path = Path(path)
    if path.stat().st_mode & 0o077:
        raise ValueError('private file permissions required')
    return json.loads(path.read_text())


def address_digest(key, address):
    values = ['v00-d03-07', 'email_send', 'ascii-email-v1', address]
    framed = b''.join(len(v.encode('ascii')).to_bytes(4, 'big') + v.encode('ascii') for v in values)
    return hmac.new(key, b'shadow.v00.email-address.v1\0' + framed, hashlib.sha256).hexdigest()


def load(fixture_path, key_path):
    fixture, keys = private_json(fixture_path), private_json(key_path)
    if set(fixture) != {'entries'} or type(fixture['entries']) is not list:
        raise ValueError('invalid fixture shape')
    key = keys['email_address']
    if key['id'] != 'email-address-1' or len(bytes.fromhex(key['hex'])) != 32:
        raise ValueError('invalid address key')
    entries = []
    for row in fixture['entries']:
        if set(row) != {'actor_id', 'normalized_email'}:
            raise ValueError('invalid fixture entry')
        address = row['normalized_email']
        if not isinstance(address, str) or not address.isascii() or address != address.lower() or address != address.strip(' '):
            raise ValueError('noncanonical provider email')
        entries.append(row | {'address_digest': address_digest(bytes.fromhex(key['hex']), address),
                              'address_key_id': key['id']})
    encoded = base64.b64encode(json.dumps({'entries': entries}, separators=(',', ':')).encode()).decode()
    statement = ('BEGIN; SET LOCAL ROLE v00_email_owner;\n'
                 "SELECT v00_email.seed_directory(convert_from(decode($1,'base64'),'UTF8')::jsonb)::text\n"
                 "\\bind '" + encoded + "'\n\\g\nCOMMIT;\n")
    argv = json.loads(os.environ['V00_EMAIL_PSQL_COMMAND_JSON'])
    result = subprocess.run(argv + ['-XAt', '-v', 'ON_ERROR_STOP=1'], input=statement,
                            text=True, capture_output=True, timeout=30)
    if result.returncode or result.stdout.splitlines()[-1:] != ['COMMIT']:
        raise RuntimeError('directory transaction not confirmed; inspect privately; do not retry blindly')
    rows = [line for line in result.stdout.splitlines() if line.startswith('{')]
    if len(rows) != 1:
        raise RuntimeError('unexpected directory reply')
    reply = json.loads(rows[0])
    if reply != {'entries_inserted': len(entries)}:
        raise RuntimeError('directory count mismatch')
    return reply


if __name__ == '__main__':
    try:
        print(json.dumps(load(sys.argv[1], sys.argv[2])))
    except Exception:
        print(json.dumps({'error': 'directory_load_unconfirmed'}))
        raise SystemExit(1)
