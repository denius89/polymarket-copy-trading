#!/usr/bin/env python3
"""Operator-run real PostgreSQL checks, public synthetic material only.

Provider rows below are explicitly constructed storage fixtures, NOT evidence of
real provider enrollment/email verification. That chain needs the backend probe.
No private seed, cookie, key, proof, query text or subprocess stderr is reported.
"""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('session_storage_checks', ROOT / 'scripts/v00-session-db/verify_storage.py')
dep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dep)
dep.COMMAND = json.loads(os.environ.get('V00_UPSTREAM_PSQL_COMMAND_JSON', '["psql"]'))
from totp_reference import hotp, matching_steps

REPORT = []
PROOF, FP, CMP, COOKIE = 'b'*64, 'a'*64, 'd'*64, 'c'*64
EXECUTOR_PROOF = 'A'*43  # Public all-zero vector, never the runtime capability.
EXECUTOR_DIGEST = hashlib.sha256(EXECUTOR_PROOF.encode()).hexdigest()
SEED = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'  # RFC public example.
uid, q = lambda: str(uuid.uuid4()), dep.quote


def sql(statement, role=None, expect_error=False):
    return dep.sql(statement, role=role, expect_error=expect_error)


def statement(method, payload):
    allowed = {'capture', 'seal_email', 'plan_email', 'plan_totp', 'complete',
               'read_operation', 'recover', 'q01', 'logout_prepare', 'logout', 'logout_result'}
    if method not in allowed:
        raise ValueError('unknown private method')
    bound = base64.b64encode(json.dumps(payload).encode()).decode()
    return ("SELECT v00_upstream." + method + "(convert_from(decode($1,'base64'),'UTF8')::jsonb)::text\n"
            "\\bind '" + bound + "'\n\\g\n")


class Transaction(dep.Transaction):
    def __init__(self, role='v00_upstream_executor', app=None):
        super().__init__(role=role, app=app)

    def rpc(self, method, payload):
        return json.loads(self.step(statement(method, payload))[-1])


def rpc(method, payload, role='v00_upstream_executor'):
    tx = Transaction(role=role)
    try:
        value = tx.rpc(method, payload)
        tx.finish()
        return value
    finally:
        tx.close()


def check(name, condition):
    REPORT.append({'id': name, 'verdict': 'pass' if condition else 'fail'})
    if not condition:
        raise AssertionError(name)


def fixture(existing=None, totp=True):
    f = dict(actor=uid(), user=uid(), factor=uid(), provider_factor=uid()) if existing is None else existing.copy()
    f.update(context=uid(), operation=uid(), login=uid(), secret=uid(), email_challenge=uid(), challenge=uid())
    if existing is None:
        sql('BEGIN; INSERT INTO auth.users(id,email,email_confirmed_at,created_at,updated_at) VALUES('
            + ','.join([q(f['user']), q('v00-'+f['user']+'@invalid.test'), 'clock_timestamp()', 'clock_timestamp()', 'clock_timestamp()'])+');'
            + 'INSERT INTO v00_session.actors(id,fixed_time) VALUES('+q(f['actor'])+',to_timestamp(4607040));'
            + 'INSERT INTO v00_upstream.subjects(actor_id,provider_user_id) VALUES('+q(f['actor'])+','+q(f['user'])+');'
            + ("INSERT INTO auth.mfa_factors(id,user_id,factor_type,status,secret,created_at,updated_at) VALUES("+
               ','.join([q(f['provider_factor']),q(f['user']),"'totp'","'verified'",q(SEED),'clock_timestamp()','clock_timestamp()'])+');'
               + 'INSERT INTO v00_upstream.factors(id,actor_id,provider_factor_id,active) VALUES('+','.join([q(f['factor']),q(f['actor']),q(f['provider_factor']),'true'])+');'
               + 'UPDATE v00_upstream.subjects SET current_factor='+q(f['factor'])+' WHERE actor_id='+q(f['actor'])+';' if totp else '') + 'COMMIT;')
    sql('BEGIN; INSERT INTO v00_session.contexts(id,actor_id,proof_digest,expires_at,login_expires_at,idle_expires_at) VALUES('
        + ','.join([q(f['context']),q(f['actor']),q(PROOF),"clock_timestamp()+interval '1 hour'","clock_timestamp()+interval '1 day'","clock_timestamp()+interval '8 hours'"])+');'
        + 'INSERT INTO v00_upstream.contexts(id,actor_id,email_challenge_id) VALUES('+','.join([q(f['context']),q(f['actor']),q(f['email_challenge'])])+');'
        + ("UPDATE v00_upstream.contexts SET stage='totp_verification',factor_version="+q(f['factor'])+',totp_challenge_id='+q(f['challenge'])+
           ",totp_issued_at=to_timestamp(4607040),totp_expires_at=to_timestamp(4607040)+interval '5 minutes' WHERE id="+q(f['context'])+';' if totp else '')+'COMMIT;')
    f['action'] = 'AUTH_TOTP_VERIFY' if totp else 'C02'
    return f


