import {decodeBuySessionReply} from '../live-buy/reader.ts';
import {REVIEW_PROFILE} from '../real-demo/review-profile.mjs';
import { exactObject, InputError, uuid } from '../http/input.ts';
import { decodeSession, timestamp } from '../paper/responses.ts';
import { StorageRecordUnavailable } from '../storage/transaction.ts';

export interface ActivityRequest {sessionId:string;afterSequence:string;limit:number}
const uint = (v:unknown,max=9223372036854775807n):v is string =>
  typeof v==='string' && /^(0|[1-9][0-9]{0,77})$/.test(v) && BigInt(v)<=max;
const hash = (v:unknown) => typeof v==='string' && /^0x[0-9a-f]{64}$/.test(v);
const sha = (v:unknown) => typeof v==='string' && /^[0-9a-f]{64}$/.test(v);
const bad=():never=>{throw new StorageRecordUnavailable();};

export function parseActivityQuery(sessionId:string,raw:string):ActivityRequest {
  if(!uuid(sessionId))throw new InputError();
  const q:Record<string,string>=Object.create(null);
  for(const part of raw.split('&')){
    const at=part.indexOf('=');if(at<1)throw new InputError();
    let k:string,v:string;
    try{k=decodeURIComponent(part.slice(0,at).replaceAll('+',' '));v=decodeURIComponent(part.slice(at+1).replaceAll('+',' '));}
    catch{throw new InputError();}
    if(!['requestSchemaVersion','afterSequence','limit'].includes(k)||Object.hasOwn(q,k))throw new InputError();q[k]=v;
  }
  const afterSequence=q.afterSequence??'0',limit=q.limit??'50';
  if(q.requestSchemaVersion!=='v1'||!uint(afterSequence)||!/^(?:[1-9]|[1-9][0-9]|100)$/.test(limit))throw new InputError();
  return {sessionId,afterSequence,limit:Number(limit)};
}

