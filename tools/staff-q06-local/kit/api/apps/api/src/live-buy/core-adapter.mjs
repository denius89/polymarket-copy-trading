// Private future inner component. No HTTP route, credentials, profile activation,
// automatic transaction, retry, or replacement for the live session projections.
const exact=(x,keys)=>x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join(',')===keys.split(' ').sort().join(',');
const uuid=x=>typeof x==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(x);
const ident=x=>typeof x==='string'&&x.length>0&&x.length<=256&&!/[\x00-\x1f\x7f]/.test(x);
const uint=x=>typeof x==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(x)&&BigInt(x)<=9223372036854775807n;
export class CoreRecordUnavailable extends Error{constructor(){super('private_core_record_unavailable');}}
const check=x=>{if(!x)throw new CoreRecordUnavailable();};
const gcd=(a,b)=>b===0n?a:gcd(b,a%b);
function rational(q){
  check(exact(q,'n d')&&typeof q.n==='string'&&typeof q.d==='string'&&/^(0|[1-9][0-9]{0,255})$/.test(q.n)&&/^[1-9][0-9]{0,255}$/.test(q.d));
  const n=BigInt(q.n),d=BigInt(q.d);check(gcd(n,d)===1n);return {n,d};
}
const equal=(a,b)=>a.n*b.d===b.n*a.d;
const add=(a,b)=>({n:a.n*b.d+b.n*a.d,d:a.d*b.d});
const deepFreeze=x=>{if(x&&typeof x==='object'){for(const v of Object.values(x))deepFreeze(v);Object.freeze(x);}return x;};
const copy=x=>deepFreeze(structuredClone(x));
function day(s){
  if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;
  const d=new Date(s+'T00:00:00.000Z');return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===s;
}

export function decodeCoreState(value,sessionId){
  check(uuid(sessionId)&&exact(value,'schemaVersion sessionId version snapshotId cash reservedCash freeCash cashExpenses positions daily'));
  check(value.schemaVersion==='paper-buy-core-state-v1'&&value.sessionId===sessionId&&uint(value.version)&&BigInt(value.version)>0n&&uuid(value.snapshotId));
  const cash=rational(value.cash),reserved=rational(value.reservedCash),free=rational(value.freeCash);rational(value.cashExpenses);
  check(equal(cash,add(reserved,free)));
  check(Array.isArray(value.positions)&&value.positions.length<=10000&&Array.isArray(value.daily)&&value.daily.length<=10000);
  let prev=null;
  for(const p of value.positions){
    check(exact(p,'conditionId tokenId cost quantity reserved')&&ident(p.conditionId)&&ident(p.tokenId));
    rational(p.cost);rational(p.quantity);rational(p.reserved);
    if(prev)check(prev.conditionId<p.conditionId||(prev.conditionId===p.conditionId&&prev.tokenId<p.tokenId));
    prev=p;
  }
  let lastDay=null;
  for(const d of value.daily){
    check(exact(d,'day used reserved')&&day(d.day)&&(!lastDay||lastDay<d.day));
    rational(d.used);rational(d.reserved);lastDay=d.day;
  }
  return copy(value);
}

export function decodeCoreResult(value,{sessionId,commandId,kind,intentId}={}){
  check(uuid(sessionId)&&uuid(commandId));
  check(value&&['reserve','settle'].includes(value.kind));
  const keys='schemaVersion sessionId commandId kind intentId version state'+(value.kind==='settle'?' executionId':'');
  check(exact(value,keys)&&value.schemaVersion==='paper-buy-core-result-v1'&&value.sessionId===sessionId&&value.commandId===commandId&&uuid(value.intentId));
  if(kind!==undefined)check(value.kind===kind);
  if(intentId!==undefined)check(value.intentId===intentId);
  check(uint(value.version)&&BigInt(value.version)>1n&&(value.kind!=='settle'||uuid(value.executionId)));
  const state=decodeCoreState(value.state,sessionId);check(state.version===value.version);
  // Historical lookup is allowed to be older than the currently observed state.
  return copy({...value,state});
}

