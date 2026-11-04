#!/usr/bin/env python3
"""Operator-run isolated V00 storage checks. No network/provider calls or secrets.

V00_PSQL_COMMAND_JSON must identify the stand's administrator psql runner.
Each probe call SET ROLEs to executor; fixture writes SET ROLE to owner.
Creates new UUID-scoped fixtures, never deletes previous runs.
"""
import concurrent.futures
import json
import os
import select
import subprocess
import time
import uuid

COMMAND = json.loads(os.environ.get('V00_PSQL_COMMAND_JSON', '["psql"]'))
ARGS = ['-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1']
REPORT = []
FP = 'a' * 64


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def sql(text, role='v00_db_owner', app=None):
    env = os.environ.copy()
    if app:
        env['PGAPPNAME'] = app
    prefix = 'SET ROLE ' + role + ';' if role else ''
    result = subprocess.run(COMMAND + ARGS, input=prefix + text, text=True,
                            capture_output=True, env=env, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return result.stdout.strip()


def rpc(name, payload):
    result = sql('SELECT v00_db.' + name + '(' + quote(json.dumps(payload)) + '::jsonb);', 'v00_db_executor')
    return json.loads(result) if result else None


def uid():
    return str(uuid.uuid4())


def fixture(step=153568, actor=None, factor=None):
    actor, factor, ctx, challenge = actor or uid(), factor or uid(), uid(), uid()
    sql('BEGIN; INSERT INTO v00_db.actors(id,fixed_time) VALUES(' + quote(actor) + ',to_timestamp(' + str(step * 30) + ')) ON CONFLICT DO NOTHING;'
        'INSERT INTO v00_db.factors(id,actor_id) VALUES(' + quote(factor) + ',' + quote(actor) + ') ON CONFLICT DO NOTHING;'
        'INSERT INTO v00_db.contexts(id,actor_id,factor_version,expires_at) VALUES(' + quote(ctx) + ',' + quote(actor) + ',' + quote(factor) + ',to_timestamp(' + str(step * 30 + 3600) + '));'
        'INSERT INTO v00_db.challenges(id,context_id,expires_at) VALUES(' + quote(challenge) + ',' + quote(ctx) + ',to_timestamp(' + str(step * 30 + 300) + '));'
        'UPDATE v00_db.contexts SET current_challenge_id=' + quote(challenge) + ' WHERE id=' + quote(ctx) + '; COMMIT;')
    return dict(actor=actor, factor=factor, context=ctx, challenge=challenge, step=step)


def request(f, steps, **overrides):
    result = dict(operation_id=uid(), context_id=f['context'], challenge_id=f['challenge'],
                  factor_version=f['factor'], fingerprint=FP, evaluation_step=f['step'],
                  matched_steps=steps, clock_trusted=True)
    result.update(overrides)
    return result


def state(f):
    return json.loads(sql("SELECT jsonb_build_object('failures',a.failures,'paused',a.blocked_until IS NOT NULL,"
                          "'steps',(SELECT COALESCE(jsonb_agg(step ORDER BY step),'[]') FROM v00_db.used_steps WHERE factor_version=" + quote(f['factor']) + "),"
                          "'results',(SELECT count(*) FROM v00_db.totp_results r JOIN v00_db.contexts c ON c.id=r.context_id WHERE c.actor_id=a.id)) FROM v00_db.actors a WHERE id=" + quote(f['actor']) + ';'))


def record(case, expected, actual):
    REPORT.append(dict(case=case, expected=expected, actual=actual, verdict='pass' if expected == actual else 'fail'))


def main():
    f = fixture()
    p = request(f, [153567, 153569])
    r = rpc('verify_totp', p)
    record('DB01-all-matching', [200, [153567, 153569], 1, 0], [r['http'], state(f)['steps'], state(f)['results'], state(f)['failures']])
    sql('UPDATE v00_db.factors SET active=false WHERE id=' + quote(f['factor']) + '; UPDATE v00_db.actors SET fixed_time=fixed_time+interval \'2 days\' WHERE id=' + quote(f['actor']) + ';')
    record('DB02-replay-after-change', [r, r], [rpc('lookup_totp', p), rpc('verify_totp', p)])
    altered = dict(p, fingerprint='b' * 64)
    record('DB03-key-conflict', [409, 1], [rpc('verify_totp', altered)['http'], state(f)['results']])

    f = fixture(step=153566)
    rpc('verify_totp', request(f, [153567]))
    sql('UPDATE v00_db.actors SET fixed_time=to_timestamp(153568*30) WHERE id=' + quote(f['actor']) + ';')
    second = fixture(actor=f['actor'], factor=f['factor'])
    p = request(second, [153567, 153569])
    r = rpc('verify_totp', p)
    replay = rpc('verify_totp', p)
    record('DB04-partial-overlap', [401, [153567], 1, 2, True], [r['http'], state(f)['steps'], state(f)['failures'], state(f)['results'], replay == r])

    f = fixture()
    second = fixture(actor=f['actor'], factor=f['factor'])
    payloads = [request(f, [153568]), request(second, [153568])]
    holder = subprocess.Popen(COMMAND + ARGS, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    holder.stdin.write('BEGIN; SET ROLE v00_db_owner; DO $$ BEGIN PERFORM id FROM v00_db.actors WHERE id=' + quote(f['actor']) + " FOR UPDATE; END $$; SELECT 'barrier-ready';\n")
    holder.stdin.flush()
    deadline = time.monotonic() + 5
    ready = False
    while time.monotonic() < deadline:
        if select.select([holder.stdout], [], [], .1)[0]:
            if holder.stdout.readline().strip() == 'barrier-ready':
                ready = True
                break
    if not ready:
        holder.kill()
        raise RuntimeError('actor barrier unavailable')
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(rpc, 'verify_totp', p) for p in payloads]
            deadline = time.monotonic() + 4
            waiters = 0
            while time.monotonic() < deadline:
                # Independent administrator observes actual lock contention, not a guessed sleep.
                waiters = int(sql("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND wait_event_type='Lock' AND query LIKE '%SELECT v00_db.verify_totp%';", role=None))
                if waiters >= 2:
                    break
                time.sleep(.05)
            holder.stdin.write('COMMIT;\n\\q\n')
            holder.stdin.flush()
            results = [future.result() for future in futures]
        holder.wait(timeout=5)
    finally:
        if holder.poll() is None:
            holder.kill()
    record('DB05-concurrent-reuse', [True, [200, 401], [153568], 2, 1],
           [waiters >= 2, sorted(r['http'] for r in results), state(f)['steps'], state(f)['results'], state(f)['failures']])

    f = fixture()
    statuses = [rpc('verify_totp', request(f, []))['http'] for _ in range(5)]
    p = request(f, [153568])
    statuses.append(rpc('verify_totp', p)['http'])
    record('DB06-user-pause', [[401]*5+[429], 5, 5, []], [statuses, state(f)['failures'], state(f)['results'], state(f)['steps']])
    sql('UPDATE v00_db.actors SET fixed_time=fixed_time+interval \'15 minutes\' WHERE id=' + quote(f['actor']) + ';')
    fresh = fixture(step=153598, actor=f['actor'], factor=f['factor'])
    r = rpc('verify_totp', request(fresh, [153598]))
    record('DB07-pause-boundary', [200, 0, False], [r['http'], state(f)['failures'], state(f)['paused']])

    f = fixture()
    before = state(f)
    cases = [dict(clock_trusted=False), dict(evaluation_step=153567), dict(challenge_id=uid())]
    statuses = [rpc('verify_totp', request(f, [153568], **change))['http'] for change in cases]
    record('DB08-precheck-no-mutation', [[503, 503, 404], before], [statuses, state(f)])

    f = fixture()
    p = request(f, [153568])
    # A real surrounding transaction rolls back step/result/counter/stage together.
    sql('BEGIN; SELECT v00_db.verify_totp(' + quote(json.dumps(p)) + '::jsonb); ROLLBACK;', role='v00_db_executor')
    record('DB09-rollback', [[], 0, 0, None], [state(f)['steps'], state(f)['results'], state(f)['failures'], rpc('lookup_totp', p)])
    record('DB10-after-rollback', 200, rpc('verify_totp', p)['http'])

    other = fixture(actor=f['actor'])
    r = rpc('verify_totp', request(other, [153568]))
    record('DB11-factor-version-isolation', [200, [153568]], [r['http'], state(other)['steps']])

    denied = []
    for role, statement in [
        ('v00_db_executor', 'UPDATE v00_db.actors SET failures=0;'),
        ('v00_db_executor', 'INSERT INTO v00_db.used_steps VALUES(NULL,NULL,NULL,NULL);'),
        ('v00_db_observer', 'SELECT v00_db.verify_totp(\'{}\');'),
        ('v00_db_owner', 'UPDATE v00_db.totp_results SET result=result;'),
    ]:
        try:
            sql(statement, role=role)
            denied.append(False)
        except RuntimeError as error:
            denied.append('permission denied' in str(error) or 'immutable V00 evidence' in str(error))
    record('DB12-role-and-history-denials', [True]*4, denied)
    print(json.dumps(dict(profile='v00-storage-primitive-v1',clock_mode='fixed_fixture',cases=REPORT), indent=2))
    return int(any(row['verdict'] != 'pass' for row in REPORT))


if __name__ == '__main__':
    raise SystemExit(main())
