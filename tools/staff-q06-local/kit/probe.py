"""Compare the browser's Q06 reads with the user API and PostgreSQL audit."""
import http.client
import json
from pathlib import Path
import ssl
import subprocess

ROOT = Path(__file__).resolve().parent


def get(connection, path, headers):
    try:
        connection.request('GET', path, headers=headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def read_audits():
    sql = """SELECT jsonb_build_object(
     'auditId',a.id,'sessionId',a.target_session_id,'version',a.snapshot_version,
     'actorService',a.actor_service,'staffLogin',a.login_id IS NOT NULL,
     'evidence',(SELECT jsonb_agg(jsonb_build_object(
        'snapshotId',e.snapshot_id,'sessionId',e.session_id,'version',e.snapshot_version,'group',e.granted_group
      ) ORDER BY e.granted_group) FROM pilot_staff.read_evidence e WHERE e.audit_id=a.id)
    ) FROM pilot_staff.audit a WHERE a.action='session_read';"""
    lines = subprocess.check_output([
        'docker','exec','-i','-u','postgres','staff-acceptance-db','psql','-XqAt',
        '-U','postgres','-d','pilot_trial_local','-v','ON_ERROR_STOP=1',
    ], input=sql, text=True).splitlines()
    return [json.loads(line) for line in lines]


def run():
    targets = json.loads((ROOT/'targets.json').read_text())
    fixtures = json.loads((ROOT/'control/user-fixtures.json').read_text())
    seed = json.loads((ROOT/'control/seed-receipt.json').read_text())
    ip = (ROOT/'control/ips').read_text().splitlines()[0]
    assert len(targets) == len(fixtures) == 2
    expected = {}
    results = []
    for target, fixture in zip(targets, fixtures):
        sid = target['session']
        login = fixture['login']
        headers = {'Host':'localhost:18443','X-Shadow-Login-Id':login,
                   'Cookie':f"__Host-shadow-user-login-{login}={fixture['proof']}"}
        status, body = get(http.client.HTTPConnection(ip,8080,timeout=8),
                           f'/api/sessions/{sid}?requestSchemaVersion=v1', headers)
        assert status == 200, status
        session = body['session']
        browser_session = json.loads((ROOT/'control'/f'staff-read-{sid}.json').read_text())
        # The daily window is calculated at request time. The stored snapshot is shared.
        user_snapshot = {key:value for key,value in session.items() if key != 'dailyContext'}
        staff_snapshot = {key:value for key,value in browser_session.items() if key != 'dailyContext'}
        assert user_snapshot == staff_snapshot, 'User and staff read different snapshots'
        if seed['sessionId'] == sid:
            assert {key:session[key] for key in seed} == seed
            financial = session['financial']
            assert len(financial['positions']) == 1
            free, positions = financial['freeCash'], financial['positions']
            snapshot, version = session['snapshotId'], session['snapshotVersion']
            cfg = ROOT/'gatewaycfg'
            tls = ssl.create_default_context(cafile=str(cfg/'gateway.crt'))
            tls.load_cert_chain(cfg/'client.crt', cfg/'client.key')
            denied, body = get(
                http.client.HTTPSConnection('localhost',18443,context=tls,timeout=8),
                f'/api/admin/sessions/{sid}?requestSchemaVersion=v1',
                headers|{'X-Shadow-Pilot-Client-IP':'192.0.2.30','Sec-Fetch-Site':'same-origin'},
            )
            assert denied == 401 and body.get('reasonCode') == 'AUTH_REQUIRED' and 'session' not in body
            print(json.dumps({'userAdminHttp':denied, 'reason':body['reasonCode']}))
        else:
            assert session['summary']['sessionId'] == sid
            financial = session['financialSnapshot']
            assert financial['positionCount'] == '0' and financial['free'] == {'n':'200','d':'1'}
            free, positions = financial['free'], []
            snapshot, version = financial['snapshotId'], financial['snapshotVersion']
        expected[sid] = (snapshot, int(version))
        results.append(dict(sessionId=sid,snapshotId=snapshot,version=version,free=free,positions=positions))

    audits = read_audits()
    assert {row['sessionId'] for row in audits} == set(expected)
    for row in audits:
        sid = row['sessionId']
        snapshot, version = expected[sid]
        assert row['staffLogin'] and row['actorService'] == 'pilot_http_reader'
        assert row['version'] == version
        assert row['evidence'] == [
            dict(snapshotId=snapshot,sessionId=sid,version=version,group=group)
            for group in ('session.financial_snapshot','session.settings','session.summary')
        ]
    print(json.dumps(dict(sessions=results,audits=[{k:r[k] for k in ('sessionId','auditId')} for r in audits])))


if __name__ == '__main__':
    run()
