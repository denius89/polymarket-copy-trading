import { createHash } from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { REVIEW_PROFILE } from '../real-demo/review-profile.mjs';

export const SOURCE=Object.freeze({endpoint:'https://polygon.publicnode.com',chainId:'137',
  exchange:'0xe111180000d2663c0091e4f400237545b87b996b',
  topic:'0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee',
  namespace:'polygon-137-ctfv2-orderfilled-owner-v1',owner:REVIEW_PROFILE.externalTraderId});
export const sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
export class SourceFailure extends Error {
  constructor(code,state='source_unavailable'){super(code);this.name='SourceFailure';this.code=code;this.state=state;}
}
const fail=(code='source_shape_invalid',state='source_unavailable')=>{throw new SourceFailure(code,state);};
export const hash=v=>typeof v==='string'&&/^0x[0-9a-f]{64}$/.test(v);
export const uint=v=>typeof v==='string'&&/^(0|[1-9][0-9]{0,77})$/.test(v)&&BigInt(v)<2n**256n;
export const quantity=v=>{
  if(typeof v!=='string'||!/^0x(?:0|[1-9a-f][0-9a-f]{0,63})$/.test(v))fail();return String(BigInt(v));
};
export const hex=n=>'0x'+BigInt(n).toString(16);
export const ownerTopic='0x'+'0'.repeat(24)+SOURCE.owner.slice(2);
export function decodeHeader(value){
  if(!value||!hash(value.hash)||!hash(value.parentHash))fail();
  const timestampSeconds=quantity(value.timestamp);
  if(BigInt(timestampSeconds)>8640000000000n)fail();
  return {number:quantity(value.number),hash:value.hash,parentHash:value.parentHash,timestampSeconds};
}
export function semanticPreimage(log,header,source=SOURCE){
  const lines=['shadow-chain-log-semantic-v1',source.chainId,source.exchange,source.namespace,
    log.transactionHash,log.logIndex,log.owner,log.blockNumber,log.blockHash,header.timestampSeconds,
    log.orderHash,log.counterparty,log.side,log.tokenId,log.makerAmountFilledRaw,
    log.takerAmountFilledRaw,log.feeRaw,log.builder,log.metadata];
  if(lines.length!==19||lines.some(v=>typeof v!=='string'||!/^[A-Za-z0-9-]+$/.test(v)))fail();
  return lines.join('\n')+'\n';
}
export const recordHash=(log,header,source=SOURCE)=>sha256(semanticPreimage(log,header,source));

export function decodeOwnerLog(log,receipt,receiptSha256,source=SOURCE){
  if(!log||log.removed!==false||log.address!==source.exchange||!hash(log.transactionHash)||!hash(log.blockHash)||
    !Array.isArray(log.topics)||log.topics.length!==4||!log.topics.every(hash)||log.topics[0]!==source.topic||
    log.topics[2]!=='0x'+'0'.repeat(24)+source.owner.slice(2)||!/^0x0{24}[0-9a-f]{40}$/.test(log.topics[3])||
    typeof log.data!=='string'||!/^0x[0-9a-f]{448}$/.test(log.data))fail();
  if(!receipt||receipt.status!=='0x1'||receipt.transactionHash!==log.transactionHash||receipt.blockHash!==log.blockHash||
    receipt.blockNumber!==log.blockNumber||!Array.isArray(receipt.logs)||
    receipt.logs.filter(l=>l.logIndex===log.logIndex&&isDeepStrictEqual(l,log)).length!==1||
    !/^[0-9a-f]{64}$/.test(receiptSha256))fail('receipt_log_mismatch','reconciliation_required');
  const words=Array.from({length:7},(_,i)=>log.data.slice(2+i*64,2+(i+1)*64));
  const side=BigInt('0x'+words[0]);if(side!==0n&&side!==1n)fail();
  return {transactionHash:log.transactionHash,logIndex:quantity(log.logIndex),blockNumber:quantity(log.blockNumber),
    blockHash:log.blockHash,orderHash:log.topics[1],owner:source.owner,counterparty:'0x'+log.topics[3].slice(26),
    side:side===0n?'BUY':'SELL',tokenId:String(BigInt('0x'+words[1])),makerAmountFilledRaw:String(BigInt('0x'+words[2])),
    takerAmountFilledRaw:String(BigInt('0x'+words[3])),feeRaw:String(BigInt('0x'+words[4])),builder:'0x'+words[5],
    metadata:'0x'+words[6],rawLogSha256:sha256(JSON.stringify(log)),receiptSha256};
}

