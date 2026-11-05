import { randomUUID } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { InputError, parseCommandJson, parseQuery, uuid } from './input.ts';
import { selectedUserProof } from './user-proof.ts';
import { parseCardRequest, parseListRequest, CatalogError } from '../catalog/contracts.ts';
import { apiError } from '../paper/service.ts';
import type { PaperService, PaperOperation, ApiReply } from '../paper/service.ts';
import { c04Request, c05Request, c06Request } from '../paper/requests.ts';
import { ingressBudget, verifyIngressBody } from './ingress.ts';
import type { Ingress } from './ingress.ts';

function header(req:IncomingMessage,name:string):string|undefined {
  const values=[];
  for(let i=0;i<req.rawHeaders.length;i+=2)if(req.rawHeaders[i].toLowerCase()===name)values.push(req.rawHeaders[i+1]);
  if(values.length>1)throw new InputError();return values[0];
}
function pathId(value:string):string {if(!uuid(value))throw new InputError();return value;}
function route(method:string,path:string,query:string,body:Uint8Array):PaperOperation {
  if(method==='GET'){
    if(body.length)throw new InputError();
    if(path==='/api/traders')return {kind:'catalog-list',request:parseListRequest(query)};
    const card=/^\/api\/traders\/([^/]+)\/([^/]+)$/.exec(path);
    if(card)return {kind:'catalog-card',request:parseCardRequest(card[1],card[2],query)};
    const command=/^\/api\/commands\/([^/]+)$/.exec(path);
    if(command){
      const q=parseQuery(query,['requestSchemaVersion','commandType','actorRealm','actorId']);
      if(q.actorRealm!=='user'||!['C04','C06'].includes(q.commandType)||!uuid(q.actorId))throw new InputError();
      return {kind:'command',clientCommandId:pathId(command[1]),commandType:q.commandType as 'C04'|'C06',actorRealm:'user',actorId:q.actorId};
    }
    parseQuery(query,['requestSchemaVersion']);
    if(path==='/__polygon__/identity')return {kind:'identity'}; // Never published by the HTTPS launcher.
    const draft=/^\/api\/demo\/drafts\/([^/]+)$/.exec(path);
    if(draft)return {kind:'draft',draftId:pathId(draft[1])};
    if(path==='/api/sessions/current')return {kind:'session',sessionId:null};
    const session=/^\/api\/sessions\/([^/]+)$/.exec(path);
    if(session)return {kind:'session',sessionId:pathId(session[1])};
  } else if(method==='POST'||method==='PATCH') {
    if(query)throw new InputError();
    const parsed=parseCommandJson(body);
    if(method==='POST'&&path==='/api/demo/drafts')return {kind:'save',draftId:null,body:c04Request(parsed,false)};
    const update=/^\/api\/demo\/drafts\/([^/]+)$/.exec(path);
    if(method==='PATCH'&&update)return {kind:'save',draftId:pathId(update[1]),body:c04Request(parsed,true)};
    if(method==='POST'&&path==='/api/demo/validate')return {kind:'validate',body:c05Request(parsed)};
    if(method==='POST'&&path==='/api/sessions')return {kind:'start',body:c06Request(parsed)};
  }
  throw new InputError(404,'RESOURCE_NOT_FOUND');
}

async function readBody(req:IncomingMessage,started:number):Promise<Uint8Array> {
  return new Promise((resolve,reject)=>{
    const chunks:Buffer[]=[];let count=0,settled=false;
    const finish=(error?:Error)=>{
      if(settled)return;settled=true;clearTimeout(timer);
      req.off('data',data);req.off('end',end);req.off('aborted',abort);req.off('error',abort);
      if(error){req.resume();reject(error);}else resolve(Buffer.concat(chunks,count));
    };
    const data=(chunk:Buffer)=>{count+=chunk.length;if(count>65536)finish(new InputError(413,'REQUEST_TOO_LARGE'));else chunks.push(chunk);};
    const end=()=>finish();const abort=()=>finish(new InputError(503,'SERVICE_UNAVAILABLE'));
    const timer=setTimeout(abort,Math.max(1,Math.floor(started+5000-performance.now())));
    req.on('data',data);req.once('end',end);req.once('aborted',abort);req.once('error',abort);
  });
}

/** Internal listener only. The existing HTTPS launcher owns TLS and exposes a strict route allowlist. */
export function paperHandler(config:{origin:string;service:Pick<PaperService,'execute'>;readCredentialKey:()=>Uint8Array;ingress?:Ingress}) {
  const origin=new URL(config.origin);
  if(origin.protocol!=='https:'||origin.origin!==config.origin)throw new Error('A canonical HTTPS origin is required');
  return async(req:IncomingMessage,res:ServerResponse)=>{
    const requestId=randomUUID();
    let correlation:string|undefined,reply:ApiReply;
    try {
      const {started,bodyHash}=ingressBudget(req,config.ingress??{mode:'direct-test'});
      const bytes=await readBody(req,started);verifyIngressBody(bytes,bodyHash);
      if(header(req,'host')!==origin.host)throw new InputError();
      const method=req.method??'';
      if(method==='POST'||method==='PATCH'){
        const media=header(req,'content-type'),encoding=header(req,'content-encoding');
        if(!media||!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(media)||(encoding!==undefined&&encoding!=='identity'))throw new InputError(415,'UNSUPPORTED_MEDIA_TYPE');
      }
      correlation=header(req,'x-correlation-id');if(correlation!==undefined&&!uuid(correlation)){correlation=undefined;throw new InputError();}
      const target=req.url??'',index=target.indexOf('?'),path=index<0?target:target.slice(0,index),query=index<0?'':target.slice(index+1);
      const op=route(method,path,query,bytes);
      if(method==='POST'||method==='PATCH'){
        let supplied,marker,site;
        try{supplied=header(req,'origin');marker=header(req,'x-shadow-auth-request');site=header(req,'sec-fetch-site');}
        catch{throw new InputError(403,'ACCESS_DENIED');}
        if(supplied!==config.origin||marker!=='1'||(site!==undefined&&site!=='same-origin'))throw new InputError(403,'ACCESS_DENIED');
      }else{
        const site=header(req,'sec-fetch-site');if(site!==undefined&&site!=='same-origin'&&site!=='none')throw new InputError(403,'ACCESS_DENIED');
      }
      const proof=selectedUserProof(header(req,'x-shadow-login-id'),header(req,'cookie'),config.readCredentialKey);
      reply=await config.service.execute(proof,op,started);
    }catch(error){
      if(error instanceof InputError||error instanceof CatalogError)reply=apiError(error.status,error.reasonCode,error.status===401?'authenticate':null);
      else reply=apiError(503,'SERVICE_UNAVAILABLE','retry_later');
    }
    if(res.destroyed)return;
    const headers:Record<string,string>={'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Request-Id':requestId,'X-Content-Type-Options':'nosniff'};
    if(correlation)headers['X-Correlation-Id']=correlation;
    res.writeHead(reply.status,headers);res.end(JSON.stringify(reply.body));
  };
}
