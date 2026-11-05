import test from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { paperHandler } from '../src/http/handler.ts';
import { selectedUserProof } from '../src/http/user-proof.ts';
import { id, request } from './paper-fixtures.mjs';
const login='11111111-1111-4111-8111-111111111111';
const secret='BwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwc';
const key=Uint8Array.from({length:32},(_,i)=>i);
const headers=()=>['Host','localhost:18443','X-Shadow-Login-Id',login,'Cookie',`__Host-shadow-user-login-${login}=${secret}`];
async function invoke({method='GET',url='/api/sessions/current?requestSchemaVersion=v1',rawHeaders=headers(),body='',reply={status:200,body:{tested:true}}}={}){
  let called=0,proof,operation;
  const handler=paperHandler({origin:'https://localhost:18443',readCredentialKey:()=>key,service:{async execute(a,b){called++;proof=a;operation=b;return reply;}}});
  const req=Readable.from([Buffer.from(body)]);Object.assign(req,{method,url,rawHeaders});
  let status,outHeaders,outBody;
  const res={destroyed:false,writeHead(s,h){status=s;outHeaders=h;},end(data){outBody=JSON.parse(data);}};
  await handler(req,res);return {status,headers:outHeaders,body:outBody,called,proof,operation};
}
test('V00 selected-cookie HMAC matches the independently computed Python framing vector',()=>{
  assert.deepEqual(selectedUserProof(login,`other=x; __Host-shadow-user-login-${login}=${secret}`,()=>key),{
    login_id:login,cookie_digest:'584413a1f74b34e3a1e5c72c1b340ec9eeca2f3ae8c6cf94c70dbaa474e91d30'});
  assert.throws(()=>selectedUserProof(login,`__Host-shadow-staff-login-${login}=${secret}`,()=>key),e=>e.status===401);
  assert.throws(()=>selectedUserProof(login,`__Host-shadow-user-login-${login}=${secret}; __Host-shadow-user-login-${login}=${secret}`,()=>key),e=>e.status===400);
});
test('successful protected read forwards only selected proof and emits fresh diagnostics',async()=>{
  const a=await invoke(),b=await invoke();assert.equal(a.status,200);assert.equal(a.called,1);assert.equal(a.operation.kind,'session');
  assert.equal(a.proof.login_id,login);assert.notEqual(a.headers['X-Request-Id'],b.headers['X-Request-Id']);
  assert.equal(a.headers['Cache-Control'],'no-store');assert.ok(!('X-Correlation-Id'in a.headers));
});
test('Host, correlation and selected login ambiguity reject before accessing storage',async()=>{
  const cases=[['Host','wrong',...headers().slice(2)],[...headers(),'X-Shadow-Login-Id',login],
    [...headers(),'X-Correlation-Id','invalid'],[...headers(),'X-Correlation-Id',id(1),'X-Correlation-Id',id(1)]];
  for(const rawHeaders of cases){const r=await invoke({rawHeaders});assert.equal(r.status,400);assert.equal(r.called,0);}
  const valid=await invoke({rawHeaders:[...headers(),'X-Correlation-Id',id(1)]});assert.equal(valid.headers['X-Correlation-Id'],id(1));
});
test('full JSON shape is rejected before Origin/Auth; valid write requires exact Origin and marker',async()=>{
  const base={method:'POST',url:'/api/demo/drafts',rawHeaders:[...headers(),'Content-Type','application/json'],body:JSON.stringify(request())};
  let r=await invoke({...base,body:'{"requestSchemaVersion":"v1"}'});assert.equal(r.status,400);assert.equal(r.called,0);
  r=await invoke(base);assert.equal(r.status,403);assert.equal(r.called,0);
  r=await invoke({...base,rawHeaders:[...base.rawHeaders,'Origin','https://localhost:18443','X-Shadow-Auth-Request','1','Sec-Fetch-Site','same-origin']});
  assert.equal(r.status,200);assert.equal(r.operation.kind,'save');
  r=await invoke({...base,rawHeaders:[...base.rawHeaders,'Origin','https://localhost:18443','X-Shadow-Auth-Request','1','X-Shadow-Auth-Request','1']});assert.equal(r.status,403);
});
test('size/media/body guards do not call storage and never echo secrets',async()=>{
  const size=await invoke({method:'POST',url:'/api/demo/drafts',body:'x'.repeat(65537)});assert.equal(size.status,413);assert.equal(size.called,0);
  const media=await invoke({method:'POST',url:'/api/demo/drafts',body:'{}'});assert.equal(media.status,415);
  const get=await invoke({body:'{}'});assert.equal(get.status,400);
  const noCookie=await invoke({rawHeaders:headers().slice(0,4)});assert.equal(noCookie.status,401);assert.equal(noCookie.body.nextAction,'authenticate');
  assert.ok(!JSON.stringify(noCookie).includes(secret));
});
test('internal identity route is distinct from public Q01 and admin routes are not implemented',async()=>{
  const r=await invoke({url:'/__polygon__/identity?requestSchemaVersion=v1'});assert.equal(r.operation.kind,'identity');
  for(const url of ['/api/me?requestSchemaVersion=v1','/api/admin/me?requestSchemaVersion=v1',`/api/admin/sessions/${id(30)}?requestSchemaVersion=v1`]){
    const x=await invoke({url});assert.equal(x.status,404);assert.equal(x.called,0);
  }
});
