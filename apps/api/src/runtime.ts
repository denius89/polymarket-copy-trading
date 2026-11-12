import { createServer } from 'node:http';
import { closeSync, constants, fstatSync, openSync, readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import process from 'node:process';
import pg from 'pg';
import { exactObject, parseCommandJson } from './http/input.ts';
import { paperHandler } from './http/handler.ts';
import { credentialKeyReader } from './http/user-proof.ts';
import { createCursorCodec } from './catalog/cursor.ts';
import { assertCalendarProfile } from './time/evaluation-deadline.ts';
import type { CalendarProfile } from './time/evaluation-deadline.ts';
import { PaperService } from './paper/service.ts';
import { StorageUnavailable } from './storage/transaction.ts';
import type { Ingress } from './http/ingress.ts';

function privateFile(path:string):unknown {
  let fd:number|undefined;
  try{
    fd=openSync(path,constants.O_RDONLY|constants.O_NOFOLLOW);const stat=fstatSync(fd);
    if(!stat.isFile()||(stat.mode&0o077)!==0||stat.size>65536)throw new Error();
    return parseCommandJson(readFileSync(fd));
  }catch{throw new StorageUnavailable();}finally{if(fd!==undefined)closeSync(fd);}
}

export async function startPaperRuntime(configPath:string) {
  const c=exactObject(privateFile(configPath),['profile','origin','databaseUrl','credentialKeyFile','cursorKeyFile','calendarProfile','startEnabled','bindHost','port','ingress']);
  if(c.profile!=='polygon-paper-v1'||typeof c.origin!=='string'||typeof c.databaseUrl!=='string'||
    typeof c.credentialKeyFile!=='string'||typeof c.cursorKeyFile!=='string'||typeof c.startEnabled!=='boolean'||
    !['127.0.0.1','0.0.0.0'].includes(c.bindHost as string)||!Number.isInteger(c.port)||(c.port as number)<1024||(c.port as number)>65535)throw new StorageUnavailable();
  const db=new URL(c.databaseUrl);if(!['postgres:','postgresql:'].includes(db.protocol))throw new StorageUnavailable();
  const calendar=c.calendarProfile as CalendarProfile;assertCalendarProfile(calendar);
  let ingress:Ingress;
  if((c.ingress as {mode?:unknown})?.mode==='direct-test'){
    exactObject(c.ingress,['mode']);ingress={mode:'direct-test'};
  }else{
    const i=exactObject(c.ingress,['mode','keyFile']);
    if(i.mode!=='gateway-monotonic-v1'||typeof i.keyFile!=='string'||process.platform!=='linux')throw new StorageUnavailable();
    const offsets=readFileSync('/proc/self/timens_offsets','utf8').trim().split('\n');
    if(offsets.length!==2||!/^monotonic\s+0\s+0$/.test(offsets[0])||!/^boottime\s+0\s+0$/.test(offsets[1]))throw new StorageUnavailable();
    const keyFile=i.keyFile;
    const readKey=()=>{
      const k=exactObject(privateFile(keyFile),['format','hex']);
      if(k.format!=='polygon-ingress-hmac-v1'||typeof k.hex!=='string'||!/^[0-9a-f]{64}$/.test(k.hex))throw new StorageUnavailable();
      return Buffer.from(k.hex,'hex');
    };
    readKey();ingress={mode:'gateway-monotonic-v1',readKey};
  }
  const readCredentialKey=credentialKeyReader(c.credentialKeyFile);readCredentialKey();
  const cursorKeyFile=c.cursorKeyFile;
  const readKeys=()=>{
    const k=exactObject(privateFile(cursorKeyFile),['format','enabled','issuerKeyId','keys','revoked']);
    if(k.format!=='q02-cursor-keyset-v1'||k.enabled!==true||typeof k.issuerKeyId!=='string'||!Array.isArray(k.keys)||!Array.isArray(k.revoked))throw new StorageUnavailable();
    const keys=new Map<string,Uint8Array>(),revoked=new Set<string>();
    for(const value of k.keys){
      const item=exactObject(value,['keyId','hex']);
      if(typeof item.keyId!=='string'||!/^[0-9a-f]{32}$/.test(item.keyId)||typeof item.hex!=='string'||!/^[0-9a-f]{64}$/.test(item.hex)||keys.has(item.keyId))throw new StorageUnavailable();
      keys.set(item.keyId,Buffer.from(item.hex,'hex'));
    }
    for(const id of k.revoked){if(typeof id!=='string'||!/^[0-9a-f]{32}$/.test(id)||revoked.has(id))throw new StorageUnavailable();revoked.add(id);}
    return {available:true,issuerKeyId:k.issuerKeyId,keys,revoked};
  };
  readKeys();
  const cursor=await createCursorCodec(readKeys);
  const pool=new pg.Pool({connectionString:c.databaseUrl,max:4,connectionTimeoutMillis:5000,idleTimeoutMillis:10000,application_name:'shadow-polygon-paper-api'});
  // A broken idle connection is discarded by pg. Never print driver messages containing connection data.
  pool.on('error',()=>{});
  const service=new PaperService({pool,cursor,calendar,startEnabled:c.startEnabled});
  const handler=paperHandler({origin:c.origin,service,readCredentialKey,ingress});
  const server=createServer((req,res)=>{
    void handler(req,res).catch(()=>{if(!res.destroyed)res.destroy();});
  });
  server.headersTimeout=5000;server.requestTimeout=5000;server.keepAliveTimeout=5000;server.maxHeadersCount=64;
  server.on('clientError',(_error,socket)=>{if(socket.writable)socket.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n');});
  try {await new Promise<void>((resolve,reject)=>{server.once('error',reject);server.listen(c.port as number,c.bindHost as string,()=>resolve());});}
  catch {await pool.end();throw new StorageUnavailable();}
  return {server,pool,async close(){await new Promise<void>((resolve,reject)=>server.close(e=>e?reject(e):resolve()));await pool.end();}};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const path=process.env.POLYGON_API_CONFIG;
  if(!path){process.stderr.write('Paper API configuration unavailable\n');process.exitCode=1;}
  else {
    startPaperRuntime(path).then(runtime=>{
      process.stdout.write('Internal polygon paper API started; readiness requires separate DB checks\n');
      for(const signal of ['SIGINT','SIGTERM']as const)process.once(signal,()=>{void runtime.close().catch(()=>{process.exitCode=1;});});
    }).catch(()=>{process.stderr.write('Paper API startup failed\n');process.exitCode=1;});
  }
}
