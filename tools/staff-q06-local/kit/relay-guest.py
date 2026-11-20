from pathlib import Path
import base64,html,http.client,json,re,ssl,sys
root=Path(__file__).resolve().parent
q=json.load(sys.stdin)
method=q['method']; path=q['path']; route=path.partition('?')[0]
def emit(status,headers,payload):
 print(json.dumps({'status':status,'headers':headers,'body':base64.b64encode(payload).decode(),'trace':{}}))
if method=='GET' and route=='/__local_permit':
 owner=json.loads((root/'control/material/owner-1.json').read_text())
 permit=html.escape(owner['permitId']); secret=html.escape(owner['secret'])
 page=f'<meta charset="utf-8"><title>Local fixture</title><label>Permit <input id="permit" value="{permit}" readonly></label><details><summary>Показать тестовый код</summary><output id="value">{secret}</output></details>'
 emit(200,[['Content-Type','text/html; charset=utf-8'],['Cache-Control','no-store']],page.encode())
 sys.exit()
assert re.fullmatch(r'/admin/(?:assets/[\w.\-]+)?|/api/admin/(?:me|pilot/(?:sessions(?:/[a-f0-9-]+/events)?|auth/[a-z0-9/\-]+)|sessions/[a-f0-9-]+)',route)
headers=q['headers']
if headers.get('Origin')==q['loopbackOrigin']: headers['Origin']='https://localhost:18443'
headers['X-Shadow-Pilot-Client-IP']='192.0.2.30'
cfg=root/'gatewaycfg'
ctx=ssl.create_default_context(cafile=str(cfg/'gateway.crt'))
ctx.load_cert_chain(cfg/'client.crt',cfg/'client.key')
conn=http.client.HTTPSConnection('localhost',18443,context=ctx,timeout=9)
conn.request(method,path,body=base64.b64decode(q['body']) if method=='POST' else None,headers=headers)
r=conn.getresponse(); data=r.read()
if r.status==200 and route.startswith('/api/admin/sessions/'):
 session=json.loads(data)['session']
 if session.get('schemaVersion')=='live-buy-session-v1':
  proof={key:session[key] for key in ('sessionId','snapshotId','snapshotVersion','financial','valuation')}
  (root/'control/staff-read-receipt.json').write_text(json.dumps(proof))

allowed={'content-type','x-shadow-login-id','cache-control','location','set-cookie'}
emit(r.status,[[k,v] for k,v in r.getheaders() if k.lower() in allowed],data)
