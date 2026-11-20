import {Temporal} from '@js-temporal/polyfill';
import {exactObject,uuid,positiveVersion} from '../http/input.ts';
import {timestamp,decodeSession,decodeLiveBuyContext} from '../paper/responses.ts';
import {StorageRecordUnavailable} from '../storage/transaction.ts';
import type {PolygonTransaction} from '../storage/transaction.ts';
import type {TrustedUserProof} from '../paper/service.ts';
import {decodeCoreState} from './core-adapter.mjs';
import type {CoreState} from './core-adapter.mjs';

const bad=():never=>{throw new StorageRecordUnavailable();};
export interface LiveBuySession {
  schemaVersion:'live-buy-session-v1';sessionId:string;sessionVersion:string;
  snapshotId:string;snapshotVersion:string;ledgerSequence:string;asOf:string;ianaTimezone:string;
  financial:CoreState;valuation:{status:'unavailable'};
}
/** Decode only the public pointer and financial core; context/activity extend this closed wire below. */
export function decodeFinancialPointer(value:unknown,expectedId:string|null):LiveBuySession {
  try{
    const v=exactObject(value,['schemaVersion','sessionId','sessionVersion','snapshotId','snapshotVersion','ledgerSequence','asOf','ianaTimezone','financial','valuation']);
    if(v.schemaVersion!=='live-buy-session-v1'||!uuid(v.sessionId)||(expectedId!==null&&v.sessionId!==expectedId)||!uuid(v.snapshotId)||
      !positiveVersion(v.sessionVersion)||!positiveVersion(v.snapshotVersion)||!positiveVersion(v.ledgerSequence)||!timestamp(v.asOf)||
      typeof v.ianaTimezone!=='string'||v.ianaTimezone.length>128)bad();
    const valuation=exactObject(v.valuation,['status']);if(valuation.status!=='unavailable')bad();
    // Reject unknown timezone; never silently choose host timezone.
    new Intl.DateTimeFormat('en',{timeZone:v.ianaTimezone as string});
    const financial=decodeCoreState(v.financial,v.sessionId as string);
    if(financial.version!==v.snapshotVersion||financial.snapshotId!==v.snapshotId||v.sessionVersion!==v.snapshotVersion||v.ledgerSequence!==v.snapshotVersion||BigInt(v.snapshotVersion as string)<=1n)bad();
    return {...v,financial,valuation} as unknown as LiveBuySession;
  }catch{throw new StorageRecordUnavailable();}
}

export function projectBalance(s:LiveBuySession){
  return {schemaVersion:'live-buy-balance-v1',sessionId:s.sessionId,sessionVersion:s.sessionVersion,snapshotId:s.snapshotId,
    snapshotVersion:s.snapshotVersion,ledgerSequence:s.ledgerSequence,asOf:s.asOf,unit:'virtual_USD',
    cash:s.financial.cash,reservedCash:s.financial.reservedCash,freeCash:s.financial.freeCash,cashExpenses:s.financial.cashExpenses,valuation:s.valuation};
}
export function projectPositions(s:LiveBuySession){
  return {schemaVersion:'live-buy-positions-v1',sessionId:s.sessionId,sessionVersion:s.sessionVersion,snapshotId:s.snapshotId,
    snapshotVersion:s.snapshotVersion,ledgerSequence:s.ledgerSequence,asOf:s.asOf,unit:'virtual_USD',items:s.financial.positions,valuation:s.valuation};
}

