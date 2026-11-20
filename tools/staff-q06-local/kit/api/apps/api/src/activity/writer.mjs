import pg from 'pg';
import { uint, hash } from './source.mjs';
const uuid=v=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
const time=v=>typeof v==='string'&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString()===v;
const exact=(v,keys)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===keys.slice().sort().join(',');
const check=(b)=>{if(!b)throw new Error('writer_reply_invalid');};
const cp=v=>exact(v,['number','hash'])&&uint(v.number)&&hash(v.hash);
const conflicts=['baseline_hash_mismatch','canonical_chain_mismatch','future_source_timestamp','log_identity_conflict'];
const states=['stopped','source_unavailable','reconciliation_required'];
export function decodeResult(r,input,method){
  check(r&&uuid(r.operationId)&&r.operationId===input.operationId&&r.sessionId===input.sessionId);
  if(r.kind==='arm')check(exact(r,['operationId','kind','sessionId','armedAt','checkpoint'])&&time(r.armedAt)&&cp(r.checkpoint));
  else if(r.kind==='ingest')check(exact(r,['operationId','kind','sessionId','checkpoint','accepted','duplicates','excluded','highWatermark'])&&
    cp(r.checkpoint)&&['accepted','duplicates','excluded','highWatermark'].every(k=>uint(r[k])&&BigInt(r[k])<=9223372036854775807n));
  else if(r.kind==='ingest_blocked')check(exact(r,['operationId','kind','sessionId','status','conflictId','conflictCode','checkpoint','highWatermark','evidenceSha256'])&&
    r.status==='reconciliation_required'&&uuid(r.conflictId)&&conflicts.includes(r.conflictCode)&&cp(r.checkpoint)&&uint(r.highWatermark)&&/^[0-9a-f]{64}$/.test(r.evidenceSha256));
  else if(r.kind==='stop')check(exact(r,['operationId','kind','sessionId','status'])&&states.includes(r.status));
  else check(false);
  if(method==='activity_arm')check(r.kind==='arm'&&r.checkpoint.number===input.baseline.number&&r.checkpoint.hash===input.baseline.hash);
  if(method==='activity_ingest'){
    check(r.kind==='ingest'||r.kind==='ingest_blocked');
    if(r.kind==='ingest')check(r.checkpoint.number===input.finalized.number&&r.checkpoint.hash===input.finalized.hash&&
      BigInt(r.accepted)+BigInt(r.duplicates)+BigInt(r.excluded)===BigInt(input.logs.length));
    else check(r.checkpoint.number===input.previous.number&&r.checkpoint.hash===input.previous.hash&&r.evidenceSha256===input.evidenceSha256);
  }
  if(method==='activity_stop')check(r.kind==='stop'&&r.status===input.status);
  return r;
}
function decodeLegacyReply(reply,input,method){
  if(method==='activity_ingest_buy'){input=input.ingest;method='activity_ingest';}
  if(method==='activity_lookup'){
    check(exact(reply,['http','status','result'])&&reply.http===200);
    if(reply.status==='not_found'){check(reply.result===null);return reply;}
    check(reply.status==='committed');decodeResult(reply.result,input,method);return reply;
  }
  check(exact(reply,['http','result'])&&reply.http===200);decodeResult(reply.result,input,method);return reply;
}
const methods=Object.freeze({live_activity_arm:'activity_arm',live_activity_ingest:'activity_ingest_buy',live_activity_stop:'activity_stop',live_activity_lookup:'activity_lookup'});
export function scopedRequest(sessionId,request){return {session_id:sessionId,request};}
export function requestIdentity(wrapper){
  if(!exact(wrapper,['session_id','request'])||!uuid(wrapper.session_id))throw new Error('worker_scope_invalid');
  const identity=wrapper.request?.ingest??wrapper.request;
  if(!identity||identity.sessionId!==wrapper.session_id||!uuid(identity.runId)||!uuid(identity.operationId))throw new Error('worker_scope_invalid');
  return identity;
}
export function decodeWriterReply(reply,input,method){
  requestIdentity(input);
  if(!Object.hasOwn(methods,method))throw new Error('worker_method_invalid');
  return decodeLegacyReply(reply,input.request,methods[method]);
}
export class WriterFailure extends Error {
  constructor(outcome,reason='writer_failure'){super(reason);this.name='WriterFailure';this.outcome=outcome;}
}
export function createWriter(database,password,Pool=pg.Pool){
  if(typeof database.database!=='string'||!/^shadow_[a-z0-9_]{1,55}$/.test(database.database)||
    typeof database.user!=='string'||!/^polygon_live_writer_[0-9a-f]{32}$/.test(database.user)||
    typeof database.host!=='string'||!database.host.startsWith('/')||database.port!==5432)throw new Error('writer_configuration_invalid');
  const pool=new Pool({host:database.host,port:database.port,user:database.user,password,database:database.database,max:1,
    connectionTimeoutMillis:3000,idleTimeoutMillis:1000,query_timeout:5000,application_name:'shadow-live-activity-v1'});
  return {close:()=>pool.end(),async call(method,input){
    if(!Object.hasOwn(methods,method))throw new WriterFailure('not_committed');
    try{requestIdentity(input);}catch{throw new WriterFailure('not_committed');}
    if(Buffer.byteLength(JSON.stringify(input))>1048576)throw new WriterFailure('not_committed');
    let client,begun=false,commitSent=false,healthy=false;
    try{
      client=await pool.connect();await client.query('BEGIN ISOLATION LEVEL SERIALIZABLE');begun=true;
      await client.query("SET LOCAL statement_timeout='4000ms'");await client.query("SET LOCAL lock_timeout='3000ms'");
      const result=await client.query(`SELECT polygon.${method}($1::jsonb) AS reply`,[JSON.stringify(input)]);
      check(result.rows.length===1&&exact(result.rows[0],['reply']));const reply=result.rows[0].reply;
      if(exact(reply,['http','reason']))throw new Error('writer_refusal');
      decodeWriterReply(reply,input,method);commitSent=true;await client.query('COMMIT');healthy=true;return reply;
    }catch{
      if(client&&begun&&!commitSent){try{await client.query('ROLLBACK');healthy=true;}catch{}}
      throw new WriterFailure(commitSent||!healthy?'unknown':'not_committed');
    }finally{client?.release(!healthy);}
  }};
}
