#!/usr/bin/env python3
"""Operator-only fresh actor/context loader for the private backend fixture envelope.

Reads a local JSON file, validates closed keys and values, inserts atomically.
No ON CONFLICT overwrite, schema reset, login insertion, key or raw-proof storage.
"""
import datetime
import json
import re
import sys
import uuid

from verify_storage import quote, sql


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('invalid fixture fields')


def uuid_text(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError('invalid fixture id')
    return quote(value)


def timestamp(value, nullable=False):
    if nullable and value is None:
        return 'NULL'
    if not isinstance(value, str):
        raise ValueError('invalid fixture timestamp')
    parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone required')
    return quote(parsed.isoformat()) + '::timestamptz'


def build(seed):
    exact(seed, ('actors', 'contexts'))
    if not isinstance(seed['actors'], list) or not isinstance(seed['contexts'], list):
        raise ValueError('fixture arrays required')
    rows = ['BEGIN;']
    actors = set()
    for a in seed['actors']:
        exact(a, ('id', 'fixed_time', 'blocked'))
        if type(a['blocked']) is not bool or a['id'] in actors:
            raise ValueError('invalid fixture actor')
        actors.add(a['id'])
        rows.append('INSERT INTO v00_session.actors(id,fixed_time,blocked) VALUES(' +
                    ','.join((uuid_text(a['id']), timestamp(a['fixed_time'], True), str(a['blocked']).lower())) + ');')
    contexts = set()
    for c in seed['contexts']:
        exact(c, ('id', 'actor_id', 'proof_digest', 'expires_at', 'login_expires_at', 'idle_expires_at'))
        if c['actor_id'] not in actors or c['id'] in contexts or not isinstance(c['proof_digest'], str) or not re.fullmatch('[0-9a-f]{64}', c['proof_digest']):
            raise ValueError('invalid fixture context')
        contexts.add(c['id'])
        rows.append('INSERT INTO v00_session.contexts(id,actor_id,proof_digest,expires_at,login_expires_at,idle_expires_at) VALUES('
                    + ','.join((uuid_text(c['id']), uuid_text(c['actor_id']), quote(c['proof_digest']), timestamp(c['expires_at']),
                                timestamp(c['login_expires_at']), timestamp(c['idle_expires_at']))) + ');')
    rows.append('COMMIT;')
    return '\n'.join(rows)


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as stream:
        seed = json.load(stream)
    sql(build(seed))
    print(json.dumps({'actors_inserted': len(seed['actors']), 'contexts_inserted': len(seed['contexts'])}))
