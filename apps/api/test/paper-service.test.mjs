import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { PaperService } from '../src/paper/service.ts';
import { id, at, identity, request, ref, receipt, draft, review, session } from './paper-fixtures.mjs';
const calendar=JSON.parse(readFileSync(process.env.CCT_CALENDAR_PROFILE_FILE??new URL('./calendar-profile.local.json',import.meta.url),'utf8'));
const proof={login_id:id(9),cookie_digest:'a'.repeat(64)};
function setup(overrides={},startEnabled=true){
  const calls=[];
  const pool={async connect(){return {async query(q){
    calls.push({text:q.text,args:q.values?.[0]});
    if(q.text==='COMMIT'&&overrides.commitError)throw new Error('lost ACK');
    const name=/^SELECT polygon\.([a-z0-9_]+)/.exec(q.text)?.[1];if(!name)return {rows:[]};
    const replies={current_identity:identity(),c04_save:{http:201,command_ref:ref(),receipt:receipt()},q03_draft:draft(),c05_validate:review(),
      c06_prepare:{http:200,prepared:true,ticket_id:id(90),started_at:at,iana_timezone:'Europe/Warsaw'},
      c06_finish:{http:201,command_ref:ref('C06'),receipt:receipt('C06')},q04_session:session(),...overrides};
    return {rows:[{reply:replies[name]}]};
  },release(){}};}};
  return {service:new PaperService({pool,calendar,startEnabled,cursor:{page(){throw new Error('not used');}}}),calls};
}
test('save encodes raw privately, returns original receipt, and commits only after decoding current navigation',async()=>{
  const {service,calls}=setup();const body=request();body.rawBudget='\0';
  const reply=await service.execute(proof,{kind:'save',draftId:null,body});
  assert.equal(reply.status,201);assert.equal(reply.body.receipt.result.draftId,id(20));
  const call=calls.find(c=>c.text.includes('polygon.c04_save'));const privateBody=JSON.parse(call.args);
  assert.equal(privateBody.raw_encoding,'utf8-base64-v1');assert.equal(privateBody.request.rawBudget,'AA==');
  assert.equal(calls.at(-1).text,'COMMIT');
});
test('validate persists own review and does not fabricate CommandReceipt',async()=>{
  const {service,calls}=setup();const reply=await service.execute(proof,{kind:'validate',body:{requestSchemaVersion:'v1',draftId:id(20),expectedDraftVersion:'1',proposedTimezone:'Europe/Warsaw'}});
  assert.equal(reply.status,200);assert.equal(reply.body.review.reviewId,id(22));assert.ok(!('receipt'in reply.body));
  assert.equal(calls.at(-1).text,'COMMIT');
});
test('start prepares/calculates/finishes in one transaction with exact profile metadata',async()=>{
  const {service,calls}=setup();const reply=await service.execute(proof,{kind:'start',body:{requestSchemaVersion:'v1',clientCommandId:id(71),reviewId:id(22),expectedDraftVersion:'1',expectedSlot:{state:'absent'}}});
  assert.equal(reply.status,201);assert.equal(reply.body.nextAction,'view_session');
  const finish=JSON.parse(calls.find(c=>c.text.includes('polygon.c06_finish')).args);
  assert.equal(finish.evaluation_deadline_at,'2026-11-18T10:00:00.000Z');assert.equal(finish.timezone_database_version,calendar.tzdb);
  assert.equal(finish.deadline_calculation_version,'paper-evaluation-deadline-v1');assert.equal(finish.ticket_id,id(90));
  assert.equal(calls.filter(c=>c.text==='BEGIN ISOLATION LEVEL SERIALIZABLE').length,1);
});
test('disabled START does not obtain a connection or create a ticket',async()=>{
  const {service,calls}=setup({},false);const reply=await service.execute(proof,{kind:'start',body:{requestSchemaVersion:'v1',clientCommandId:id(71),reviewId:id(22),expectedDraftVersion:'1',expectedSlot:{state:'absent'}}});
  assert.equal(reply.status,503);assert.equal(calls.length,0);
});
test('unknown COMMIT emits only error and original commandRef, never receipt or a new key',async()=>{
  const {service,calls}=setup({commitError:true});const reply=await service.execute(proof,{kind:'save',draftId:null,body:request()});
  assert.equal(reply.status,503);assert.equal(reply.body.reasonCode,'SERVICE_UNAVAILABLE');assert.ok(!('receipt'in reply.body));
  assert.deepEqual(reply.body.nextActionParams.commandRef,ref());assert.equal(reply.body.nextAction,'resolve_command');
  assert.equal(calls.filter(c=>c.text.includes('polygon.c04_save')).length,1);
});
test('malformed prepared result and corrupt owned session are technical failures before COMMIT',async()=>{
  const {service,calls}=setup({c06_prepare:{http:200,prepared:true,ticket_id:id(90),started_at:'bad',iana_timezone:'UTC'}});
  const reply=await service.execute(proof,{kind:'start',body:{requestSchemaVersion:'v1',clientCommandId:id(71),reviewId:id(22),expectedDraftVersion:'1',expectedSlot:{state:'absent'}}});
  assert.equal(reply.status,503);assert.ok(!calls.some(c=>c.text==='COMMIT'));
  const bad=session();delete bad.session.financialSnapshot;
  const x=setup({q04_session:bad});const read=await x.service.execute(proof,{kind:'session',sessionId:null});
  assert.equal(read.body.reasonCode,'RECORD_UNAVAILABLE');assert.ok(!('session'in read.body));
});