def read_ref(f):
    return dict(context_id=f['context'], proof_digest=PROOF, operation_id=f['operation'], action=f['action'])


def write_ref(f):
    return read_ref(f) | dict(fingerprint=FP, comparison_hmac=CMP, comparison_key_id='public-test-comparison')


def capture(f):
    p = write_ref(f) | dict(executor_id=uid(), executor_proof_digest=EXECUTOR_DIGEST)
    r = rpc('capture', p, 'v00_upstream_ingress')
    if r.get('http') not in (200, 201):
        raise AssertionError('capture fixture unavailable')
    f['admission'] = r['admission_id']
    return p, r


def plan(f, code='468457'):
    return write_ref(f) | dict(challenge_id=f['challenge'], code=code, admission_id=f['admission'],
                               executor_proof=EXECUTOR_PROOF, login_id=f['login'], secret_id=f['secret'])


def material(f):
    return write_ref(f) | dict(cookie_digest=COOKIE, ciphertext=base64.b64encode(bytes(32)).decode(),
                              nonce=base64.b64encode(bytes(24)).decode(), key_id='public-synthetic', credential_key_id='public-synthetic')


def full(f, method='plan_totp'):
    tx = Transaction()
    try:
        p = plan(f) if method == 'plan_totp' else write_ref(f) | dict(login_id=f['login'], secret_id=f['secret'])
        r = tx.rpc(method, p)
        if r.get('http') == 200 and 'metadata' in r:
            r = tx.rpc('complete', material(f))
        tx.finish()
        return r
    finally:
        tx.close()


def snapshot(f):
    return json.loads(sql('SELECT v00_upstream.snapshot('+q(f['actor'])+'::uuid);', role='v00_upstream_observer'))


