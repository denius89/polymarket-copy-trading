import test from 'node:test';
import assert from 'node:assert/strict';
import sodium from 'libsodium-wrappers';
import { decodeSnapshot, canonical } from '../src/catalog/snapshot.ts';
import { createCursorCodec } from '../src/catalog/cursor.ts';
import { StorageRecordUnavailable, StorageUnavailable } from '../src/storage/transaction.ts';

const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
function source() {
  const traders=[1,2,3].map(n=>({traderId:id(n),version:'3',currentRevisionId:id(100+n),currentRevision:'1',readVisible:true,startAllowed:true}));
  return {http:200,read_binding:{environment:'test-only',realm:'user',read_context_id:id(50),scope_id:id(60),scope_revision:`q02-read-scope-v1:${id(60)}:1`},
    descriptor:{venueId:id(10),venueCode:'polymarket',paperControl:{id:id(20),version:'4',startEnabled:true},sources:[
      {sourceId:id(11),venueId:id(10),version:'2',readVisible:true,startEnabled:true,traders}]},
    items:traders.map(t=>({traderId:t.traderId,venueId:id(10),catalogSourceId:id(11),venueCode:'polymarket',externalTraderId:'synthetic-'+t.traderId,
      displayName:'Synthetic',traderRevisionId:t.currentRevisionId,traderRevision:'1',dataOrigin:'synthetic',sourceRef:'fixture:catalog:1',
      observedAt:'2026-11-04T10:00:00.000Z',revisionCreatedAt:'2026-11-04T10:01:00.000Z',catalogVersionAtCreation:'1',catalogVersion:'2',
      traderControlVersion:'3',paperControlVersion:'4',startAvailability:{available:true,capabilityReasonCode:null}}))};
}
// Deliberately public test keys; never used by runtime or provisioned as an operator key.
const firstId='01'.repeat(16), secondId='02'.repeat(16);
const firstKey=Uint8Array.from({length:32},(_,i)=>i), secondKey=new Uint8Array(32).fill(99);
const keyset=()=>({available:true,issuerKeyId:firstId,keys:new Map([[firstId,firstKey]]),revoked:new Set()});
const req={venueCode:'polymarket',limit:2};
const invalid=fn=>assert.throws(fn,e=>e.status===400);


