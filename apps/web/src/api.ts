export type Locale = 'ru' | 'en';
export type VenueCode = 'polymarket' | 'limitless';
export type NextAction = 'authenticate'|'complete_totp'|'enroll_totp'|'select_trader'|'continue_setup'|'review_setup'|'view_session'|'resolve_command'|'retry_later'|null;
export interface ApiProblem { reasonCode: string; reasonDetails?: { code:string; params:Record<string,unknown> }[]; nextAction: NextAction; nextActionParams: Record<string,unknown> }
export class ApiError extends Error {
  constructor(public readonly status:number, public readonly reasonCode:string, public readonly nextAction:NextAction=null, public readonly details:unknown=null) { super(reasonCode); }
}
let selectedLoginId: string|null = sessionStorage.getItem('shadow.selectedLoginId');
export function getSelectedLoginId() { return selectedLoginId; }
export function setSelectedLoginId(value:string|null) { selectedLoginId=value; if(value)sessionStorage.setItem('shadow.selectedLoginId',value);else sessionStorage.removeItem('shadow.selectedLoginId'); }
export interface ApiResult<T> { data:T; status:number; headers:Headers }
export async function api<T>(path:string, init:RequestInit={}, options:{signal?:AbortSignal; loginId?:string|null; interactive?:boolean}={}):Promise<ApiResult<T>> {
  const method=(init.method||'GET').toUpperCase();
  const headers=new Headers(init.headers);
  if(method!=='GET' && method!=='HEAD') { headers.set('Content-Type','application/json'); headers.set('X-Shadow-Auth-Request','1'); }
  const loginId=options.loginId===undefined?selectedLoginId:options.loginId;
  if(loginId) headers.set('X-Shadow-Login-Id',loginId);
  const controller=new AbortController();
  const timer=window.setTimeout(()=>controller.abort(),10000);
  const onAbort=()=>controller.abort();
  options.signal?.addEventListener('abort',onAbort,{once:true});
  try {
    const response=await fetch(path,{...init,headers,credentials:'same-origin',cache:'no-store',signal:controller.signal});
    const raw=response.status===204?null:await response.json().catch(()=>null);
    if(!response.ok) {
      const problem=raw as Partial<ApiProblem>|null;
      throw new ApiError(response.status,problem?.reasonCode||`HTTP_${response.status}`,problem?.nextAction||null,problem);
    }
    return {data:raw as T,status:response.status,headers:response.headers};
  } catch(error) {
    if(error instanceof ApiError) throw error;
    throw new ApiError(0,controller.signal.aborted?'REQUEST_TIMEOUT':'NETWORK_UNAVAILABLE',null,error);
  } finally { window.clearTimeout(timer); options.signal?.removeEventListener('abort',onAbort); }
}
const q='?requestSchemaVersion=v1';
const post=(path:string,body:Record<string,unknown>,options?:{loginId?:string|null})=>api<any>(path,{method:'POST',body:JSON.stringify(body)},options);
export const id=()=>crypto.randomUUID();
export interface AuthContext { authContextId:string; expiresAt?:string }
export interface AuthReply { status?:'resolved'|'unresolved'; result?: {kind:string;challengeId?:string;stage?:string;challengeExpiresAt?:string;completion?:{loginId:string}}; completion?:{loginId:string}; nextAction?:NextAction }
export async function createAuthContext():Promise<AuthContext> { const r=await post('/api/auth/contexts',{requestSchemaVersion:'v1'},{loginId:null}); return r.data.authContext; }
export async function confirmAuthContext(contextId:string):Promise<AuthContext> { const r=await api<{authContext:AuthContext}>(`/api/auth/contexts/${contextId}${q}`,{}, {loginId:null}); return r.data.authContext; }
export async function requestEmail(contextId:string,email:string,operationId:string):Promise<AuthReply> { const r=await post('/api/auth/request',{requestSchemaVersion:'v1',commandType:'C01',authContextId:contextId,authOperationId:operationId,email,locale:'en'},{loginId:null});return r.data; }
export async function verifyEmail(contextId:string,challengeId:string,code:string,operationId:string):Promise<AuthReply> { const r=await post('/api/auth/verify',{requestSchemaVersion:'v1',commandType:'C02',authContextId:contextId,authOperationId:operationId,challengeId,code},{loginId:null});return r.data; }
export async function verifyTotp(contextId:string,challengeId:string,code:string,operationId:string):Promise<AuthReply> { const r=await post('/api/auth/totp/verify',{requestSchemaVersion:'v1',commandType:'AUTH_TOTP_VERIFY',authContextId:contextId,authOperationId:operationId,challengeId,code},{loginId:null});return r.data; }
export async function readAuthOperation(contextId:string,operationId:string,commandType:string):Promise<AuthReply> { const r=await api<AuthReply>(`/api/auth/contexts/${contextId}/operations/${operationId}${q}&commandType=${commandType}`,{}, {loginId:null});return r.data; }
export async function confirmLogin(loginId:string):Promise<{authenticated:boolean;user?:unknown;loginId:string}> { const r=await api<{authenticated:boolean;user?:unknown}>(`/api/me${q}`,{}, {loginId});const observed=r.headers.get('X-Shadow-Login-Id');if(!r.data.authenticated||observed!==loginId)throw new ApiError(401,'LOGIN_NOT_CONFIRMED');setSelectedLoginId(loginId);return {...r.data,loginId}; }
export async function currentUser():Promise<{authenticated:boolean;user?:unknown;loginId:string}> { const loginId=getSelectedLoginId();if(!loginId)throw new ApiError(401,'AUTH_REQUIRED');return confirmLogin(loginId); }
export interface Trader { traderId:string;venueId:string;venueCode:VenueCode;displayName:string;externalTraderId:string;dataOrigin:string;startAvailability:{available:boolean;capabilityReasonCode:string|null};observedAt:string }
export interface TraderList { venueCode:VenueCode;items:Trader[];nextCursor:string|null }
export async function getTraders(venueCode:VenueCode,cursor?:string,signal?:AbortSignal):Promise<TraderList> { const params=new URLSearchParams({requestSchemaVersion:'v1',venueCode,limit:'20'});if(cursor)params.set('cursor',cursor);const r=await api<TraderList>(`/api/traders?${params}`,{}, {signal});return r.data; }
export async function getTrader(venueCode:VenueCode,traderId:string,signal?:AbortSignal):Promise<Trader> { const r=await api<{trader:Trader}>(`/api/traders/${venueCode}/${traderId}${q}`,{}, {signal});return r.data.trader; }
export interface CopyInputs {selectedMode:'fixed'|'percent';rawBudget:string;rawFixedAmount:string;rawCopyPercent:string;rawMarketLimitPercent:string;rawDailyBuyLimitPercent:string;proposedTimezone:string|null}
export interface CommandRef {actorRealm:'user'|'guest';actorId:string;commandType:'C04'|'C06';clientCommandId:string}
const uuidValue=(value:unknown):value is string=>typeof value==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value);
export function parseCommandRef(value:unknown,type:'C04'|'C06',clientCommandId:string):CommandRef|null {
  if(!value||typeof value!=='object'||Array.isArray(value))return null;
  const ref=value as Record<string,unknown>;
  if(ref.actorRealm!=='user'||!uuidValue(ref.actorId)||ref.commandType!==type||ref.clientCommandId!==clientCommandId)return null;
  return ref as unknown as CommandRef;
}
export function commandRefFromError(error:unknown,type:'C04'|'C06',clientCommandId:string):CommandRef|null {
  if(!(error instanceof ApiError)||error.nextAction!=='resolve_command'||!error.details||typeof error.details!=='object')return null;
  const params=(error.details as ApiProblem).nextActionParams;
  return params&&typeof params==='object'?parseCommandRef(params.commandRef,type,clientCommandId):null;
}
export interface CommandReceipt { outcome:'succeeded'|'rejected';reasonCode:string|null;result:Record<string,string>|null;fieldErrors?:{field:string;code:string}[] }
export interface CommandReply {commandRef:CommandRef;receipt:CommandReceipt;nextAction:NextAction;nextActionParams:Record<string,unknown>}
export async function saveDraft(inputs:CopyInputs, trader:Trader, locale:Locale, commandId:string, draft?:{draftId:string;draftVersion:string}):Promise<CommandReply> {
  const body={requestSchemaVersion:'v1',clientCommandId:commandId,locale,step:'configure',entryContext:'catalog',venueId:trader.venueId,traderId:trader.traderId,...inputs,...(draft?{expectedDraftVersion:draft.draftVersion}:{})};
  const path=draft?`/api/demo/drafts/${draft.draftId}`:'/api/demo/drafts';
  const r=await api<CommandReply>(path,{method:draft?'PATCH':'POST',body:JSON.stringify(body)});return r.data;
}
export interface Review {reviewId:string;draftId:string;draftVersion:string;ownerKind:'user'|'guest';allowedToStart:boolean;requiresAuthentication:boolean;primaryReasonCode:string|null;reasonDetails:{code:string;params:Record<string,unknown>}[];warnings:{code:string;params:Record<string,unknown>}[];expectedSlot:{state:'absent'|'present'|'not_applicable';generation?:string};rawBudget:string|null;rawFixedAmount:string|null;rawCopyPercent:string|null;selectedMode:'fixed'|'percent'|null;expiresAt:string}
export async function validateDraft(draftId:string,draftVersion:string,proposedTimezone:string|null):Promise<Review> {const r=await post('/api/demo/validate',{requestSchemaVersion:'v1',draftId,expectedDraftVersion:draftVersion,proposedTimezone});return r.data.review;}
export async function launchSession(review:Review,commandId:string):Promise<CommandReply> {const r=await post('/api/sessions',{requestSchemaVersion:'v1',clientCommandId:commandId,reviewId:review.reviewId,expectedDraftVersion:review.draftVersion,expectedSlot:review.expectedSlot});return r.data;}
export async function resolveCommand(ref:CommandRef):Promise<{status:'committed'|'rejected'|'pending';receipt:CommandReceipt|null}> { const params=new URLSearchParams({requestSchemaVersion:'v1',commandType:ref.commandType,actorRealm:ref.actorRealm,actorId:ref.actorId});const r=await api<{status:'committed'|'rejected'|'pending';receipt:CommandReceipt|null}>(`/api/commands/${ref.clientCommandId}?${params}`);return r.data; }
export interface MoneyValue { n:string; d:string }
export interface CurrentSession {
  summary:{mode:'paper';dataOrigin:'synthetic';traderDisplayName:string;venueId:string;controlState:string;contentState:string;asOf:string};
  settings:{sizingMode:'fixed'|'percent';budget:MoneyValue;fixedAmount:MoneyValue|null;copyPercent:string|null;marketLimitPercent:string;dailyBuyLimitPercent:string};
  financialSnapshot:{dataOrigin:'synthetic';controlState:string;free:MoneyValue;equity:MoneyValue;reserved:MoneyValue;positionValue:MoneyValue;tradingResult:MoneyValue;positionCount:string;orderCount:string;contentState:string;coverageState:string};
}
export interface CurrentSessionResponse { session:CurrentSession|null }
const record=(value:unknown):value is Record<string,unknown>=>typeof value==='object'&&value!==null&&!Array.isArray(value);
const moneyValue=(value:unknown):value is MoneyValue=>record(value)&&typeof value.n==='string'&&/^\d+$/.test(value.n)&&typeof value.d==='string'&&/^[1-9]\d*$/.test(value.d);
export async function currentSession(signal?:AbortSignal):Promise<CurrentSessionResponse> {
  const r=await api<unknown>(`/api/sessions/current${q}`,{}, {signal});
  const body=r.data;
  if(!record(body)||!('session' in body))throw new ApiError(502,'INVALID_SESSION_RESPONSE');
  if(body.session===null)return {session:null};
  if(!record(body.session))throw new ApiError(502,'INVALID_SESSION_RESPONSE');
  const {summary,settings,financialSnapshot}=body.session;
  if(!record(summary)||!record(settings)||!record(financialSnapshot)||
    summary.mode!=='paper'||summary.dataOrigin!=='synthetic'||typeof summary.traderDisplayName!=='string'||typeof summary.venueId!=='string'||
    typeof summary.controlState!=='string'||typeof summary.contentState!=='string'||typeof summary.asOf!=='string'||Number.isNaN(Date.parse(summary.asOf))||
    !['fixed','percent'].includes(String(settings.sizingMode))||!moneyValue(settings.budget)||
    (settings.fixedAmount!==null&&!moneyValue(settings.fixedAmount))||
    (settings.copyPercent!==null&&typeof settings.copyPercent!=='string')||
    typeof settings.marketLimitPercent!=='string'||typeof settings.dailyBuyLimitPercent!=='string'||
    !moneyValue(financialSnapshot.free)||!moneyValue(financialSnapshot.equity)||
    !moneyValue(financialSnapshot.reserved)||!moneyValue(financialSnapshot.positionValue)||
    !moneyValue(financialSnapshot.tradingResult)||!/^\d+$/.test(String(financialSnapshot.positionCount))||
    !/^\d+$/.test(String(financialSnapshot.orderCount))||typeof financialSnapshot.contentState!=='string'||
    financialSnapshot.dataOrigin!=='synthetic'||typeof financialSnapshot.controlState!=='string'||
    typeof financialSnapshot.coverageState!=='string'||summary.contentState!==financialSnapshot.contentState||
    summary.controlState!==financialSnapshot.controlState||
    (summary.contentState==='EMPTY'&&(summary.controlState!=='copying_not_connected'||financialSnapshot.positionCount!=='0'||financialSnapshot.orderCount!=='0'))
  )throw new ApiError(502,'INVALID_SESSION_RESPONSE');
  return body as unknown as CurrentSessionResponse;
}
export async function readDraft(draftId:string):Promise<{draft:{draftId:string;draftVersion:string;proposedTimezone:string|null}}>{const r=await api<{draft:{draftId:string;draftVersion:string;proposedTimezone:string|null}}>(`/api/demo/drafts/${draftId}${q}`);return r.data;}
