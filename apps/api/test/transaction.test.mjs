import test from 'node:test';
import assert from 'node:assert/strict';
import { withPolygonTransaction, StorageUnavailable, StorageRecordUnavailable, RpcRefusal } from '../src/storage/transaction.ts';

function fixture(behavior = () => undefined) {
  const queries = [], releases = [];
  let connections = 0;
  const pool = {async connect() {
    const connection = ++connections;
    return {async query(q) {
      queries.push({connection, text: q.text, values: q.values, timeout: q.query_timeout});
      const custom = await behavior(q, connection);
      return custom ?? {rows: q.text.startsWith('SELECT polygon.') ? [{reply: {http: 200, value: 'ok'}}] : []};
    }, release(destroy) { releases.push({connection, destroy}); }};
  }};
  return {pool, queries, releases, connections: () => connections};
}
const auth = {login_id: '11111111-1111-4111-8111-111111111111', cookie_digest: 'a'.repeat(64)};

test('one client, Serializable, parameters and COMMIT acknowledgement before returning success', async () => {
  let acknowledge;
  const wait = new Promise(resolve => { acknowledge = resolve; });
  const f = fixture(q => q.text === 'COMMIT' ? wait : undefined);
  let returned = false;
  const pending = withPolygonTransaction(f.pool, 'command', async tx => {
    await tx.call('c06_prepare', {auth, request: {}});
    return tx.call('c06_finish', {auth, ticket_id: 'prepared'});
  }).then(r => {returned = true; return r;});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(returned, false);
  assert.equal(f.connections(), 1);
  assert.equal(f.queries[0].text, 'BEGIN ISOLATION LEVEL SERIALIZABLE');
  assert.equal(f.queries.at(-1).text, 'COMMIT');
  assert.ok(f.queries.every(q => q.connection === 1 && q.timeout > 0 && q.timeout <= 5000));
  assert.ok(f.queries.filter(q => q.text.startsWith('SELECT polygon.')).every(q => q.text.includes('$1::jsonb') && !q.text.includes(auth.cookie_digest)));
  acknowledge({rows: []});
  assert.equal((await pending).http, 200);
  assert.deepEqual(f.releases, [{connection: 1, destroy: false}]);
});

test('COMMIT connection loss never retries or returns the proposed result', async () => {
  const f = fixture(q => {if (q.text === 'COMMIT') throw Object.assign(new Error('sensitive driver message'), {code: 'ECONNRESET'});});
  await assert.rejects(withPolygonTransaction(f.pool, 'command', tx => tx.call('c04_save', {auth})), e =>
    e instanceof StorageUnavailable && e.outcome === 'unknown' && !e.message.includes('sensitive'));
  assert.equal(f.connections(), 1);
  assert.equal(f.queries.filter(q => q.text === 'ROLLBACK').length, 0);
  assert.deepEqual(f.releases, [{connection: 1, destroy: true}]);
});

for (const stage of ['SELECT polygon.c04_save', 'COMMIT']) test(`confirmed serialization rollback at ${stage} permits bounded retry`, async () => {
  const f = fixture((q, n) => {if (n === 1 && q.text.startsWith(stage)) throw Object.assign(new Error(), {code: '40001'});});
  await withPolygonTransaction(f.pool, 'command', tx => tx.call('c04_save', {auth}));
  assert.equal(f.connections(), 2);
  assert.ok(f.queries.some(q => q.connection === 1 && q.text === 'ROLLBACK'));
  assert.equal(f.queries.filter(q => q.text.startsWith('SELECT polygon.')).length, 2);
});

test('deadlock stops after three attempts; read never internally retries', async () => {
  const f = fixture(q => {if (q.text.startsWith('SELECT polygon.')) throw Object.assign(new Error(), {code: '40P01'});});
  await assert.rejects(withPolygonTransaction(f.pool, 'command', tx => tx.call('c04_save', {auth})), StorageUnavailable);
  assert.equal(f.connections(), 3);
  const read = fixture(q => {if (q.text.startsWith('SELECT polygon.')) throw Object.assign(new Error(), {code: '40001'});});
  await assert.rejects(withPolygonTransaction(read.pool, 'read', tx => tx.call('q04_session', {auth})), StorageUnavailable);
  assert.equal(read.connections(), 1);
});