/** Closed decode inside the same SERIALIZABLE read transaction as guard + Q04. */
export function decodeActivityLive(value:unknown,request:ActivityRequest):Record<string,unknown> {return decodeActivity(value,request,false);}
export function decodeActivityBuy(value:unknown,request:ActivityRequest):Record<string,unknown> {return decodeActivity(value,request,true);}
function decodeActivity(value:unknown,request:ActivityRequest,buy:boolean):Record<string,unknown> {
  try {
    const r=exactObject(value,['http','binding','observation','items','page','session',...(buy?['schemaVersion']:[])]);
    if(buy&&r.schemaVersion!=='live-buy-activity-v1')bad();
    if(r.http!==200)bad();
    const candidate=r.session as Record<string,unknown>;
    const session=buy&&candidate?.schemaVersion==='live-buy-session-v1'?decodeBuySessionReply({http:200,...candidate},request.sessionId):decodeSession({http:200,session:r.session},request.sessionId).session;
    if(!session)bad();
    const summary=session.context?.summary??session.summary;
    let binding:Record<string,unknown>|null=null;
    if(r.binding!==null){
      binding=exactObject(r.binding,['streamId','venueCode','catalogSourceId','traderId','traderRevisionId','externalTraderId','bindingRevision']);
      if(summary.dataOrigin!=='public_api'||binding.venueCode!=='polymarket'||!uuid(binding.streamId)||
        typeof binding.externalTraderId!=='string'||binding.externalTraderId!==REVIEW_PROFILE.externalTraderId||
        !uint(binding.bindingRevision)||binding.bindingRevision==='0')bad();
      for(const k of ['catalogSourceId','traderId','traderRevisionId'])if(!uuid(binding[k])||binding[k]!==summary[k])bad();
    }
    const o=exactObject(r.observation,['status','armedAt','lastObservedAt','completeness']);
    if(!['not_armed','observing','source_unavailable','reconciliation_required','stopped'].includes(o.status as string)||o.completeness!=='unproven')bad();
    if(o.status==='not_armed'){
      if(o.armedAt!==null||o.lastObservedAt!==null)bad();
    }else if(!timestamp(o.armedAt)||Date.parse(o.armedAt as string)<Date.parse(summary.startedAt))bad();
    if(o.lastObservedAt!==null&&(!timestamp(o.lastObservedAt)||!timestamp(o.armedAt)||Date.parse(o.lastObservedAt as string)<Date.parse(o.armedAt as string)))bad();
    const p=exactObject(r.page,['afterSequence','nextAfterSequence','highWatermark','hasMore']);
    if(!uint(p.afterSequence)||!uint(p.nextAfterSequence)||!uint(p.highWatermark)||p.afterSequence!==request.afterSequence||typeof p.hasMore!=='boolean')bad();
    const after=BigInt(p.afterSequence as string),high=BigInt(p.highWatermark as string);
    if(binding===null&&(o.status!=='not_armed'||o.armedAt!==null||o.lastObservedAt!==null||high!==0n||after!==0n))bad();
    if(high<after||!Array.isArray(r.items)||r.items.length>request.limit)bad();
    const items=r.items as unknown[];
    const expected=high-after<BigInt(request.limit)?high-after:BigInt(request.limit);
    if(BigInt(items.length)!==expected||(o.status==='not_armed'&&high!==0n))bad();
    let next=after;const ids=new Set();
    for(const item of items){
      const i=exactObject(item,['activityId','sequence','source','trade','decision']);
      if(!uuid(i.activityId)||ids.has(i.activityId)||!uint(i.sequence)||BigInt(i.sequence)!==++next)bad();ids.add(i.activityId);
      const s=exactObject(i.source,['venueCode','externalTraderId','transactionHash','identityStatus','sourceOccurredAt','receivedAt','recordHash']);
      if(s.venueCode!=='polymarket'||binding===null||s.externalTraderId!==binding.externalTraderId||s.identityStatus!=='verified_log'||!hash(s.transactionHash)||!sha(s.recordHash)||!timestamp(s.sourceOccurredAt)||!timestamp(s.receivedAt)||!timestamp(o.lastObservedAt))bad();
      const occurred=Date.parse(s.sourceOccurredAt as string),received=Date.parse(s.receivedAt as string);
      if(occurred<=Date.parse(o.armedAt as string)||occurred>received||received>Date.parse(o.lastObservedAt as string))bad();
      const t=exactObject(i.trade,['conditionId','tokenId','marketTitle','outcome','side','size','price','sizeUnit','priceUnit']);
      if(!uint(t.tokenId,2n**256n-1n)||!['BUY','SELL'].includes(t.side as string)||
        ['size','price','sizeUnit','priceUnit'].some(k=>t[k]!==null))bad();
      const unbound=t.conditionId===null&&t.marketTitle===null&&t.outcome===null;
      const bound=hash(t.conditionId)&&typeof t.marketTitle==='string'&&t.marketTitle.length>0&&t.marketTitle.length<=2048&&!/\p{Cc}/u.test(t.marketTitle)&&typeof t.outcome==='string'&&t.outcome.length>0&&t.outcome.length<=256&&!/\p{Cc}/u.test(t.outcome);
      if(!unbound&&!bound)bad();
      const d=exactObject(i.decision,['status','reasonCode','detailCode','decidedAt','policyVersion','copy']);
      if(buy&&d.status!=='skipped'){
        if(t.side!=='BUY'||!bound)bad();
        decodeCopyDecision(d,session,received);
      }else if(d.status!=='skipped'||d.reasonCode!=='context_invalid'||!['not_buy', 'signal_expired', 'market_binding_unavailable', 'market_unavailable', 'book_unavailable', 'book_stale', 'clock_unproven', 'profile_unavailable', 'fee_profile_unavailable', 'invalid_book', 'insufficient_liquidity', 'below_minimum', 'precision_unavailable', 'insufficient_funds', 'position_limit_exceeded', 'daily_limit_exceeded', 'source_unavailable', 'one_buy_scope_complete'].includes(d.detailCode as string)||
        d.policyVersion!=='paper-bound-skip-v1'||d.copy!==null||!timestamp(d.decidedAt)||Date.parse(d.decidedAt as string)<received)bad();
    }
    if(p.nextAfterSequence!==String(next)||p.hasMore!==(next<high))bad();
    return {schemaVersion:buy?'live-buy-activity-v1':'paper-source-activity-v3',sessionId:request.sessionId,bindingStatus:binding===null?'unavailable':'verified',binding,observation:o,items,page:p,session,nextAction:null,nextActionParams:{}};
  }catch{throw new StorageRecordUnavailable();}
}


