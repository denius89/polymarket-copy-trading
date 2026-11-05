import type { Pool } from 'pg';
import { performance } from 'node:perf_hooks';
import { exactObject, InputError, positiveVersion, uuid } from '../http/input.ts';
import { withPolygonTransaction, RpcRefusal, StorageRecordUnavailable, StorageUnavailable } from '../storage/transaction.ts';
import type { PolygonTransaction } from '../storage/transaction.ts';
import { calculateEvaluationDeadline } from '../time/evaluation-deadline.ts';
import type { CalendarProfile } from '../time/evaluation-deadline.ts';
import { decodeSnapshot } from '../catalog/snapshot.ts';
import { c04Request, c05Request, c06Request } from './requests.ts';
import { decodeCommand, decodeDraft, decodeReview, decodeSession, timestamp } from './responses.ts';
import { encodeRaw, RAW_ENCODING } from './raw-codec.ts';
import type { createCursorCodec } from '../catalog/cursor.ts';
import type { ListRequest, CardRequest } from '../catalog/contracts.ts';

export interface TrustedUserProof {login_id: string; cookie_digest: string}
export interface ApiReply {status: number; body: Record<string, unknown>}
export type PaperOperation =
  | {kind:'identity'}
  | {kind:'catalog-list'; request:ListRequest}
  | {kind:'catalog-card'; request:CardRequest}
  | {kind:'save'; draftId:string|null; body:unknown}
  | {kind:'validate'; body:unknown}
  | {kind:'start'; body:unknown}
  | {kind:'draft'; draftId:string}
  | {kind:'session'; sessionId:string|null}
  | {kind:'command'; actorId:string; actorRealm:'user'; commandType:'C04'|'C06'; clientCommandId:string};
const navigation = (nextAction: string|null=null, nextActionParams:Record<string,unknown>={}) => ({nextAction,nextActionParams});
export function apiError(status:number, reasonCode:string, nextAction:string|null=null, params:Record<string,unknown>={}): ApiReply {
  return {status,body:{reasonCode,reasonDetails:[{code:reasonCode,params:{}}],...navigation(nextAction,params)}};
}
function identity(value: unknown): Record<string, any> {
  try {
    const v=exactObject(value,['http','user_id','read_context_id','scope_id','scope_revision']);
    if(v.http!==200||!uuid(v.user_id)||v.read_context_id!==v.user_id||!uuid(v.scope_id)||
      typeof v.scope_revision!=='string'||!v.scope_revision.startsWith(`q02-read-scope-v1:${v.scope_id}:`)||
      !positiveVersion(v.scope_revision.slice(`q02-read-scope-v1:${v.scope_id}:`.length)))throw new Error();
    return v;
  }catch{throw new StorageRecordUnavailable();}
}