test('failed rollback and unique violation are not retry signals', async () => {
  const f = fixture(q => {
    if (q.text.startsWith('SELECT polygon.')) throw Object.assign(new Error(), {code: '40001'});
    if (q.text === 'ROLLBACK') throw new Error('lost connection');
  });
  await assert.rejects(withPolygonTransaction(f.pool, 'command', tx => tx.call('c04_save', {auth})), StorageUnavailable);
  assert.equal(f.connections(), 1);
  assert.equal(f.releases[0].destroy, true);
  const unique = fixture(q => {if (q.text.startsWith('SELECT polygon.')) throw Object.assign(new Error(), {code: '23505'});});
  await assert.rejects(withPolygonTransaction(unique.pool, 'command', tx => tx.call('c04_save', {auth})), StorageUnavailable);
  assert.equal(unique.connections(), 1);
});

test('early finish refusal rolls back the prepared START, without COMMIT or retry', async () => {
  const f = fixture(q => q.text.includes('polygon.c06_finish') ? {rows: [{reply: {http: 503, reason: 'SERVICE_UNAVAILABLE'}}]} : undefined);
  await assert.rejects(withPolygonTransaction(f.pool, 'command', async tx => {
    await tx.call('c06_prepare', {auth});
    return tx.call('c06_finish', {auth});
  }), RpcRefusal);
  assert.equal(f.queries.at(-1).text, 'ROLLBACK');
  assert.ok(!f.queries.some(q => q.text === 'COMMIT'));
  assert.equal(f.connections(), 1);
});

test('stored business rejection is a committed result, not an early transport failure', async () => {
  const f = fixture(q => q.text.startsWith('SELECT polygon.') ? {rows: [{reply: {http: 409, receipt: {outcome: 'rejected'}}}]} : undefined);
  const reply = await withPolygonTransaction(f.pool, 'command', tx => tx.call('c04_save', {auth}));
  assert.equal(reply.http, 409);
  assert.equal(f.queries.at(-1).text, 'COMMIT');
});

test('corrupt RPC envelope and operation decoder failure rollback, not empty success', async () => {
  const f = fixture(q => q.text.startsWith('SELECT polygon.') ? {rows: [{reply: {http: 200, reason: 'ACCESS_DENIED'}}]} : undefined);
  await assert.rejects(withPolygonTransaction(f.pool, 'read', tx => tx.call('q04_session', {auth})), StorageRecordUnavailable);
  assert.equal(f.queries.at(-1).text, 'ROLLBACK');
  const decoder = fixture();
  await assert.rejects(withPolygonTransaction(decoder.pool, 'command', async tx => {
    await tx.call('c04_save', {auth}); throw new StorageRecordUnavailable();
  }), StorageRecordUnavailable);
  assert.equal(decoder.queries.at(-1).text, 'ROLLBACK');
});

test('allowlist blocks identifier injection and read mode cannot write', async () => {
  for (const fn of ['c04_save); DROP TABLE x; --', 'c04_save']) {
    const f = fixture();
    await assert.rejects(withPolygonTransaction(f.pool, 'read', tx => tx.call(fn, {auth})), StorageUnavailable);
    assert.ok(!f.queries.some(q => q.text.startsWith('SELECT polygon.')));
  }
});

test('late connection after pool-wait deadline is destroyed and never used', async t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  let resolve;
  const releases = [];
  const connection = new Promise(r => {resolve = r;});
  const pending = withPolygonTransaction({connect: () => connection}, 'read', () => assert.fail('must not run'));
  const check = assert.rejects(pending, StorageUnavailable);
  t.mock.timers.tick(5001);
  await check;
  resolve({release: destroy => releases.push(destroy), query: () => assert.fail('must not query')});
  await new Promise(r => setImmediate(r));
  assert.deepEqual(releases, [true]);
});
