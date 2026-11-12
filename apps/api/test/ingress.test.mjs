import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { Readable } from 'node:stream';
import { performance } from 'node:perf_hooks';
import { ingressMac, ingressBudget, verifyIngressBody, INGRESS_HEADERS } from '../src/http/ingress.ts';
import { paperHandler } from '../src/http/handler.ts';
const key=Uint8Array.from({length:32},(_,i)=>i),profile={mode:'gateway-monotonic-v1',readKey:()=>key};
const hash=body=>createHash('sha256').update(body).digest('hex');
test('ingress signature matches independent Python HMAC framing vector',()=>{
  assert.equal(ingressMac(key,'POST','/api/demo/drafts',hash('{}'),'1234567890123456').toString('hex'),
    '4d72d46383a1447fc91588ac4d46f438e896cac40a982a651578a4260b56b3d1');
});
function signed(deadline,method='GET',url='/api/sessions/current?requestSchemaVersion=v1',body=''){
  const bodyHash=hash(body),proof=ingressMac(key,method,url,bodyHash,deadline).toString('base64url');
  return {method,url,rawHeaders:[INGRESS_HEADERS[0],deadline,INGRESS_HEADERS[1],bodyHash,INGRESS_HEADERS[2],proof]};
}
test('signed original monotonic deadline carries prior queue time into the same five-second budget',()=>{
  const r=ingressBudget(signed('13000000000'),profile,1000,10000000000n);
  assert.equal(r.started,-1000);assert.equal(1000-r.started,2000);assert.equal(r.bodyHash,hash(''));
});
test('expired, implausible future, missing, duplicate and noncanonical ingress fail closed',()=>{
  for(const deadline of ['10000000000','9999999999','15000000001'])assert.throws(()=>ingressBudget(signed(deadline),profile,1000,10000000000n));
  const req=signed('13000000000');
  assert.throws(()=>ingressBudget({...req,rawHeaders:req.rawHeaders.slice(2)},profile));
  assert.throws(()=>ingressBudget({...req,rawHeaders:[...req.rawHeaders,INGRESS_HEADERS[0],'13000000000']},profile));
  assert.throws(()=>ingressBudget({...req,rawHeaders:req.rawHeaders.map((x,i)=>i===1?'013000000000':x)},profile));
});
test('proof binds exact method, raw target and body hash; direct test mode cannot accept ingress proof',()=>{
  const req=signed('13000000000');
  for(const changed of [{...req,method:'POST'},{...req,url:'/different'},
    {...req,rawHeaders:req.rawHeaders.map((x,i)=>i===3?hash('changed'):x)}])assert.throws(()=>ingressBudget(changed,profile,1000,10000000000n));
  assert.throws(()=>ingressBudget(req,{mode:'direct-test'}));
  assert.deepEqual(ingressBudget({rawHeaders:[]},{mode:'direct-test'},1000,0n),{started:1000,bodyHash:null});
  assert.throws(()=>verifyIngressBody(Buffer.from('changed'),hash('')));
  assert.doesNotThrow(()=>verifyIngressBody(Buffer.from(''),hash('')));
});
test('missing or malformed ingress key never becomes unsigned fallback',()=>{
  for(const readKey of [()=>{throw new Error('unavailable');},()=>new Uint8Array(31)]){
    assert.throws(()=>ingressBudget(signed('13000000000'),{mode:'gateway-monotonic-v1',readKey},1000,10000000000n));
  }
});
test('body arriving after the remaining original budget returns 503 without reaching service',async()=>{
  let calls=0,status;const deadline=(process.hrtime.bigint()+30_000_000n).toString();
  const req=new Readable({read(){}});Object.assign(req,signed(deadline));
  const handler=paperHandler({origin:'https://localhost:18443',ingress:profile,readCredentialKey:()=>key,
    service:{async execute(){calls++;return {status:200,body:{}};}}});
  const begin=performance.now();
  const timer=setTimeout(()=>{req.push(null);},200);
  await handler(req,{destroyed:false,writeHead(s){status=s;},end(){}});
  clearTimeout(timer);req.destroy();assert.equal(status,503);assert.equal(calls,0);assert.ok(performance.now()-begin<180);
});
test('Q01-to-identity keeps its original elapsed budget and missing gateway proof never calls storage',async()=>{
  let seen,status,calls=0;
  const handler=paperHandler({origin:'https://localhost:18443',ingress:profile,readCredentialKey:()=>key,
    service:{async execute(_auth,_op,start){calls++;seen=performance.now()-start;return {status:200,body:{}};}}});
  const login='11111111-1111-4111-8111-111111111111',secret=Buffer.alloc(32,7).toString('base64url');
  for(const valid of [false,true]){
    const props=signed((process.hrtime.bigint()+1_000_000_000n).toString(),'GET','/__polygon__/identity?requestSchemaVersion=v1');
    const req=Readable.from([]);Object.assign(req,{...props,rawHeaders:[...(valid?props.rawHeaders:[]),
      'Host','localhost:18443','X-Shadow-Login-Id',login,'Cookie',`__Host-shadow-user-login-${login}=${secret}`]});
    await handler(req,{destroyed:false,writeHead(s){status=s;},end(){}});assert.equal(status,valid?200:503);
  }
  assert.equal(calls,1);assert.ok(seen>=4000&&seen<5000);
});
