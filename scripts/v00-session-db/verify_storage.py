#!/usr/bin/env python3
"""Independent operator-run D03-07 SQL checks; fresh synthetic fixtures only.

No provider/network/browser/crypto claims. psql is selected by the operator via
V00_SESSION_PSQL_COMMAND_JSON. Never use this against an existing Auth database.
Published report contains only expected/actual structural facts, not credentials.
"""
import base64
import concurrent.futures
import json
import os
import select
import subprocess
import time
import uuid

COMMAND = json.loads(os.environ.get('V00_SESSION_PSQL_COMMAND_JSON', '["psql"]'))
ARGS = ['-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1']
REPORT = []
FP, PROOF, COOKIE = 'a' * 64, 'b' * 64, 'c' * 64
BASE = "'2026-11-04T12:00:00Z'::timestamptz"


def uid():
    return str(uuid.uuid4())


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def statement(name, payload):
    if name not in {'plan_completion', 'complete', 'lookup_result', 'recover', 'q01', 'revoke',
                    'logout_prepare', 'logout_continue', 'logout', 'logout_result'}:
        raise ValueError('unknown private function')
    return 'SELECT v00_session.' + name + '(' + quote(json.dumps(payload)) + '::jsonb);'


def sql(text, role='v00_session_owner', app=None, expect_error=False):
    prefix = ('SET ROLE ' + role + ';') if role else ''
    if app:
        prefix += 'SET application_name=' + quote(app) + ';'
    r = subprocess.run(COMMAND + ARGS + ['-q'], input=prefix + text, text=True,
                       capture_output=True, timeout=25)
    if expect_error:
        return r.returncode != 0
    if r.returncode:
        # Do not put query parameters, private digests or material in an exception/report.
        raise RuntimeError('psql failed; inspect privately on isolated stand')
    return r.stdout.strip()