def run():
    # RFC vectors exercise independently implemented SQL and Python, not SQL self-equality.
    for seconds, expected in [(59,'287082'),(1111111109,'081804'),(1111111111,'050471'),(1234567890,'005924'),(2000000000,'279037'),(20000000000,'353130')]:
        actual = sql('SELECT v00_upstream.hotp(v00_upstream.base32('+q(SEED)+'),'+str(seconds//30)+');','v00_upstream_owner')
        check('RFC6238-'+str(seconds), actual == expected)
    check('all-matching-SQL-vs-reference', json.loads(sql('SELECT to_jsonb(v00_upstream.matches('+q(SEED)+",'468457',to_timestamp(4607040)));",'v00_upstream_owner')) == matching_steps(SEED,'468457',4607040))
    check('executor-no-dependency-complete', sql("SELECT has_function_privilege('v00_upstream_executor','v00_session.complete(jsonb)','EXECUTE');") == 'f')
    check('executor-no-provider-seed', sql('SELECT secret FROM auth.mfa_factors LIMIT 1;','v00_upstream_executor',True))
    check('executor-no-capture', sql("SELECT v00_upstream.capture('{}'::jsonb);",'v00_upstream_executor',True))
    f = fixture(); p, initial = capture(f)
    repeated = rpc('capture', p | {'executor_id':uid(),'executor_proof_digest':'e'*64}, 'v00_upstream_ingress')
    check('capture-immutable-replay', initial['http']==201 and repeated=={'http':200,'admission_id':initial['admission_id'],'created':False})
    wrong_action=read_ref(f)|{'action':'C02'}
    check('unresolved-action-bound', rpc('read_operation',wrong_action)['http']==404)
    check('new-key-cannot-bypass-unknown', rpc('capture',p|{'operation_id':uid()},'v00_upstream_ingress')['http']==503)
    check('wrong-executor-proof', rpc('plan_totp',plan(f)|{'executor_proof':'B'*42+'A'})['http']==403)
    tx=Transaction()
    try:
        r=tx.rpc('plan_totp',plan(f)); check('successful-plan',r.get('http')==200 and 'metadata' in r)
        tx.finish(False)
    finally: tx.close()
    snap=snapshot(f)
    check('rollback-no-partial-bundle',snap['steps']==[] and snap['results']==[] and snap['plans']==[] and snap['dependency']['logins']==[])
    tx=Transaction(); failed=False
    try:
        tx.rpc('plan_totp',plan(f))
        try: tx.finish()
        except RuntimeError: failed=True
    finally: tx.close()
    check('plan-only-commit-rejected', failed and snapshot(f)['plans']==[])
    r=full(f); snap=snapshot(f)
    check('atomic-two-steps-and-login',r['http']==200 and r['result']['kind']=='login_completed' and [x['step'] for x in snap['steps']]==[153567,153569] and len(snap['results'])==1 and len(snap['dependency']['logins'])==1 and snap['results'][0]['valid'])
    check('replay-original-result',rpc('plan_totp',plan(f))=={'http':200,'replay':True,'result':r['result']})
    check('payload-conflict-no-second-result',rpc('plan_totp',plan(f)|{'comparison_hmac':'e'*64})['http']==409 and len(snapshot(f)['results'])==1)
    g=fixture(existing=f); capture(g); reused=full(g)
    check('used-step-rejected-atomically',reused['http']==401 and reused['result']=={'kind':'verification_rejected','reasonCode':'AUTH_VERIFICATION_FAILED'} and len(snapshot(g)['steps'])==2 and snapshot(g)['failures']==1)
    check('negative-read-http200',rpc('read_operation',read_ref(g))['http']==200)
    check('negative-replay-no-counter',rpc('plan_totp',plan(g))['replay'] is True and snapshot(g)['failures']==1)
    check('recover-same-login',rpc('recover',read_ref(f))['result']==r['result'])
    check('q01-closes-window',rpc('q01',{'login_id':f['login'],'cookie_digest':COOKIE})['http']==200 and not snapshot(f)['dependency']['logins'][0]['secret_present'])
    check('closed-recovery409',rpc('recover',read_ref(f))['reason']=='AUTH_COOKIE_RECOVERY_CLOSED')
    # Core email witness uses constructed SQL provider transition, labelled separately.
    e=fixture(totp=False)
    sql("UPDATE auth.users SET recovery_token='public-storage-fixture',recovery_sent_at=clock_timestamp() WHERE id="+q(e['user'])+';')
    capture(e)
    seal_input=write_ref(e)|dict(challenge_id=e['email_challenge'],admission_id=e['admission'],executor_proof=EXECUTOR_PROOF)
    seal=rpc('seal_email',seal_input)
    check('email-seal-one-permit',seal['dispatch_allowed'] and rpc('seal_email',seal_input)['dispatch_allowed'] is False)
    check('email-no-witness-no-plan',rpc('plan_email',write_ref(e)|dict(login_id=e['login'],secret_id=e['secret']))['http']==503)
    sql('BEGIN; UPDATE auth.users SET recovery_token=NULL WHERE id='+q(e['user'])+'; INSERT INTO auth.sessions(id,user_id,created_at,updated_at,aal) VALUES('
        +','.join([q(uid()),q(e['user']),'clock_timestamp()','clock_timestamp()',"'aal1'"])+'); COMMIT;')
    er=full(e,'plan_email'); es=snapshot(e)
    check('storage-email-witness-bound-completion',er['http']==200 and len(es['email_outcomes'])==1 and es['email_outcomes'][0]['consumption_txid']==es['email_outcomes'][0]['outcome_txid'] and len(es['results'])==1)
    prior_generation=es['email_outcomes'][0]['generation_id']
    sql("UPDATE auth.users SET recovery_token='public-next-storage-fixture',recovery_sent_at=clock_timestamp() WHERE id="+q(e['user'])+';')
    after_issuance=snapshot(e)
    check('new-issuance-preserves-consumed-history',next(x for x in after_issuance['generations'] if x['id']==prior_generation)['state']=='consumed'
          and after_issuance['email_outcomes']==es['email_outcomes'] and len(after_issuance['generations'])==2)
    # Current no-MFA source must not bypass a real verified provider factor.
    check('observer-no-secret-material',not any(k in json.dumps(es) for k in ['executor_proof','comparison_hmac','ciphertext','cookie_digest']))
    h=fixture(); capture(h)
    sql('UPDATE v00_upstream.gate SET epoch=epoch+1;')
    check('old-epoch-no-completion',rpc('plan_totp',plan(h))['http']==503 and snapshot(h)['results']==[])
    REPORT.extend({'id':case,'verdict':'not_run'} for case in ['real-provider-email-and-enrollment','HTTP-crypto-browser-loss','global-drain-reopening'])


if __name__ == '__main__':
    try:
        run()
    except Exception:
        print(json.dumps({'schema':'v00-upstream-storage-checks-v1','checks':REPORT,'completed':False}))
        raise SystemExit('upstream storage checks stopped; inspect privately, no raw query output') from None
    print(json.dumps({'schema':'v00-upstream-storage-checks-v1','checks':REPORT,'completed':True}))
