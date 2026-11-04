#!/usr/bin/env python3
"""Operator-only fresh fixtures; writes PRIVATE controller config, never prints keys.

Run after storage installation. The output file must be outside Git and not exist.
Each execution creates a new UUID scope. No old fixture reset/deletion.
"""
import argparse
import base64
import json
import os
import secrets

from verify_storage import FP, fixture, quote, request, rpc, sql, uid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    # Reserve the private destination BEFORE creating fixtures; never overwrite keys.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    config = dict(fingerprint_key_hex=secrets.token_hex(32), principals={}, contexts={}, cases={}, email_operations={})
    public_seed = base64.b32encode(b'12345678901234567890').decode()
    actor_keys = {}

    def bind(label, f, seed=public_seed):
        actor = f['actor']
        if actor not in actor_keys:
            actor_keys[actor] = secrets.token_urlsafe(32)
            config['principals'][actor_keys[actor]] = actor
        config['contexts'][f['context']] = dict(principal_id=actor, factor_version=f['factor'], secret_base32=seed)
        config['cases'][label] = dict(contextId=f['context'], challengeId=f['challenge'], principal_id=actor,
                                      factor_version=f['factor'], clock_mode='fixed_fixture')

    try:
        a = fixture()
        bind('collision', a)
        bind('collision_reuse', fixture(actor=a['actor'], factor=a['factor']))
        bind('new_factor_version', fixture(actor=a['actor']))
        b = fixture(step=153566)
        rpc('verify_totp', request(b, [153567], fingerprint=FP))
        sql('UPDATE v00_db.actors SET fixed_time=to_timestamp(153568*30) WHERE id=' + quote(b['actor']) + ';')
        bind('partial_overlap', fixture(actor=b['actor'], factor=b['factor']))
        c = fixture()
        bind('concurrent_a', c)
        bind('concurrent_b', fixture(actor=c['actor'], factor=c['factor']))
        bind('wrong_codes', fixture())
        d = fixture()
        sql('UPDATE v00_db.challenges SET expires_at=to_timestamp(153568*30) WHERE id=' + quote(d['challenge']) + ';')
        bind('expired_challenge', d)
        e = fixture()
        sql('UPDATE v00_db.contexts SET current_challenge_id=NULL WHERE id=' + quote(e['context']) + ';')
        bind('missing_current_challenge', e)
        w = fixture()
        sql('UPDATE v00_db.actors SET fixed_time=NULL WHERE id=' + quote(w['actor']) + ';'
            'UPDATE v00_db.contexts SET expires_at=clock_timestamp()+interval \'1 hour\' WHERE id=' + quote(w['context']) + ';'
            'UPDATE v00_db.challenges SET expires_at=clock_timestamp()+interval \'5 minutes\' WHERE id=' + quote(w['challenge']) + ';')
        bind('wall_clock', w, base64.b32encode(secrets.token_bytes(20)).decode())
        config['cases']['wall_clock']['clock_mode'] = 'wall'
        with os.fdopen(fd, 'w') as out:
            json.dump(config, out, indent=2)
            out.write('\n')
        print(json.dumps({'fixture_contexts': len(config['contexts']), 'private_config_written': True,
                          'fixed_vector': {'evaluation_step':153568,'code':'468457','matched_steps':[153567,153569]},
                          'partial_overlap_preconsumed_steps':[153567]}))
    except BaseException:
        # Leave the reserved file as evidence of partial setup; do not rerun/overwrite.
        os.close(fd)
        raise


if __name__ == '__main__':
    main()