test('manifest sorting is canonical, contains hidden guards, and is bound to permanent reader and scope',()=>{
  assert.equal(canonical({z:[true,null,'é'],a:1}),'{"a":1,"z":[true,null,"é"]}');
  const a=source(), b=source(); b.descriptor.sources[0].traders.reverse();b.items.reverse();
  assert.deepEqual(decodeSnapshot(a,'polymarket'),decodeSnapshot(b,'polymarket'));
  const before=decodeSnapshot(a,'polymarket');
  a.descriptor.sources[0].traders[0].readVisible=false; a.items.shift();
  const hidden=decodeSnapshot(a,'polymarket');
  a.descriptor.sources[0].traders[0].version='4';
  assert.notEqual(decodeSnapshot(a,'polymarket').catalogFingerprint,hidden.catalogFingerprint);
  b.read_binding.scope_revision=`q02-read-scope-v1:${id(60)}:2`;
  const changed=decodeSnapshot(b,'polymarket');
  assert.equal(changed.readerBinding,before.readerBinding);assert.notEqual(changed.catalogFingerprint,before.catalogFingerprint);
  b.read_binding.read_context_id=id(51);assert.notEqual(decodeSnapshot(b,'polymarket').readerBinding,before.readerBinding);
});
test('missing/extra visible data, duplicate hidden revision, foreign scope and malformed guards fail closed',()=>{
  const cases=[];
  let v=source();v.items.pop();cases.push(v);
  v=source();v.items[0].catalogVersion='3';cases.push(v);
  v=source();v.descriptor.sources[0].traders[1].currentRevisionId=id(101);cases.push(v);
  v=source();v.read_binding.scope_revision='1';cases.push(v);
  v=source();v.descriptor.sources[0].venueId=id(99);cases.push(v);
  v=source();v.descriptor.paperControl.version=4;cases.push(v);
  for(const x of cases)assert.throws(()=>decodeSnapshot(x,'polymarket'),StorageRecordUnavailable);
});
test('page boundary, ciphertext shell and exact canonical plaintext match the accepted format',async()=>{
  const codec=await createCursorCodec(keyset), snapshot=decodeSnapshot(source(),'polymarket');
  const page=codec.page(req,snapshot);
  assert.equal(page.items.length,2);assert.match(page.nextCursor,/^[A-Za-z0-9_-]{1,2048}$/);
  const wire=Buffer.from(page.nextCursor,'base64url'), header=wire.subarray(0,17);
  assert.equal(wire[0],1);assert.equal(wire.subarray(1,17).toString('hex'),firstId);
  const clear=sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(null,wire.subarray(41),Buffer.concat([Buffer.from('shadow.q02.cursor.v1\0'),header]),wire.subarray(17,41),firstKey);
  const p=JSON.parse(Buffer.from(clear).toString('utf8'));
  assert.equal(Object.keys(p).length,8);assert.equal(p.lastTraderId,id(2));assert.equal(p.limit,2);
  assert.equal(Buffer.from(clear).toString('utf8'),canonical(p));
  assert.ok(!('expiresAt'in p));assert.ok(!('issuedAt'in p));
  assert.ok(!wire.includes(Buffer.from('Synthetic')));
  const next=codec.page({...req,cursor:page.nextCursor},snapshot);
  assert.deepEqual(next.items.map(x=>x.traderId),[id(3)]);assert.equal(next.nextCursor,null);
  assert.deepEqual(codec.page({...req,limit:3},snapshot).nextCursor,null);
  assert.notEqual(codec.page(req,snapshot).nextCursor,page.nextCursor);
});
test('full final page and authentic empty first page need no continuation',async()=>{
  const codec=await createCursorCodec(keyset), raw=source();raw.items=[];raw.descriptor.sources[0].traders=[];
  assert.deepEqual(codec.page(req,decodeSnapshot(raw,'polymarket')),{venueCode:'polymarket',items:[],nextCursor:null});
});
test('tampering, noncanonical encoding and changed reader/limit are 400; changed permitted scope is 409',async()=>{
  const codec=await createCursorCodec(keyset), snapshot=decodeSnapshot(source(),'polymarket');
  const token=codec.page(req,snapshot).nextCursor;
  for(const offset of [0,1,17,41,Buffer.from(token,'base64url').length-1]) {
    const bytes=Buffer.from(token,'base64url');bytes[offset]^=1;
    invalid(()=>codec.page({...req,cursor:bytes.toString('base64url')},snapshot));
  }
  for(const bad of [token+'=',token+' ',token.slice(1),'a'.repeat(2049),'AB'])invalid(()=>codec.page({...req,cursor:bad},snapshot));
  invalid(()=>codec.page({...req,limit:1,cursor:token},snapshot));
  const other=source();other.read_binding.read_context_id=id(99);
  invalid(()=>codec.page({...req,cursor:token},decodeSnapshot(other,'polymarket')));
  const changed=source();changed.read_binding.scope_revision=`q02-read-scope-v1:${id(60)}:2`;
  assert.throws(()=>codec.page({...req,cursor:token},decodeSnapshot(changed,'polymarket')),e=>e.status===409&&e.reasonCode==='CATALOG_CHANGED');
});
test('rotation retains old readers, revocation rejects, unavailable key state never falls back',async()=>{
  let keys=keyset();const codec=await createCursorCodec(()=>keys),snapshot=decodeSnapshot(source(),'polymarket');
  const token=codec.page(req,snapshot).nextCursor;
  keys={...keys,issuerKeyId:secondId,keys:new Map([[firstId,firstKey],[secondId,secondKey]])};
  assert.equal(codec.page({...req,cursor:token},snapshot).items.length,1);
  keys={...keys,revoked:new Set([firstId])};invalid(()=>codec.page({...req,cursor:token},snapshot));
  keys={...keys,available:false};assert.throws(()=>codec.page(req,snapshot),StorageUnavailable);
});
