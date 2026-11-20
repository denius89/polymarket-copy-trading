import {randomBytes,randomUUID} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import type {Pool} from 'pg';
import {InputError,uuid} from '../http/input.ts';
import {parsePilotRequest,canonicalSecret} from './requests.ts';
import {decodePilotList,decodePilotEvents,decodePilotSession,PilotRecordUnavailable} from './responses.ts';
import {closed,contextReply,loginResult,logoutOutcome,logoutContextReply,outcome,cookieReply,meReply,type LoginResult} from './auth-responses.ts';
import {withPilotTransaction,type PilotReply,PilotStorageUnavailable} from './transaction.ts';
import type {createPilotCrypto,createPilotReaderCrypto} from './crypto.ts';

export interface PilotFrame {
  method:string;target:string;body:Uint8Array;deadlineNs:bigint;
  selectedLoginId:string|null;proof:string|null;networkDigest:string|null;
}
export interface PilotHttpReply {status:number;headers:Record<string,string>;body:unknown}
type Base={pool:Pick<Pool,'connect'>;deploymentDigest:string};
type AuthCrypto=Awaited<ReturnType<typeof createPilotCrypto>>;
type ReaderCrypto=ReturnType<typeof createPilotReaderCrypto>;
const nav={nextAction:null,nextActionParams:{}};
function response(status:number,body:unknown,headers:Record<string,string>={}):PilotHttpReply {
  return {status,body,headers:{'Cache-Control':'no-store',...headers}};
}
function refusal(r:{http:number;reasonCode:string}) {
  return response(r.http,{reasonCode:r.reasonCode,reasonDetails:{code:r.reasonCode,params:{}},...nav});
}
function cookie(name:string,id:string,value:string,expiry:string) {
  if(!uuid(id)||!canonicalSecret(value))throw new PilotRecordUnavailable();
  return `__Host-shadow-${name}-${id}=${value}; Path=/; Secure; HttpOnly; SameSite=Strict; Expires=${new Date(expiry).toUTCString()}`;
}
function requestProof(){return {requestId:randomUUID(),requestProofDigest:randomBytes(32).toString('hex')};}
function deadline(frame:PilotFrame){
  const ns=frame.deadlineNs-process.hrtime.bigint();
  if(ns<1000000n||ns>5000000000n)throw new PilotStorageUnavailable('not_started');
  return performance.now()+Number(ns)/1e6;
}
function proof(frame:PilotFrame){if(!canonicalSecret(frame.proof))throw new InputError(401,'AUTH_REQUIRED');return frame.proof;}
function selected(frame:PilotFrame){if(!uuid(frame.selectedLoginId))throw new InputError(401,'AUTH_REQUIRED');return frame.selectedLoginId;}
function completion(result:LoginResult,contextId:string){
  if(result.kind!=='pilot_login_completed'||!result.loginId)throw new PilotRecordUnavailable();
  return {contextId,operationId:result.operationId,realm:'staff',loginId:result.loginId,completedAt:result.completedAt};
}

export function createPilotAuthService(deps:Base & {crypto:AuthCrypto}) {
  return async(frame:PilotFrame):Promise<PilotHttpReply>=>{
    const r=parsePilotRequest(frame.method,frame.target,frame.body),end=deadline(frame);
    if(!r||!['pilot_context','pilot_login','pilot_outcome','pilot_cookie'].includes(r.route))return refusal({http:404,reasonCode:'RESOURCE_NOT_FOUND'});
    return withPilotTransaction(deps.pool,'auth',deps.deploymentDigest,end,requestProof(),async tx=>{
      if(r.route==='pilot_context') {
        if(!frame.networkDigest||!/^[a-f0-9]{64}$/.test(frame.networkDigest))throw new InputError(503,'SERVICE_UNAVAILABLE');
        const id=randomUUID(),material=deps.crypto.issue('context',id);
        const out=await tx.call('context_prepare',{context_id:id,context_proof_digest:material.digest,network_digest:frame.networkDigest},v=>contextReply(v,id));
        if(out.status==='error')return refusal(out);
        return response(201,{staffContext:out.data,observedAt:out.observedAt,...nav},{'Set-Cookie':cookie('pilotctx',id,material.cookie,out.data.expiresAt)});
      }
      if(r.route!=='pilot_login'&&r.route!=='pilot_outcome'&&r.route!=='pilot_cookie')throw new PilotRecordUnavailable();
      const contextId=r.contextId,operationId=r.route==='pilot_login'?r.payload.operationId as string:r.operationId;
      const auth={context_id:contextId,context_proof_digest:deps.crypto.proof('context',contextId,proof(frame)),operation_id:operationId};
      if(r.route==='pilot_outcome') {
        const out=await tx.call('operation_read',auth,v=>outcome(v,x=>loginResult(x,operationId)));
        if(out.status==='error')return refusal(out);
        return response(out.data.state==='resolved'?200:202,{operationRef:{contextId,operationId},status:out.data.state,
          ...(out.data.state==='resolved'?{result:out.data.result}:{}),observedAt:out.observedAt,...nav});
      }
      let result:LoginResult|undefined;
      if(r.route==='pilot_login') {
        const loginId=randomUUID(),material=deps.crypto.issue('login',loginId);
        const out=await tx.call('login_execute',{...auth,permit_id:r.payload.permitId,
          permit_digest:deps.crypto.proof('permit',r.payload.permitId as string,r.payload.secret),login_id:loginId,
          cookie_digest:material.digest,cookie_envelope:deps.crypto.seal({contextId,operationId,loginId},material.cookie)},v=>{
            const o=outcome(v,x=>loginResult(x,operationId));if(o.state!=='resolved')throw new PilotRecordUnavailable();return o.result;
          });
        if(out.status==='error')return refusal(out);
        result=out.data;
        if(result.kind==='pilot_login_rejected')return refusal({http:401,reasonCode:'AUTH_REQUIRED'});
      }
      const recovered=await tx.call('cookie_recover',auth,cookieReply);
      if(recovered.status==='error')return refusal(recovered);
      if(result&&result.loginId!==recovered.data.loginId)throw new PilotRecordUnavailable();
      const loginId=recovered.data.loginId;
      const raw=deps.crypto.open({contextId,operationId,loginId},recovered.data.cookieEnvelope);
      const body=result?{completion:completion(result,contextId)}:{loginId};
      return response(200,{...body,observedAt:recovered.observedAt,...nav},{
        'Set-Cookie':cookie('staff-login',loginId,raw,recovered.data.cookieExpiresAt),'X-Shadow-Login-Id':loginId});
    });
  };
}

