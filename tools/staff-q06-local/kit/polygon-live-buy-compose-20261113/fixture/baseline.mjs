import {readFile} from 'node:fs/promises';import {randomUUID,randomBytes,createHmac} from 'node:crypto';
const base=new URL('../../base-sql/',import.meta.url);
export async function loadSource(db,path){let sql=await readFile(path,'utf8');sql=sql.split('\n').filter(l=>!l.trimStart().startsWith('\\')).join('\n');await db.exec(sql)}
export async function baseline(db){
 for(const path of ['v00-session-db/001-storage.sql','v00-session-db/002-api.sql','v00-session-db/003-logout.sql','v00-session-db/004-observer.sql','v00-upstream-db/001-core.sql','polygon-paper-db/001-storage.sql','polygon-paper-db/002-guards-numbers.sql','polygon-paper-db/003-drafts-reviews.sql','polygon-paper-db/004-start.sql','polygon-paper-db/005-integrity.sql','polygon-paper-db/006-reads.sql'])await loadSource(db,new URL(path,base));
 await db.exec(`BEGIN ISOLATION LEVEL SERIALIZABLE;
 INSERT INTO polygon.profile VALUES(true,'shadow-polygon-synthetic-v1',true,'${process.env.FIXTURE_TZ}','24076847cf48c911eaa5fb21ca34b5969f89f109');
 INSERT INTO polygon.paper_policy_versions VALUES(gen_random_uuid(),1,100,1000,10,5,200,1,1,20,0.5,5,20,1,10,30,1,30,'paper-settings-calculation-v1');
 INSERT INTO polygon.paper_controls SELECT gen_random_uuid(),true,1,true,id FROM polygon.paper_policy_versions;
 INSERT INTO polygon.venues VALUES(gen_random_uuid(),'polymarket'),(gen_random_uuid(),'limitless');
 INSERT INTO polygon.catalog_sources SELECT gen_random_uuid(),id,1,true,true,'synthetic' FROM polygon.venues;
 INSERT INTO polygon.traders SELECT gen_random_uuid(),id,venue_id,1,true,true,gen_random_uuid(),'synthetic-trader' FROM polygon.catalog_sources;
 INSERT INTO polygon.trader_revisions SELECT current_revision_id,id,source_id,venue_id,'Synthetic trader','synthetic:fixture',clock_timestamp(),1,clock_timestamp(),1 FROM polygon.traders;
 COMMIT;`);
 const users=[];
 for(let n=0;n<2;n++){
  const actor=randomUUID(),uid=randomUUID(),scope=randomUUID(),ctx=randomUUID(),lid=randomUUID(),op=randomUUID();const proof=randomBytes(32).toString('base64url');const parts=['v00-d03-07','user',lid,'v00-test-login-cookie-v1',proof].flatMap(value=>{const x=Buffer.from(value);const n=Buffer.alloc(4);n.writeUInt32BE(x.length);return [n,x]});const digest=createHmac('sha256',Buffer.from(process.env.USER_KEY,'hex')).update(Buffer.concat([Buffer.from('shadow.v00.login-verify.v1\0'),...parts])).digest('hex');const auth={login_id:lid,cookie_digest:digest};
  await db.exec('BEGIN ISOLATION LEVEL SERIALIZABLE');
  await db.query('INSERT INTO v00_session.actors(id) VALUES($1)',[actor]);
  await db.query('INSERT INTO polygon.users VALUES($1,$2,clock_timestamp())',[uid,actor]);await db.query('INSERT INTO polygon.read_scopes VALUES($1,$2,1)',[scope,uid]);await db.query('INSERT INTO polygon.scope_sources SELECT $1,id FROM polygon.catalog_sources',[scope]);
  await db.query("INSERT INTO v00_session.contexts(id,actor_id,proof_digest,expires_at,login_expires_at,idle_expires_at) VALUES($1,$2,$3,clock_timestamp()+interval '1 day',clock_timestamp()+interval '1 day',clock_timestamp()+interval '1 day')",[ctx,actor,'c'.repeat(64)]);
  const p={context_id:ctx,proof_digest:'c'.repeat(64),operation_id:op,fingerprint:'d'.repeat(64)};
  for(const [name,r]of [['plan_completion',{...p,login_id:lid,secret_id:randomUUID()}],['complete',{...p,cookie_digest:digest,ciphertext:Buffer.alloc(16,1).toString('base64'),nonce:Buffer.alloc(24,2).toString('base64'),key_id:'synthetic-only',credential_key_id:'credential-1'}]]){const out=(await db.query(`SELECT v00_session.${name}($1) r`,[r])).rows[0].r;if(out.http!==200)throw Error(name+JSON.stringify(out))}
  await db.exec('COMMIT');users.push({uid,actor,auth,proof});
 }
 return users;
}
export async function start(db,user,traderId,rawBudget){
 const trader=(await db.query('SELECT * FROM polygon.traders WHERE id=$1',[traderId])).rows[0];await db.exec('BEGIN ISOLATION LEVEL SERIALIZABLE');
 const req={requestSchemaVersion:'v1',clientCommandId:randomUUID(),locale:'ru',step:'configure',entryContext:'catalog',venueId:trader.venue_id,traderId,selectedMode:'fixed',rawBudget,rawFixedAmount:'MTA=',rawCopyPercent:null,rawMarketLimitPercent:'MjA=',rawDailyBuyLimitPercent:'MTU=',proposedTimezone:'Europe/Warsaw'};
 const run=async(name,p)=>(await db.query(`SELECT polygon.${name}($1) r`,[p])).rows[0].r;
 const save=await run('c04_save',{auth:user.auth,draft_id:null,raw_encoding:'utf8-base64-v1',request:req});if(save.http!==201)throw Error(JSON.stringify(save));
 const review=await run('c05_validate',{auth:user.auth,request:{requestSchemaVersion:'v1',draftId:save.receipt.result.draftId,expectedDraftVersion:'1',proposedTimezone:'Europe/Warsaw'}});if(!review.review?.allowedToStart)throw Error(JSON.stringify(review));
 const pre=await run('c06_prepare',{auth:user.auth,request:{requestSchemaVersion:'v1',clientCommandId:randomUUID(),reviewId:review.review.reviewId,expectedDraftVersion:'1',expectedSlot:{state:'absent'}}});if(!pre.prepared)throw Error(JSON.stringify(pre));
 const result=await run('c06_finish',{auth:user.auth,ticket_id:pre.ticket_id,evaluation_deadline_at:new Date(Date.parse(pre.started_at)+7*86400000).toISOString(),deadline_calculation_version:'paper-evaluation-deadline-v1',timezone_database_version:process.env.FIXTURE_TZ});if(result.http!==201)throw Error(JSON.stringify(result));await db.exec('COMMIT');return result.receipt.result.sessionId;
}
export async function loadLive(db,users){
 const root=new URL('../../',import.meta.url);const run=randomUUID();const dbOid=(await db.query('SELECT oid FROM pg_database WHERE datname=current_database()')).rows[0].oid;const sqlDir=new URL('polygon-live-db-20261113/sql/',root);
 await db.exec('BEGIN ISOLATION LEVEL SERIALIZABLE; CREATE SCHEMA polygon_live AUTHORIZATION polygon_owner; CREATE TEMP TABLE live_install_input(database_name text,run_id uuid,provenance jsonb);');
 await db.query("INSERT INTO live_install_input VALUES(current_database(),$1,$2)",[run,{displayName:'Synthetic Q06 fixture',sourceRef:'https://fixture.invalid/synthetic',observedAt:new Date(Date.now()-1000).toISOString(),snapshotSha256:'0'.repeat(64)}]);
 await db.exec('GRANT SELECT ON live_install_input TO polygon_owner;SET LOCAL ROLE polygon_owner;');
 for(const f of ['002-storage.sql','003-initial-derived.sql','004-public-source.sql','005-integrity.sql','006-completion.sql','007-start-derived.sql','008-review-derived.sql','009-resolver-derived.sql','010-staff-derived.sql'])await loadSource(db,new URL(f,sqlDir));
 await db.exec('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon_live FROM PUBLIC;COMMIT;');
 for(const [index,user] of users.entries()) user.sid=await start(db,user,'6e91ae7c-a813-4b98-9bbc-022c0e04c2ff',index===0?'MzAw':'MjAw');
 const adir=new URL('polygon-live-db-20261113/activity-db/',root);
 await db.exec('BEGIN;CREATE SCHEMA polygon_live_activity AUTHORIZATION polygon_owner;CREATE TEMP TABLE live_activity_input(db text,run_id uuid);');await db.query('INSERT INTO live_activity_input VALUES(current_database(),$1)',[run]);await db.exec('GRANT SELECT ON live_activity_input TO polygon_owner;SET LOCAL ROLE polygon_owner;');
 for(const f of ['002-shapes.sql','002-installation.sql','003-storage-derived.sql','004-bound-contract.sql','005-guard.sql','006-runtime-derived.sql','007-ingest-derived.sql','008-integrity-derived.sql','009-bound-rpc-derived.sql','010-bound-integrity-derived.sql','011-item-derived.sql','012-wrappers.sql','013-read.sql'])await loadSource(db,new URL(f,adir));
 let release=await readFile(new URL('polygon-live-db-20261113/release-activation/001-pin-release.sql',root),'utf8');release=release.slice(release.indexOf('CREATE TABLE polygon_live_activity.release_record'),release.indexOf('INSERT INTO polygon_live_activity.release_record'));await db.exec(release);
 await db.query("INSERT INTO polygon_live_activity.release_record VALUES(true,current_database(),$1,$3,'1',$2,'operator-bounded-public-skip-v1',clock_timestamp())",[run,'0'.repeat(64),dbOid]);
 let patch=await readFile(new URL('polygon-live-resume-db-20261113/001-install.sql',root),'utf8');patch=patch.slice(patch.indexOf('CREATE TABLE polygon_live_activity.resume_patch'),patch.indexOf('\\ir 003-resume.sql'));await db.exec(patch);
 await loadSource(db,new URL('polygon-live-resume-db-20261113/003-resume.sql',root));await loadSource(db,new URL('polygon-live-resume-db-20261113/005-functions.sql',root));
 await db.exec('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon_live_activity FROM PUBLIC; REVOKE ALL ON ALL TABLES IN SCHEMA polygon_live_activity FROM PUBLIC;REVOKE ALL ON ALL FUNCTIONS IN SCHEMA polygon FROM PUBLIC;COMMIT;');
 for(const user of users){
  user.writer='polygon_live_writer_'+randomUUID().replaceAll('-','');await db.exec(`CREATE ROLE ${user.writer} LOGIN;GRANT USAGE ON SCHEMA polygon TO ${user.writer};GRANT EXECUTE ON FUNCTION polygon.live_activity_arm(jsonb),polygon.live_activity_ingest(jsonb),polygon.live_activity_stop(jsonb),polygon.live_activity_lookup(jsonb),polygon.live_activity_resume(jsonb) TO ${user.writer};`);
  await db.exec('BEGIN ISOLATION LEVEL SERIALIZABLE');
  await db.query(`INSERT INTO polygon_live_activity.assignments SELECT s.id,gen_random_uuid(),1,current_database(),$1,r.rolname,r.oid,s.user_id,s.source_id,s.venue_id,s.trader_id,s.trader_revision_id,t.external_trader_id,'polygon-137-ctfv2-orderfilled-owner-v1',clock_timestamp() FROM polygon.paper_sessions s JOIN polygon.traders t ON t.id=s.trader_id,pg_roles r WHERE s.id=$2 AND r.rolname=$3`,[run,user.sid,user.writer]);await db.exec('COMMIT');
 }
 // Installed resume baseline permits exactly one targeted session; original other session remains unbound.
 await db.query("INSERT INTO polygon_live_activity.resume_patch SELECT true,$1,$2,rolname,oid,$3,'explicit-clean-stop-resume-v1',clock_timestamp(),'{}'::jsonb FROM pg_roles WHERE rolname=$4",[users[0].sid,run,'0'.repeat(64),users[0].writer]);
 return {run,users};
}
