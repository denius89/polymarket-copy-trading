import { exactObject, positiveVersion, uuid, validUnicode } from '../http/input.ts';
import { StorageRecordUnavailable } from '../storage/transaction.ts';
import { RAW_FIELDS } from './requests.ts';
import { decodeRaw } from './raw-codec.ts';

type Check = (value: unknown) => boolean;
type RecordValue = Record<string, any>;
const bad = (): never => {throw new StorageRecordUnavailable();};
const isNull: Check = v => v === null;
const bool: Check = v => typeof v === 'boolean';
const str: Check = v => typeof v === 'string' && v.length > 0 && validUnicode(v);
const one = (...values: unknown[]): Check => v => values.includes(v);
const nullable = (check: Check): Check => v => v === null || check(v);
export const timestamp: Check = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(v) &&
  Number.isFinite(Date.parse(v)) && new Date(v).toISOString() === v;
const raw: Check = v => v === null || (typeof v === 'string' && validUnicode(v) && [...v].length <= 64);
const percent: Check = v => typeof v === 'string' && /^(0|[1-9][0-9]{0,61})\.[0-9]{2}$/.test(v);
const integer: Check = v => typeof v === 'string' && /^(0|[1-9][0-9]{0,63})$/.test(v);
function record(value: unknown, shape: Record<string, Check>): RecordValue {
  try {
    const v = exactObject(value, Object.keys(shape));
    if (Object.entries(shape).some(([k,check]) => !check(v[k]))) return bad();
    return v;
  } catch {return bad();}
}
const fields = (names: string, check: Check) => Object.fromEntries(names.split(' ').map(k => [k, check]));
export const money: Check = value => {
  try {
    const v=record(value,{n:integer,d:integer});let a=BigInt(v.n),b=BigInt(v.d);
    if(b===0n)return false;
    while(b!==0n){const next=a%b;a=b;b=next;}
    return a===1n;
  } catch {return false;}
};
const positiveMoney: Check = v => money(v) && (v as RecordValue).n !== '0';
const empty: Check = v => {try {exactObject(v,[]);return true;}catch{return false;}};
const array: Check = Array.isArray;
const capabilities=['PAPER_START_DISABLED','CATALOG_SOURCE_DISABLED','TRADER_START_DISABLED'];
const priorities = {
  C04:['DRAFT_USED','DRAFT_EXPIRED','VERSION_CONFLICT'],
  C06:['DRAFT_USED','DRAFT_EXPIRED','VERSION_CONFLICT','SESSION_NOT_SETTLED','CURRENT_SESSION_EXISTS','CAPABILITY_UNAVAILABLE','REVIEW_EXPIRED','REVIEW_STALE','SETUP_INVALID'],
  review:['AUTH_REQUIRED','SESSION_NOT_SETTLED','CURRENT_SESSION_EXISTS','CAPABILITY_UNAVAILABLE','VENUE_REQUIRED','TRADER_REQUIRED','SIZING_MODE_REQUIRED','TIMEZONE_REQUIRED','NUMERIC_SETTINGS_INVALID'],
};
function reasons(value: unknown, context: keyof typeof priorities, primary: unknown): void {
  if (!Array.isArray(value) || value.length > priorities[context].length) bad();
  let last=-1;
  for(const item of value as unknown[]) {
    const r=record(item,{code:str,params:v=>!!v&&typeof v==='object'&&!Array.isArray(v)});
    const index=priorities[context].indexOf(r.code);
    if(index<=last)bad();last=index;
    if(r.code==='CAPABILITY_UNAVAILABLE')record(r.params,{capabilityReasonCode:one(...capabilities)});
    else if(!empty(r.params))bad();
  }
  if(primary===null ? (value as unknown[]).length!==0 : (value as RecordValue[])[0]?.code!==primary)bad();
}
export function fieldErrors(value: unknown, mode?: unknown): void {
  if(!Array.isArray(value)||value.length>4)bad();
  let last=-1, sizing=0;
  for(const item of value as unknown[]) {
    const e=record(item,{field:one(...RAW_FIELDS),code:one('REQUIRED','INVALID_DECIMAL','OUT_OF_RANGE','INVALID_STEP','FIXED_LIMIT_EXCEEDED'),params:v=>!!v&&typeof v==='object'&&!Array.isArray(v)});
    const index=RAW_FIELDS.indexOf(e.field);if(index<=last)bad();last=index;
    if(index===1||index===2){sizing++;if(sizing>1||(mode!==undefined&&mode!==(index===1?'fixed':'percent')))bad();}
    const isMoney=e.field==='rawBudget'||e.field==='rawFixedAmount';
    const unit=one(isMoney?'virtual_USD':'percentage_points'),number=isMoney?money:percent;
    const rational=(v:any):[bigint,bigint]=>isMoney?[BigInt(v.n),BigInt(v.d)]:[BigInt(v.replace('.','')),100n];
    if(e.code==='REQUIRED'||e.code==='INVALID_DECIMAL'){if(!empty(e.params))bad();}
    else if(e.code==='OUT_OF_RANGE'){
      const p=record(e.params,{min:number,max:number,unit});const [a,b]=rational(p.min),[c,d]=rational(p.max);if(a*d>c*b)bad();
    }else if(e.code==='INVALID_STEP'){
      const p=record(e.params,{step:number,origin:number,unit});if(rational(p.step)[0]===0n)bad();
    }else {if(e.field!=='rawFixedAmount')bad();record(e.params,{max:money,unit:one('virtual_USD')});}
  }
}
function boundedDetails(reasonsValue: unknown, errorsValue: unknown): void {
  if(Buffer.byteLength(JSON.stringify({reasons:reasonsValue,fieldErrors:errorsValue}),'utf8')>16384)bad();
}
export function commandRef(value: unknown, expected?: {actorId?: string; commandType?: string; clientCommandId?: string}): RecordValue {
  const v=record(value,{actorRealm:one('user'),actorId:uuid,commandType:one('C04','C06'),clientCommandId:uuid});
  for(const [k,wanted]of Object.entries(expected??{}))if(wanted!==undefined&&v[k]!==wanted)bad();
  return v;
}
export function receipt(value: unknown, type: 'C04'|'C06'): RecordValue {
  const success=(value as RecordValue)?.outcome==='succeeded';
  const v=record(value,{receiptId:uuid,recordSchemaVersion:one('v1'),commandType:one(type),outcome:one('succeeded','rejected'),createdAt:timestamp,
    reasonCode:nullable(str),reasonDetails:array,result:success?v=>!!v&&typeof v==='object'&&!Array.isArray(v):isNull,
    ...(success&&type==='C04'?{fieldErrors:array}:{})});
  reasons(v.reasonDetails,type,v.reasonCode);
  if(success){
    if(v.reasonCode!==null)bad();
    if(type==='C04'){
      record(v.result,{draftId:uuid,ownershipId:uuid,draftVersion:positiveVersion,changeKind:one('created','updated','unchanged'),lastSavedAt:timestamp,expiresAt:timestamp});
      if(v.result.expiresAt<=v.result.lastSavedAt)bad();fieldErrors(v.fieldErrors);
      if(Buffer.byteLength(JSON.stringify({fieldErrors:v.fieldErrors}))>16384)bad();
    }else record(v.result,{sessionId:uuid,settingsRevisionId:uuid,snapshotVersion:one('1'),sessionVersion:one('1')});
  }else if(v.reasonCode===null)bad();
  if(Buffer.byteLength(JSON.stringify({reasons:v.reasonDetails}))>16384)bad();
  return v;
}
export function decodeCommand(value: unknown, expected: {actorId?: string; commandType: 'C04'|'C06'; clientCommandId: string}, lookup=false): RecordValue {
  const v=record(value,{http:n=>Number.isInteger(n),command_ref:x=>!!x&&typeof x==='object',receipt:()=>true,...(lookup?{status:one('committed','rejected','pending')}:{})});
  const ref=commandRef(v.command_ref,expected);
  if(lookup&&v.status==='pending') {if(v.http!==202||v.receipt!==null)bad();return {commandRef:ref,status:'pending',receipt:null};}
  const r=receipt(v.receipt,expected.commandType);
  const http=lookup?200:r.outcome==='rejected'?409:r.commandType==='C06'||r.result.changeKind==='created'?201:200;
  if(v.http!==http||(lookup&&v.status!==(r.outcome==='succeeded'?'committed':'rejected')))bad();
  return {commandRef:ref,receipt:r,...(lookup?{status:v.status}:{})};
}
function slot(value: unknown): boolean {
  try{const v=value as RecordValue;if(v?.state==='absent')exactObject(v,['state']);else record(v,{state:one('present'),generation:positiveVersion});return true;}catch{return false;}
}
const normalized={budget:positiveMoney,fixedAmount:nullable(positiveMoney),copyPercent:nullable(percent),marketLimitPercent:percent,dailyBuyLimitPercent:percent,effectiveMarketLimit:positiveMoney,effectiveDailyBuyLimit:positiveMoney};
function checkNormalization(v: RecordValue, mode: unknown, valid=true): void {
  if(!valid){if(Object.keys(normalized).some(k=>v[k]!==null))bad();return;}
  if(Object.entries(normalized).some(([k,check])=>!check(v[k])))bad();
  if(mode==='fixed'){if(v.fixedAmount===null||v.copyPercent!==null)bad();}
  else if(mode==='percent'){if(v.copyPercent===null||v.fixedAmount!==null)bad();}else bad();
}
export function decodeReview(value: unknown, userId: string, draftId: string, version: string): RecordValue {
  const root=record(value,{http:one(200),raw_encoding:one('utf8-base64-v1'),review:v=>!!v&&typeof v==='object'});
  const v=record(decodeRaw(root.review,root.raw_encoding),{
    ...fields('reviewId draftId ownershipId policyVersionId paperControlId',uuid),recordSchemaVersion:one('v1'),draftVersion:positiveVersion,
    ownerKind:one('user'),ownerUserId:uuid,...fields('venueId catalogSourceId traderId traderRevisionId',nullable(uuid)),
    ...fields('catalogVersion traderControlVersion',nullable(positiveVersion)),paperControlVersion:positiveVersion,selectedMode:one('fixed','percent',null),
    ...Object.fromEntries(RAW_FIELDS.map(k=>[k,raw])),proposedTimezone:nullable(str),normalizationValid:bool,
    ...Object.fromEntries(Object.keys(normalized).map(k=>[k,()=>true])),expectedSlot:slot,allowedToStart:bool,requiresAuthentication:one(false),
    primaryReasonCode:nullable(str),reasonDetails:array,fieldErrors:array,warnings:array,...fields('checkedAt expiresAt createdAt',timestamp),
  });
  if(v.ownerUserId!==userId||v.draftId!==draftId||v.draftVersion!==version||Date.parse(v.expiresAt)-Date.parse(v.checkedAt)!==600000)bad();
  const traderGroup=['catalogSourceId','traderId','traderRevisionId','catalogVersion','traderControlVersion'];
  if(v.traderId===null?traderGroup.some(k=>v[k]!==null):traderGroup.some(k=>v[k]===null)||v.venueId===null)bad();
  checkNormalization(v,v.selectedMode,v.normalizationValid);reasons(v.reasonDetails,'review',v.primaryReasonCode);fieldErrors(v.fieldErrors,v.selectedMode);boundedDetails(v.reasonDetails,v.fieldErrors);
  if(v.reasonDetails.some((r:RecordValue)=>r.code==='AUTH_REQUIRED')||
    (v.allowedToStart?(v.primaryReasonCode!==null||v.fieldErrors.length!==0||!v.normalizationValid):v.primaryReasonCode===null))bad();
  if(v.fieldErrors.length>0&&!v.reasonDetails.some((r:RecordValue)=>r.code==='NUMERIC_SETTINGS_INVALID'))bad();
  if(v.normalizationValid&&v.fieldErrors.length!==0)bad();
  if(v.allowedToStart&&(v.venueId===null||v.traderId===null||v.proposedTimezone===null))bad();
  const warningOrder=['SYNTHETIC_DATA','COPYING_NOT_CONNECTED'];let last=-1;
  for(const item of v.warnings){const w=record(item,{code:one(...warningOrder),params:empty});const index=warningOrder.indexOf(w.code);if(index<=last)bad();last=index;}
  return {review:v};
}
export function decodeDraft(value: unknown, draftId: string): RecordValue {
  const root=record(value,{http:one(200),raw_encoding:one('utf8-base64-v1'),draft:v=>!!v&&typeof v==='object',field_errors:array,field_errors_source:v=>!!v&&typeof v==='object'});
  const d=record(decodeRaw(root.draft,root.raw_encoding),{...fields('draftId currentOwnershipId',uuid),draftVersion:positiveVersion,ownerKind:one('user'),state:one('editable','expired','used'),
    locale:one('ru','en'),step:one('select_trader','configure','review'),entryContext:one('catalog','trader_details','session_summary',null),
    venueId:nullable(uuid),traderId:nullable(uuid),selectedMode:one('fixed','percent',null),...Object.fromEntries(RAW_FIELDS.map(k=>[k,raw])),proposedTimezone:nullable(str),
    ...fields('lastSavedAt expiresAt createdAt updatedAt',timestamp),usedAt:nullable(timestamp),usedBySessionId:nullable(uuid)});
  if(d.draftId!==draftId||(d.traderId!==null&&d.venueId===null)||(d.state==='used'?(d.usedAt===null||d.usedBySessionId===null):(d.usedAt!==null||d.usedBySessionId!==null)))bad();
  const source=record(root.field_errors_source,{receiptId:uuid,draftVersion:one(d.draftVersion)});fieldErrors(root.field_errors,d.selectedMode);
  return {draft:d,fieldErrors:root.field_errors,fieldErrorsSource:source};
}
export function decodeSession(value: unknown, expectedId: string|null): RecordValue {
  const root=record(value,{http:one(200),session:()=>true});
  if(root.session===null){if(expectedId!==null)bad();return {session:null};}
  const s=record(root.session,{summary:v=>!!v&&typeof v==='object',settings:v=>!!v&&typeof v==='object',financialSnapshot:v=>!!v&&typeof v==='object'});
  const summary=record(s.summary,{...fields('sessionId venueId catalogSourceId traderId traderRevisionId settingsRevisionId',uuid),mode:one('paper'),traderDisplayName:str,
    dataOrigin:one('synthetic'),lifecycle:one('active'),controlState:one('copying_not_connected'),contentState:one('EMPTY'),coverageState:one('no_trade_data'),
    ...fields('sessionVersion snapshotVersion',positiveVersion),...fields('asOf startedAt evaluationDeadlineAt createdAt updatedAt',timestamp),ianaTimezone:str,
    deadlineCalculationVersion:one('paper-evaluation-deadline-v1'),timezoneDatabaseVersion:str});
  if((expectedId!==null&&summary.sessionId!==expectedId)||summary.evaluationDeadlineAt<=summary.startedAt)bad();
  const settings=record(s.settings,{...fields('settingsRevisionId sessionId policyVersionId commandReceiptId',uuid),recordSchemaVersion:one('v1'),sequence:one('1'),previousRevisionId:isNull,
    sizingMode:one('fixed','percent'),...normalized,calculationVersion:one('paper-settings-calculation-v1'),signalMaxAgeSeconds:one(30),createdAt:timestamp});
  checkNormalization(settings,settings.sizingMode);
  const snapshot=record(s.financialSnapshot,{...fields('snapshotId sessionId settingsRevisionId',uuid),recordSchemaVersion:one('v1'),...fields('snapshotVersion sessionVersion ledgerSequence',positiveVersion),
    projectionCalculationVersion:one('paper-empty-snapshot-v1'),lifecycle:one('active'),controlState:one('copying_not_connected'),contentState:one('EMPTY'),dataOrigin:one('synthetic'),coverageState:one('no_trade_data'),unit:one('virtual_USD'),
    ...fields('initialFunding free equity',positiveMoney),...fields('reserved positionCost positionValue tradingResult',money),...fields('tradeCount positionCount orderCount',one('0')),...fields('asOf createdAt',timestamp)});
  for(const key of ['sessionId','settingsRevisionId','snapshotVersion','sessionVersion','asOf','lifecycle','controlState','contentState','dataOrigin','coverageState'])if(summary[key]!==snapshot[key])bad();
  if(settings.sessionId!==summary.sessionId||settings.settingsRevisionId!==summary.settingsRevisionId)bad();
  for(const key of ['initialFunding','free','equity'])if(snapshot[key].n!==settings.budget.n||snapshot[key].d!==settings.budget.d)bad();
  for(const key of ['reserved','positionCost','positionValue','tradingResult'])if(snapshot[key].n!=='0'||snapshot[key].d!=='1')bad();
  return {session:s};
}
