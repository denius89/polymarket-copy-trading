import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const modulePath = process.argv[2];
if (!modulePath) throw new Error('Pass the local PGlite module entry point as the first argument');
const { PGlite } = await import(pathToFileURL(resolve(modulePath)).href);
const dataDir = await mkdtemp(join(tmpdir(), 'cct-provisioning-'));
const seed = new PGlite({dataDir});
await seed.exec('CREATE DATABASE shadow_v00');
await seed.close();
const db = new PGlite({dataDir,database:'shadow_v00'});
const migration = file => readFile(new URL(file, import.meta.url), 'utf8');
const uuid = n => '00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const wallet = n => '0x'+String(n).padStart(40,'0');
try {
await db.exec(`
  CREATE ROLE polygon_owner;
  CREATE ROLE polygon_executor;
  CREATE ROLE activation_worker;
  CREATE ROLE provisioner;
  CREATE SCHEMA polygon AUTHORIZATION polygon_owner;
  CREATE SCHEMA polygon_live AUTHORIZATION polygon_owner;
  CREATE SCHEMA demo_delivery AUTHORIZATION polygon_owner;
  SET ROLE polygon_owner;
  CREATE TABLE polygon_live.installation (singleton boolean, database_name text, operator_run_id uuid);
  INSERT INTO polygon_live.installation VALUES (true,current_database(),'${uuid(1)}');
  CREATE TABLE demo_delivery.pilot_marker(kind text);
  INSERT INTO demo_delivery.pilot_marker VALUES ('isolated-public-market-pilot-v1');
  CREATE TABLE demo_delivery.subscriptions(session_id uuid PRIMARY KEY,venue text,trader_key text);
  CREATE TABLE demo_delivery.start_receipts(outbox_id uuid PRIMARY KEY,session_id uuid UNIQUE,venue text,wallet text,trader_revision_id uuid);
  CREATE TABLE demo_delivery.session_writers(session_id uuid PRIMARY KEY,writer_oid oid);
  CREATE TABLE demo_delivery.fixture_writer(session_id uuid PRIMARY KEY,venue text,writer_oid oid);
  CREATE TABLE polygon.paper_sessions(id uuid PRIMARY KEY,trader_revision_id uuid,user_id uuid,slot_id uuid,current_settings_revision_id uuid,lifecycle text,evaluation_deadline_at timestamptz);
  CREATE TABLE polygon.user_session_slots(id uuid PRIMARY KEY,user_id uuid,current_session_id uuid);
  CREATE TABLE polygon.settings_revisions(id uuid PRIMARY KEY,session_id uuid,sizing_mode text,fixed_n bigint,fixed_d bigint);
  CREATE FUNCTION demo_delivery.app_subscription_current(sid uuid) RETURNS boolean LANGUAGE sql
    SET search_path=pg_catalog AS $$SELECT EXISTS (
      SELECT FROM polygon.paper_sessions s JOIN polygon.user_session_slots sl
        ON (sl.id,sl.user_id,sl.current_session_id)=(s.slot_id,s.user_id,s.id)
      WHERE s.id=sid AND s.lifecycle='active' AND s.evaluation_deadline_at>clock_timestamp()
    )$$;
  CREATE FUNCTION demo_delivery.app_financial_writer(sid uuid, p_venue text) RETURNS oid LANGUAGE sql
    SET search_path=pg_catalog AS $$SELECT writer_oid FROM demo_delivery.fixture_writer WHERE session_id=sid AND venue=p_venue$$;
  CREATE FUNCTION demo_delivery.consume_ready_demo_sessions() RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
  CREATE FUNCTION demo_delivery.consume_confirmed_starts() RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
  CREATE FUNCTION demo_delivery.bind_confirmed_writers() RETURNS int LANGUAGE sql AS $$ SELECT 0 $$;
  RESET ROLE;
`);
await db.exec(await migration('closed-demo-activation.sql'));
await db.exec(await migration('closed-demo-runtime-profile.sql'));
await db.exec(await migration('closed-demo-provisioning.sql'));
for (const [n, venue, active, subscriptionMatches] of [
  [10,'polymarket',true,true],[11,'limitless',true,true],
  [12,'polymarket',false,true],[13,'limitless',true,false],[14,'polymarket',true,true]
]){
  const sid=uuid(n), owner=uuid(n+100), slot=uuid(n+200), revision=uuid(n+300), settings=uuid(n+400);
  if (n!==14) await db.query('INSERT INTO polygon.user_session_slots VALUES ($1,$2,$3)',[slot,owner,sid]);
  await db.query('INSERT INTO polygon.paper_sessions VALUES ($1,$2,$3,$4,$5,$6,now()+interval \'10 minutes\')',[sid,revision,owner,slot,settings,active?'active':'ended']);
  await db.query('INSERT INTO polygon.settings_revisions VALUES ($1,$2,\'fixed\',10,1)',[settings,sid]);
  await db.query('INSERT INTO demo_delivery.subscriptions VALUES ($1,$2,$3)',[sid,venue,subscriptionMatches ? wallet(n) : wallet(n+800)]);
  await db.query('INSERT INTO demo_delivery.start_receipts VALUES ($1,$2,$3,$4,$5)',[uuid(n+500),sid,venue,wallet(n),revision]);
  if ([10,11,12,13,14].includes(n)) await db.query(
    'INSERT INTO demo_delivery.activation_requests (request_id,session_id,attempt_after) VALUES ($1,$2,now()-interval \'1 minute\')',[uuid(n+500),sid]);
}
await db.exec(`
  GRANT USAGE ON SCHEMA demo_delivery TO activation_worker,provisioner,polygon_executor;
  GRANT EXECUTE ON FUNCTION demo_delivery.pending_demo_assignments(text) TO provisioner;
  GRANT EXECUTE ON FUNCTION demo_delivery.claim_activation(text[]),demo_delivery.claim_activation(),
    demo_delivery.finish_activation(uuid,uuid,uuid),demo_delivery.activation_runtime_profile(uuid,uuid) TO activation_worker;
  SET ROLE provisioner;
`);
const rows = async (sql,args=[]) => (await db.query(sql,args)).rows;
const scalar = async (sql,args=[]) => Object.values((await rows(sql,args))[0])[0];
const pending = venue => rows('SELECT * FROM demo_delivery.pending_demo_assignments($1)',[venue]);
const scope=['polymarket','limitless'];
assert.deepEqual((await pending('polymarket')).map(x=>x.request_id),[uuid(510)]);
assert.deepEqual((await pending('limitless')).map(x=>x.request_id),[uuid(511)]);
assert.deepEqual(await pending('invalid'),[]);
assert.equal((await pending('polymarket'))[0].request_id,uuid(510));
await assert.rejects(scalar('SELECT demo_delivery.claim_activation($1::text[])',[scope]),/permission denied/);
await db.exec('SET ROLE polygon_executor');
await assert.rejects(pending('polymarket'),/permission denied/);
await assert.rejects(scalar('SELECT demo_delivery.claim_activation($1::text[])',[scope]),/permission denied/);
await db.exec('SET ROLE activation_worker');
const claim = () => scalar('SELECT demo_delivery.claim_activation($1::text[])',[scope]);
assert.equal(await claim(),null);
await assert.rejects(scalar("SELECT demo_delivery.claim_activation(ARRAY['invalid'])"),/Invalid activation broker venues/);
await db.exec('RESET ROLE');
const assign = sid => db.query("INSERT INTO demo_delivery.fixture_writer VALUES ($1,$2,'activation_worker'::regrole::oid)",sid);
const bind = sid => db.query("INSERT INTO demo_delivery.session_writers VALUES ($1,'activation_worker'::regrole::oid)",[sid]);
await assign([uuid(11),'limitless']);
await db.exec('SET ROLE activation_worker');
assert.equal(await claim(),null);
await db.exec('RESET ROLE');
await bind(uuid(11));
for (const [n,venue] of [[12,'polymarket'],[13,'limitless'],[14,'polymarket']]) {
  await assign([uuid(n),venue]);
  await bind(uuid(n));
}
await db.exec('SET ROLE activation_worker');
const ll=await claim();
assert.equal(ll.requestId,uuid(511));
assert.equal(await scalar('SELECT demo_delivery.activation_runtime_profile($1,$2)',[ll.requestId,uuid(6)]),null);
assert.equal((await scalar('SELECT demo_delivery.activation_runtime_profile($1,$2)',[ll.requestId,ll.token])).venue,'limitless');
assert.equal(await scalar('SELECT demo_delivery.finish_activation($1,$2,$3)',[ll.requestId,ll.token,uuid(4)]),true);
assert.equal(await scalar('SELECT demo_delivery.finish_activation($1,$2,$3)',[ll.requestId,ll.token,uuid(5)]),false);
assert.equal(await claim(),null);
await db.exec('RESET ROLE');
await assign([uuid(10),'polymarket']);
await bind(uuid(10));
await db.exec('SET ROLE activation_worker');
const pm=await claim();
assert.equal(pm.requestId,uuid(510));
assert.equal((await scalar('SELECT demo_delivery.activation_runtime_profile($1,$2)',[pm.requestId,pm.token])).venue,'polymarket');
assert.equal(await scalar('SELECT demo_delivery.finish_activation($1,$2,$3)',[pm.requestId,pm.token,uuid(5)]),true);
await db.exec('SET ROLE provisioner');
assert.deepEqual(await pending('polymarket'),[]);
assert.deepEqual(await pending('limitless'),[]);
await db.exec('SET ROLE activation_worker');
assert.equal(await claim(),null);
await db.exec('RESET ROLE');
await db.query('DELETE FROM demo_delivery.activation_requests WHERE request_id NOT IN ($1,$2)',[uuid(510),uuid(511)]);
await db.query('UPDATE demo_delivery.activation_requests SET activated_at=NULL,worker_instance=NULL WHERE request_id=$1',[uuid(510)]);
await db.query('DELETE FROM demo_delivery.session_writers WHERE session_id=$1',[uuid(10)]);
await db.query('DELETE FROM demo_delivery.fixture_writer WHERE session_id=$1',[uuid(10)]);
await db.exec('SET ROLE activation_worker');
assert.equal(await claim(),null);
assert.equal((await scalar('SELECT demo_delivery.claim_activation()')).requestId,uuid(510));
console.log('PASS both venues, current slot and matching subscription, stable C06 provisioning, broker readiness, scoped grant, lease and replay, legacy claim');
} catch (error) {
  console.error(error.message,error.detail??'',error.where??'', error.stack);
  process.exitCode=1;
} finally {
  await db.close();
  await rm(dataDir,{recursive:true,force:true});
}