/** No retries, alternate endpoint, proxy or changed fingerprint on source refusal. */
export function createRpc(store,fetcher=fetch,clock=()=>new Date().toISOString(),budgetMs=300000){
  const captures=[],deadline=performance.now()+budgetMs;
  return {captures,async call(method,params){
    if(!['eth_chainId','eth_getBlockByNumber','eth_getLogs','eth_getTransactionReceipt'].includes(method))fail();
    const remaining=Math.floor(deadline-performance.now());
    if(remaining<=0)throw new SourceFailure('observation_budget_exhausted','stopped');
    const request={jsonrpc:'2.0',id:1,method,params};const startedAt=clock();let status=null,raw=Buffer.alloc(0);
    try{
      const response=await fetcher(SOURCE.endpoint,{method:'POST',redirect:'error',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(request),signal:AbortSignal.timeout(Math.min(10000,remaining))});status=response.status;
      const chunks=[];let size=0;
      for await(const part of response.body){size+=part.length;if(size>2097152)fail('source_response_too_large');chunks.push(part);}
      raw=Buffer.concat(chunks);const bodySha256=store.put(raw);
      const capture={endpoint:SOURCE.endpoint,request,startedAt,receivedAt:clock(),status,bodySha256,bytes:raw.length};
      captures.push(store.putJSON(capture));
      if(status!==200)fail('source_http_refusal');
      const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
      if(!value||value.jsonrpc!=='2.0'||value.id!==1||Object.keys(value).sort().join(',')!=='id,jsonrpc,result'||value.result===null)fail('source_rpc_refusal');
      return {value:value.result,bodySha256,receivedAt:capture.receivedAt};
    }catch(error){
      if(!(error instanceof SourceFailure))captures.push(store.putJSON({endpoint:SOURCE.endpoint,request,startedAt,receivedAt:clock(),status,error:'source_transport_or_decode_failure'}));
      if(error instanceof SourceFailure)throw error;
      if(performance.now()>=deadline&&['TimeoutError','AbortError'].includes(error?.name))throw new SourceFailure('observation_budget_exhausted','stopped');
      throw new SourceFailure('source_transport_or_decode_failure');
    }
  }};
}

export async function fetchBaseline(rpc){
  const chain=await rpc.call('eth_chainId',[]);if(quantity(chain.value)!==SOURCE.chainId)fail('wrong_chain','reconciliation_required');
  const r=await rpc.call('eth_getBlockByNumber',['latest',false]);
  return {baseline:decodeHeader(r.value),baselineReceivedAt:r.receivedAt};
}

/** Every header and receipt is fetched outside DB locks. finality is source-reported. */
export async function fetchRange(rpc,baseline,previous){
  const b=decodeHeader((await rpc.call('eth_getBlockByNumber',[hex(baseline.number),false])).value);
  const f=decodeHeader((await rpc.call('eth_getBlockByNumber',['finalized',false])).value);
  if(b.hash!==baseline.hash) return {blocked:'baseline_hash_mismatch'};
  if(BigInt(f.number)<BigInt(previous.number)){
    if(previous.number!==baseline.number)fail('finalized_head_regressed','reconciliation_required');
    return {waiting:true};
  }
  if(f.number===previous.number){
    if(f.hash!==previous.hash)fail('canonical_checkpoint_mismatch','reconciliation_required');
    return {waiting:true};
  }
  if(BigInt(f.number)-BigInt(previous.number)>64n)fail('source_lag_exceeds_window','reconciliation_required');
  const headers=[];
  for(let n=BigInt(previous.number)+1n;n<=BigInt(f.number);n++){
    const h=n===BigInt(f.number)?f:decodeHeader((await rpc.call('eth_getBlockByNumber',[hex(n),false])).value);
    if(BigInt(h.number)!==n)fail('source_header_number_mismatch','reconciliation_required');headers.push(h);
  }
  const response=await rpc.call('eth_getLogs',[{address:SOURCE.exchange,fromBlock:hex(BigInt(previous.number)+1n),toBlock:hex(f.number),topics:[SOURCE.topic,null,ownerTopic]}]);
  if(!Array.isArray(response.value)||response.value.length>128)fail('source_logs_incomplete_or_limit');
  const receipts=new Map(),logs=[];
  for(const raw of response.value){
    if(!raw||!hash(raw.transactionHash))fail();
    let receipt=receipts.get(raw.transactionHash);
    if(!receipt){receipt=await rpc.call('eth_getTransactionReceipt',[raw.transactionHash]);receipts.set(raw.transactionHash,receipt);}
    const log=decodeOwnerLog(raw,receipt.value,receipt.bodySha256);
    const header=headers.find(h=>h.number===log.blockNumber);
    if(!header||header.hash!==log.blockHash)fail('source_log_outside_canonical_range','reconciliation_required');
    logs.push(log);
  }
  logs.sort((a,b)=>BigInt(a.blockNumber)<BigInt(b.blockNumber)?-1:BigInt(a.blockNumber)>BigInt(b.blockNumber)?1:BigInt(a.logIndex)<BigInt(b.logIndex)?-1:BigInt(a.logIndex)>BigInt(b.logIndex)?1:0);
  return {baselineCanonicalHash:b.hash,finalized:f,headers,logs};
}
