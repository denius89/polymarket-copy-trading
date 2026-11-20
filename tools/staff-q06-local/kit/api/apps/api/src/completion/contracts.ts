import {exactObject,InputError,uuid,positiveVersion} from '../http/input.ts';
import {timestamp} from '../paper/responses.ts';
import {StorageRecordUnavailable} from '../storage/transaction.ts';
export interface CompleteEmptyRequest {requestSchemaVersion:'v1';clientCommandId:string;expectedSessionVersion:string}
export type CompletionOperation = {kind:'complete-empty';sessionId:string;body:unknown}|{kind:'completion-result';clientCommandId:string};
export function parseCompleteEmptyRequest(value:unknown):CompleteEmptyRequest {
  const v=exactObject(value,['requestSchemaVersion','clientCommandId','expectedSessionVersion']);
  if(v.requestSchemaVersion!=='v1'||!uuid(v.clientCommandId)||!positiveVersion(v.expectedSessionVersion))throw new InputError();
  return v as unknown as CompleteEmptyRequest;
}
export function decodeCompletion(value:unknown,clientCommandId:string,sessionId:string|null,lookup:boolean):Record<string,unknown>{
  try{
    const r=exactObject(value,['http','status','clientCommandId','completion','reasonCode']);
    if(r.clientCommandId!==clientCommandId||!uuid(clientCommandId))throw Error();
    if(r.status==='committed'){
      if(r.http!==200||r.reasonCode!==null)throw Error();
      const c=exactObject(r.completion,['completionId','sessionId','sessionVersion','snapshotVersion','completedAt','releasedSlotGeneration']);
      if(!uuid(c.completionId)||!uuid(c.sessionId)||(sessionId!==null&&c.sessionId!==sessionId)||
        c.sessionVersion!=='2'||c.snapshotVersion!=='2'||!timestamp(c.completedAt)||!positiveVersion(c.releasedSlotGeneration))throw Error();
    }else if(r.status==='rejected'){
      if(r.http!==(lookup?200:409)||r.completion!==null||!['SESSION_NOT_SETTLED','VERSION_CONFLICT'].includes(r.reasonCode as string))throw Error();
    }else if(r.status==='pending'){
      if(!lookup||r.http!==202||r.completion!==null||r.reasonCode!==null)throw Error();
    }else throw Error();
    return {schemaVersion:'paper-empty-completion-v1',status:r.status,clientCommandId:r.clientCommandId,
      completion:r.completion,reasonCode:r.reasonCode,nextAction:null,nextActionParams:{}};
  }catch{throw new StorageRecordUnavailable();}
}
