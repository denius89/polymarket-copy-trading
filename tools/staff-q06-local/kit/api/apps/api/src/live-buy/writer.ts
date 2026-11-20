import type {Pool} from 'pg';
import {exactObject,uuid} from '../http/input.ts';
import {withPolygonTransaction,StorageRecordUnavailable} from '../storage/transaction.ts';
import {validateCoreRequest,decodeCoreResult} from './core-adapter.mjs';

/** Internal worker only. No browser route or default grants. SQL checks current
 * role/release BEFORE receipt lookup, and exact immutable admission on new writes.
 * admission_id is a reference to independently installed evidence, never a flag.
 */
export class LiveBuyWriter {
  private readonly pool:Pick<Pool,'connect'>;
  constructor(pool:Pick<Pool,'connect'>){this.pool=pool;}
  async execute(kind:'reserve'|'settle',input:unknown){
    const v=exactObject(input,['session_id','request','admission_id']);
    if(!uuid(v.session_id)||!uuid(v.admission_id)||!['reserve','settle'].includes(kind))throw new StorageRecordUnavailable();
    validateCoreRequest(kind,v.request);
    if(Buffer.byteLength(JSON.stringify(v))>1048576)throw new StorageRecordUnavailable();
    const request=structuredClone(v.request) as Record<string,unknown>,sessionId=v.session_id;
    const envelope={session_id:sessionId,request,admission_id:v.admission_id};
    // No automatic retry, including serialization failures and unknown COMMIT.
    return withPolygonTransaction(this.pool,'single-command',async tx=>{
      const raw=await tx.call(kind==='reserve'?'live_buy_reserve_v1':'live_buy_settle_v1',envelope);
      const r=exactObject(raw,['http','result']);if(r.http!==200)throw new StorageRecordUnavailable();
      return decodeCoreResult(r.result,{sessionId,commandId:request.commandId as string,kind,intentId:request.intentId as string});
    });
  }
  async lookup(sessionId:string,commandId:string){
    if(!uuid(sessionId)||!uuid(commandId))throw new StorageRecordUnavailable();
    return withPolygonTransaction(this.pool,'read',async tx=>{
      const raw=await tx.call('live_buy_lookup_v1',{session_id:sessionId,command_id:commandId});
      if(raw.http===202){
        const r=exactObject(raw,['http','status','commandId']);
        if(r.status!=='pending'||r.commandId!==commandId)throw new StorageRecordUnavailable();
        return {status:'pending' as const,commandId};
      }
      const r=exactObject(raw,['http','result']);if(r.http!==200)throw new StorageRecordUnavailable();
      return {status:'committed' as const,result:decodeCoreResult(r.result,{sessionId,commandId})};
    });
  }
}
