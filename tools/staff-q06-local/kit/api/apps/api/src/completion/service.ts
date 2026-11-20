import type {Pool} from 'pg';
import {InputError,uuid} from '../http/input.ts';
import {withPolygonTransaction,RpcRefusal,StorageRecordUnavailable} from '../storage/transaction.ts';
import {parseCompleteEmptyRequest,decodeCompletion} from './contracts.ts';
import type {CompletionOperation} from './contracts.ts';
const error=(status:number,reasonCode:string)=>({status,body:{reasonCode,reasonDetails:[{code:reasonCode,params:{}}],nextAction:reasonCode.startsWith('AUTH_')?'authenticate':null,nextActionParams:{}}});
export async function executeCompletion(pool:Pick<Pool,'connect'>,auth:{login_id:string;cookie_digest:string},op:CompletionOperation,started:number){
  let clientCommandId:string|undefined,sessionId:string|null=null;
  try{
    const request=op.kind==='complete-empty'?parseCompleteEmptyRequest(op.body):null;
    clientCommandId=request?.clientCommandId??(op as {clientCommandId:string}).clientCommandId;
    if(!uuid(clientCommandId)||(op.kind==='complete-empty'&&!uuid(op.sessionId)))throw new InputError();
    if(op.kind==='complete-empty')sessionId=op.sessionId;
    const key=clientCommandId;
    return await withPolygonTransaction(pool,request?'single-command':'read',async tx=>{
      const r=request?await tx.call('complete_empty_v1',{auth,session_id:sessionId,request}):
        await tx.call('complete_empty_lookup_v1',{auth,client_command_id:key});
      return {status:r.http,body:decodeCompletion(r,key,sessionId,!request)};
    },started);
  }catch(e){
    if(e instanceof InputError)return error(e.status,e.reasonCode);
    if(e instanceof RpcRefusal)return error(e.response.http,e.response.reason as string);
    if(e instanceof StorageRecordUnavailable)return error(503,'RECORD_UNAVAILABLE');
    if(clientCommandId)return {status:503,body:{schemaVersion:'paper-empty-completion-v1',status:'unknown',clientCommandId,
      completion:null,reasonCode:'SERVICE_UNAVAILABLE',nextAction:null,nextActionParams:{}}};
    return error(503,'SERVICE_UNAVAILABLE');
  }
}
