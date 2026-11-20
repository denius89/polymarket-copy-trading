import {exactObject,uuid} from '../http/input.ts';
import {timestamp} from '../paper/responses.ts';
import {PilotRecordUnavailable} from './responses.ts';
const bad=():never=>{throw new PilotRecordUnavailable();};
export function closed(value:unknown,keys:readonly string[]){try{return exactObject(value,keys);}catch{return bad();}}
export function contextReply(value:unknown,id:string,logout=false){
  const key=logout?'logoutContextId':'contextId';
  const r=closed(value,[key,'expiresAt']);
  if(r[key]!==id||!timestamp(r.expiresAt))return bad();
  return r as Record<string,string>;
}
export function logoutContextReply(value:unknown,id:string,sourceContextId:string|null){
  const r=closed(value,['logoutContextId','loginId','realm','createdAt','expiresAt',...(sourceContextId?['sourceLogoutContextId']:[])]);
  if(r.logoutContextId!==id||!uuid(r.loginId)||r.realm!=='staff'||!timestamp(r.createdAt)||!timestamp(r.expiresAt)
    ||Date.parse(r.expiresAt as string)-Date.parse(r.createdAt as string)!==15*60*1000
    ||(sourceContextId&&r.sourceLogoutContextId!==sourceContextId))return bad();
  return r as Record<string,string>;
}
export interface LoginResult {kind:'pilot_login_completed'|'pilot_login_rejected';operationId:string;completedAt:string;loginId?:string;reasonCode?:'AUTH_REQUIRED'}
export function loginResult(value:unknown,operationId:string):LoginResult{
  const kind=(value as Record<string,unknown>|null)?.kind;
  const r=closed(value,kind==='pilot_login_completed'?['kind','operationId','loginId','completedAt']:['kind','operationId','reasonCode','completedAt']);
  if(r.operationId!==operationId||!timestamp(r.completedAt))return bad();
  if(kind==='pilot_login_completed'){if(!uuid(r.loginId))return bad();}
  else if(kind!=='pilot_login_rejected'||r.reasonCode!=='AUTH_REQUIRED')return bad();
  return r as unknown as LoginResult;
}
export interface LogoutResult {kind:'logout_completed';operationId:string;targetLoginId:string;completedAt:string}
export function logoutResult(value:unknown,operationId:string):LogoutResult{
  const r=closed(value,['kind','operationId','targetLoginId','completedAt']);
  if(r.kind!=='logout_completed'||r.operationId!==operationId||!uuid(r.targetLoginId)||!timestamp(r.completedAt))return bad();
  return r as unknown as LogoutResult;
}
export function outcome<T>(value:unknown,decode:(v:unknown)=>T):{state:'unresolved'}|{state:'resolved';result:T}{
  if((value as Record<string,unknown>|null)?.state==='unresolved'){closed(value,['state']);return {state:'unresolved'};}
  const r=closed(value,['state','result']);if(r.state!=='resolved')return bad();
  return {state:'resolved',result:decode(r.result)};
}
export function logoutOutcome(value:unknown,operationId:string){
  const r=closed(value,(value as Record<string,unknown>|null)?.state==='resolved'?['state','targetLoginId','result']:['state','targetLoginId']);
  if(!uuid(r.targetLoginId))return bad();
  if(r.state==='unresolved')return {state:'unresolved' as const,targetLoginId:r.targetLoginId};
  if(r.state!=='resolved')return bad();
  const result=logoutResult(r.result,operationId);if(result.targetLoginId!==r.targetLoginId)return bad();
  return {state:'resolved' as const,targetLoginId:r.targetLoginId,result};
}
export function cookieReply(value:unknown){
  const r=closed(value,['loginId','cookieEnvelope','deliveryDeadline','cookieExpiresAt']);
  if(!uuid(r.loginId)||!timestamp(r.deliveryDeadline)||!timestamp(r.cookieExpiresAt)||String(r.deliveryDeadline)>String(r.cookieExpiresAt))return bad();
  const e=closed(r.cookieEnvelope,['key_id','nonce','ciphertext']);
  if(!uuid(e.key_id)||typeof e.nonce!=='string'||!/^[a-f0-9]{48}$/.test(e.nonce)
    ||typeof e.ciphertext!=='string'||!/^[a-f0-9]{96}$/.test(e.ciphertext))return bad();
  return {loginId:r.loginId,cookieEnvelope:e,deliveryDeadline:r.deliveryDeadline as string,cookieExpiresAt:r.cookieExpiresAt as string};
}
export function meReply(value:unknown,loginId:string){
  const r=closed(value,['staffId','loginId','observedAt','displayLabel','absoluteExpiresAt','idleExpiresAt','pilotExpiresAt']);
  if(!uuid(r.staffId)||r.loginId!==loginId||!['observedAt','absoluteExpiresAt','idleExpiresAt','pilotExpiresAt'].every(k=>timestamp(r[k]))
    ||typeof r.displayLabel!=='string'||r.displayLabel.length>80)return bad();
  for(const key of ['absoluteExpiresAt','idleExpiresAt','pilotExpiresAt'])if(String(r.observedAt)>=String(r[key]))return bad();
  return r as Record<string,string>;
}
