import {REVIEW_PROFILE,isReviewTrader} from './review-profile.mjs';
/** Empty-session boundary; database remains responsible for authorization. */
export class BoundaryError extends Error {
  constructor(status, reasonCode, reasonParams={}) { super(reasonCode); this.status=status; this.reasonCode=reasonCode; this.reasonParams=Object.freeze({...reasonParams}); }
}
const invalid=()=>{throw new BoundaryError(400,'INVALID_REQUEST');};
const corrupt=()=>{throw new BoundaryError(503,'RECORD_UNAVAILABLE');};
export const isVenue=v=>v==='polymarket'||v==='limitless';
export const isUuid=v=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
export const isVersion=v=>typeof v==='string'&&/^[1-9][0-9]{0,18}$/.test(v)&&BigInt(v)<=9223372036854775807n;
export const isTimestamp=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString()===v;
export const isText=(v,max=512)=>typeof v==='string'&&v.length>0&&v.length<=max&&!/[\u0000-\u001f\u007f]/u.test(v)&&!/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(v);
export function exact(v,keys,fail=corrupt) {
  if(v===null||typeof v!=='object'||Array.isArray(v)||Object.keys(v).length!==keys.length||Object.keys(v).some(k=>!keys.includes(k)))fail();
  return v;
}
export function canonicalAccount(value,fail=invalid) {
  if(typeof value!=='string'||!/^0x[0-9a-fA-F]{40}$/.test(value))fail();
  return value.toLowerCase();
}

/** Addresses only for the two current public catalogs. No name/URL/UUID fallback. */
export function parseResolveRequest(rawQuery,bodyBytes=0) {
  if(typeof rawQuery!=='string'||rawQuery.length>1024||bodyBytes!==0)invalid();
  const q=new Map();
  for(const part of rawQuery.replace(/^\?/,'').split('&')) {
    const split=part.indexOf('='); if(split<0)invalid();
    let key,value;
    try {
      key=decodeURIComponent(part.slice(0,split).replaceAll('+',' '));
      value=decodeURIComponent(part.slice(split+1).replaceAll('+',' '));
    } catch {invalid();}
    if(!['requestSchemaVersion','venueCode','externalTraderId'].includes(key)||q.has(key))invalid();
    q.set(key,value);
  }
  if(q.size!==3||q.get('requestSchemaVersion')!=='v1'||!isVenue(q.get('venueCode')))invalid();
  return Object.freeze({venueCode:q.get('venueCode'),externalTraderId:canonicalAccount(q.get('externalTraderId'))});
}

const traderKeys=['traderId','venueId','catalogSourceId','venueCode','externalTraderId','displayName',
  'traderRevisionId','traderRevision','dataOrigin','sourceRef','observedAt','revisionCreatedAt',
  'catalogVersionAtCreation','catalogVersion','traderControlVersion','paperControlVersion','startAvailability'];

/** Candidate real-origin DTO; does not broaden the installed synthetic decoder. */
export function decodeRealTrader(value,request) {
  const v=exact(value,traderKeys);
  if(!['traderId','venueId','catalogSourceId','traderRevisionId'].every(k=>isUuid(v[k]))||
    v.venueCode!==request.venueCode||!isVenue(v.venueCode)||v.dataOrigin!=='public_api'||
    canonicalAccount(v.externalTraderId,corrupt)!==request.externalTraderId||v.externalTraderId!==v.externalTraderId.toLowerCase()||
    !['traderRevision','catalogVersionAtCreation','catalogVersion','traderControlVersion','paperControlVersion'].every(k=>isVersion(v[k]))||
    BigInt(v.catalogVersionAtCreation)>BigInt(v.catalogVersion)||
    !isText(v.displayName,240)||!isText(v.sourceRef,2048)||!isTimestamp(v.observedAt)||!isTimestamp(v.revisionCreatedAt))corrupt();
  const a=exact(v.startAvailability,['available','capabilityReasonCode']);
  if(!(a.available===true&&a.capabilityReasonCode===null)&&
    !(a.available===false&&['PAPER_START_DISABLED','CATALOG_SOURCE_DISABLED','TRADER_START_DISABLED'].includes(a.capabilityReasonCode)))corrupt();
  return structuredClone(v);
}

/**
 * Call ONLY inside a trusted authenticated read transaction. The storage adapter
 * must scope rows to current user/environment, and read mapping + admission in
 * one consistent snapshot. This pure decoder is NOT an authorization mechanism.
 * `admission` is an internal projection, never client input or public JSON cache.
 */
export function resolveAuthorizedSnapshot(request,value,readScope) {
  exact(request,['venueCode','externalTraderId'],invalid);
  if(!isVenue(request.venueCode)||canonicalAccount(request.externalTraderId)!==request.externalTraderId)invalid();
  const scope=exact(readScope,['venueCode','venueId','canonicalSourceId']);
  if(scope.venueCode!==request.venueCode||!isUuid(scope.venueId)||!isUuid(scope.canonicalSourceId))corrupt();
  const r=exact(value,['venueCode','externalTraderId','matches']);
  if(r.venueCode!==request.venueCode||r.externalTraderId!==request.externalTraderId||!Array.isArray(r.matches)||r.matches.length>1)corrupt();
  if(r.matches.length===0)throw new BoundaryError(404,'RESOURCE_NOT_FOUND');
  const row=exact(r.matches[0],['trader','admission']);
  const trader=decodeRealTrader(row.trader,request);
  if(!isReviewTrader(trader))corrupt();
  if(trader.venueId!==scope.venueId||trader.catalogSourceId!==scope.canonicalSourceId)corrupt();
  const a=exact(row.admission,['state','admissionId','venueId','catalogSourceId','traderId','traderRevisionId',
    'catalogVersion','traderControlVersion','paperControlVersion','sourceBindingVersion','adapterVersion','policyVersion']);
  if(!['empty_session_only','blocked'].includes(a.state)||!isUuid(a.admissionId)||!isVersion(a.sourceBindingVersion)||
    !isText(a.adapterVersion,128)||!isText(a.policyVersion,128))corrupt();
  for(const key of ['venueId','catalogSourceId','traderId','traderRevisionId','catalogVersion','traderControlVersion','paperControlVersion'])
    if(a[key]!==trader[key])corrupt();
  // Only a known existing product start flag is a business refusal. A missing
  // integration/reader dependency must never impersonate that refusal.
  if(a.state!=='empty_session_only')throw new BoundaryError(503,'SERVICE_UNAVAILABLE');
  for(const key of ['admissionId','sourceBindingVersion','adapterVersion','policyVersion'])if(a[key]!==REVIEW_PROFILE[key])corrupt();
  return {schemaVersion:'real-trader-empty-session-selection-v1',selectionPurpose:'empty_session_only',trader,nextAction:null,nextActionParams:{}};
}