export function createPilotReaderService(deps:Base & {crypto:ReaderCrypto}) {
  return async(frame:PilotFrame):Promise<PilotHttpReply>=>{
    const r=parsePilotRequest(frame.method,frame.target,frame.body),end=deadline(frame);
    if(!r||!['pilot_list','pilot_session','pilot_events','staff_existing'].includes(r.route))return refusal({http:404,reasonCode:'RESOURCE_NOT_FOUND'});
    return withPilotTransaction(deps.pool,'reader',deps.deploymentDigest,end,requestProof(),async tx=>{
      if(r.route==='staff_existing'&&(r.request.route==='logout_execute'||r.request.route==='logout_read')){
        const direct=r.request.route==='logout_execute',p=r.request.payload;
        const contextId=direct?p.logoutContextId as string:r.request.contextId!;
        const operationId=direct?p.authOperationId as string:r.request.operationId!;
        const out=await tx.call(direct?'logout_execute':'logout_read',{
          logout_context_id:contextId,logout_proof_digest:deps.crypto.proof('logout',contextId,proof(frame)),operation_id:operationId,
        },v=>logoutOutcome(v,operationId));
        if(out.status==='error')return refusal(out);
        if(direct){
          if(out.data.state!=='resolved')throw new PilotRecordUnavailable();
          if(frame.selectedLoginId!==null&&frame.selectedLoginId!==out.data.targetLoginId)throw new InputError();
          return response(204,null,{'Set-Cookie':`__Host-shadow-staff-login-${out.data.result.targetLoginId}=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0`});
        }
        return response(out.data.state==='resolved'?200:202,{operationRef:{logoutContextId:contextId,authOperationId:operationId,loginId:out.data.targetLoginId,commandType:'C07'},
          status:out.data.state==='resolved'?'completed':'unresolved',confirmedAt:out.data.state==='resolved'?out.data.result!.completedAt:null,observedAt:out.observedAt,...nav});
      }
      const loginId=selected(frame),auth={login_id:loginId,cookie_digest:deps.crypto.proof('login',loginId,proof(frame))};
      if(r.route==='pilot_list') {
        const out=await tx.call('session_list',auth,(v,observedAt)=>{const d=closed(v,['sessions']);return decodePilotList({...d,observedAt});});
        return out.status==='error'?refusal(out):response(200,{...out.data,...nav});
      }
      if(r.route==='pilot_session') {
        const out=await tx.call('session_read',{...auth,session_id:r.sessionId},v=>decodePilotSession(v,r.sessionId));
        return out.status==='error'?refusal(out):response(200,{...out.data,...nav});
      }
      if(r.route==='pilot_events') {
        const out=await tx.call('session_events',{...auth,session_id:r.sessionId},(v,observedAt)=>{
          const d=closed(v,['events']);return decodePilotEvents({...d,sessionId:r.sessionId,observedAt},r.sessionId);
        });
        return out.status==='error'?refusal(out):response(200,{...out.data,...nav});
      }
      if(r.route!=='staff_existing')throw new PilotRecordUnavailable();
      if(r.request.route==='R28') {
        const out=await tx.call('own_me',auth,v=>meReply(v,loginId));
        return out.status==='error'?refusal(out):response(200,{authenticated:true,staff:{staffId:out.data.staffId},observedAt:out.data.observedAt,...nav},{'X-Shadow-Login-Id':loginId});
      }
      if(r.request.route!=='logout_prepare'&&r.request.route!=='logout_continue')return refusal({http:404,reasonCode:'RESOURCE_NOT_FOUND'});
      const continuation=r.request.route==='logout_continue',id=randomUUID(),material=deps.crypto.issue(id);
      const out=await tx.call(continuation?'logout_continue':'logout_prepare',{...auth,logout_context_id:id,logout_proof_digest:material.digest,
        ...(continuation?{source_context_id:r.request.payload.sourceLogoutContextId,mode:r.request.payload.authorizationMode}:{})},v=>logoutContextReply(v,id,continuation?r.request.payload.sourceLogoutContextId as string:null));
      return out.status==='error'?refusal(out):response(201,{logoutContext:out.data,observedAt:out.observedAt,...nav},{'Set-Cookie':cookie('stafflogoutctx',id,material.cookie,out.data.expiresAt)});
    });
  };
}
