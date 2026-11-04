#!/usr/bin/env python3
"""Compare independently captured, quiescent pre-backup and restored V00 snapshots.

This is row equality/integrity evidence, NOT proof of WAL continuity, external freshness,
backup encryption, access separation or a permission to reopen Auth.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def compare(before, after):
    required = {'actors','factors','contexts','challenges','totp_results','used_steps',
                'email_confirmations','email_outcomes','email_seals_redacted','provider_observations'}
    checks = []
    def check(name, ok, detail=None):
        checks.append(dict(criterion=name, verdict='pass' if ok else 'fail', detail=detail))
    check('snapshot-profile', before.get('profile') == after.get('profile') == 'v00-db-snapshot-v1')
    check('table-inventory', set(before.get('tables',{})) == set(after.get('tables',{})) == required)
    for name in sorted(required):
        left, right = before.get('tables',{}).get(name), after.get('tables',{}).get(name)
        check(name, isinstance(left,list) and left == right,
              dict(before_count=len(left) if isinstance(left,list) else None,
                   after_count=len(right) if isinstance(right,list) else None,
                   behavioral_coverage='no_data' if left == [] else 'not_asserted',
                   before_digest=digest(left), after_digest=digest(right)))
    expected_integrity = {'used_step_wrong_result':0,'success_step_count_mismatch':0,'outcome_wrong_txid':0,
                          'confirmation_wrong_user':0,'outcome_missing_provider_session':0}
    check('source-integrity', before.get('integrity') == expected_integrity)
    check('restore-integrity', after.get('integrity') == expected_integrity)
    return dict(profile='v00-db-restore-comparison-v1', source_lsn=before.get('wal_lsn'), restore_lsn=after.get('wal_lsn'),
                checks=checks, verdict='pass' if all(x['verdict']=='pass' for x in checks) else 'fail',
                limits=['row equality only; empty tables carry no behavioral coverage',
                        'requires same quiescent capture point; later effects require separate external reconciliation',
                        'does not authorize gate reopening or assert RPO/RTO'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('source')
    p.add_argument('restored')
    args = p.parse_args()
    report = compare(json.loads(Path(args.source).read_text()), json.loads(Path(args.restored).read_text()))
    print(json.dumps(report, indent=2))
    return int(report['verdict'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
