import test from 'node:test';
import assert from 'node:assert/strict';
import { money, decodeCommand, decodeReview, decodeDraft, decodeSession, fieldErrors } from '../src/paper/responses.ts';
import { StorageRecordUnavailable } from '../src/storage/transaction.ts';
import { id, M, ref, receipt, draft, review, session } from './paper-fixtures.mjs';
const corrupt=fn=>assert.throws(fn,StorageRecordUnavailable);
test('canonical rational amounts reject rounded numbers, unreduced fractions and invalid zero',()=>{
  assert.ok(money({n:'1',d:'3'}));assert.ok(money(M(0)));
  for(const x of [{n:1,d:3},{n:'2',d:'6'},{n:'0',d:'2'},{n:'1',d:'0'},{n:'01',d:'1'},{n:'-1',d:'1'},{n:'1'.repeat(65),d:'1'}])assert.equal(money(x),false);
});
test('C04/Q05 retain identical historical receipt and distinguish pending from missing receipt',()=>{
  const r=receipt(), expected={actorId:id(1),commandType:'C04',clientCommandId:id(70)};
  const direct=decodeCommand({http:201,command_ref:ref(),receipt:r},expected);
  const lookup=decodeCommand({http:200,command_ref:ref(),receipt:r,status:'committed'},expected,true);
  assert.deepEqual(direct.receipt,lookup.receipt);
  assert.equal(decodeCommand({http:202,command_ref:ref(),receipt:null,status:'pending'},expected,true).receipt,null);
  corrupt(()=>decodeCommand({http:200,command_ref:ref(),receipt:null,status:'committed'},expected,true));
  corrupt(()=>decodeCommand({http:201,command_ref:{...ref(),actorId:id(99)},receipt:r},expected));
  corrupt(()=>decodeCommand({http:200,command_ref:ref(),receipt:r},expected));
});
test('rejected result cannot carry fieldErrors or successful references, reasons keep priority and params',()=>{
  const r={...receipt(),outcome:'rejected',reasonCode:'DRAFT_USED',reasonDetails:[{code:'DRAFT_USED',params:{}}],result:null};delete r.fieldErrors;
  const expected={commandType:'C04',clientCommandId:id(70)};
  assert.equal(decodeCommand({http:409,command_ref:ref(),receipt:r},expected).receipt.reasonCode,'DRAFT_USED');
  corrupt(()=>decodeCommand({http:409,command_ref:ref(),receipt:{...r,fieldErrors:[]}},expected));
  corrupt(()=>decodeCommand({http:409,command_ref:ref(),receipt:{...r,reasonDetails:[{code:'DRAFT_USED',params:{draftId:id(20)}}]}},expected));
});
test('field error units/order/closed parameters and inactive sizing cannot be weakened',()=>{
  assert.doesNotThrow(()=>fieldErrors([{field:'rawBudget',code:'OUT_OF_RANGE',params:{min:M(100),max:M(1000),unit:'virtual_USD'}}],'fixed'));
  for(const errors of [
    [{field:'rawBudget',code:'INVALID_DECIMAL',params:{message:'raw'}}],
    [{field:'rawBudget',code:'OUT_OF_RANGE',params:{min:'100.00',max:'1000.00',unit:'percentage_points'}}],
    [{field:'rawBudget',code:'OUT_OF_RANGE',params:{min:M(1000),max:M(100),unit:'virtual_USD'}}],
    [{field:'rawCopyPercent',code:'REQUIRED',params:{}}],
    [{field:'rawBudget',code:'REQUIRED',params:{}},{field:'rawBudget',code:'INVALID_DECIMAL',params:{}}],
  ])corrupt(()=>fieldErrors(errors,'fixed'));
});
test('Q03 error provenance and raw are preserved; malformed encoding or wrong version is not empty success',()=>{
  const d=draft();d.draft.rawBudget=Buffer.from('\0 20.00 ').toString('base64');
  assert.equal(decodeDraft(d,id(20)).draft.rawBudget,'\0 20.00 ');
  corrupt(()=>decodeDraft({...d,field_errors_source:{receiptId:id(80),draftVersion:'2'}},id(20)));
  corrupt(()=>decodeDraft({...d,raw_encoding:undefined},id(20)));
});
test('review validates owner/version, conditional normalization and closed warnings',()=>{
  assert.equal(decodeReview(review(),id(1),id(20),'1').review.allowedToStart,true);
  corrupt(()=>decodeReview(review(),id(2),id(20),'1'));
  corrupt(()=>decodeReview(review(),id(1),id(20),'2'));
  const r=review();r.review.copyPercent='2.50';corrupt(()=>decodeReview(r,id(1),id(20),'1'));
  const n=review();n.review.normalizationValid=false;corrupt(()=>decodeReview(n,id(1),id(20),'1'));
  const w=review();w.review.warnings.push(w.review.warnings[0]);corrupt(()=>decodeReview(w,id(1),id(20),'1'));
});
test('Q04 validates same-session/version/settings and financial equalities without repairing data',()=>{
  assert.equal(decodeSession(session(),id(30)).session.summary.sessionId,id(30));
  assert.deepEqual(decodeSession({http:200,session:null},null),{session:null});
  corrupt(()=>decodeSession({http:200,session:null},id(30)));
  for(const mutate of [s=>s.financialSnapshot.sessionId=id(99),s=>s.financialSnapshot.snapshotVersion='2',
    s=>s.financialSnapshot.free=M(99),s=>s.financialSnapshot.tradingResult=M(1),s=>s.settings.settingsRevisionId=id(99),
    s=>delete s.financialSnapshot.equity,s=>s.summary.mode='live']){
    const v=session();mutate(v.session);corrupt(()=>decodeSession(v,null));
  }
});
