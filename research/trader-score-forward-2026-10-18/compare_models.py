#!/usr/bin/env python3
"""Readiness gates only. No network, fill simulation, ranking or production score."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

SHA = re.compile(r"[0-9a-f]{64}\Z")


def stamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be text')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp missing timezone')
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value):
    if not isinstance(value, str):
        raise ValueError('amount must be decimal text')
    result = Decimal(value)
    if not result.is_finite() or result < 0:
        raise ValueError('amount must be nonnegative finite')
    return result


def validate_target(config, standard):
    if (standard['standard_id'] != 'copy-reference-single-v1'
        or config.get('schema_version') != 'forward-comparison-v1'
        or standard['opening']['virtual_cash'] != config['target']['opening_virtual_cash']
        or standard['target']['target_horizon_calendar_days'] != config['target']['horizon_calendar_days']
        or standard['sizing']['session_zone'] != config['target']['timezone']
        or number(config['target']['opening_virtual_cash']) <= 0):
        raise ValueError('frozen copier target mismatch')


def evidence_hashes(entries, base):
    if not isinstance(entries, list) or not entries:
        raise ValueError('no immutable evidence files')
    hashes = set()
    for entry in entries:
        relative = entry['path']
        expected = entry['sha256']
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError('evidence path must be relative')
        candidate = (base / relative).resolve()
        if not candidate.is_relative_to(base.resolve()):
            raise ValueError('evidence path escapes bundle')
        if not isinstance(expected, str) or not SHA.fullmatch(expected):
            raise ValueError('malformed evidence hash')
        if digest(candidate) != expected:
            raise ValueError('evidence hash mismatch')
        hashes.add(expected)
    return hashes


def check_session(row, config, base, standard_hash, now):
    reasons = []
    sid = row.get('session_id')
    for name in ('session_id', 'canonical_identity', 'venue_binding_id'):
        if not isinstance(row.get(name), str) or not row[name].strip():
            reasons.append('missing_' + name)
    if row.get('standard_sha256') != standard_hash:
        reasons.append('standard_mismatch')
    if row.get('outcome_kind') != 'forward_shadow_conditional':
        reasons.append('not_conditional_shadow_outcome')
    if row.get('ledger_status') != 'independently_crosschecked':
        reasons.append('ledger_not_crosschecked')
    if row.get('unknown_components') != []:
        reasons.append('unknown_components')
    if not isinstance(row.get('path_sha256'), str) or not SHA.fullmatch(row['path_sha256']):
        reasons.append('missing_common_monetary_path_hash')
    try:
        start, cutoff, observed = [stamp(row.get(k)) for k in ('started_at', 'cutoff_at', 'observed_until')]
        zone = ZoneInfo(config['target']['timezone'])
        local_start = start.astimezone(zone)
        if (local_start.hour, local_start.minute, local_start.second, local_start.microsecond) != (0, 0, 0, 0):
            reasons.append('start_not_local_midnight')
        expected_end = local_start + timedelta(days=config['target']['horizon_calendar_days'])
        if cutoff.astimezone(timezone.utc) != expected_end.astimezone(timezone.utc):
            reasons.append('horizon_mismatch')
        if cutoff > now or observed < cutoff or observed > now:
            reasons.append('horizon_not_observed_or_future_claim')
    except (KeyError, TypeError, ValueError):
        reasons.append('invalid_times')
    try:
        hashes = evidence_hashes(row.get('evidence'), base)
        if row.get('path_sha256') not in hashes:
            reasons.append('monetary_path_not_attached')
        requirement_evidence = row.get('requirement_evidence', {})
        if not isinstance(requirement_evidence, dict):
            raise ValueError('requirement evidence must be an object')
        for requirement in config['point_outcome_requirements']:
            links = requirement_evidence.get(requirement)
            if not isinstance(links, list) or not links or any(x not in hashes for x in links):
                reasons.append('missing_evidence_' + requirement)
    except (KeyError, OSError, TypeError, ValueError):
        reasons.append('invalid_evidence_bundle')
    x = None
    try:
        wealth = number(row.get('terminal_net_wealth'))
        if not reasons:
            x = str(wealth / number(config['target']['opening_virtual_cash']))
    except (InvalidOperation, ValueError, TypeError):
        reasons.append('terminal_wealth_unknown_or_invalid')
    return {'session_id': sid, 'status': 'structurally_eligible' if not reasons else 'not_eligible',
            'reasons': sorted(set(reasons)), 'conditional_X': x}


def assess(config, rows, base, standard_hash, now):
    checks = [check_session(row, config, base, standard_hash, now) for row in rows]
    counts = Counter(row.get('session_id') for row in rows if isinstance(row.get('session_id'), str))
    for check in checks:
        if isinstance(check['session_id'], str) and counts[check['session_id']] > 1:
            check['reasons'].append('duplicate_session_id')
            check['status'] = 'not_eligible'
            check['conditional_X'] = None
    blockers = ['no_financial_or_statistical_acceptance_from_schema_gate']
    if config.get('schema_version') != 'forward-comparison-v1':
        blockers.append('unsupported_config_schema')
    if not rows:
        blockers.append('no_complete_future_session_outcomes')
    if any(x['status'] != 'structurally_eligible' for x in checks):
        blockers.append('session_evidence_incomplete')
    for name in ('scope_manifest_sha256', 'enrollment_manifest_sha256'):
        if not SHA.fullmatch(config.get('universe', {}).get(name) or ''):
            blockers.append('unfrozen_' + name)
    for name in ('validation_start_at', 'confirmation_start_at', 'frozen_before_confirmation_sha256', 'holdout_access_log_sha256'):
        if not config.get('phases', {}).get(name):
            blockers.append('missing_' + name)
    for candidate in config.get('candidates', []):
        if not SHA.fullmatch(candidate.get('artifact_sha256') or ''):
            blockers.append('candidate_artifact_not_frozen:' + candidate.get('id', 'unknown'))
    for name in ('owner_approved_risk_tolerance', 'owner_approved_minimum_economic_effect', 'minimum_independent_clusters_for_inference'):
        if config.get('acceptance', {}).get(name) is None:
            blockers.append('unresolved_' + name)
    return {'schema_version': 'forward-comparison-readiness-v1',
            'checked_at': now.isoformat(), 'status': 'collecting' if not rows else 'not_eligible',
            'comparison_executed': False, 'winner': None, 'production_score': None,
            'scope': 'structural_evidence_gate_only_not_audit_verification',
            'sessions_total': len(rows),
            'sessions_structurally_eligible': sum(x['status'] == 'structurally_eligible' for x in checks),
            'blockers': blockers, 'sessions': checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('comparison-config.json'))
    parser.add_argument('--sessions', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    standard_path = (config_path.parent / config['standard_path']).resolve()
    standard = json.loads(standard_path.read_text())
    validate_target(config, standard)
    rows = []
    base = config_path.parent
    if args.sessions:
        supplied = json.loads(args.sessions.read_text())
        if supplied.get('schema_version') != 'forward-session-evidence-v1' or not isinstance(supplied.get('sessions'), list):
            raise ValueError('unsupported sessions schema')
        rows = supplied['sessions']
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError('session must be an object')
        base = args.sessions.resolve().parent
    report = assess(config, rows, base, digest(standard_path), datetime.now(timezone.utc))
    report['config_sha256'] = digest(config_path)
    report['standard_sha256'] = digest(standard_path)
    report['sessions_sha256'] = digest(args.sessions) if args.sessions else None
    with args.out.open('x') as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    print(json.dumps({'status': report['status'], 'comparison_executed': False, 'sessions_total': len(rows)}))


if __name__ == '__main__':
    main()
