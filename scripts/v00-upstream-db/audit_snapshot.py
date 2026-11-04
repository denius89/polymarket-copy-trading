#!/usr/bin/env python3
"""Independent safe-projection reconciliation; never trusts producer valid=true alone.

Input is v00-upstream-snapshot-v1, NOT a private DB dump. No server/network calls.
Empty groups are reported as counts, not behavioral coverage. Does not prove HTTP,
seed computation, timestamps against external clocks, crypto, or provider dispatch.
"""
import datetime
import json
import sys


class Mismatch(Exception):
    pass


def audit(value):
    checked = 0
    coverage = {}

    def need(condition, reason):
        nonlocal checked
        checked += 1
        if not condition:
            raise Mismatch(reason)

    def index(rows, keys, label):
        need(type(rows) is list, label+'-array')
        out = {}
        for row in rows:
            need(type(row) is dict and all(k in row for k in keys), label+'-keys')
            key = tuple(row[k] for k in keys)
            need(key not in out, label+'-unique')
            out[key] = row
        return out

    def instant(text):
        need(type(text) is str, 'timestamp-type')
        try:
            t = datetime.datetime.fromisoformat(text.replace('Z','+00:00'))
        except ValueError:
            raise Mismatch('timestamp-format') from None
        need(t.tzinfo is not None, 'timestamp-zone')
        return t

    try:
        need(type(value) is dict and set(value)=={'schema','actor_id','current_factor','failures','paused_until','gate','dependency',
             'contexts','admissions','results','steps','plans','generations','email_outcomes','audit'},'snapshot-closed-shape')
        need(value['schema']=='v00-upstream-snapshot-v1','snapshot-version')
        dep=value['dependency']; need(type(dep) is dict and dep.get('actor_id')==value['actor_id'],'same-actor')
        need(type(value['failures']) is int and 0<=value['failures']<=5,'counter-bounds')
        contexts=index(value['contexts'],['id'],'contexts')
        admissions=index(value['admissions'],['context_id','operation_id'],'admissions')
        admission_ids=index(value['admissions'],['id'],'admission-ids')
        results=index(value['results'],['context_id','operation_id'],'results')
        plans=index(value['plans'],['context_id','operation_id'],'plans')
        steps=index(value['steps'],['factor_version','step'],'steps')
        generations=index(value['generations'],['id'],'generations')
        seals=index(value['email_outcomes'],['admission_id'],'seals')
        audit_rows=index(value['audit'],['context_id','operation_id'],'audit')
        dresults=index(dep['results'],['context_id','operation_id'],'dependency-results')
        logins=index(dep['logins'],['id'],'dependency-logins')
        dcontexts=index(dep['contexts'],['id'],'dependency-contexts')
        coverage={'contexts':len(contexts),'admissions':len(admissions),'results':len(results),'steps':len(steps),
                  'full_logins':len(logins),'provider_seals':len(seals)}
        need(set(contexts)==set(dcontexts),'context-inventory')
        for ctx in contexts.values():
            if ctx['totp_challenge_id'] is not None:
                seconds=(instant(ctx['totp_expires_at'])-instant(ctx['totp_issued_at'])).total_seconds()
                need(0<seconds<=300 and ctx['factor_version'] is not None,'challenge-bound-factor')
        for key,a in admissions.items():
            need((a['context_id'],) in contexts and a['action'] in ('C02','AUTH_TOTP_VERIFY'),'admission-scope')
            need((instant(a['deadline_at'])-instant(a['captured_at'])).total_seconds()==10,'original-budget')
            need(type(a['epoch']) is int and 0<a['epoch']<=value['gate']['epoch'],'admission-epoch')
        full_keys=set()
        for key,r in results.items():
            need(key in admissions and r['action']==admissions[key]['action'],'result-original-action')
            need(r.get('valid') is True,'producer-not-corrupt')
            result=r['result']; need(type(result) is dict,'result-object')
            need(key in audit_rows,'result-audit')
            kind=result.get('kind')
            need(audit_rows[key]['kind']=={'login_completed':'completion','verification_rejected':'verification_rejected','auth_step_required':'email_stage'}.get(kind),'audit-kind')
            if kind=='login_completed':
                full_keys.add(key)
                need(set(result)=={'kind','completion'},'completion-shape')
                c=result['completion']; need(set(c)=={'authContextId','authOperationId','loginId','realm','completedAt'},'completion-fields')
                need((c['authContextId'],c['authOperationId'])==key and c['realm']=='user' and c['loginId']==r['login_id'],'completion-source')
                need(key in dresults and dresults[key]['result']==result and dresults[key]['login_id']==r['login_id'],'dependency-original-result')
                # v00_session.utc() uses PostgreSQL MS (truncation); upstream JSON keeps microseconds.
                raw_time=instant(r['resolved_at'])
                need(instant(dresults[key]['resolved_at'])==raw_time.replace(microsecond=raw_time.microsecond//1000*1000),'same-resolution-time-ms-projection')
                need((r['login_id'],) in logins,'complete-login-present')
                login=logins[(r['login_id'],)]
                need((login['context_id'],login['operation_id'])==key and instant(login['completed_at'])==instant(c['completedAt']),'login-source')
                need(login['credential_present'] is True and login['secret_row_present'] is True,'credential-and-secret-row')
                need((login['closed_at'] is None)==(login['close_reason'] is None),'window-closure-pair')
                need(login['secret_present']==(login['erased_at'] is None) and login['secret_present']==(login['closed_at'] is None),'window-erasure')
                dc=dcontexts[(r['context_id'],)]
                need(dc['completed_login_id']==r['login_id'] and dc['completed_operation_id']==r['operation_id'],'completed-context-source')
                need(contexts[(r['context_id'],)]['stage']=='completed','upstream-completed-stage')
                need(key in plans and plans[key]['admission_id']==admissions[key]['id'] and plans[key]['action']==r['action'],'plan-source')
                own=[s for s in steps.values() if (s['context_id'],s['operation_id'])==key]
                if r['action']=='AUTH_TOTP_VERIFY':
                    need(1<=len(own)<=3 and max(s['step'] for s in own)-min(s['step'] for s in own)<=2,'complete-step-window')
                    need(all(s['factor_version']==contexts[(r['context_id'],)]['factor_version'] for s in own),'step-factor-version')
                    prior=[x for x in results.values() if x['context_id']==r['context_id'] and x['action']=='C02'
                           and x['result'].get('kind')=='auth_step_required']
                    need(len(prior)==1,'totp-original-email-stage')
                else:
                    need(own==[],'email-no-totp-consumption')
            else:
                need(r['login_id'] is None and key not in plans and key not in dresults,'noncompletion-no-login-plan')
                if kind=='verification_rejected':
                    need(result=={'kind':kind,'reasonCode':'AUTH_VERIFICATION_FAILED'},'negative-result-shape')
                elif kind=='auth_step_required':
                    ctx=contexts[(r['context_id'],)]
                    need(r['action']=='C02' and set(result)=={'kind','stage','challengeId','challengeIssuedAt','challengeExpiresAt'},'email-stage-result-shape')
                    need(result['stage']=='totp_verification' and result['challengeId']==ctx['totp_challenge_id'],'original-challenge')
                    need(instant(result['challengeIssuedAt'])==instant(ctx['totp_issued_at']) and instant(result['challengeExpiresAt'])==instant(ctx['totp_expires_at']),'original-challenge-time')
                else:
                    raise Mismatch('unsupported-slice-result')
            if r['action']=='C02' and kind in ('login_completed','auth_step_required'):
                need((admissions[key]['id'],) in seals,'email-seal-present')
                seal=seals[(admissions[key]['id'],)]
                need(seal['provider_session_id'] is not None and seal['consumption_txid']==seal['outcome_txid'] and seal['outcome_txid'] is not None,'exact-email-outcome')
                need((seal['generation_id'],) in generations and generations[(seal['generation_id'],)]['state']=='consumed','consumed-generation')
        need(set(plans)==full_keys and set(dresults)==full_keys and len(logins)==len(full_keys) and dep['plans']==len(full_keys),'full-bundle-inventory')
        need(set(audit_rows)==set(results),'audit-result-inventory')
        for s in steps.values():
            key=(s['context_id'],s['operation_id'])
            need(type(s['step']) is int and s['step']>=0 and key in full_keys and results[key]['action']=='AUTH_TOTP_VERIFY','step-original-success')
        for seal in seals.values():
            need((seal['admission_id'],) in admission_ids and (seal['generation_id'],) in generations,'seal-original-sources')
            need(seal['family']==generations[(seal['generation_id'],)]['family'],'seal-family')
        logout_contexts=index(dep.get('logout_contexts',[]),['id'],'logout-contexts')
        logout_results=index(dep.get('logout_results',[]),['context_id','operation_id'],'logout-results')
        for lr in logout_results.values():
            need(lr.get('valid') is True and (lr['context_id'],) in logout_contexts,'logout-valid-context')
            lc=logout_contexts[(lr['context_id'],)]
            need(lr['target_login_id']==lc['target_login_id'] and (lr['target_login_id'],) in logins,'logout-exact-target')
            login=logins[(lr['target_login_id'],)]
            need(login['revoked_at'] is not None and instant(login['revoked_at'])<=instant(lr['confirmed_at']),'logout-revoked-target')
            confirmation=[a for a in dep.get('audit',[]) if a['kind']=='logout_confirmed' and a['operation_id']==lr['operation_id']]
            need(len(confirmation)==1 and confirmation[0]['login_id']==lr['target_login_id']
                 and instant(confirmation[0]['recorded_at'])==instant(lr['confirmed_at']),'logout-original-audit')
        coverage['logout_results']=len(logout_results)
        return {'schema':'v00-upstream-independent-audit-v1','verdict':'pass','conditions_checked':checked,'counts':coverage,'errors':[],
                'limits':['safe projection only; no HTTP/crypto/provider dispatch or independent clock proof','zero rows are no-data, not behavioral coverage']}
    except (Mismatch,KeyError,TypeError,ValueError) as e:
        reason=str(e) if isinstance(e,Mismatch) else 'malformed-projection'
        return {'schema':'v00-upstream-independent-audit-v1','verdict':'fail','conditions_checked':checked,'counts':coverage,'errors':[reason]}


if __name__=='__main__':
    with open(sys.argv[1],encoding='utf-8') as stream:
        report=audit(json.load(stream))
    print(json.dumps(report))
    raise SystemExit(0 if report['verdict']=='pass' else 1)
