import test from 'node:test';
import assert from 'node:assert/strict';
import {parseListRequest, parseCardRequest, decodeTrader, decodePage, availability} from '../src/catalog/contracts.ts';

const id = n => `${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const trader = (n=1) => ({traderId:id(n),venueId:id(10),catalogSourceId:id(11),venueCode:'polymarket',
  externalTraderId:'synthetic-trader-'+n,displayName:'Синтетический трейдер',traderRevisionId:id(100+n),traderRevision:'1',
  dataOrigin:'synthetic',sourceRef:'fixture:catalog:1',observedAt:'2026-11-04T10:00:00.000Z',revisionCreatedAt:'2026-11-04T10:01:00.000Z',
  catalogVersionAtCreation:'1',catalogVersion:'2',traderControlVersion:'3',paperControlVersion:'4',startAvailability:{available:true,capabilityReasonCode:null}});
const invalid = fn => assert.throws(fn,e => e.status===400 && e.reasonCode==='INVALID_REQUEST');
const corrupt = fn => assert.throws(fn,e => e.status===503 && e.reasonCode==='RECORD_UNAVAILABLE');
const prefix='requestSchemaVersion=v1&venueCode=polymarket';

test('list defaults, both venues, and boundary limits',()=>{
  assert.deepEqual(parseListRequest(prefix),{venueCode:'polymarket',limit:20});
  assert.equal(parseListRequest(prefix+'&limit=1').limit,1);
  assert.equal(parseListRequest(prefix+'&limit=50').limit,50);
  assert.equal(parseListRequest('requestSchemaVersion=v1&venueCode=limitless').venueCode,'limitless');
});
test('duplicates after decoding, unknown filters, malformed UTF8 and GET bodies rejected',()=>{
  for(const q of [prefix+'&venue%43ode=limitless',prefix+'&offset=1',prefix+'&cursor=%ff',prefix+'&cursor=%',prefix+'&limit=20&limit=20',prefix+'&']) invalid(()=>parseListRequest(q));
  invalid(()=>parseListRequest(prefix,1));
});
test('limit accepts canonical decimal only; empty cursor is not absent',()=>{
  for(const v of ['', '0','01','51','+1',' 1','1.0','1e1','١']) invalid(()=>parseListRequest(prefix+'&limit='+encodeURIComponent(v)));
  for(const v of ['', 'a=', 'a/b', 'a'.repeat(2049)]) invalid(()=>parseListRequest(prefix+'&cursor='+encodeURIComponent(v)));
});
test('card path has exact venue and UUID, query has no client identity',()=>{
  assert.deepEqual(parseCardRequest('polymarket',id(1),'requestSchemaVersion=v1'),{venueCode:'polymarket',traderId:id(1)});
  invalid(()=>parseCardRequest('other',id(1),'requestSchemaVersion=v1'));
  invalid(()=>parseCardRequest('polymarket',id(1),'requestSchemaVersion=v1&userId='+id(2)));
});
test('disable priority preserves visible cards and is not personal authorization',()=>{
  assert.equal(availability(false,false,false).capabilityReasonCode,'PAPER_START_DISABLED');
  assert.equal(availability(true,false,false).capabilityReasonCode,'CATALOG_SOURCE_DISABLED');
  assert.equal(availability(true,true,false).capabilityReasonCode,'TRADER_START_DISABLED');
  assert.deepEqual(availability(true,true,true),{available:true,capabilityReasonCode:null});
  corrupt(()=>availability(null,true,true));
});
test('bigint versions never round through JS number',()=>{
  const t=trader();t.catalogVersion='9223372036854775807';assert.equal(decodeTrader(t,'polymarket').catalogVersion,t.catalogVersion);
  for(const v of ['0','01','9223372036854775808',1,null]) corrupt(()=>decodeTrader({...t,catalogVersion:v},'polymarket'));
});
test('missing revision, foreign venue, unknown fields and invalid origin are corrupt, not empty',()=>{
  const t=trader();delete t.traderRevisionId;corrupt(()=>decodeTrader(t,'polymarket'));
  corrupt(()=>decodeTrader(trader(),'limitless'));
  corrupt(()=>decodeTrader({...trader(),score:99},'polymarket'));
  corrupt(()=>decodeTrader({...trader(),dataOrigin:'live'},'polymarket'));
});
test('timestamp validates calendar and exact milliseconds, availability null is conditional',()=>{
  for(const v of ['2026-02-30T10:00:00.000Z','2026-11-04T10:00:00Z','2026-11-04T10:00:00.000+00:00']) corrupt(()=>decodeTrader({...trader(),observedAt:v},'polymarket'));
  corrupt(()=>decodeTrader({...trader(),startAvailability:{available:false,capabilityReasonCode:null}},'polymarket'));
  corrupt(()=>decodeTrader({...trader(),displayName:'\uD800'},'polymarket'));
});
test('full final page is legal; continuation needs exact page size',()=>{
  const req={venueCode:'polymarket',limit:2};
  assert.equal(decodePage({venueCode:'polymarket',items:[trader(1),trader(2)],nextCursor:null},req).items.length,2);
  corrupt(()=>decodePage({venueCode:'polymarket',items:[trader(1)],nextCursor:'abc'},req));
});
test('only first allowed empty page is legal; corruption never becomes empty',()=>{
  assert.deepEqual(decodePage({venueCode:'polymarket',items:[],nextCursor:null},{venueCode:'polymarket',limit:20}).items,[]);
  corrupt(()=>decodePage({venueCode:'polymarket',items:[],nextCursor:null},{venueCode:'polymarket',limit:20,cursor:'abc'}));
  corrupt(()=>decodePage({venueCode:'polymarket',items:null,nextCursor:null},{venueCode:'polymarket',limit:20}));
});
test('duplicate/out-of-order identities and mixed snapshot guards are rejected',()=>{
  for(const rows of [[trader(2),trader(1)],[trader(1),trader(1)],[trader(1),{...trader(2),paperControlVersion:'5'}]])
    corrupt(()=>decodePage({venueCode:'polymarket',items:rows,nextCursor:null},{venueCode:'polymarket',limit:20}));
});
test('one source cannot expose two current catalog guard versions',()=>{
  corrupt(()=>decodePage({venueCode:'polymarket',items:[trader(1),{...trader(2),catalogVersion:'3'}],nextCursor:null},
    {venueCode:'polymarket',limit:20}));
});
test('one current revision cannot belong to two trader identities',()=>{
  corrupt(()=>decodePage({venueCode:'polymarket',items:[trader(1),{...trader(2),traderRevisionId:trader(1).traderRevisionId}],nextCursor:null},
    {venueCode:'polymarket',limit:20}));
});