type Q={n:bigint;d:bigint};
const addQ=(a:Q,b:Q):Q=>{let n=a.n*b.d+b.n*a.d,d=a.d*b.d,x=n,y=d;while(y){const r=x%y;x=y;y=r;}n/=x;d/=x;if(String(n).length>256||String(d).length>256)bad();return {n,d};};
const eqQ=(a:Q,b:Q)=>a.n*b.d===b.n*a.d;
const mulQ=(a:Q,b:Q):Q=>({n:a.n*b.n,d:a.d*b.d});
function amount(value:unknown,positive=false):Q {
  const v=exactObject(value,['n','d']);
  if(typeof v.n!=='string'||typeof v.d!=='string'||!/^(0|[1-9][0-9]{0,255})$/.test(v.n)||!/^[1-9][0-9]{0,255}$/.test(v.d))bad();
  const n=BigInt(v.n as string),d=BigInt(v.d as string);let a=n,b=d;while(b){const r=a%b;a=b;b=r;}
  if(a!==1n||(positive&&n===0n))bad();return {n,d};
}
function decodeCopyDecision(d:Record<string,unknown>,session:Record<string,any>,received:number){
  if(!['pending','filled'].includes(d.status as string)||d.policyVersion!=='paper-buy-queued-v1'||d.reasonCode!==null||d.detailCode!==null||!timestamp(d.decidedAt)||Date.parse(d.decidedAt as string)<received)bad();
  if(d.status==='pending'){
    const c=exactObject(d.copy,['kind','intentId','reservedCash','reservedNotional','admittedAt']);
    if(c.kind!=='pending')bad();
    if(c.intentId===null){if(['reservedCash','reservedNotional','admittedAt'].some(k=>c[k]!==null))bad();return;}
    if(!uuid(c.intentId)||session.schemaVersion!=='live-buy-session-v1'||!timestamp(c.admittedAt)||Date.parse(c.admittedAt as string)<Date.parse(d.decidedAt as string)||Date.parse(c.admittedAt as string)>Date.parse(session.asOf))bad();
    const cash=amount(c.reservedCash,true),notional=amount(c.reservedNotional,true);if(cash.n*notional.d<notional.n*cash.d)bad();return;
  }
  if(session.schemaVersion!=='live-buy-session-v1')bad();
  const c=exactObject(d.copy,['kind','intentId','executionId','settledAt','notional','quantityGross','quantityNet','quantityFee','cashFee','snapshotId','snapshotVersion','fills']);
  if(c.kind!=='filled'||!uuid(c.intentId)||!uuid(c.executionId)||!uuid(c.snapshotId)||!uint(c.snapshotVersion)||BigInt(c.snapshotVersion as string)<=1n||BigInt(c.snapshotVersion as string)>BigInt(session.snapshotVersion)||
    (c.snapshotVersion===session.snapshotVersion&&c.snapshotId!==session.snapshotId)||!timestamp(c.settledAt)||Date.parse(c.settledAt as string)<Date.parse(d.decidedAt as string)||Date.parse(c.settledAt as string)>Date.parse(session.asOf)||!Array.isArray(c.fills)||c.fills.length<1||c.fills.length>128)bad();
  const totals:Record<string,Q>=Object.fromEntries(['notional','quantityGross','quantityNet','quantityFee','cashFee'].map(k=>[k,{n:0n,d:1n}]));
  const seen=new Set();
  for(const raw of c.fills as unknown[]){
    const f=exactObject(raw,['fillId','executedAt','price','quantityGross','quantityNet','quantityFee','cashFee','notional']);
    if(!uuid(f.fillId)||seen.has(f.fillId)||!timestamp(f.executedAt)||Date.parse(f.executedAt as string)<Date.parse(d.decidedAt as string)||Date.parse(f.executedAt as string)>Date.parse(c.settledAt as string))bad();seen.add(f.fillId);
    const price=amount(f.price,true),gross=amount(f.quantityGross,true),net=amount(f.quantityNet,true),fee=amount(f.quantityFee),cost=amount(f.notional,true);
    if(price.n>price.d||!eqQ(gross,addQ(net,fee))||!eqQ(cost,mulQ(price,gross)))bad();
    for(const k of Object.keys(totals))totals[k]=addQ(totals[k],amount(f[k]));
  }
  for(const k of Object.keys(totals))if(!eqQ(totals[k],amount(c[k])))bad();
}
