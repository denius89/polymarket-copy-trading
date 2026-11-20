import {readFile,writeFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';import {randomUUID,createHash} from 'node:crypto';import assert from 'node:assert/strict';
import {baseline,loadLive,loadSource} from './fixture/baseline.mjs';
import {LiveBuyWriter} from '../api/apps/api/src/live-buy/writer.ts';
import pg from '../api/node_modules/pg/lib/index.js';
import {decodeBuySessionReply} from '../api/apps/api/src/live-buy/reader.ts';
const client=new pg.Client({host:'pgtrial',port:5432,database:'pilot_trial_local',user:'postgres',password:process.env.POSTGRES_PASSWORD});await client.connect();
const db={exec:sql=>client.query(sql),query:(sql,args)=>client.query(sql,args),close:()=>client.end()};const checks=[],outputs={};let phase='load',last='';
const exec=db.exec.bind(db),query=db.query.bind(db);db.exec=async(sql,...a)=>{last=sql.slice(0,140);return exec(sql,...a)};db.query=async(sql,...a)=>{last=sql;return query(sql,...a)};
const q=(n,d=1)=>({n:String(n),d:String(d)}),hash=c=>'0x'+c.repeat(64);
async function tx(fn,role){await db.exec('BEGIN ISOLATION LEVEL SERIALIZABLE');try{if(role)await db.exec('SET LOCAL SESSION AUTHORIZATION '+role);const r=await fn();await db.exec('COMMIT');if(role)await db.exec('SET SESSION AUTHORIZATION postgres');return r}catch(e){await db.exec('ROLLBACK');if(role)await db.exec('SET SESSION AUTHORIZATION postgres');throw e}}
async function rpc(fn,p){return(await db.query(`SELECT polygon.${fn}($1::jsonb) reply`,[p])).rows[0].reply}
async function preserved(sid){return(await db.query(`SELECT jsonb_build_object('snapshot1',(SELECT to_jsonb(x) FROM polygon.session_snapshots x WHERE session_id=$1 AND version=1),'startReceipt',(SELECT polygon.receipt_reply(start_receipt_id) FROM polygon.paper_sessions WHERE id=$1),'funding',(SELECT jsonb_agg(to_jsonb(x)) FROM polygon.funding_flows x WHERE session_id=$1),'initialJournals',(SELECT jsonb_agg(to_jsonb(x)) FROM polygon.journals x WHERE session_id=$1),'operations',(SELECT jsonb_agg(to_jsonb(x) ORDER BY ordinal) FROM polygon_live_activity.operations x WHERE session_id=$1),'decisions',(SELECT jsonb_agg(to_jsonb(x) ORDER BY sequence) FROM polygon_live_activity.decisions x WHERE session_id=$1)) data`,[sid])).rows[0].data}
try{
 const users=await baseline(db);
 for(const f of ['001-storage.sql','002-runtime.sql','003-paper-read.sql','004-operator.sql','005-completeness.sql'])await loadSource(db,new URL('../staff-db/'+f,import.meta.url));
 const live=await loadLive(db,users),u=users[0],sid=u.sid,run=live.run;
 const worker=async(fn,p)=>{const r=await tx(()=>rpc(fn,p),u.writer);if(r.http!==200)throw Error(fn+JSON.stringify(r));return r};
 phase='legacy history';const now=new Date();const arm={session_id:sid,request:{runId:run,sessionId:sid,operationId:randomUUID(),baseline:{number:'100',hash:hash('a'),parentHash:hash('9'),timestampSeconds:String(Math.floor(now.getTime()/1000)-1)},baselineReceivedAt:now.toISOString(),evidenceSha256:'f'.repeat(64)}};
 const armed=await worker('live_activity_arm',arm);await new Promise(r=>setTimeout(r,1100));
 const binding={tokenId:'123',conditionId:hash('4'),outcome:'Synthetic Yes',marketTitle:'Synthetic market',protocol:'v1',marketSha256:'5'.repeat(64)};
 const log=(block,bh,txh)=>({transactionHash:txh,logIndex:'0',blockNumber:String(block),blockHash:bh,orderHash:hash('d'),owner:'0x1111111111111111111111111111111111111111',counterparty:'0x'+'e'.repeat(40),side:'BUY',tokenId:'123',makerAmountFilledRaw:'10000000',takerAmountFilledRaw:'20000000',feeRaw:'0',builder:hash('0'),metadata:hash('0'),rawLogSha256:'1'.repeat(64),receiptSha256:'2'.repeat(64)});
 const header={number:'101',hash:hash('b'),parentHash:hash('a'),timestampSeconds:String(Math.floor(Date.now()/1000))};
 const ingest=(h,previous,lg,evidence)=>({session_id:sid,request:{ingest:{runId:run,sessionId:sid,operationId:randomUUID(),previous,baselineCanonicalHash:hash('a'),finalized:h,headers:[h],observedAt:new Date().toISOString(),logs:[lg],evidenceSha256:'f'.repeat(64)},expectedSnapshotVersion:'1',evaluations:[{transactionHash:lg.transactionHash,logIndex:'0',evidence}]}});
 const skipped=await worker('live_activity_ingest',ingest(header,armed.result.checkpoint,log(101,hash('b'),hash('c')),{schemaVersion:'paper-buy-evidence-v1',kind:'skip',reason:'profile_unavailable',evidenceSha256:'3'.repeat(64),binding}));
 const stop=()=>({session_id:sid,request:{runId:run,sessionId:sid,operationId:randomUUID(),status:'stopped',evidenceSha256:'f'.repeat(64)}});
 let stopped=await worker('live_activity_stop',stop());
 const resume=()=>({session_id:sid,request:{runId:run,sessionId:sid,operationId:randomUUID(),expectedLastOperationId:stopped.result.operationId,expectedCheckpoint:skipped.result.checkpoint,expectedHighWatermark:'1',evidenceSha256:'f'.repeat(64)}});
 await worker('live_activity_resume',resume());stopped=await worker('live_activity_stop',stop());outputs.before=await preserved(sid);
 phase='compose install';await db.exec('BEGIN ISOLATION LEVEL SERIALIZABLE;CREATE SCHEMA live_buy_core AUTHORIZATION polygon_owner;CREATE SCHEMA polygon_buy AUTHORIZATION polygon_owner;SET LOCAL ROLE polygon_owner;');
 for(const f of ['core/001-core.sql','core/002-state.sql','core/003-write.sql','core/004-integrity.sql','010-bindings.sql']){let sql=await readFile(new URL(f,import.meta.url),'utf8');sql=sql.replace(/^CREATE SCHEMA .*;$/mg,'');await db.exec(sql)}
 await db.exec('RESET ROLE');await loadSource(db,new URL('009-catalog-operator.sql',import.meta.url));await db.exec('SET LOCAL ROLE polygon_owner');
 for(const f of ['011-projection.sql','012-writes-reads.sql','013-activity.sql','014-integrity-reads.sql'])await loadSource(db,new URL(f,import.meta.url));await db.exec('COMMIT');
 phase='bind actual session';await tx(()=>db.query('SELECT polygon_buy.bind_session($1)',[sid]));assert.deepEqual(await preserved(sid),outputs.before);
 outputs.empty=await tx(()=>rpc('buy_session_read_v1',{auth:u.auth,session_id:sid}));assert.equal(outputs.empty.buyState,null);
 outputs.noGrant=(await db.query("SELECT has_function_privilege($1,'polygon.live_buy_reserve_v1(jsonb)','EXECUTE') allowed",[u.writer])).rows[0];assert.equal(outputs.noGrant.allowed,false);
 // Synthetic test role assignment only, after proving the delivered default is closed.
 await db.exec(`GRANT EXECUTE ON FUNCTION polygon.live_buy_reserve_v1(jsonb),polygon.live_buy_settle_v1(jsonb),polygon.live_buy_lookup_v1(jsonb) TO ${u.writer}`);
 phase='resume composed';await worker('live_activity_resume',resume());
 const setting=(await db.query('SELECT current_settings_revision_id AS id FROM polygon.paper_sessions WHERE id=$1',[sid])).rows[0].id;
 const req={commandId:randomUUID(),intentId:randomUUID(),observationId:randomUUID(),expectedVersion:'1',conditionId:binding.conditionId,tokenId:'123',sizingRevisionId:setting,admissionRevisionId:setting,evidenceRef:'synthetic-only-not-market-evidence',desiredNotional:q(10),fullQuantity:q(20),quantityStep:q(1),priceCap:q(1,2),feeCashBound:q(1,5),delayMs:'0'};
 async function admission(kind,request,txh){const id=randomUUID();await db.query("INSERT INTO polygon_buy.admissions VALUES($1,$2,$3,$4,$5,$6,0,'123',$7,'synthetic-profile','synthetic-clock','synthetic-fee','synthetic-book',clock_timestamp()-interval '1 second',clock_timestamp()+interval '2 minutes')",[id,sid,run,kind,request,txh,binding.conditionId]);return id}
 const admissionId=await admission('reserve',req,hash('6'));
 const h2={number:'102',hash:hash('7'),parentHash:hash('b'),timestampSeconds:String(Math.floor(Date.now()/1000))};
 phase='queue new admitted observation';await worker('live_activity_ingest',ingest(h2,skipped.result.checkpoint,log(102,hash('7'),hash('6')),{schemaVersion:'paper-buy-pending-v1',kind:'candidate',admissionId,binding,evidenceSha256:'8'.repeat(64)}));
 // Connect/query/release bridge exercises the actual backend transaction and decoder.
 const pool={connect:async()=>({query:async config=>{const text=typeof config==='string'?config:config.text,values=typeof config==='string'?[]:config.values;if(text.startsWith('BEGIN')){const r=await db.exec(text);await db.exec('SET LOCAL SESSION AUTHORIZATION '+u.writer);return {rows:[]}}if(['COMMIT','ROLLBACK'].includes(text)){await db.exec(text);await db.exec('SET SESSION AUTHORIZATION postgres');return {rows:[]}}return db.query(text,values)},release:()=>{}})};
 const writer=new LiveBuyWriter(pool);
 phase='large exact fraction in composed reader';
 await writer.execute('reserve',{session_id:sid,request:req,admission_id:admissionId});
 const denominator=10n;
 const settle={commandId:randomUUID(),intentId:req.intentId,expectedVersion:'2',evidenceRef:'synthetic-only',confirmationId:randomUUID(),fills:[{fillId:randomUUID(),price:q(49,100),quantityGross:q(20),quantityFee:q(0),cashFee:q(1,denominator),executedAt:new Date().toISOString()}]};
 const aid=await admission('settle',settle,hash('6'));await writer.execute('settle',{session_id:sid,request:settle,admission_id:aid});
 const read=await tx(()=>rpc('buy_session_read_v1',{auth:u.auth,session_id:sid}));decodeBuySessionReply(read,sid);
 assert.deepEqual(read.financial.cashExpenses,q(1,denominator));const free=read.financial.freeCash;
 assert.equal(free.n,'2901');assert.equal(free.d,'10');checks.push('new reader preserves exact fraction beyond legacy 64-digit formatter');
 const staff=(await tx(()=>db.query('SELECT polygon.pilot_staff_snapshot($1) reply',[sid]))).rows[0].reply;
 assert.deepEqual(staff.session.financial,read.financial);checks.push('staff source shares same exact large-denominator financial state');
 const result={sessionId:sid,snapshotId:read.snapshotId,snapshotVersion:read.snapshotVersion,financial:read.financial,valuation:read.valuation};
 await writeFile(new URL('../control/seed-receipt.json',import.meta.url),JSON.stringify(result));
 await writeFile(new URL('../targets.json',import.meta.url),JSON.stringify(users.map(u=>({user:u.uid,session:u.sid}))));
 await writeFile(new URL('../control/user-fixtures.json',import.meta.url),JSON.stringify(users.map(u=>({login:u.auth.login_id,proof:u.proof}))),{mode:0o600});
 console.log(JSON.stringify({status:'PASS',sessionId:sid,snapshotVersion:read.snapshotVersion,positionCount:read.financial.positions.length}));
}catch(e){console.error(JSON.stringify({error:e.message,where:e.where,code:e.code,phase,last,checks}));process.exitCode=1}finally{await db.close()}
