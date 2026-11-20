import type {Pool, PoolClient} from 'pg';
import {performance} from 'node:perf_hooks';
import {exactObject, uuid, InputError} from '../http/input.ts';
import {timestamp} from '../paper/responses.ts';
import {PilotRecordUnavailable} from './responses.ts';

const methods = {
  auth: ['context_prepare','login_execute','operation_read','cookie_recover'],
  reader: ['own_me','logout_prepare','logout_continue','logout_execute','logout_read','session_list','session_read','session_events'],
} as const;
export type PilotRole = keyof typeof methods;
export type PilotMethod = typeof methods[PilotRole][number];
export type PilotReply<T> = {status:'ok'; data:T; observedAt:string} | {status:'error'; http:number; reasonCode:string};
export class PilotStorageUnavailable extends Error {
  readonly outcome: 'not_started'|'not_committed'|'unknown';
  constructor(outcome: 'not_started'|'not_committed'|'unknown') {super('Pilot storage unavailable');this.outcome=outcome;}
}
export interface PilotTx {
  call<T>(method:PilotMethod, input:Record<string,unknown>, decode:(value:unknown,observedAt:string)=>T):Promise<PilotReply<T>>;
}
export interface PilotRequestProof {requestId:string; requestProofDigest:string}
const codes: Record<string,number> = {
  AUTH_REQUIRED:401, AUTH_CONTEXT_EXPIRED:409, AUTH_CONTEXT_STATE_CONFLICT:409,
  SERVICE_UNAVAILABLE:503, AUTH_EXPIRED:401, AUTH_REVOKED:401, RESOURCE_NOT_FOUND:404,
  RECORD_UNAVAILABLE:503, RATE_LIMITED:429, ACCESS_DENIED:403,
};
const bad = ():never => {throw new PilotRecordUnavailable();};

function reply<T>(value:unknown, decode:(data:unknown,observedAt:string)=>T):PilotReply<T> {
  if(!value||typeof value!=='object')return bad();
  try {
    if((value as Record<string,unknown>).status==='error') {
      const r=exactObject(value,['status','http','reason_code']);
      if(typeof r.reason_code!=='string'||!Object.hasOwn(codes,r.reason_code)||codes[r.reason_code]!==r.http)return bad();
      return {status:'error',http:r.http as number,reasonCode:r.reason_code};
    }
    const r=exactObject(value,['status','data','observed_at']);
    if(r.status!=='ok'||!timestamp(r.observed_at))return bad();
    return {status:'ok',data:decode(r.data,r.observed_at as string),observedAt:r.observed_at as string};
  } catch {return bad();}
}

/** The caller must preserve business refusals as values through COMMIT, so quota,
 * failure evidence and immutable rejected outcomes are not rolled back by HTTP errors. */
export async function withPilotTransaction<T>(pool:Pick<Pool,'connect'>, role:PilotRole,
  deploymentDigest:string, deadline:number, proof:PilotRequestProof, work:(tx:PilotTx)=>Promise<T>):Promise<T> {
  if(!Object.hasOwn(methods,role)||!/^[a-f0-9]{64}$/.test(deploymentDigest)||!uuid(proof.requestId)
    ||!/^[a-f0-9]{64}$/.test(proof.requestProofDigest)||!Number.isFinite(deadline)
    ||deadline<=performance.now()||deadline-performance.now()>5000)throw new PilotStorageUnavailable('not_started');
  let client:PoolClient|undefined, released=false, begun=false, committing=false, abandoned=false;
  const release=(destroy=false)=>{if(client&&!released){released=true;client.release(destroy);}};
  function remaining() {
    const ms=Math.floor(deadline-performance.now());
    if(released||ms<1)throw new PilotStorageUnavailable(begun?'unknown':'not_started');
    return ms;
  }
  async function bounded<R>(fn:()=>Promise<R>):Promise<R> {
    const ms=remaining();let timer:ReturnType<typeof setTimeout>|undefined;
    try {return await Promise.race([Promise.resolve().then(fn),new Promise<never>((_,reject)=>{
      timer=setTimeout(()=>{release(true);reject(new PilotStorageUnavailable(begun?'unknown':'not_started'));},ms);
    })]);} finally {clearTimeout(timer);}
  }
  async function query(text:string,values?:unknown[]) {
    remaining();return bounded(()=>{remaining();return client!.query({text,values});});
  }
  try {
    try {client=await bounded(()=>pool.connect().then(c=>{
      if(abandoned){c.release(true);throw new PilotStorageUnavailable('not_started');}return c;
    }));} catch(error){abandoned=true;throw error;}
    await query('BEGIN ISOLATION LEVEL SERIALIZABLE');begun=true;
    await query("SELECT set_config('pilot_staff.expected_deployment_digest',$1,true)",[deploymentDigest]);
    const tx:PilotTx={async call(method,input,decode){
      if(!(methods[role] as readonly string[]).includes(method)||typeof decode!=='function')return bad();
      if(!input||typeof input!=='object'||Array.isArray(input)
        ||['request_id','request_proof_digest','remaining_ms'].some(k=>Object.hasOwn(input,k)))return bad();
      await query("SELECT set_config('statement_timeout',$1,true),set_config('lock_timeout',$1,true)",[remaining()+'ms']);
      const result=await query(`SELECT pilot_staff.${method}($1::jsonb) AS reply`,[JSON.stringify({...input,
        request_id:proof.requestId,request_proof_digest:proof.requestProofDigest,remaining_ms:remaining()})]);
      remaining();
      if(result.rows.length!==1||!result.rows[0]||Object.keys(result.rows[0]).join(',')!=='reply')return bad();
      return reply(result.rows[0].reply,decode);
    }};
    const result=await bounded(()=>work(tx));
    await query("SELECT set_config('statement_timeout',$1,true),set_config('lock_timeout',$1,true)",[remaining()+'ms']);
    committing=true;await query('COMMIT');release();return result;
  } catch(error) {
    if(committing){release(true);throw new PilotStorageUnavailable('unknown');}
    let rolledBack=false;
    if(client&&!released&&begun)try{await query('ROLLBACK');rolledBack=true;}catch{/* connection discarded below */}
    release(true);
    if(rolledBack&&(error instanceof PilotRecordUnavailable||error instanceof InputError))throw error;
    if(error instanceof PilotStorageUnavailable)throw error;
    throw new PilotStorageUnavailable(rolledBack?'not_committed':begun?'unknown':'not_started');
  }
}