export class PaperService {
  private readonly pool: Pick<Pool,'connect'>;
  private readonly cursor: Awaited<ReturnType<typeof createCursorCodec>>;
  private readonly calendar: CalendarProfile;
  private readonly startEnabled: boolean;
  constructor(config: {pool:Pick<Pool,'connect'>; cursor:Awaited<ReturnType<typeof createCursorCodec>>; calendar:CalendarProfile; startEnabled:boolean}) {
    this.pool=config.pool;this.cursor=config.cursor;this.calendar=config.calendar;this.startEnabled=config.startEnabled;
  }
  async execute(auth: TrustedUserProof, operation: PaperOperation, executionStartedAt=performance.now()): Promise<ApiReply> {
    let reference:Record<string,unknown>|undefined;
    let catalogVenueId:string|undefined;
    const write=['save','validate','start'].includes(operation.kind);
    try {
      let body: Record<string,unknown>|undefined;
      if(operation.kind==='save')body=c04Request(operation.body,operation.draftId!==null);
      if(operation.kind==='validate')body=c05Request(operation.body);
      if(operation.kind==='start'){
        body=c06Request(operation.body);
        if(!this.startEnabled)throw new StorageUnavailable();
      }
      return await withPolygonTransaction(this.pool,write?'command':'read',async tx=>{
        if(operation.kind==='identity') {
          const current=identity(await tx.call('current_identity',{auth}));
          return {status:200,body:{userId:current.user_id}};
        }
        if(operation.kind==='catalog-list'||operation.kind==='catalog-card'){
          const snapshot=decodeSnapshot(await tx.call('catalog_read',{auth,venue_code:operation.request.venueCode}),operation.request.venueCode);
          catalogVenueId=snapshot.venueId;
          if(operation.kind==='catalog-list')return {status:200,body:{...this.cursor.page(operation.request,snapshot),...navigation()}};
          const trader=snapshot.items.find(t=>t.traderId===operation.request.traderId);
          if(!trader)throw new InputError(404,'RESOURCE_NOT_FOUND');
          return {status:200,body:{trader,...navigation()}};
        }
        if(operation.kind==='draft')return {status:200,body:{...decodeDraft(await tx.call('q03_draft',{auth,draft_id:operation.draftId}),operation.draftId),...navigation()}};
        if(operation.kind==='session')return {status:200,body:{...decodeSession(await tx.call('q04_session',{auth,session_id:operation.sessionId}),operation.sessionId),...navigation()}};
        const current=identity(await tx.call('current_identity',{auth}));
        if(operation.kind==='command'){
          const result=decodeCommand(await tx.call('q05_command',{auth,command_type:operation.commandType,client_command_id:operation.clientCommandId,
            actor_id:operation.actorId,actor_realm:operation.actorRealm}),{actorId:current.user_id,commandType:operation.commandType,clientCommandId:operation.clientCommandId},true);
          return {status:result.status==='pending'?202:200,body:{...result,...await this.resultNavigation(tx,auth,result)}};
        }
        if(operation.kind==='validate'){
          const result=decodeReview(await tx.call('c05_validate',{auth,request:body}),current.user_id,body!.draftId as string,body!.expectedDraftVersion as string);
          const review=result.review;
          const next=review.allowedToStart?'review_setup':
            ['VENUE_REQUIRED','TRADER_REQUIRED'].includes(review.primaryReasonCode)?'select_trader':
            ['SIZING_MODE_REQUIRED','TIMEZONE_REQUIRED','NUMERIC_SETTINGS_INVALID'].includes(review.primaryReasonCode)?'continue_setup':null;
          return {status:200,body:{...result,...navigation(next,next?{draftId:review.draftId}:{})}};
        }
        const type=operation.kind==='save'?'C04':'C06';
        reference={actorRealm:'user',actorId:current.user_id,commandType:type,clientCommandId:body!.clientCommandId};
        let reply;
        if(operation.kind==='save')reply=await tx.call('c04_save',{auth,draft_id:operation.draftId,raw_encoding:RAW_ENCODING,request:encodeRaw(body!)});
        else {
          reply=await tx.call('c06_prepare',{auth,request:body});
          if('prepared'in reply){
            let p:Record<string,unknown>;
            try{p=exactObject(reply,['http','prepared','ticket_id','started_at','iana_timezone']);}
            catch{throw new StorageRecordUnavailable();}
            if(p.http!==200||p.prepared!==true||!uuid(p.ticket_id)||!timestamp(p.started_at)||typeof p.iana_timezone!=='string')throw new StorageRecordUnavailable();
            const deadline=calculateEvaluationDeadline(p.started_at as string,p.iana_timezone,this.calendar);
            reply=await tx.call('c06_finish',{auth,ticket_id:p.ticket_id,evaluation_deadline_at:deadline.evaluationDeadlineAt,
              deadline_calculation_version:deadline.deadlineCalculationVersion,timezone_database_version:deadline.timezoneDatabaseVersion});
          }
        }
        const result=decodeCommand(reply,{actorId:current.user_id,commandType:type,clientCommandId:body!.clientCommandId as string});
        return {status:reply.http,body:{...result,...await this.resultNavigation(tx,auth,result)}};
      },executionStartedAt);
    } catch(error) {
      if(error instanceof InputError){
        if(error.reasonCode==='CATALOG_CHANGED')return catalogVenueId
          ?apiError(409,'CATALOG_CHANGED','select_trader',{venueId:catalogVenueId})
          :apiError(503,'RECORD_UNAVAILABLE');
        return apiError(error.status,error.reasonCode);
      }
      if(error instanceof RpcRefusal){
        const code=error.response.reason as string;
        return apiError(error.response.http,code,code.startsWith('AUTH_')?'authenticate':code==='SERVICE_UNAVAILABLE'?'retry_later':null);
      }
      if(error instanceof StorageRecordUnavailable)return apiError(503,'RECORD_UNAVAILABLE');
      // A known reference is safe navigation only, never a success/receipt or permission to re-execute.
      return apiError(503,'SERVICE_UNAVAILABLE',reference?'resolve_command':'retry_later',reference?{commandRef:reference}:{});
    }
  }
  private async resultNavigation(tx:PolygonTransaction,auth:TrustedUserProof,result:Record<string,any>):Promise<Record<string,unknown>> {
    if(result.status==='pending')return navigation('resolve_command',{commandRef:result.commandRef});
    const r=result.receipt;
    if(r.outcome!=='succeeded')return navigation();
    try {
      if(r.commandType==='C06'){
        decodeSession(await tx.call('q04_session',{auth,session_id:r.result.sessionId}),r.result.sessionId);
        return navigation('view_session',{sessionId:r.result.sessionId});
      }
      const {draft}=decodeDraft(await tx.call('q03_draft',{auth,draft_id:r.result.draftId}),r.result.draftId);
      if(draft.state==='editable')return navigation(draft.draftVersion===r.result.draftVersion?'continue_setup':'recover_setup',{draftId:draft.draftId});
      return navigation('recover_setup',{draftId:draft.draftId});
    }catch(error){
      if(error instanceof RpcRefusal&&(error.response.http===403||error.response.http===404))return navigation();
      throw error;
    }
  }
}
