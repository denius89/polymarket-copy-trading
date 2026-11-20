import {gammaBinding} from './binding.mjs';
import {BuyBlocked} from './guard.mjs';

// Run-local memo: at most one GET per token, including failure; no denial retry.
// Cached identity is for immutable skipped observations only, never execution.
export function createFallbackEvaluator({client,store,wall=Date.now}){
  const captures=new Map();
  return async function evaluate(signal){
    let gamma=null,binding=null,reason='profile_unavailable';
    try{
      if(!captures.has(signal.tokenId))captures.set(signal.tokenId,client.gamma(signal.tokenId));
      gamma=await captures.get(signal.tokenId);
      const {outcomeSlot,...known}=gammaBinding(signal.tokenId,gamma);binding=known;
    }catch(error){reason=error instanceof BuyBlocked?error.reason:'source_unavailable';}
    const now=wall(),at=Date.parse(signal.sourceOccurredAt),g=gamma?.market;
    if(signal.side!=='BUY')reason='not_buy';
    // ADR0057: verified context/profile unavailability outranks signal age/market.
    // This fallback has no execution profile, so neither can become primary.
    else if(binding)reason='profile_unavailable';
    const checks={
      action:{status:signal.side==='BUY'?'passed':'not_applicable'},
      binding:{status:binding?'passed':'unavailable'},
      executionProfile:{status:signal.side==='BUY'?'unavailable':'not_applicable'},
      signalAge:{status:!Number.isSafeInteger(at)||!Number.isSafeInteger(now)?'unavailable':at>now?'unavailable':now-at>30000?'failed':'passed',rawAgeMs:Number.isSafeInteger(at)?now-at:null,clockTrust:'unproven'},
      market:{status:!g?'not_evaluated':g.active===true&&g.closed===false&&g.archived===false&&g.acceptingOrders===true&&g.enableOrderBook===true?'passed':'unavailable'},
      book:{status:'not_evaluated'},fees:{status:'not_evaluated'},limits:{status:'not_evaluated'}
    };
    const evidenceSha256=store.putJSON({schemaVersion:'bound-skip-capture-v1',signal,binding,
      evaluatedAt:new Date(now).toISOString(),reason,checks,activation:'disabled',
      gammaSha256:gamma?.bodySha256??null,gammaReceivedAt:gamma?new Date(gamma.receivedWallMs).toISOString():null,
      observedMarketFields:g?{secondsDelay:g.secondsDelay??null,feesEnabled:g.feesEnabled??null,feeSchedule:g.feeSchedule??null}:null,
      bookRequested:false,clockProof:null,executionProfile:null});
    return {schemaVersion:'paper-buy-evidence-v1',kind:'skip',reason,binding,evidenceSha256};
  };
}

export async function buildEnvelope(ingest,{armedAt,evaluate}){
  const unique=new Set(),evaluations=[];
  for(const log of ingest.logs){
    const key=log.transactionHash+':'+log.logIndex;
    if(unique.has(key))continue;unique.add(key);
    const header=ingest.headers.find(h=>h.number===log.blockNumber);
    if(!header)throw new Error('range_header_missing');
    const ms=BigInt(header.timestampSeconds)*1000n;
    if(ms<=BigInt(Date.parse(armedAt)))continue;
    if(ms>8640000000000000n)throw new Error('source_time_invalid');
    const signal={tokenId:log.tokenId,side:log.side,exchange:'0xe111180000d2663c0091e4f400237545b87b996b',sourceOccurredAt:new Date(Number(ms)).toISOString(),transactionHash:log.transactionHash,logIndex:log.logIndex};
    const evidence=await evaluate(signal);
    if(evidence.kind!=='skip')throw new Error('fallback_rejects_candidate');
    evaluations.push({transactionHash:log.transactionHash,logIndex:log.logIndex,evidence});
  }
  return {ingest,expectedSnapshotVersion:'1',evaluations};
}
