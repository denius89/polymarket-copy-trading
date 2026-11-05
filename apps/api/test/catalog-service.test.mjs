import test from 'node:test';
import assert from 'node:assert/strict';
import { createCursorCodec } from '../src/catalog/cursor.ts';
import { PaperService } from '../src/paper/service.ts';
import { id, identity } from './paper-fixtures.mjs';

function catalog() {
  const traders=[1,2].map(n=>({traderId:id(n),version:'1',currentRevisionId:id(100+n),currentRevision:'1',readVisible:true,startAllowed:true}));
  return {http:200,read_binding:{environment:'test-only',realm:'user',read_context_id:id(50),scope_id:id(60),scope_revision:`q02-read-scope-v1:${id(60)}:1`},
    descriptor:{venueId:id(10),venueCode:'polymarket',paperControl:{id:id(20),version:'1',startEnabled:true},sources:[
      {sourceId:id(11),venueId:id(10),version:'1',readVisible:true,startEnabled:true,traders}]},
    items:traders.map(t=>({traderId:t.traderId,venueId:id(10),catalogSourceId:id(11),venueCode:'polymarket',externalTraderId:'synthetic-'+t.traderId,
      displayName:'Synthetic',traderRevisionId:t.currentRevisionId,traderRevision:'1',dataOrigin:'synthetic',sourceRef:'fixture:catalog:1',
      observedAt:'2026-11-04T10:00:00.000Z',revisionCreatedAt:'2026-11-04T10:01:00.000Z',catalogVersionAtCreation:'1',catalogVersion:'1',
      traderControlVersion:'1',paperControlVersion:'1',startAvailability:{available:true,capabilityReasonCode:null}}))};
}
const proof={login_id:id(9),cookie_digest:'a'.repeat(64)};
const request={venueCode:'polymarket',limit:1};
async function setup() {
  const raw=catalog(),queries=[],releases=[];
  const state={rollbackFails:false,commitFails:false,driverFails:false};
  const pool={async connect(){return {async query(q){
    queries.push(q.text);
    if((q.text==='ROLLBACK'&&state.rollbackFails)||(q.text==='COMMIT'&&state.commitFails)||
      (q.text.includes('polygon.catalog_read')&&state.driverFails))throw new Error('private driver detail');
    if(q.text.includes('polygon.current_identity'))return {rows:[{reply:identity()}]};
    if(q.text.includes('polygon.catalog_read'))return {rows:[{reply:structuredClone(raw)}]};
    return {rows:[]};
  },release(destroy){releases.push(destroy);}};}};
  // Public test-only key, never a runtime provisioned key.
  const keyId='01'.repeat(16),cursor=await createCursorCodec(()=>({available:true,issuerKeyId:keyId,
    keys:new Map([[keyId,new Uint8Array(32).fill(7)]]),revoked:new Set()}));
  const service=new PaperService({pool,cursor,calendar:{},startEnabled:false});
  const first=await service.execute(proof,{kind:'catalog-list',request});
  assert.equal(first.status,200);assert.ok(first.body.nextCursor);
  queries.length=0;releases.length=0;
  return {raw,queries,releases,state,service,cursor:first.body.nextCursor};
}
const follow=f=>f.service.execute(proof,{kind:'catalog-list',request:{...request,cursor:f.cursor}});
function rolledBack(f){assert.equal(f.queries.at(-1),'ROLLBACK');assert.equal(f.queries.filter(x=>x.startsWith('BEGIN')).length,1);
  assert.ok(!f.queries.includes('COMMIT'));assert.deepEqual(f.releases,[false]);}
test('foreign reader cursor survives actual codec, service and transaction boundary as INVALID_REQUEST400',async()=>{
  const f=await setup();f.raw.read_binding.read_context_id=id(51);
  const reply=await follow(f);assert.equal(reply.status,400);assert.equal(reply.body.reasonCode,'INVALID_REQUEST');rolledBack(f);
});
test('changed permitted catalog scope survives transaction as CATALOG_CHANGED409',async()=>{
  const f=await setup();f.raw.read_binding.scope_revision=`q02-read-scope-v1:${id(60)}:2`;
  const reply=await follow(f);assert.equal(reply.status,409);assert.equal(reply.body.reasonCode,'CATALOG_CHANGED');rolledBack(f);
  assert.equal(reply.body.nextAction,'select_trader');assert.deepEqual(reply.body.nextActionParams,{venueId:id(10)});
});
test('absent catalog card survives transaction as RESOURCE_NOT_FOUND404',async()=>{
  const f=await setup();const reply=await f.service.execute(proof,{kind:'catalog-card',request:{venueCode:'polymarket',traderId:id(999)}});
  assert.equal(reply.status,404);assert.equal(reply.body.reasonCode,'RESOURCE_NOT_FOUND');rolledBack(f);
});
test('corrupt catalog stays RECORD_UNAVAILABLE503, never empty success or input refusal',async()=>{
  const f=await setup();f.raw.items.pop();const reply=await follow(f);
  assert.equal(reply.status,503);assert.equal(reply.body.reasonCode,'RECORD_UNAVAILABLE');rolledBack(f);
});
test('lost rollback masks cursor refusal with technical503 and destroys connection without retry',async()=>{
  const f=await setup();f.raw.read_binding.read_context_id=id(51);f.state.rollbackFails=true;
  const reply=await follow(f);assert.equal(reply.status,503);assert.equal(reply.body.reasonCode,'SERVICE_UNAVAILABLE');
  assert.equal(f.queries.at(-1),'ROLLBACK');assert.ok(!f.queries.includes('COMMIT'));assert.deepEqual(f.releases,[true]);
});
test('lost COMMIT and unknown driver exception remain technical503 without success or leaked detail',async()=>{
  for(const fail of ['commitFails','driverFails']){
    const f=await setup();f.state[fail]=true;const reply=await follow(f);
    assert.equal(reply.status,503);assert.equal(reply.body.reasonCode,'SERVICE_UNAVAILABLE');
    assert.ok(!JSON.stringify(reply).includes('private driver detail'));
    assert.equal(f.queries.filter(x=>x.startsWith('BEGIN')).length,1);
    if(fail==='commitFails'){assert.ok(!f.queries.includes('ROLLBACK'));assert.deepEqual(f.releases,[true]);}
  }
});
