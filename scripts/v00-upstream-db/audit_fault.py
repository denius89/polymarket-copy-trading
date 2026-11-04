#!/usr/bin/env python3
"""Offline, scoped before/after storage verifier. No DB/network, no secret output.

Operator supplies private snapshots and original operation refs. Output contains
constant labels/counts only. Storage PASS never certifies dispatch or lock waiting.
"""
import datetime
import json
import sys

from audit_snapshot import audit


class Mismatch(Exception):
    pass


def audit_fault(value):
    checked = 0
    counts = {}

    def need(ok, label):
        nonlocal checked
        checked += 1
        if not ok:
            raise Mismatch(label)

    def instant(text):
        result = datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))
        need(result.tzinfo is not None, 'timestamp-zone')
        return result

    def key(row):
        return row['context_id'], row['operation_id']

    def rows(snapshot, group):
        return {key(r): r for r in snapshot[group]}

    def bundle(snapshot):
        # Validate only this new fixture, not the earlier seven-chain evidence.
        report = audit(snapshot)
        need(report['verdict'] == 'pass', 'snapshot-integrity')
        return report

    try:
        need(type(value) is dict and set(value) == {'schema', 'case', 'before', 'after', 'operations'}, 'closed-envelope')
        need(value['schema'] == 'v00-upstream-fault-storage-v1', 'schema')
        case = value['case']
        need(case in {'UB07', 'UB04', 'UB10', 'UB15', 'UNKNOWN_NO_FORWARD'}, 'supported-case')
        before, after = value['before'], value['after']
        bundle(before); report = bundle(after)
        counts = report['counts']
        need(before['actor_id'] == after['actor_id'], 'same-actor')
        need(before['gate'] == after['gate'], 'unchanged-gate-not-global-drain')
        need(before['current_factor'] == after['current_factor'], 'same-factor-version')
        need(type(value['operations']) is list and len(value['operations']) == (2 if case == 'UB07' else 1), 'operation-count')
        refs = value['operations']
        need(all(type(r) is dict and set(r) == {'context_id', 'operation_id', 'action'} for r in refs), 'operation-shape')
        keys = {key(r) for r in refs}
        need(len(keys) == len(refs), 'distinct-original-operations')
        need(all(r['action'] == ('AUTH_TOTP_VERIFY' if case == 'UB07' else 'C02') for r in refs), 'original-actions')
        before_adm, after_adm = rows(before, 'admissions'), rows(after, 'admissions')
        before_results, after_results = rows(before, 'results'), rows(after, 'results')
        for group in ('admissions', 'results', 'plans', 'audit'):
            old, new = rows(before, group), rows(after, group)
            need(all(k in new and new[k] == v for k, v in old.items()), group + '-history-immutable')
            need(set(new) - set(old) <= keys, group + '-no-unrelated-operation')
        need(all(k not in before_results for k in keys), 'fresh-unresolved-operations')
        old_steps = {(s['factor_version'], s['step']): s for s in before['steps']}
        new_steps = {(s['factor_version'], s['step']): s for s in after['steps']}
        need(all(k in new_steps and new_steps[k] == v for k, v in old_steps.items()), 'old-steps-immutable')
        added_steps = [v for k, v in new_steps.items() if k not in old_steps]
        need(all(key(v) in keys for v in added_steps), 'steps-only-original-operations')
        need({c['id'] for c in before['contexts']} == {c['id'] for c in after['contexts']}, 'same-context-inventory')
        need({g['id'] for g in before['generations']} == {g['id'] for g in after['generations']}, 'no-new-issuance-during-case')
        old_seals = {s['seal_id']: s for s in before['email_outcomes']}
        new_seals = {s['seal_id']: s for s in after['email_outcomes']}
        need(len(old_seals) == len(before['email_outcomes']) and len(new_seals) == len(after['email_outcomes']), 'unique-seal-identities')
        need(set(old_seals) <= set(new_seals), 'old-seals-retained')
        sessions = [s['provider_session_id'] for s in new_seals.values() if s['provider_session_id'] is not None]
        need(len(sessions) == len(set(sessions)), 'unique-provider-session-witness')
        for sid, old in old_seals.items():
            new = new_seals[sid]
            need(all(new[k] == old[k] for k in ('seal_id','admission_id','generation_id','family','sealed_at')), 'old-seal-source-immutable')
            if old['provider_session_id'] is not None:
                need(old == new, 'old-consumed-witness-immutable')
        own_admission_ids = {a['id'] for k, a in after_adm.items() if k in keys}
        need(all(s['admission_id'] in own_admission_ids for k, s in new_seals.items() if k not in old_seals), 'no-unrelated-new-seal')
        old_logins = {r['id']: r for r in before['dependency']['logins']}
        new_logins = {r['id']: r for r in after['dependency']['logins']}
        need(set(old_logins) <= set(new_logins), 'old-logins-retained')
        added_logins = [r for k, r in new_logins.items() if k not in old_logins]
        need(all(key(r) in keys for r in added_logins), 'logins-only-original-operations')
        resolved = [after_results[k] for k in keys if k in after_results]
        for ref in refs:
            if key(ref) in after_adm:
                need(after_adm[key(ref)]['action'] == ref['action'], 'admission-action')

        if case == 'UB07':
            need(len({r['context_id'] for r in refs}) == 2, 'two-contexts')
            need(before['failures'] == 0 and before['paused_until'] is None, 'race-clean-counter')
            contexts = {c['id']: c for c in before['contexts']}
            for ref in refs:
                c = contexts[ref['context_id']]
                need(c['stage'] == 'totp_verification' and c['factor_version'] == before['current_factor']
                     and c['factor_version'] is not None, 'race-shared-active-factor')
                email = [r for r in before['results'] if r['context_id'] == c['id'] and r['action'] == 'C02']
                need(len(email) == 1 and email[0]['result']['kind'] == 'auth_step_required', 'race-original-email-stage')
            winner = [r for r in resolved if r['result']['kind'] == 'login_completed']
            loser = [r for r in resolved if r['result']['kind'] == 'verification_rejected']
            need(len(winner) == 1 and len(added_logins) == 1, 'race-one-full-login')
            need(1 <= len(added_steps) <= 3 and all(key(s) == key(winner[0]) for s in added_steps), 'race-one-step-owner')
            need(len(resolved) == 1 + len(loser) and len(loser) <= 1, 'race-only-rejection-or-unresolved')
            need(after['failures'] == len(loser) and after['paused_until'] is None, 'race-counter-exact')
            need(before['email_outcomes'] == after['email_outcomes'] and before['generations'] == after['generations'], 'race-no-new-email-effect')
            counts['loser_rejection_results'] = len(loser)
            counts['loser_unresolved'] = 1 - len(loser)
        else:
            ref = refs[0]; k = key(ref)
            need(k in after_adm, 'original-admission-present')
            adm = after_adm[k]
            seals = [s for s in after['email_outcomes'] if s['admission_id'] == adm['id']]
            need(len(seals) == 1, 'one-original-seal')
            seal = seals[0]
            generation = [g for g in after['generations'] if g['id'] == seal['generation_id']]
            need(len(generation) == 1, 'exact-generation')
            need(after['failures'] == before['failures'] and after['paused_until'] == before['paused_until'], 'no-fabricated-failure')
            if case == 'UB10':
                need(len(resolved) == 1 and resolved[0]['result']['kind'] == 'login_completed'
                     and len(added_logins) == 1 and added_steps == [], 'commit-gap-one-email-completion')
                need(generation[0]['state'] == 'consumed' and seal['consumption_txid'] is not None
                     and seal['consumption_txid'] == seal['outcome_txid'] and seal['provider_session_id'] is not None, 'commit-gap-exact-provider-witness')
            else:
                need(resolved == [] and added_logins == [] and added_steps == [], 'unknown-no-completion-or-rejection')
                need(not any(key(p) in keys for p in after['plans']), 'unknown-no-plan')
                need(before['contexts'] == after['contexts'], 'unknown-stage-unchanged')
                need(before['dependency'] == after['dependency'], 'unknown-dependency-unchanged')
                if case in {'UB04', 'UNKNOWN_NO_FORWARD'}:
                    need(generation[0]['state'] == 'issued' and seal['consumption_txid'] is None
                         and seal['outcome_txid'] is None and seal['provider_session_id'] is None, 'no-provider-outcome')
                else:
                    need(generation[0]['state'] == 'consumed' and seal['consumption_txid'] is not None
                         and seal['consumption_txid'] == seal['outcome_txid'] and seal['provider_session_id'] is not None, 'late-exact-provider-witness')
                    need(instant(seal['observed_at']) >= instant(adm['deadline_at']), 'late-witness-after-original-deadline')
        return {'schema': 'v00-upstream-fault-review-v1', 'case': case, 'storage_verdict': 'pass',
                'conditions_checked': checked, 'counts': counts, 'errors': [],
                'not_proven_by_this_verifier': ['network dispatch count', 'actual lock wait or independent actor progress',
                    'COMMIT acknowledgement loss injection', 'public HTTP status/cookie behavior', 'U03 or UB09 global drain/reopening']}
    except (Mismatch, KeyError, TypeError, ValueError, IndexError):
        error = sys.exc_info()[1]
        return {'schema': 'v00-upstream-fault-review-v1', 'storage_verdict': 'fail', 'conditions_checked': checked,
                'counts': counts, 'errors': [str(error) if isinstance(error, Mismatch) else 'malformed-projection']}


if __name__ == '__main__':
    try:
        with open(sys.argv[1], encoding='utf-8') as stream:
            report = audit_fault(json.load(stream))
    except (OSError, ValueError, IndexError):
        report = {'storage_verdict': 'fail', 'errors': ['unreadable-input']}
    print(json.dumps(report))
    raise SystemExit(0 if report['storage_verdict'] == 'pass' else 1)