const addQ=(a:{n:string;d:string},b:{n:string;d:string})=>{
  let n=BigInt(a.n)*BigInt(b.d)+BigInt(b.n)*BigInt(a.d),d=BigInt(a.d)*BigInt(b.d),x=n,y=d;
  while(y){const r=x%y;x=y;y=r;}n/=x;d/=x;
  if(String(n).length>256||String(d).length>256)bad();return {n:String(n),d:String(d)};
};
const sameQ=(a:{n:string;d:string},b:{n:string;d:string})=>BigInt(a.n)*BigInt(b.d)===BigInt(b.n)*BigInt(a.d);
const q=(v:unknown)=>{
  const x=exactObject(v,['n','d']);
  if(typeof x.n!=='string'||typeof x.d!=='string'||!/^(0|[1-9][0-9]{0,255})$/.test(x.n)||!/^[1-9][0-9]{0,255}$/.test(x.d))bad();
  let a=BigInt(x.n as string),b=BigInt(x.d as string);while(b){const c=a%b;a=b;b=c;}if(a!==1n)bad();
  return x as {n:string;d:string};
};
export function decodeBuySessionReply(value:unknown,expectedId:string|null):Record<string,any>|null {
  try{
    if(value&&typeof value==='object'&&Object.hasOwn(value,'buyState')){
      const v=exactObject(value,['http','schemaVersion','sessionId','buyState']);
      if(v.http!==200||v.schemaVersion!=='live-buy-session-v1'||v.buyState!==null||
        (v.sessionId!==null&&!uuid(v.sessionId))||(expectedId!==null&&v.sessionId!==expectedId))bad();
      return null;
    }
    const v=exactObject(value,['http','schemaVersion','sessionId','sessionVersion','snapshotId','snapshotVersion','ledgerSequence','asOf','ianaTimezone','financial','valuation','context','dailyContext']);
    if(v.http!==200)bad();
    const {http,context,dailyContext,...pointer}=v;
    const financial=decodeFinancialPointer(pointer,expectedId);
    const c=decodeLiveBuyContext(context,financial.sessionId),summary=c.summary;
    if(summary.updatedAt!==financial.asOf)bad();
    for(const k of ['sessionId','sessionVersion','snapshotVersion','asOf','ianaTimezone'])if(summary[k]!==v[k])bad();
    const day=exactObject(dailyContext,['day','timezone','used','reserved','limit','nextResetAt','asOf']);
    if(typeof day.day!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(day.day)||!Number.isFinite(Date.parse(day.day+'T00:00:00.000Z'))||
      new Date(day.day+'T00:00:00.000Z').toISOString().slice(0,10)!==day.day||day.timezone!==financial.ianaTimezone||
      !timestamp(day.asOf)||!timestamp(day.nextResetAt)||Date.parse(day.nextResetAt as string)<=Date.parse(day.asOf as string)||
      Date.parse(day.asOf as string)<Date.parse(financial.asOf))bad();
    q(day.used);q(day.reserved);const limit=q(day.limit);if(limit.n==='0'||limit.n!==c.settings.effectiveDailyBuyLimit.n||limit.d!==c.settings.effectiveDailyBuyLimit.d)bad();
    const parts=new Intl.DateTimeFormat('en-US',{timeZone:financial.ianaTimezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(day.asOf as string));
    const part=(type:string)=>parts.find(p=>p.type===type)?.value;
    if(day.day!==`${part('year')}-${part('month')}-${part('day')}`)bad();
    const nextMidnight=Temporal.Instant.from(day.asOf as string).toZonedDateTimeISO(financial.ianaTimezone).toPlainDate().add({days:1}).toZonedDateTime(financial.ianaTimezone).toInstant().toString({smallestUnit:'millisecond'});
    if(day.nextResetAt!==nextMidnight)bad();
    const cost=financial.financial.positions.reduce((total,p)=>addQ(total,p.cost),{n:'0',d:'1'});
    if(!sameQ(addQ(addQ(financial.financial.cash,cost),financial.financial.cashExpenses),c.settings.budget))bad();
    return {...financial,context:c,dailyContext:day};
  }catch{throw new StorageRecordUnavailable();}
}
export async function readCurrentFinancial(tx:PolygonTransaction,auth:TrustedUserProof,sessionId:string|null):Promise<Record<string,any>>{
  const raw=await tx.call('buy_session_read_v1',{auth,session_id:sessionId});
  const bound=decodeBuySessionReply(raw,sessionId);
  if(bound)return {session:bound};
  // Explicit unbound only. Missing/malformed or unavailable RPC never becomes EMPTY.
  const actualId=raw.sessionId as string|null;
  return decodeSession(await tx.call('q04_session',{auth,session_id:actualId}),sessionId??actualId);
}
