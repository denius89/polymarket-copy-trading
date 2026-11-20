import {createHash} from 'node:crypto';
import {losslessJSON} from './json.mjs';
import {check,sha,BuyBlocked} from './guard.mjs';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const token=v=>typeof v==='string'&&/^(0|[1-9][0-9]{0,77})$/.test(v)&&BigInt(v)<2n**256n;
const address=v=>typeof v==='string'&&/^0x[0-9a-f]{40}$/.test(v);
const condition=v=>typeof v==='string'&&/^0x[0-9a-f]{64}$/.test(v);
const iso=ms=>new Date(ms).toISOString();
const array=v=>typeof v==='string'?losslessJSON(v):v;
export function createMarketClient({store,fetcher=fetch,wall=Date.now,mono=()=>performance.now(),deadlineMonoMs=Infinity}){
  async function get(url,book=false){
    const u=new URL(url);
    check((u.origin==='https://gamma-api.polymarket.com'&&u.pathname==='/markets')||
      (u.origin==='https://clob.polymarket.com'&&(/^\/clob-markets\/0x[0-9a-f]{64}$/.test(u.pathname)||u.pathname==='/book')),'source_unavailable');
    const startedAt=wall(),start=mono();let response,bytes;
    const timeout=Math.min(book?1000:5000,Math.floor(deadlineMonoMs-start));
    check(timeout>0,'source_unavailable');
    try{
      response=await fetcher(url,{method:'GET',redirect:'error',signal:AbortSignal.timeout(timeout),headers:{accept:'application/json'}});
      const chunks=[];let length=0;for await(const c of response.body){length+=c.length;check(length<=2_000_000,'source_unavailable');chunks.push(c);}bytes=Buffer.concat(chunks);
      const receivedWallMs=wall(),receivedMonoMs=mono(),bodySha256=store.put(bytes);
      store.putJSON({url,method:'GET',startedAt:iso(startedAt),receivedAt:iso(receivedWallMs),status:response.status,bodySha256});
      check(response.ok,'source_unavailable');
      return {url,bodySha256,value:losslessJSON(bytes.toString('utf8')),receivedWallMs,receivedMonoMs,acquisitionMs:receivedMonoMs-start};
    }catch(e){store.putJSON({url,method:'GET',startedAt:iso(startedAt),failedAt:iso(wall()),status:response?.status??null,error:'public_get_failed'});if(e instanceof BuyBlocked)throw e;throw new BuyBlocked('source_unavailable');}
  }
  async function gamma(asset){
    check(token(asset),'market_binding_unavailable');
    const response=await get('https://gamma-api.polymarket.com/markets?clob_token_ids='+asset);
    check(Array.isArray(response.value),'market_binding_unavailable');
    const matches=response.value.filter(m=>{try{const ids=m.version==='v1'?array(m.clobTokenIds):m.version==='v2'?array(m.positionIds):null;return Array.isArray(ids)&&ids.includes(asset);}catch{return false;}});
    check(matches.length===1&&condition(matches[0].conditionId),'market_binding_unavailable');
    return {...response,market:matches[0]};
  }
  return {
    gamma,
    async metadata(asset){
      const g=await gamma(asset);
      const clob=await get('https://clob.polymarket.com/clob-markets/'+g.market.conditionId);
      return {gamma:g,clob};
    },
    book:asset=>{check(token(asset),'market_binding_unavailable');return get('https://clob.polymarket.com/book?token_id='+asset,true);},
  };
}

export function gammaBinding(asset,gamma){
  const g=gamma.market;
  check(token(asset)&&['v1','v2'].includes(g.version)&&condition(g.conditionId),'market_binding_unavailable');
  const ids=g.version==='v1'?array(g.clobTokenIds):array(g.positionIds),labels=array(g.outcomes);
  check(Array.isArray(ids)&&ids.length===2&&new Set(ids).size===2&&ids.every(token)&&Array.isArray(labels)&&labels.length===2&&labels.every(x=>typeof x==='string'&&x.length>0&&x.length<=256&&!/\p{Cc}/u.test(x)),'market_binding_unavailable');
  const at=ids.indexOf(asset);check(at>=0&&sha(gamma.bodySha256),'market_binding_unavailable');
  check(typeof g.question==='string'&&g.question.length>0&&g.question.length<=2048&&!/\p{Cc}/u.test(g.question),'market_binding_unavailable');
  return {tokenId:asset,conditionId:g.conditionId,outcome:labels[at],outcomeSlot:at,marketTitle:g.question,protocol:g.version,marketSha256:gamma.bodySha256};
}
