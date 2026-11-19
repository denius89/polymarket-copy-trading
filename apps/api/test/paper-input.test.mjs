import test from 'node:test';
import assert from 'node:assert/strict';
import { parseCommandJson, parseQuery, InputError } from '../src/http/input.ts';
import { c04Request, c05Request, c06Request, RAW_FIELDS } from '../src/paper/requests.ts';
import { encodeRaw, decodeRaw, RAW_ENCODING } from '../src/paper/raw-codec.ts';
import { StorageRecordUnavailable } from '../src/storage/transaction.ts';
const id = '11111111-1111-4111-8111-111111111111';
const bytes = value => Buffer.from(value, 'utf8');
const form = () => ({requestSchemaVersion:'v1',clientCommandId:id,locale:'ru',step:'configure',entryContext:null,
  venueId:null,traderId:null,selectedMode:'fixed',rawBudget:'100',rawFixedAmount:'5',rawCopyPercent:null,
  rawMarketLimitPercent:'10',rawDailyBuyLimitPercent:'20',proposedTimezone:'Europe/Warsaw'});

test('strict JSON rejects duplicate escaped names, invalid Unicode/UTF8, trailing tokens and syntax', () => {
  for (const source of ['{"a":1,"\\u0061":2}', '{"x":{"a":1,"a":2}}', '{"x":"\\ud800"}',
    '{"x":"\\udc00"}', '{"a":1,}', '[1,]', '{"a":01}', '{"a":1e999}', '{} true', '\ufeff{}',
    '{"x":"unescaped\nline"}', '{"x":"\\x"}']) {
    assert.throws(() => parseCommandJson(bytes(source)), InputError, source);
  }
  assert.throws(() => parseCommandJson(Uint8Array.from([0xc0,0x80])), InputError);
});
test('JSON byte/depth boundaries are exact and __proto__ never changes object prototype', () => {
  assert.deepEqual(Object.keys(parseCommandJson(bytes(' '.repeat(65534)+'{}'))), []);
  assert.throws(() => parseCommandJson(bytes(' '.repeat(65535)+'{}')), e => e.status === 413);
  assert.doesNotThrow(() => parseCommandJson(bytes('['.repeat(8)+'null'+']'.repeat(8))));
  assert.throws(() => parseCommandJson(bytes('['.repeat(9)+'null'+']'.repeat(9))), InputError);
  const obj = parseCommandJson(bytes('{"__proto__":{"polluted":true},"value":"\\u0000😀"}'));
  assert.equal(Object.getPrototypeOf(obj), null);
  assert.equal({}.polluted, undefined);
  assert.equal(obj.value, '\0😀');
});
test('C04 full form preserves all raw strings including inactive mode and NUL', () => {
  const f = form(); f.rawBudget=' 20,00 '; f.rawFixedAmount='\0'; f.rawCopyPercent='😀'.repeat(64);
  assert.equal(c04Request(f, false), f);
  assert.equal(c04Request({...f, expectedDraftVersion:'9223372036854775807'}, true).rawBudget, ' 20,00 ');
  for (const key of Object.keys(f)) {
    const missing={...f}; delete missing[key]; assert.throws(() => c04Request(missing,false), InputError, key);
  }
  for (const f of [{...form(),rawBudget:20},{...form(),rawCopyPercent:'😀'.repeat(65)},
    {...form(),rawBudget:'\ud800'}, {...form(),userId:id}, {...form(),expectedDraftVersion:'1'},
    {...form(),traderId:id}, {...form(),proposedTimezone:'+01:00'}]) {
    assert.throws(() => c04Request(f,false), InputError);
  }
});
test('C05 and C06 closed forms do not accept substituted settings, slots or keys', () => {
  const review={requestSchemaVersion:'v1',draftId:id,expectedDraftVersion:'1',proposedTimezone:null};
  assert.equal(c05Request(review),review);
  assert.throws(() => c05Request({...review,clientCommandId:id}), InputError);
  const start={requestSchemaVersion:'v1',clientCommandId:id,reviewId:id,expectedDraftVersion:'1',expectedSlot:{state:'absent'}};
  assert.equal(c06Request(start),start);
  assert.doesNotThrow(() => c06Request({...start,expectedSlot:{state:'present',generation:'1'}}));
  for (const slot of [{state:'absent',generation:null},{state:'present',generation:'0'},
    {state:'present',generation:1},{state:'not_applicable'},{state:'present'}]) {
    assert.throws(() => c06Request({...start,expectedSlot:slot}), InputError);
  }
});
test('query parsing checks decoded duplicates and required fields without normalization', () => {
  const keys=['requestSchemaVersion','actorRealm'];
  assert.equal(parseQuery('requestSchemaVersion=v1&actorRealm=user',keys).actorRealm,'user');
  for(const q of ['requestSchemaVersion=v1', 'requestSchemaVersion=v1&actorRealm=user&%61ctorRealm=user',
    'requestSchemaVersion=v1&actorRealm=%ff','requestSchemaVersion=v1&actorRealm=user&extra=1']) {
    assert.throws(()=>parseQuery(q,keys), InputError);
  }
});
test('private raw codec is exact for null/empty/NUL/BOM/Unicode and distinct numeric spellings', () => {
  for(const raw of [null,'','\0','\ufeff20','😀'.repeat(64),'é','e\u0301','20','20.00','20,000',' 20 ']) {
    const f=form(); for(const field of RAW_FIELDS)f[field]=raw;
    const encoded=encodeRaw(f);
    assert.deepEqual(decodeRaw(encoded,RAW_ENCODING),f);
    assert.equal(f.rawBudget,raw);
  }
  assert.notEqual(encodeRaw({...form(),rawBudget:'20'}).rawBudget,encodeRaw({...form(),rawBudget:'20.00'}).rawBudget);
});
test('private codec rejects malformed base64, Unicode and missing markers rather than empty fallback', () => {
  const f=encodeRaw(form());
  for(const raw of ['YQ','YQ=','YR==','Y Q==','YQ==\n','//==','7aCA',Buffer.from('😀'.repeat(65)).toString('base64')]) {
    assert.throws(()=>decodeRaw({...f,rawBudget:raw},RAW_ENCODING),StorageRecordUnavailable,raw);
  }
  const missing={...f}; delete missing.rawBudget;
  assert.throws(()=>decodeRaw(missing,RAW_ENCODING),StorageRecordUnavailable);
  assert.throws(()=>decodeRaw(f,undefined),StorageRecordUnavailable);
  assert.throws(()=>encodeRaw({...form(),rawBudget:'\ud800'}),InputError);
});
