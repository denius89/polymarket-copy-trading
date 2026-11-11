#!/usr/bin/env python3
"""Independent offline email-entry reconciliation, no DB/network/private keys."""
import datetime
import json
import sys


class Mismatch(Exception):
    pass


def audit(value):
    count = 0
    coverage = {}

    def need(condition, label):
        nonlocal count
        count += 1
        if not condition:
            raise Mismatch(label)

    def indexed(rows, keys, label):
        need(type(rows) is list, label + '-array')
        result = {}
        for row in rows:
            need(type(row) is dict and all(k in row for k in keys), label + '-keys')
            key = tuple(row[k] for k in keys)
            need(key not in result, label + '-unique')
            result[key] = row
        return result

    def instant(value):
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        need(parsed.tzinfo is not None, 'timestamp-zone')
        return parsed

    def millis(value):
        parsed = instant(value)
        return parsed.replace(microsecond=parsed.microsecond // 1000 * 1000)

    try:
        need(type(value) is dict and set(value) == {'schema','context','material','directory_enabled','gate',
             'admissions','results','challenges','sends','send_observations','verifies','consumptions',
             'verify_observations','negative_proofs','plans','steps','audit','address_sends','dependency','generations'}, 'closed-snapshot')
        need(value['schema'] == 'v00-email-entry-snapshot-v1', 'snapshot-version')
        c = value['context']; cid = c['id']
        need(c['stage'] in ('ready','email_verification','totp_verification','completed'), 'known-stage')
        need('proof_digest' not in c and 'address_digest' not in c, 'no-private-context-verifiers')
        need((instant(c['expires_at']) - instant(c['created_at'])).total_seconds() == 1800, 'fixed-context-expiry')
        need(type(c['failures']) is int and 0 <= c['failures'] <= 5, 'failure-bounds')
        groups = {'admissions': ['id'], 'results': ['operation_id'], 'challenges': ['id'], 'sends': ['id'],
                  'send_observations': ['dispatch_id'], 'verifies': ['id'], 'consumptions': ['dispatch_id'],
                  'verify_observations': ['dispatch_id'], 'negative_proofs': ['admission_id'], 'plans': ['operation_id'],
                  'steps': ['factor_version','step'], 'audit': ['operation_id'], 'address_sends': ['dispatch_id'], 'generations': ['id']}
        g = {name: indexed(value[name], keys, name) for name, keys in groups.items()}
        ops = indexed(value['admissions'], ['operation_id'], 'operation-scope')
        need(all(a['context_id'] == cid for a in ops.values()), 'admission-context')
        for a in ops.values():
            need((instant(a['deadline_at']) - instant(a['captured_at'])).total_seconds() == 10, 'original-budget')
            need(a['action'] in ('C01','C02','C03','AUTH_TOTP_VERIFY'), 'action')
        for d in g['sends'].values():
            need((d['admission_id'],) in g['admissions'] and g['admissions'][(d['admission_id'],)]['action'] in ('C01','C03'), 'send-original-admission')
            need((d['id'],) in g['address_sends'], 'persistent-address-slot')
        for o in g['send_observations'].values():
            need((o['dispatch_id'],) in g['sends'] and (o['generation_id'],) in g['generations'], 'acceptance-sources')
            d = g['sends'][(o['dispatch_id'],)]; generation = g['generations'][(o['generation_id'],)]
            need(generation['id'] != d['before_generation_id'] and generation['user_id'] == d['provider_user_id']
                 and generation['family'] == 'recovery', 'new-source-generation')
            need(instant(d['sealed_at']) <= instant(generation['issued_at']) <= instant(o['accepted_at']) <= instant(o['observed_at']), 'send-time-order')
        for ch in g['challenges'].values():
            need(ch['context_id'] == cid and (ch['send_admission_id'],) in g['admissions']
                 and (ch['dispatch_id'],) in g['send_observations'], 'challenge-sources')
            o = g['send_observations'][(ch['dispatch_id'],)]; generation = g['generations'][(ch['generation_id'],)]
            need(ch['generation_id'] == o['generation_id'] and instant(ch['issued_at']) == instant(generation['issued_at']), 'challenge-generation')
            need(instant(ch['expires_at']) == min(instant(ch['issued_at']) + datetime.timedelta(minutes=10), instant(c['expires_at'])), 'challenge-fixed-expiry')
            if ch['replaced_by_id'] is not None:
                need((ch['replaced_by_id'],) in g['challenges'] and ch['consumed_by_operation_id'] is None, 'same-context-replacement')
        for d in g['verifies'].values():
            need((d['admission_id'],) in g['admissions'] and g['admissions'][(d['admission_id'],)]['action'] == 'C02'
                 and (d['challenge_id'],) in g['challenges'], 'verify-sources')
            need(d['generation_id'] == g['challenges'][(d['challenge_id'],)]['generation_id'], 'verify-exact-generation')
            generation = g['generations'][(d['generation_id'],)]
            need(generation['user_id'] == d['provider_user_id'] and generation['family'] == 'recovery', 'verify-provider-generation')
        for co in g['consumptions'].values():
            need((co['dispatch_id'],) in g['verifies'] and co['provider_user_id'] == g['verifies'][(co['dispatch_id'],)]['provider_user_id'], 'consumption-original-dispatch')
        for o in g['verify_observations'].values():
            key = (o['dispatch_id'],)
            need(key in g['verifies'] and key in g['consumptions'], 'verify-witness-sources')
            co, d = g['consumptions'][key], g['verifies'][key]
            need(co['provider_txid'] == o['provider_txid'] and co['provider_user_id'] == d['provider_user_id'], 'same-provider-transaction')
        full = set(); counts = {}
        for key, r in g['results'].items():
            need(key in ops and r['context_id'] == cid and r['action'] == ops[key]['action'] and r['valid'] is True, 'result-scope')
            need(key in g['audit'], 'mandatory-audit')
            a = ops[key]; result = r['result']; kind = result['kind']; counts[kind] = counts.get(kind, 0) + 1
            need(instant(a['captured_at']) <= instant(r['resolved_at']) < instant(a['deadline_at']), 'resolution-original-budget')
            need(g['audit'][key]['kind'] == {'auth_step_required':'email_stage','login_completed':'completion'}.get(kind, kind)
                 and instant(g['audit'][key]['recorded_at']) == instant(r['resolved_at']), 'audit-kind-time')
            if kind == 'email_dispatch_accepted':
                need(set(result) == {'kind','acceptedAt','challengeId','resendNotBeforeAt'} and r['historical_http_status'] == 202, 'accepted-result-shape')
                ch = g['challenges'][(result['challengeId'],)]; o = g['send_observations'][(ch['dispatch_id'],)]
                need(ch['send_admission_id'] == a['id'] and instant(result['acceptedAt']) == millis(o['accepted_at']), 'original-accepted-result')
                need(instant(result['resendNotBeforeAt']) >= instant(result['acceptedAt']) + datetime.timedelta(seconds=60), 'historical-send-bound')
            elif kind == 'verification_rejected':
                need(result == {'kind':kind,'reasonCode':'AUTH_VERIFICATION_FAILED'} and r['historical_http_status'] == 401
                     and a['action'] in ('C02','AUTH_TOTP_VERIFY'), 'negative-result-shape')
                if a['action'] == 'C02':
                    n = g['negative_proofs'][(a['id'],)]; ch = g['challenges'][(n['challenge_id'],)]
                    need(n['context_id'] == cid and n['operation_id'] == a['operation_id'] and n['generation_id'] == ch['generation_id']
                         and a['challenge_id'] == ch['id'] and instant(n['checked_at']) == instant(r['resolved_at']), 'negative-source-time')
                    need((n['kind'] == 'expired_current' and instant(n['checked_at']) >= instant(ch['expires_at']))
                         or (n['kind'] == 'live_mismatch' and instant(n['checked_at']) < instant(ch['expires_at'])), 'negative-classification')
                    need(not any(d['admission_id'] == a['id'] for d in g['verifies'].values()), 'negative-no-network-seal')
            elif kind == 'auth_step_required':
                need(set(result) == {'kind','stage','challengeId','challengeIssuedAt','challengeExpiresAt'}, 'step-result-shape')
                need(a['action'] == 'C02' and r['historical_http_status'] == 200 and result['stage'] == 'totp_verification'
                     and result['challengeId'] == c['totp_challenge_id'], 'original-totp-stage')
                need(instant(result['challengeIssuedAt']) == instant(c['totp_issued_at']) and instant(result['challengeExpiresAt']) == instant(c['totp_expires_at']), 'totp-original-times')
            elif kind == 'login_completed':
                full.add(key); dep = value['dependency']
                need(a['action'] in ('C02','AUTH_TOTP_VERIFY') and r['historical_http_status'] == 200 and set(result) == {'kind','completion'}
                     and set(result['completion']) == {'authContextId','authOperationId','loginId','realm','completedAt'}
                     and result['completion']['realm'] == 'user', 'closed-completion-shape')
                matches = [x for x in dep['results'] if x['context_id'] == cid and x['operation_id'] == a['operation_id']]
                need(len(matches) == 1 and matches[0]['result'] == result and matches[0]['login_id'] == r['login_id'], 'dependency-original-completion')
                need((result['completion']['authContextId'], result['completion']['authOperationId'], result['completion']['loginId']) == (cid, a['operation_id'], r['login_id']), 'completion-source')
                logins = [x for x in dep['logins'] if x['id'] == r['login_id']]
                need(len(logins) == 1 and logins[0]['credential_present'] and logins[0]['secret_row_present'], 'full-login-material')
                login = logins[0]
                need((login['context_id'], login['operation_id']) == (cid, a['operation_id'])
                     and instant(login['completed_at']) == instant(result['completion']['completedAt']), 'full-login-source-time')
                need(instant(matches[0]['resolved_at']) == millis(r['resolved_at']), 'dependency-resolution-time')
                need(instant(login['expires_at']) == instant(login['completed_at']) + datetime.timedelta(days=30)
                     and instant(login['idle_expires_at']) == instant(login['completed_at']) + datetime.timedelta(days=7), 'fixed-login-lifetime')
                need(login['secret_present'] == (login['erased_at'] is None) == (login['closed_at'] is None)
                     and (login['closed_at'] is None) == (login['close_reason'] is None), 'window-cipher-consistency')
                contexts = [x for x in dep['contexts'] if x['id'] == cid]
                need(len(contexts) == 1 and contexts[0]['completed_login_id'] == r['login_id']
                     and contexts[0]['completed_operation_id'] == a['operation_id'] and c['stage'] == 'completed', 'completed-context-source')
                need(key in g['plans'] and g['plans'][key]['admission_id'] == a['id'], 'completion-plan')
                if a['action'] == 'AUTH_TOTP_VERIFY':
                    steps = [s for s in g['steps'].values() if s['operation_id'] == a['operation_id']]
                    need(1 <= len(steps) <= 3 and max(s['step'] for s in steps)-min(s['step'] for s in steps) <= 2, 'complete-step-window')
            else:
                raise Mismatch('unsupported-result')
            if kind in ('auth_step_required','login_completed') and a['action'] == 'C02':
                witnesses = [d for d in g['verifies'].values() if d['admission_id'] == a['id'] and (d['id'],) in g['verify_observations']]
                need(len(witnesses) == 1, 'email-proof-before-identity')
                need(g['generations'][(witnesses[0]['generation_id'],)]['state'] == 'consumed', 'proved-email-generation-consumed')
        need(set(g['audit']) == set(g['results']), 'audit-result-inventory')
        need(set(g['plans']) == full, 'plan-result-inventory')
        failures, pause = 0, None
        for n in sorted(g['negative_proofs'].values(), key=lambda row: instant(row['checked_at'])):
            need((n['operation_id'],) in g['results'] and ops[(n['operation_id'],)]['id'] == n['admission_id'], 'negative-result-inventory')
            if n['kind'] == 'live_mismatch':
                checked = instant(n['checked_at'])
                need(pause is None or checked >= pause, 'no-new-wrong-during-pause')
                if pause is not None:
                    failures, pause = 0, None
                failures += 1
                if failures == 5:
                    pause = checked + datetime.timedelta(minutes=15)
        need(c['failures'] == failures and (None if c['paused_until'] is None else instant(c['paused_until'])) == pause, 'email-counter-from-original-proofs')
        for step in g['steps'].values():
            need((step['operation_id'],) in full and step['factor_version'] == c['factor_version']
                 and ops[(step['operation_id'],)]['action'] == 'AUTH_TOTP_VERIFY', 'step-original-completion')
        if c['stage'] in ('ready','email_verification'):
            need(c['actor_id'] is None and value['dependency'] is None, 'no-premature-identity')
        else:
            need(c['actor_id'] is not None and value['dependency']['actor_id'] == c['actor_id'], 'proved-subject')
        if c['stage'] != 'ready':
            need(value['material']['cipher_present'] is True and instant(value['material']['reveal_until']) == instant(c['expires_at']), 'bound-material')
        coverage = {'operations':len(ops),'unresolved':len(ops)-len(g['results']),'results':counts,
                    'sends':len(g['sends']),'verify_dispatches':len(g['verifies']),'negative_proofs':len(g['negative_proofs'])}
        return {'schema':'v00-email-entry-audit-v1','verdict':'pass','conditions_checked':count,'coverage':coverage,'errors':[],
                'limits':['safe projection only; provider HTTP/SMTP/locks/crypto require separate evidence',
                          'zero rows are no-data, not behavioral coverage; counter deltas require before/after comparison']}
    except (Mismatch, KeyError, TypeError, ValueError, AttributeError, IndexError):
        error = sys.exc_info()[1]
        label = str(error) if isinstance(error, Mismatch) else 'malformed-projection'
        return {'schema':'v00-email-entry-audit-v1','verdict':'fail','conditions_checked':count,'coverage':coverage,'errors':[label]}


if __name__ == '__main__':
    try:
        with open(sys.argv[1], encoding='utf-8') as stream:
            report = audit(json.load(stream))
    except Exception:
        report = {'schema':'v00-email-entry-audit-v1','verdict':'fail','errors':['input-unavailable']}
    print(json.dumps(report))
    raise SystemExit(0 if report['verdict'] == 'pass' else 1)