class Transaction:
    """Keep database locks through the trusted adapter phase and verified COMMIT."""
    def __init__(self, role='v00_session_executor', app=None):
        self.p = subprocess.Popen(COMMAND + ARGS, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  bufsize=0)
        self.buffer = b''
        self.step('BEGIN; SET LOCAL ROLE ' + role + ';' +
                  ('SET LOCAL application_name=' + quote(app) + ';' if app else ''))

    def step(self, text):
        marker = 'ready_' + uuid.uuid4().hex
        self.p.stdin.write((text + '\n\\echo ' + marker + '\n').encode())
        self.p.stdin.flush()
        result, deadline = [], time.monotonic() + 25
        while time.monotonic() < deadline:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                line = line.decode().strip()
                if line == marker:
                    return result
                if line:
                    result.append(line)
            if select.select([self.p.stdout], [], [], .1)[0]:
                chunk = os.read(self.p.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError('interactive psql stopped before confirmation')
                self.buffer += chunk
            elif self.p.poll() is not None:
                raise RuntimeError('interactive psql failed before confirmation')
        raise RuntimeError('interactive psql confirmation timeout')

    def rpc(self, name, payload):
        return json.loads(self.step(statement(name, payload))[-1])

    def finish(self, commit=True):
        expected = 'COMMIT' if commit else 'ROLLBACK'
        lines = self.step(expected + ';')
        if lines != [expected]:
            raise RuntimeError('transaction end was not positively confirmed')
        self.close()

    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close()
            try:
                self.p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait()


def rpc(name, payload, app=None, role='v00_session_executor'):
    return json.loads(sql(statement(name, payload), role, app))


def fixture(actor=None, context_seconds=3600, wall=False):
    f = dict(actor=actor or uid(), context=uid(), operation=uid(), login=uid(), secret=uid())
    now = 'clock_timestamp()' if wall else BASE
    fixed = 'NULL' if wall else BASE
    sql('BEGIN; INSERT INTO v00_session.actors(id,fixed_time) VALUES(' + quote(f['actor']) + ',' + fixed + ') ON CONFLICT DO NOTHING;'
        'INSERT INTO v00_session.contexts(id,actor_id,proof_digest,expires_at,login_expires_at,idle_expires_at) VALUES('
        + ','.join([quote(f['context']), quote(f['actor']), quote(PROOF),
                    now + "+interval '" + str(context_seconds) + " seconds'", now + "+interval '8 hours'", now + "+interval '2 hours'"])
        + '); COMMIT;')
    return f


def plan(f, **kw):
    p = dict(context_id=f['context'], proof_digest=PROOF, operation_id=f['operation'],
             fingerprint=FP, login_id=f['login'], secret_id=f['secret'])
    p.update(kw)
    return p


def material(f):
    # Non-secret synthetic bytes; SQL tests do not claim authenticated encryption.
    return dict(context_id=f['context'], proof_digest=PROOF, operation_id=f['operation'],
                fingerprint=FP, cookie_digest=COOKIE, nonce=base64.b64encode(bytes(24)).decode(),
                ciphertext=base64.b64encode(bytes(32)).decode(), key_id='synthetic-only', credential_key_id='synthetic-only')


def complete(f, t=None, app=None):
    own = t is None
    t = t or Transaction(app=app)
    try:
        r = t.rpc('plan_completion', plan(f))
        if r['http'] == 200 and not r['replay']:
            r = t.rpc('complete', material(f))
        if own:
            t.finish(r['http'] == 200)
        return r
    finally:
        if own:
            t.close()


def ref(f):
    return dict(context_id=f['context'], proof_digest=PROOF, operation_id=f['operation'])


def login(f):
    return dict(login_id=f['login'], cookie_digest=COOKIE)


def snapshot(f):
    return json.loads(sql('SELECT v00_session.snapshot(' + quote(f['actor']) + ');', 'v00_session_observer'))


def advance(f, seconds):
    sql('UPDATE v00_session.actors SET fixed_time=' + BASE + "+interval '" + str(seconds) + " seconds' WHERE id=" + quote(f['actor']) + ';')


def record(case, expected, actual):
    REPORT.append(dict(case=case, expected=expected, actual=actual, verdict='pass' if expected == actual else 'fail'))


def counts(f):
    s = snapshot(f)
    return [len(s['logins']), len(s['results']), s['plans']]


def logout_prepare(f):
    ctx = uid()
    r = rpc('logout_prepare', dict(logout_context_id=ctx, **login(f), logout_proof_digest=PROOF))
    if r['http'] != 201:
        raise RuntimeError('logout fixture preparation failed')
    return dict(logout_context_id=ctx, proof_digest=PROOF, operation_id=uid(), fingerprint=FP)


def logout_ref(p):
    return {k: p[k] for k in ('logout_context_id', 'proof_digest', 'operation_id')}


def ordered(first, second, expected, case):
    f = fixture()
    complete(f)
    requests = {'recover': ref(f), 'q01': login(f), 'revoke': {'login_id': f['login']}}
    t = Transaction(role='v00_session_owner')
    app = 'd0307_wait_' + uuid.uuid4().hex
    observed = False
    try:
        a = t.rpc(first, requests[first])
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(rpc, second, requests[second], app, 'v00_session_owner')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                observed = sql('SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() '
                               "AND wait_event_type='Lock' AND application_name=" + quote(app) + ');', role=None) == 't'
                if observed:
                    break
                time.sleep(.05)
            t.finish()
            b = future.result(timeout=10)
        # Inspect current guard after the serialized operations; no delayed response revives a login.
        current = rpc('q01', login(f))['http'] if 'revoke' in (first, second) else 200
        s = snapshot(f)
        record(case, [True, *expected, 401 if 'revoke' in (first, second) else 200, 1, False],
               [observed, a['http'], b['http'], current, len(s['logins']), s['logins'][0]['secret_present']])
    finally:
        t.close()


def main():
    f = fixture()
    r = complete(f)
    s = snapshot(f)
    l = s['logins'][0]
    record('D07-DB01-atomic-bundle', [200, [1, 1, 1], True, '2026-11-04T12:05:00.000Z', True, True],
           [r['http'], counts(f), s['results'][0]['valid'], l['deadline'], l['secret_present'], l['credential_present']])
    replay = complete(f)
    new = rpc('plan_completion', plan(f, operation_id=uid()))
    record('D07-DB02-replay', [r['result'], 409, [1, 1, 1]], [replay['result'], new['http'], counts(f)])
    conflict = rpc('plan_completion', plan(f, fingerprint='d' * 64))
    record('D07-DB03-payload', [409, 'KEY_REUSE_CONFLICT', r['result']],
           [conflict['http'], conflict['reason'], rpc('lookup_result', ref(f))['result']])

    z = fixture()
    t = Transaction()
    app = 'd0307_complete_' + uuid.uuid4().hex
    try:
        first = complete(z, t)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(complete, z, None, app)
            deadline, observed = time.monotonic() + 5, False
            while time.monotonic() < deadline:
                observed = sql('SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() '
                               "AND wait_event_type='Lock' AND application_name=" + quote(app) + ');', role=None) == 't'
                if observed:
                    break
                time.sleep(.05)
            t.finish()
            second = future.result(timeout=10)
        record('D07-DB02-concurrent-absent-result', [True, first['result'], [1, 1, 1]],
               [observed, second['result'], counts(z)])
    finally:
        t.close()

    advance(f, 299.999)
    recovered = rpc('recover', ref(f))
    record('D07-DB04-before-boundary', [200, True, [1, 1, 1], l['deadline']],
           [recovered['http'], recovered.get('cookie_digest') == COOKIE, counts(f), snapshot(f)['logins'][0]['deadline']])
    for elapsed in (300, 300.001):
        g = fixture()
        complete(g)
        advance(g, elapsed)
        out = rpc('recover', ref(g))
        x = snapshot(g)['logins'][0]
        record('D07-DB05-boundary-' + str(elapsed), [409, 'AUTH_COOKIE_RECOVERY_CLOSED', False, True, True, 'deadline'],
               [out['http'], out['reason'], x['secret_present'], x['erased_at'] is not None, x['credential_present'], x['close_reason']])
        deadline = x['deadline']
        q = rpc('q01', login(g))
        x = snapshot(g)['logins'][0]
        record('D07-DB13-late-q01-' + str(elapsed), [200, 'deadline', deadline, True],
               [q['http'], x['close_reason'], x['deadline'], x['first_confirmed_at'] is not None])

    g = fixture(context_seconds=120)
    complete(g)
    advance(g, 120)
    record('D07-DB06-context-min', ['2026-11-04T12:02:00.000Z', 401, 200],
           [snapshot(g)['logins'][0]['deadline'], rpc('recover', ref(g))['http'], rpc('q01', login(g))['http']])
    g = fixture()
    complete(g)
    before = snapshot(g)['logins'][0]
    q = rpc('q01', login(g))
    q2 = rpc('q01', login(g))
    after = snapshot(g)
    x = after['logins'][0]
    record('D07-DB07-q01', [200, 200, before['idle_expires_at'], before['deadline'], False, 1, 1],
           [q['http'], q2['http'], x['idle_expires_at'], x['deadline'], x['secret_present'],
            sum(a['kind'] == 'first_confirmation' for a in after['audit']), sum(a['kind'] == 'window_closed' for a in after['audit'])])
    for first, second, expected, case in [
        ('q01', 'recover', [200, 409], 'D07-DB08-q01-before-recovery'),
        ('recover', 'q01', [200, 200], 'D07-DB09-recovery-before-q01'),
        ('revoke', 'recover', [204, 401], 'D07-DB10-revoke-before-recovery'),
        ('recover', 'revoke', [200, 204], 'D07-DB11-recovery-before-revoke'),
        ('q01', 'revoke', [200, 204], 'D07-DB12-q01-before-revoke'),
        ('revoke', 'q01', [204, 401], 'D07-DB12-revoke-before-q01')]:
        ordered(first, second, expected, case)

    g = fixture()
    old = complete(g)['result']
    rpc('revoke', {'login_id': g['login']}, role='v00_session_owner')
    record('D07-DB16-history-after-revoke', [old, 401, 401],
           [rpc('lookup_result', ref(g))['result'], rpc('recover', ref(g))['http'], rpc('q01', login(g))['http']])
    record('D07-DB17-wrong-proofs', [404, 404, 401],
           [rpc('lookup_result', dict(ref(g), proof_digest='e' * 64))['http'],
            rpc('recover', dict(ref(g), proof_digest='e' * 64))['http'], rpc('q01', dict(login(g), cookie_digest='e' * 64))['http']])
    unknown = dict(ref(g), operation_id=uid())
    record('D07-DB18-trusted-absence', [202, 503, [1, 1, 1]],
           [rpc('lookup_result', unknown)['http'], rpc('recover', unknown)['http'], counts(g)])

    # Corruption is confined to a rollback-only operator transaction; it cannot enter other fixtures.
    for label, malformed in [('missing-completion', {'kind': 'login_completed'}),
                             ('wrong-login', dict(old, completion=dict(old['completion'], loginId=uid())))]:
        t = Transaction(role='v00_session_owner')
        try:
            t.step('ALTER TABLE v00_session.results DISABLE TRIGGER immutable_result; UPDATE v00_session.results SET result='
                   + quote(json.dumps(malformed)) + '::jsonb WHERE context_id=' + quote(g['context']) + ';')
            statuses = [t.rpc('lookup_result', ref(g))['http'], t.rpc('recover', ref(g))['http'],
                        t.rpc('plan_completion', plan(g, fingerprint='d' * 64))['http']]
            record('D07-DB14-corrupt-' + label, [503, 503, 503], statuses)
            t.finish(False)
        finally:
            t.close()
    h = fixture()
    sql('INSERT INTO v00_session.results(context_id,operation_id,fingerprint,result,resolved_at) VALUES('
        + ','.join([quote(h['context']), quote(h['operation']), quote(FP),
                    quote(json.dumps({'kind': 'verification_rejected', 'reasonCode': 'AUTH_VERIFICATION_FAILED'})) + '::jsonb', BASE]) + ');')
    record('D07-DB14-known-rejection', [200, '2026-11-04T12:00:00.000Z', 409, 'AUTH_COOKIE_RECOVERY_NOT_APPLICABLE'],
           [rpc('lookup_result', ref(h))['http'], rpc('lookup_result', ref(h))['resolved_at'], rpc('recover', ref(h))['http'], rpc('recover', ref(h))['reason']])
    t = Transaction(role='v00_session_owner')
    try:
        t.step("ALTER TABLE v00_session.results DISABLE TRIGGER immutable_result; UPDATE v00_session.results SET result='{\"kind\":\"verification_rejected\"}' WHERE context_id=" + quote(h['context']) + ';')
        record('D07-DB14-corrupt-rejection', [503, 503, 503],
               [t.rpc('lookup_result', ref(h))['http'], t.rpc('recover', ref(h))['http'], t.rpc('plan_completion', plan(h))['http']])
        t.finish(False)
    finally:
        t.close()
    h = fixture()
    complete(h)
    t = Transaction(role='v00_session_owner')
    try:
        t.step('UPDATE v00_session.secrets SET ciphertext=NULL,erased_at=' + BASE + ' WHERE login_id=' + quote(h['login']) + ';')
        record('D07-DB14-unlawful-erasure', [503], [t.rpc('recover', ref(h))['http']])
        t.finish(False)
    finally:
        t.close()

    a = fixture()
    complete(a)
    b = fixture(actor=a['actor'])
    complete(b)
    p = logout_prepare(a)
    before_b = next(x for x in snapshot(b)['logins'] if x['id'] == b['login'])
    read = rpc('logout_result', logout_ref(p))
    record('D07-DB22-read-absence', [202, None, None],
           [read['http'], read['result'], next(x for x in snapshot(a)['logins'] if x['id'] == a['login'])['revoked_at']])
    new_ctx = uid()
    continued = rpc('logout_continue', dict(logout_context_id=new_ctx, source_context_id=p['logout_context_id'],
                    authorization_login_id=b['login'], cookie_digest=COOKIE, authorization_mode='current_user', logout_proof_digest=PROOF))
    record('D07-DB20-continue-target', [201, a['login'], p['logout_context_id'], '2026-11-04T12:15:00.000Z'],
           [continued['http'], continued['target_login_id'], continued['source_context_id'], continued['expires_at']])
    new_p = dict(p, logout_context_id=new_ctx, operation_id=uid())
    out = rpc('logout', new_p)
    after_b = next(x for x in snapshot(b)['logins'] if x['id'] == b['login'])
    record('D07-DB19-target-only', [204, a['login'], before_b, 202],
           [out['http'], out['result']['target_login_id'], after_b, rpc('logout_result', logout_ref(p))['http']])
    record('D07-DB21-logout-replay', [out, 409, out['result']],
           [rpc('logout', new_p), rpc('logout', dict(new_p, fingerprint='d' * 64))['http'], rpc('logout_result', logout_ref(new_p))['result']])
    old_target = logout_prepare(a)
    record('D07-DB23-revoked-original-limited', [401, 204],
           [rpc('q01', login(a))['http'], rpc('logout', old_target)['http']])
    advance(a, 901)
    c = rpc('logout_continue', dict(logout_context_id=uid(), source_context_id=p['logout_context_id'], authorization_login_id=a['login'],
                                   cookie_digest=COOKIE, authorization_mode='original_login', logout_proof_digest=PROOF))
    record('D07-DB23-expired-context-continue', [401, 201, a['login']],
           [rpc('logout_result', logout_ref(p))['http'], c['http'], c['target_login_id']])
    outsider = fixture()
    complete(outsider)
    denial = rpc('logout_continue', dict(logout_context_id=uid(), source_context_id=p['logout_context_id'], authorization_login_id=outsider['login'],
                                        cookie_digest=COOKIE, authorization_mode='current_user', logout_proof_digest=PROOF))
    record('D07-DB20-foreign-actor', [404], [denial['http']])

    for action in ('completion', 'q01', 'logout'):
        z = fixture()
        if action != 'completion':
            complete(z)
        pz = logout_prepare(z) if action == 'logout' else None
        before = snapshot(z)
        t = Transaction()
        try:
            if action == 'completion':
                complete(z, t)
            else:
                t.rpc(action, pz if action == 'logout' else login(z))
            t.finish(False)
        finally:
            t.close()
        record('D07-DB24-rollback-' + action, [before], [snapshot(z)])
    z = fixture()
    fail = sql('BEGIN;' + statement('plan_completion', plan(z)) + 'COMMIT;', 'v00_session_executor', expect_error=True)
    record('D07-DB24-plan-alone', [True, [0, 0, 0]], [fail, counts(z)])
    z = fixture()
    fail = sql('BEGIN;' + statement('plan_completion', plan(z)) + statement('complete', material(z))
               + 'SET ROLE v00_session_owner; DELETE FROM v00_session.secrets WHERE login_id=' + quote(z['login']) + '; COMMIT;', expect_error=True)
    record('D07-DB24-partial-bundle', [True, [0, 0, 0]], [fail, counts(z)])

    # True wall clock crosses context deadline while an interactive plan is held.
    z = fixture(context_seconds=2, wall=True)
    t = Transaction()
    try:
        planned = t.rpc('plan_completion', plan(z))
        t.step('SELECT pg_sleep(2.1);')
        failed = t.rpc('complete', material(z))
        t.finish(False)
        record('D07-DB24-time-after-crypto-phase', [200, 401, [0, 0, 0]], [planned['http'], failed['http'], counts(z)])
    finally:
        t.close()

    denied = []
    for role, query in [
        ('v00_session_executor', 'SELECT * FROM v00_session.secrets;'),
        ('v00_session_executor', 'UPDATE v00_session.actors SET fixed_time=clock_timestamp();'),
        ('v00_session_executor', statement('revoke', {'login_id': a['login']})),
        ('v00_session_observer', 'SELECT * FROM v00_session.credentials;'),
        ('v00_session_observer', statement('q01', login(a))),
        ('v00_session_executor', 'SELECT v00_session.snapshot(' + quote(a['actor']) + ');')]:
        denied.append(sql(query, role, expect_error=True))
    record('D07-roles-no-secret-or-mutation', [True] * 6, denied)
    # These belong to other independently observed layers, never marked pass here.
    for case in ('D07-DB15-authenticated-crypto', 'D07-DB18-network-commit-uncertainty', 'D07-browser-cookie-and-cache'):
        REPORT.append(dict(case=case, verdict='not_run', reason='separate backend/operator actual required'))
    print(json.dumps(dict(profile='v00-session-storage-v1', tests=REPORT,
                          passed=sum(x['verdict'] == 'pass' for x in REPORT), failed=sum(x['verdict'] == 'fail' for x in REPORT),
                          not_run=sum(x['verdict'] == 'not_run' for x in REPORT)), indent=2))
    return 1 if any(x['verdict'] == 'fail' for x in REPORT) else 0


if __name__ == '__main__':
    raise SystemExit(main())
