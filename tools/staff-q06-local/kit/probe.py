from pathlib import Path
import hashlib,http.client,json,ssl,subprocess
p=Path(__file__).resolve().parent
target=json.loads((p/'targets.json').read_text())[0]
sid=target['session']
fixture=json.loads((p/'control/user-fixtures.json').read_text())[0]
login=fixture['login']
headers={'Host':'localhost:18443','X-Shadow-Login-Id':login,
         'Cookie':f"__Host-shadow-user-login-{login}={fixture['proof']}"}
def get(connection,path,headers):
 try:
  connection.request('GET',path,headers=headers)
  r=connection.getresponse()
  return r.status,json.loads(r.read())
 finally:
  connection.close()
ip=(p/'control/ips').read_text().splitlines()[0]
status,body=get(http.client.HTTPConnection(ip,8080,timeout=8),f'/api/sessions/{sid}?requestSchemaVersion=v1',headers)
print(f'user_own_session_http={status}')
assert status==200
session=body['session']
seed=json.loads((p/'control/seed-receipt.json').read_text())
assert session['schemaVersion']=='live-buy-session-v1' and session['sessionId']==sid
assert {k:session[k] for k in seed}==seed==json.loads((p/'control/staff-read-receipt.json').read_text())
snapshot=session['financial']
assert len(snapshot['positions'])==1
cfg=p/'gatewaycfg'
ctx=ssl.create_default_context(cafile=str(cfg/'gateway.crt'))
ctx.load_cert_chain(cfg/'client.crt',cfg/'client.key')
status,denied=get(http.client.HTTPSConnection('localhost',18443,context=ctx,timeout=8),
 f'/api/admin/sessions/{sid}?requestSchemaVersion=v1',
 headers|{'X-Shadow-Pilot-Client-IP':'192.0.2.30','Sec-Fetch-Site':'same-origin'})
assert status in (401,403) and 'session' not in denied,(status,denied)
safe={k:snapshot[k] for k in ('cash','reservedCash','freeCash','cashExpenses','positions')}
print(json.dumps(dict(session=sid,snapshot_id=session['snapshotId'],snapshot_version=session['snapshotVersion'],user_snapshot=safe,user_admin_http=status,reason=denied.get('reasonCode'))))
sql="""SELECT jsonb_build_object('action',a.action,'session',a.target_session_id,'snapshot',a.snapshot_version,
 'service',a.actor_service,'staff_login',a.login_id IS NOT NULL,'audit_id',a.id,
 'evidence',(SELECT jsonb_agg(granted_group ORDER BY granted_group) FROM pilot_staff.read_evidence e
 WHERE e.audit_id=a.id AND e.session_id=a.target_session_id AND e.snapshot_version=a.snapshot_version),
 'snapshot_id',(SELECT min(e.snapshot_id::text) FROM pilot_staff.read_evidence e WHERE e.audit_id=a.id))
 FROM pilot_staff.audit a WHERE a.action='session_read' AND a.target_session_id=:'sid'::uuid;"""
lines=subprocess.check_output(['docker','exec','-i','-u','postgres','staff-acceptance-db','psql','-XqAt','-U','postgres',
 '-d','pilot_trial_local','-v','ON_ERROR_STOP=1','-v',f'sid={sid}'],input=sql,text=True).splitlines()
audits=[json.loads(line) for line in lines]
assert len(audits)==1 and audits[0]['staff_login'] and audits[0]['service']=='pilot_http_reader' and len(audits[0]['evidence'])==3 and audits[0]['snapshot_id']==session['snapshotId'] and str(audits[0]['snapshot'])==session['snapshotVersion'],audits
print(json.dumps(audits[0]))
