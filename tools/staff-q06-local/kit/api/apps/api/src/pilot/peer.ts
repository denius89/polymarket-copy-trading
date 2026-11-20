import {createHmac,timingSafeEqual} from 'node:crypto';
import type {IncomingMessage,ServerResponse} from 'node:http';
import {exactObject,InputError,parseCommandJson,uuid} from '../http/input.ts';
import {canonicalSecret} from './requests.ts';
import {PilotRecordUnavailable} from './responses.ts';
import type {PilotFrame,PilotHttpReply} from './services.ts';
import type {PilotRole} from './transaction.ts';

const MAX=32768;
export interface PilotPeerSettings {role:PilotRole;deploymentDigest:string;readIngressKey:()=>Uint8Array;enabled:()=>boolean}
type Service=(frame:PilotFrame)=>Promise<PilotHttpReply>;
function failure(error:unknown):PilotHttpReply {
  const status=error instanceof InputError?error.status:503;
  const reasonCode=error instanceof InputError?error.reasonCode:error instanceof PilotRecordUnavailable?'RECORD_UNAVAILABLE':'SERVICE_UNAVAILABLE';
  return {status,headers:{'Cache-Control':'no-store'},body:{reasonCode,reasonDetails:{code:reasonCode,params:{}},nextAction:null,nextActionParams:{}}};
}

/** Private MAC-authenticated ingress. Caller of this factory starts listeners explicitly. */
export function createPilotPeer(cfg:PilotPeerSettings,service:Service) {
  return async function handle(wire:Buffer,mac:string):Promise<PilotHttpReply>{
    try {
      if(!cfg.enabled()||wire.length>MAX||!/^[a-f0-9]{64}$/.test(mac))throw new InputError(503,'SERVICE_UNAVAILABLE');
      const key=cfg.readIngressKey();
      if(!(key instanceof Uint8Array)||key.length!==32)throw new InputError(503,'SERVICE_UNAVAILABLE');
      const expected=createHmac('sha256',key).update('shadow.pilot.ingress.v1\0').update(wire).digest();
      if(!timingSafeEqual(expected,Buffer.from(mac,'hex')))throw new InputError(503,'SERVICE_UNAVAILABLE');
      const r=exactObject(parseCommandJson(wire),['version','role','deploymentDigest','method','target','deadlineNs','bodyBase64','selectedLoginId','proof','networkDigest']);
      if(r.version!=='pilot-staff-peer-v1'||r.role!==cfg.role||r.deploymentDigest!==cfg.deploymentDigest||!['GET','POST'].includes(r.method as string)
        ||typeof r.target!=='string'||r.target.length>2048||typeof r.deadlineNs!=='string'||!/^[0-9]{1,20}$/.test(r.deadlineNs)
        ||typeof r.bodyBase64!=='string'||(r.selectedLoginId!==null&&!uuid(r.selectedLoginId))
        ||(r.proof!==null&&!canonicalSecret(r.proof))||(r.networkDigest!==null&&(typeof r.networkDigest!=='string'||!/^[a-f0-9]{64}$/.test(r.networkDigest))))throw new InputError();
      const body=Buffer.from(r.bodyBase64,'base64');
      if(body.toString('base64')!==r.bodyBase64||body.length>8192)throw new InputError();
      const deadlineNs=BigInt(r.deadlineNs),left=deadlineNs-process.hrtime.bigint();
      if(left<=0n||left>5000000000n)throw new InputError(503,'SERVICE_UNAVAILABLE');
      const reply=await service({method:r.method as string,target:r.target,body,deadlineNs,
        selectedLoginId:r.selectedLoginId as string|null,proof:r.proof as string|null,networkDigest:r.networkDigest as string|null});
      if(!cfg.enabled()||process.hrtime.bigint()>=deadlineNs)throw new InputError(503,'SERVICE_UNAVAILABLE');
      return reply;
    } catch(error){return failure(error);}
  };
}

export function createPilotHttpHandler(cfg:PilotPeerSettings,service:Service) {
  const peer=createPilotPeer(cfg,service);
  return async(req:IncomingMessage,res:ServerResponse)=>{
    let timer:ReturnType<typeof setTimeout>|undefined;
    try {
      if(req.method!=='POST'||req.url!=='/internal/pilot-staff/v1')throw new InputError(404,'RESOURCE_NOT_FOUND');
      const one=(name:string)=>{const values=req.headersDistinct[name];if(!values||values.length!==1)throw new InputError();return values[0];};
      if(req.headersDistinct['transfer-encoding']||one('content-type')!=='application/json')throw new InputError();
      const rawLength=one('content-length');
      if(!/^[1-9][0-9]{0,4}$/.test(rawLength)||Number(rawLength)>MAX)throw new InputError(413,'REQUEST_TOO_LARGE');
      const signature=one('x-pilot-signature');
      let size=0;const chunks:Buffer[]=[];
      const reading=(async()=>{for await(const chunk of req){const b=Buffer.from(chunk);size+=b.length;if(size>Number(rawLength))throw new InputError();chunks.push(b);}})();
      await Promise.race([reading,new Promise<never>((_,reject)=>{timer=setTimeout(()=>{req.destroy();reject(new InputError(503,'SERVICE_UNAVAILABLE'));},5000);})]);
      clearTimeout(timer);
      if(size!==Number(rawLength))throw new InputError();
      const out=await peer(Buffer.concat(chunks),signature);
      res.writeHead(out.status,{'Content-Type':'application/json',...out.headers});
      res.end(out.body===null?undefined:JSON.stringify(out.body));
    } catch(error){
      if(!res.headersSent&&!res.destroyed){const out=failure(error);res.writeHead(out.status,{'Content-Type':'application/json',...out.headers});res.end(JSON.stringify(out.body));}
    } finally {clearTimeout(timer);}
  };
}