export function validateCoreRequest(kind,input){
  const reserve='commandId intentId observationId expectedVersion conditionId tokenId sizingRevisionId admissionRevisionId evidenceRef desiredNotional fullQuantity quantityStep priceCap feeCashBound delayMs';
  const settle='commandId intentId expectedVersion evidenceRef confirmationId fills';
  check(exact(input,kind==='reserve'?reserve:settle)&&uuid(input.commandId)&&uuid(input.intentId)&&typeof input.expectedVersion==='string'&&/^[1-9][0-9]{0,17}$/.test(input.expectedVersion)&&ident(input.evidenceRef));
  if(kind==='reserve'){
    check(['observationId','sizingRevisionId','admissionRevisionId'].every(k=>uuid(input[k]))&&ident(input.conditionId)&&ident(input.tokenId)&&typeof input.delayMs==='string'&&/^(0|[1-9][0-9]{0,8})$/.test(input.delayMs));
    for(const k of ['desiredNotional','fullQuantity','quantityStep','priceCap','feeCashBound'])rational(input[k]);
  }else{
    check(uuid(input.confirmationId)&&Array.isArray(input.fills)&&input.fills.length>0&&input.fills.length<=128);
    const seen=new Set();
    for(const f of input.fills){
      check(exact(f,'fillId price quantityGross quantityFee cashFee executedAt')&&uuid(f.fillId)&&typeof f.executedAt==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(f.executedAt)&&Number.isFinite(Date.parse(f.executedAt))&&new Date(f.executedAt).toISOString()===f.executedAt&&!seen.has(f.fillId));seen.add(f.fillId);
      for(const k of ['price','quantityGross','quantityFee','cashFee'])rational(f[k]);
    }
  }
}

/** Called inside the caller-owned SERIALIZABLE transaction. Decode BEFORE COMMIT.
 * authorize must be the real current Auth/ownership/release check before deployment;
 * a test fixture callback is never evidence of that production boundary.
 * Throws propagate so the outer transaction can rollback. No internal retry/catch.
 */
export function createPrivateCoreAdapter({query,authorize}){
  check(typeof query==='function'&&typeof authorize==='function');
  return Object.freeze({async call(kind,sessionId,input){
    check(['reserve','settle','lookup','read_state'].includes(kind)&&uuid(sessionId));
    if(kind==='reserve'||kind==='settle')validateCoreRequest(kind,input);
    else if(kind==='lookup')check(uuid(input));
    else check(input===undefined);
    const request=input===undefined?undefined:structuredClone(input);
    await authorize({sessionId,kind});
    const sql=kind==='read_state'?'SELECT live_buy_core.read_state($1::uuid) AS reply':
      kind==='lookup'?'SELECT live_buy_core.lookup($1::uuid,$2::uuid) AS reply':
      kind==='reserve'?'SELECT live_buy_core.reserve($1::uuid,$2::jsonb) AS reply':
      'SELECT live_buy_core.settle($1::uuid,$2::jsonb) AS reply';
    const values=kind==='read_state'?[sessionId]:[sessionId,kind==='lookup'?request:JSON.stringify(request)];
    const rows=(await query(sql,values)).rows;
    check(Array.isArray(rows)&&rows.length===1&&exact(rows[0],'reply'));
    const value=rows[0].reply;
    if(kind==='read_state')return decodeCoreState(value,sessionId);
    if(kind==='lookup')return value===null?null:decodeCoreResult(value,{sessionId,commandId:request});
    return decodeCoreResult(value,{sessionId,commandId:request.commandId,intentId:request.intentId,kind});
  }});
}

export function projectPrivateState(value,sessionId){
  const state=decodeCoreState(value,sessionId);
  return copy({schemaVersion:'paper-buy-private-projection-v1',scope:'private-core-only',sessionId,
    financialVersion:state.version,snapshotId:state.snapshotId,
    balance:{unit:'virtual_USD',cash:state.cash,reservedCash:state.reservedCash,freeCash:state.freeCash,cashExpenses:state.cashExpenses},
    positions:state.positions,daily:state.daily,valuation:{status:'unavailable'},runtimeAdmission:false});
}
