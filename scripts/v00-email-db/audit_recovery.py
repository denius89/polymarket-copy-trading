"""Offline structural/equality review of safe recovery snapshots, not runtime proof."""
import json
import re
import sys
from audit_snapshot import audit as audit_email
from recovery_reference import micros


class Invalid(Exception):pass


def audit(value):
    checked=0;structural=0
    def need(ok,label):
        nonlocal checked
        checked+=1
        if not ok:raise Invalid(label)
    def index(rows,key,label):
        need(type(rows) is list,label+'-rows');out={}
        for row in rows:
            item=tuple(row[k] for k in key)
            need(item not in out,label+'-unique');out[item]=row
        return out
    try:
        need(type(value) is dict and set(value)=={'schema','context_id','email','scope','admissions','attempts','uses','replay_guards'},'closed-snapshot')
        need(value['schema']=='v00-email-recovery-snapshot-v1','schema')
        original=audit_email(value['email']);structural=original['conditions_checked']
        need(original['verdict']=='pass','email-bundle')
        c=value['email']['context'];q=value['scope'];cid=value['context_id']
        need(c['id']==cid and q is not None and q['context_id']==cid,'expected-scope')
        need(set(q)=={'context_id','environment','purpose','limit_count','window_seconds','created_at'},'scope-shape')
        need((q['environment'],q['purpose'],q['limit_count'],q['window_seconds'])==
             ('v00-d03-07','user/login/cookie_recovery',3,60),'fixed-policy-scope')
        need(micros(q['created_at'])==micros(c['created_at']),'atomic-scope-initialization')
        admissions=index(value['admissions'],['admission_token'],'admission')
        attempts=index(value['attempts'],['admission_token'],'attempt')
        uses=index(value['uses'],['admission_token'],'use')
        index(value['attempts'],['target_pid','target_txid'],'target')
        guards=index(value['replay_guards'],['target_txid','context_id','operation_id'],'replay')
        for key,a in admissions.items():
            need(set(a)=={'admission_token','context_id','operation_id','action','executor_id','admitted_epoch','request_started_at','admitted_at','deadline_at','row_sha256'},'admission-shape')
            need(a['context_id']==cid and a['action'] in ('C02','AUTH_TOTP_VERIFY'),'original-context-action')
            need(micros(a['deadline_at'])-micros(a['request_started_at'])==5000000,'original-five-second-deadline')
            need(micros(q['created_at'])<=micros(a['admitted_at'])
                 and micros(a['request_started_at'])<=micros(a['admitted_at'])<micros(a['deadline_at']),'admission-time')
            need(a['admitted_epoch']>0 and a['executor_id'] and a['operation_id'],'source-and-executor')
            need('executor_proof_digest' not in a and re.fullmatch('[0-9a-f]{64}',a['row_sha256']) is not None,'private-digest-only')
            t=micros(a['admitted_at'])
            need(sum(t-60000000<micros(x['admitted_at'])<=t for x in admissions.values())<=3,'never-four-in-window')
        for key,s in attempts.items():
            need(set(s)=={'admission_token','target_pid','target_txid','sealed_at'},'attempt-shape')
            need(key in admissions,'attempt-admission')
            a=admissions[key]
            need(type(s['target_pid']) is int and s['target_pid']>0 and type(s['target_txid']) is int and s['target_txid']>0,'exact-target')
            need(micros(a['admitted_at'])<=micros(s['sealed_at'])<micros(a['deadline_at']),'attempt-original-budget')
        for key,u in uses.items():
            need(set(u)=={'admission_token','target_pid','target_txid','entered_at'},'use-shape')
            need(key in attempts,'use-persisted-attempt')
            s=attempts[key];a=admissions[key]
            need((u['target_pid'],u['target_txid'])==(s['target_pid'],s['target_txid']),'same-subject-transaction')
            need(micros(s['sealed_at'])<=micros(u['entered_at'])<micros(a['deadline_at']),'use-original-budget')
            matches=[r for r in value['email']['results'] if r['operation_id']==a['operation_id'] and r['action']==a['action']]
            need(len(matches)==1 and matches[0]['result']['kind']=='login_completed','committed-use-original-completion')
        for g in guards.values():
            need(set(g)=={'target_txid','context_id','operation_id','used_at'},'replay-shape')
            need(g['context_id']==cid and g['target_txid']>0,'replay-same-source')
            matches=[r for r in value['email']['results'] if r['operation_id']==g['operation_id']]
            need(len(matches)==1 and matches[0]['result']['kind']=='login_completed'
                 and matches[0]['action'] in ('C02','AUTH_TOTP_VERIFY'),'replay-known-completion')
            if g['used_at'] is not None:need(micros(g['used_at'])>=micros(matches[0]['resolved_at']),'replay-after-completion')
        return {'verdict':'pass','cross_checks':checked,'email_structural_checks':structural,
                'admissions':len(admissions),'attempts':len(attempts),'committed_uses':len(uses),'replay_guards':len(guards),
                'limits':['No inference from absence of uses: subject rollback erases use but persistent attempt remains',
                          'No proof of network/HTTP or hidden-history completeness from this projection']}
    except (Invalid,KeyError,ValueError,TypeError,AttributeError,IndexError):
        e=sys.exc_info()[1]
        return {'verdict':'fail','cross_checks':checked,'email_structural_checks':structural,
                'reason':str(e) if isinstance(e,Invalid) else 'malformed-projection'}


def delta(before,after):
    if audit(before)['verdict']!='pass' or audit(after)['verdict']!='pass':raise Invalid('invalid-snapshot')
    if before['context_id']!=after['context_id'] or before['scope']!=after['scope']:raise Invalid('scope-replaced')
    out={}
    for key in ('admissions','attempts','uses'):
        if any(row not in after[key] for row in before[key]):raise Invalid('immutable-history-changed')
        out[key]=len(after[key])-len(before[key])
    for row in before['replay_guards']:
        matching=[r for r in after['replay_guards'] if all(r[k]==row[k] for k in ('target_txid','context_id','operation_id'))]
        if len(matching)!=1 or (row['used_at'] is not None and matching[0]!=row):raise Invalid('replay-history-changed')
    return out


if __name__=='__main__':
    try:
        with open(sys.argv[1],encoding='utf-8') as f:report=audit(json.load(f))
    except (OSError,ValueError,IndexError):report={'verdict':'fail','reason':'input-unavailable'}
    print(json.dumps(report));raise SystemExit(0 if report['verdict']=='pass' else 1)
