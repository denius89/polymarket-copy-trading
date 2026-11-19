import { createHash, createHmac, timingSafeEqual } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import type { IncomingMessage } from 'node:http';
import { StorageUnavailable } from '../storage/transaction.ts';

export const INGRESS_HEADERS = ['x-shadow-internal-deadline-ns','x-shadow-internal-body-sha256','x-shadow-internal-proof'] as const;
export type Ingress = {mode:'direct-test'} | {mode:'gateway-monotonic-v1';readKey:()=>Uint8Array};
const fail=():never=>{throw new StorageUnavailable();};
function one(req:Pick<IncomingMessage,'rawHeaders'>,name:string):string|undefined {
  const values:string[]=[];
  for(let i=0;i<req.rawHeaders.length;i+=2)if(req.rawHeaders[i].toLowerCase()===name)values.push(req.rawHeaders[i+1]);
  if(values.length>1)return fail();return values[0];
}
export function ingressMac(key:Uint8Array,method:string,target:string,bodyHash:string,deadline:string):Buffer {
  if(key.length!==32)return fail();
  const mac=createHmac('sha256',key).update('shadow.polygon.ingress.v1\0','ascii');
  for(const text of [method,target,bodyHash,deadline]){
    const bytes=Buffer.from(text,'utf8'),length=Buffer.alloc(4);length.writeUInt32BE(bytes.length);
    mac.update(length).update(bytes);
  }
  return mac.digest();
}
/** Linux CLOCK_MONOTONIC only. The operator verifies shared zero-offset time namespaces. */
export function ingressBudget(req:Pick<IncomingMessage,'rawHeaders'|'method'|'url'>,profile:Ingress,
  localNow=performance.now(),kernelNow=process.hrtime.bigint()):{started:number;bodyHash:string|null} {
  const [deadline,bodyHash,proof]=INGRESS_HEADERS.map(name=>one(req,name));
  if(profile.mode==='direct-test'){
    if(deadline!==undefined||bodyHash!==undefined||proof!==undefined)return fail();
    return {started:localNow,bodyHash:null};
  }
  if(!deadline||!/^[1-9][0-9]{0,18}$/.test(deadline)||!bodyHash||!/^[0-9a-f]{64}$/.test(bodyHash)||
    !proof||!/^[A-Za-z0-9_-]{43}$/.test(proof))return fail();
  const decoded=Buffer.from(proof,'base64url');
  if(decoded.length!==32||decoded.toString('base64url')!==proof)return fail();
  let expected:Buffer;
  try{expected=ingressMac(profile.readKey(),req.method??'',req.url??'',bodyHash,deadline);}catch{return fail();}
  if(!timingSafeEqual(decoded,expected))return fail();
  const remaining=BigInt(deadline)-kernelNow;
  if(remaining<=0n||remaining>5_000_000_000n)return fail();
  // localNow was sampled before kernelNow, so conversion cannot add queue time.
  return {started:localNow-(5000-Number(remaining)/1e6),bodyHash};
}
export function verifyIngressBody(body:Uint8Array,expected:string|null):void {
  if(expected!==null&&createHash('sha256').update(body).digest('hex')!==expected)return fail();
}
