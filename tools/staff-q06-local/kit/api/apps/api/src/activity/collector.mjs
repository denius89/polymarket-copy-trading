import { randomUUID } from 'node:crypto';
import { mkdirSync, lstatSync, readFileSync, writeFileSync, openSync, closeSync, fsyncSync, readdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { SOURCE, sha256, SourceFailure, createRpc, fetchBaseline, fetchRange } from './source.mjs';
import {createMarketClient} from '../paper-buy/binding.mjs';
import {createFallbackEvaluator,buildEnvelope} from '../paper-buy/fallback.mjs';
import { createWriter, decodeWriterReply, WriterFailure, scopedRequest, requestIdentity } from './writer.mjs';

function privateDir(path){
  if(!path||resolve(path)!==path)throw new Error('private_directory_required');
  mkdirSync(path,{recursive:true,mode:0o700});const s=lstatSync(path);
  if(!s.isDirectory()||s.isSymbolicLink()||(s.mode&0o077))throw new Error('private_directory_required');
}
function durableNew(path,bytes){
  const fd=openSync(path,'wx',0o600);try{writeFileSync(fd,bytes);fsyncSync(fd);}finally{closeSync(fd);}
  const dir=openSync(resolve(path,'..'),'r');try{fsyncSync(dir);}finally{closeSync(dir);}
}
export function contentStore(path){
  privateDir(path);return {put(bytes){
    bytes=Buffer.from(bytes);const h=sha256(bytes),file=join(path,h);
    try{durableNew(file,bytes);}catch(error){
      if(error.code!=='EEXIST')throw error;
      const s=lstatSync(file);if(!s.isFile()||s.isSymbolicLink()||sha256(readFileSync(file))!==h)throw new Error('evidence_integrity_failure');
    }return h;
  },putJSON(value){return this.put(JSON.stringify(value));}};
}
export function journal(path){
  privateDir(path);return {
    start(config){durableNew(join(path,'START.json'),JSON.stringify(config));},
    intent(method,body){durableNew(join(path,`intent-${requestIdentity(body).operationId}.json`),JSON.stringify({method,body}));},
    reply(id,value){durableNew(join(path,`reply-${id}.json`),JSON.stringify(value));},
    finish(value){durableNew(join(path,'RESULT.json'),JSON.stringify(value));},
    pending(){return readdirSync(path).filter(x=>/^intent-[0-9a-f-]{36}\.json$/.test(x)&&
      !readdirSync(path).includes(x.replace('intent-','reply-'))).map(x=>JSON.parse(readFileSync(join(path,x),'utf8')));},
  };
}
const now=()=>new Date().toISOString();
export async function observe({config,db,rpc,store,journal:log,clock=now,monotonic=()=>performance.now(),sleep=ms=>new Promise(r=>setTimeout(r,ms)),evaluate}){
  if(!Number.isInteger(config.windowMs)||config.windowMs<10000||config.windowMs>300000||
    !Number.isInteger(config.pollIntervalMs)||config.pollIntervalMs<1000||config.pollIntervalMs>30000)throw new Error('collector_budget_invalid');
  const started=monotonic();let armed=null,checkpoint=null,accepted=0n,reads=0,pending=null;
  log.start({runId:config.runId,sessionId:config.sessionId,source:SOURCE,startedAt:clock(),windowMs:config.windowMs});
  const evidence=()=>store.putJSON({schemaVersion:'chain-observation-evidence-v1',runId:config.runId,sessionId:config.sessionId,source:SOURCE,captures:[...rpc.captures]});
  const submit=async(method,fields)=>{
    let body={runId:config.runId,operationId:randomUUID(),sessionId:config.sessionId,...fields};
    if(method==='activity_ingest'){
      body=await buildEnvelope(body,{armedAt:armed.armedAt,evaluate});
      body.ingest.observedAt=clock();method='activity_ingest';
    }
    body=scopedRequest(config.sessionId,body);method='live_'+method;
    const identity=requestIdentity(body);
    log.intent(method,body);pending={method,body};
    const reply=await db.call(method,body);decodeWriterReply(reply,body,method);
    log.reply(identity.operationId,reply);pending=null;return reply.result;
  };
  try{
    const base=await fetchBaseline(rpc);
    armed=await submit('activity_arm',{...base,evidenceSha256:evidence()});checkpoint=armed.checkpoint;
    while(monotonic()-started<config.windowMs){
      const range=await fetchRange(rpc,base.baseline,checkpoint);
      if(range.blocked)throw new SourceFailure(range.blocked,'reconciliation_required');
      if(!range.waiting){
        const result=await submit('activity_ingest',{previous:checkpoint,...range,evidenceSha256:evidence(),observedAt:clock()});
        if(result.kind==='ingest_blocked'){
          const outcome={status:'reconciliation_required',result};log.finish(outcome);return outcome;
        }
        checkpoint=result.checkpoint;accepted+=BigInt(result.accepted);reads++;
      }
      const remaining=config.windowMs-(monotonic()-started);if(remaining>0)await sleep(Math.min(config.pollIntervalMs,remaining));
    }
    const result=await submit('activity_stop',{status:'stopped',evidenceSha256:evidence()});
    const outcome={status:accepted>0n?'OBSERVED':reads>0?'NOT_OBSERVED':'NO_CONFIRMED_RANGE',accepted:String(accepted),ranges:reads,checkpoint,result};
    log.finish(outcome);return outcome;
  }catch(error){
    if(pending){
      let recovery=null;
      try{recovery=await db.call('live_activity_lookup',scopedRequest(config.sessionId,{runId:config.runId,operationId:requestIdentity(pending.body).operationId,sessionId:config.sessionId}));
        decodeWriterReply(recovery,scopedRequest(config.sessionId,{runId:config.runId,sessionId:config.sessionId,operationId:requestIdentity(pending.body).operationId}),'live_activity_lookup');if(recovery.status==='committed')log.reply(requestIdentity(pending.body).operationId,recovery);
      }catch{/* No retry, no new operation key. */}
      const outcome={status:'WRITER_STOPPED',operationId:requestIdentity(pending.body).operationId,outcome:error instanceof WriterFailure?error.outcome:'unknown',recovery};
      log.finish(outcome);return outcome;
    }
    const state=error instanceof SourceFailure?error.state:'source_unavailable';let stopResult=null;
    if(armed){
      try{stopResult=await submit('activity_stop',{status:state,evidenceSha256:evidence()});}
      catch{
        let recovery=null;
        if(pending)try{recovery=await db.call('live_activity_lookup',scopedRequest(config.sessionId,{runId:config.runId,operationId:requestIdentity(pending.body).operationId,sessionId:config.sessionId}));}catch{}
        const outcome={status:'STOP_UNKNOWN',operationId:pending?requestIdentity(pending.body).operationId:null,recovery};log.finish(outcome);return outcome;
      }
    }
    if(error instanceof SourceFailure&&error.code==='observation_budget_exhausted'){
      const outcome={status:accepted>0n?'OBSERVED':reads>0?'NOT_OBSERVED':'NO_CONFIRMED_RANGE',accepted:String(accepted),ranges:reads,
        checkpoint,incompleteRangeDiscarded:true,stopResult,evidenceSha256:evidence()};log.finish(outcome);return outcome;
    }
    const outcome={status:state,reason:error instanceof SourceFailure?error.code:'collector_local_failure',stopResult,evidenceSha256:evidence()};
    log.finish(outcome);return outcome;
  }
}

function privateJSON(path){const s=lstatSync(path);if(!s.isFile()||s.isSymbolicLink()||(s.mode&0o077))throw new Error('private_config_required');return JSON.parse(readFileSync(path,'utf8'));}
async function main(){
  if(process.argv.length!==3&&!(process.argv.length===4&&process.argv[3]==='--recover'))throw new Error('usage_config_file');
  const config=privateJSON(resolve(process.argv[2]));
  const id=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  if(!id.test(config.runId)||!id.test(config.sessionId))throw new Error('run_binding_invalid');
  const p=config.database?.passwordFile,s=lstatSync(p);if(!s.isFile()||s.isSymbolicLink()||(s.mode&0o077))throw new Error('private_password_required');
  const password=readFileSync(p,'utf8').replace(/\r?\n$/,'');if(!password)throw new Error('empty_password');
  const store=contentStore(config.evidenceDir),log=journal(config.stateDir),db=createWriter(config.database,password);
  try{
    if(process.argv[3]==='--recover'){
      const pending=log.pending();if(pending.length!==1)throw new Error('single_pending_operation_required');const body=requestIdentity(pending[0].body);
      if(body.runId!==config.runId||body.sessionId!==config.sessionId)throw new Error('pending_scope_mismatch');
      const reply=await db.call('live_activity_lookup',scopedRequest(config.sessionId,{runId:config.runId,operationId:body.operationId,sessionId:config.sessionId}));
      if(reply.status==='committed')log.reply(body.operationId,reply);process.stdout.write(JSON.stringify({status:'RECOVERY_ONLY',operationId:body.operationId,result:reply.status})+'\n');return;
    }
    const client=createMarketClient({store,deadlineMonoMs:performance.now()+config.windowMs});
    const evaluate=createFallbackEvaluator({client,store});
    const result=await observe({config,db,rpc:createRpc(store,fetch,now,config.windowMs),store,journal:log,evaluate});
    process.stdout.write(JSON.stringify({status:result.status,accepted:result.accepted??null,ranges:result.ranges??null})+'\n');
    if(!['OBSERVED','NOT_OBSERVED'].includes(result.status))process.exitCode=2;
  }finally{await db.close();}
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(()=>{process.stderr.write('Collector stopped; inspect private evidence. No automatic retry.\n');process.exitCode=2;});
