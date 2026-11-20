import {open,stat} from 'node:fs/promises';
import {constants} from 'node:fs';
import {dirname,isAbsolute} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createServer} from 'node:http';
import {isIP} from 'node:net';
import {performance} from 'node:perf_hooks';
import {timingSafeEqual} from 'node:crypto';
import {Pool} from 'pg';
import {exactObject,parseCommandJson,uuid} from '../http/input.ts';
import {timestamp} from '../paper/responses.ts';
import {createPilotCrypto,createPilotReaderCrypto} from './crypto.ts';
import {createPilotAuthService,createPilotReaderService} from './services.ts';
import {createPilotHttpHandler} from './peer.ts';

const unavailable=():never=>{throw new Error('Pilot startup unavailable');};
async function protectedFile(path:unknown,max:number):Promise<Buffer>{
  if(typeof path!=='string'||!isAbsolute(path))return unavailable();
  const parent=await stat(dirname(path));
  if(!parent.isDirectory()||(parent.mode&0o022)!==0)return unavailable();
  const file=await open(path,constants.O_RDONLY|constants.O_NOFOLLOW);
  try{
    const s=await file.stat(),uid=process.getuid?.();
    if(!s.isFile()||s.size<1||s.size>max||(s.mode&0o027)!==0||(s.uid!==0&&s.uid!==uid))return unavailable();
    return await file.readFile();
  }finally{await file.close();}
}
function privateHost(value:unknown):value is string{
  if(typeof value!=='string')return false;
  if(isIP(value)===4){const [a,b]=value.split('.').map(Number);return a===10||a===127||(a===172&&b>=16&&b<=31)||(a===192&&b===168);}
  return /^[a-z][a-z0-9-]{0,62}$/.test(value); // explicit single Docker DNS name; no public DNS suffix
}
function port(value:unknown):value is number{return Number.isInteger(value)&&Number(value)>=1024&&Number(value)<=65535;}

/** Explicit startup only. Importing the module opens no port, DB connection or key. */
export async function startPilotRuntime(configPath:string){
  if(process.getuid?.()===0)return unavailable();
  const rawConfig=await protectedFile(configPath,16384);
  let cfg:Record<string,unknown>;
  try{cfg=exactObject(parseCommandJson(rawConfig),['version','enabled','role','runId','deploymentDigest','cutoffAt','bindHost','port','dbTransport','database','ingressKeyFile','keys']);}
  finally{rawConfig.fill(0);}
  if(cfg.version!=='pilot-staff-runtime-v1'||cfg.enabled!==true||!['auth','reader'].includes(cfg.role as string)||!uuid(cfg.runId)
    ||typeof cfg.deploymentDigest!=='string'||!/^[a-f0-9]{64}$/.test(cfg.deploymentDigest)||!timestamp(cfg.cutoffAt)
    ||!['127.0.0.1','0.0.0.0'].includes(cfg.bindHost as string)||!port(cfg.port)||cfg.dbTransport!=='isolated-private-network')return unavailable();
  const timeLeft=Date.parse(cfg.cutoffAt as string)-Date.now();
  if(timeLeft<=0||timeLeft>48*60*60*1000)return unavailable();
  const monotonicCutoff=performance.now()+timeLeft;
  const db=exactObject(cfg.database,['host','port','name','user','passwordFile']);
  if(!privateHost(db.host)||!port(db.port)||typeof db.name!=='string'||!/^[a-z][a-z0-9_]{0,62}$/.test(db.name)
    ||typeof db.user!=='string'||!/^[a-z][a-z0-9_]{0,62}$/.test(db.user))return unavailable();
  const role=cfg.role as 'auth'|'reader';
  const keyPaths=exactObject(cfg.keys,role==='auth'?['permit','context','login','cipher','cipherKeyId']:['login','logout']);
  if(role==='auth'&&!uuid(keyPaths.cipherKeyId))return unavailable();
  const loaded:Buffer[]=[],keyMaterial:Buffer[]=[];
  const readKey=async(path:unknown)=>{const b=await protectedFile(path,32);loaded.push(b);
    if(stopped||b.length!==32||keyMaterial.some(k=>timingSafeEqual(k,b))){b.fill(0);return unavailable();}
    keyMaterial.push(b);return b;};
  let pool:Pool|undefined;
  let crypto:{close:()=>void}|undefined;
  let server:ReturnType<typeof createServer>|undefined;
  let timer:ReturnType<typeof setTimeout>|undefined;
  let stopped=false;
  const enabled=()=>!stopped&&Date.now()<Date.parse(cfg.cutoffAt as string)&&performance.now()<monotonicCutoff;
  async function close(){
    if(stopped)return;stopped=true;clearTimeout(timer);
    server?.closeAllConnections();
    if(server?.listening)await new Promise<void>(resolve=>server!.close(()=>resolve()));
    await pool?.end();crypto?.close();for(const key of loaded)key.fill(0);
  }
  try{
    const ingress=await readKey(cfg.ingressKeyFile),binding={runId:cfg.runId as string,deploymentDigest:cfg.deploymentDigest as string};
    const pass=await protectedFile(db.passwordFile,1024);loaded.push(pass);
    const password=new TextDecoder('utf-8',{fatal:true}).decode(pass);
    if(!password||/[\x00\r\n]/.test(password))return unavailable();
    pool=new Pool({host:db.host as string,port:db.port as number,database:db.name as string,user:db.user as string,password,
      ssl:false,max:4,connectionTimeoutMillis:5000,idleTimeoutMillis:30000,statement_timeout:5000,application_name:'pilot-staff-'+role});
    pool.on('error',()=>{void close();}); // no raw connection errors or credentials in logs
    const acl=await pool.query(`SELECT current_user AS name, r.rolsuper,r.rolbypassrls,r.rolcreaterole,r.rolcreatedb,r.rolreplication,
      pg_has_role(current_user,'pilot_staff_auth','MEMBER') AS auth,
      pg_has_role(current_user,'pilot_staff_reader','MEMBER') AS reader,
      pg_has_role(current_user,'pilot_staff_operator','MEMBER') AS operator,
      pg_has_role(current_user,'pilot_staff_owner','MEMBER') AS owner
      FROM pg_roles r WHERE r.rolname=current_user`);
    const account=acl.rows[0];
    if(acl.rows.length!==1||account.name!==db.user||account.rolsuper||account.rolbypassrls||account.rolcreaterole||account.rolcreatedb
      ||account.rolreplication||account.operator||account.owner||account[role]!==true||account[role==='auth'?'reader':'auth']!==false)return unavailable();
    if(!enabled())return unavailable();
    let service;
    if(role==='auth'){
      const auth=await createPilotCrypto(binding,{permit:await readKey(keyPaths.permit),context:await readKey(keyPaths.context),
        login:await readKey(keyPaths.login),cipher:await readKey(keyPaths.cipher),cipherKeyId:keyPaths.cipherKeyId as string});
      if(stopped){auth.close();return unavailable();}
      crypto=auth;service=createPilotAuthService({pool,crypto:auth,deploymentDigest:binding.deploymentDigest});
    }else{
      const reader=createPilotReaderCrypto(binding,{login:await readKey(keyPaths.login),logout:await readKey(keyPaths.logout)});
      crypto=reader;service=createPilotReaderService({pool,crypto:reader,deploymentDigest:binding.deploymentDigest});
    }
    if(!enabled())return unavailable();
    server=createServer(createPilotHttpHandler({role,deploymentDigest:binding.deploymentDigest,readIngressKey:()=>ingress,enabled},service));
    server.requestTimeout=6000;server.headersTimeout=5000;server.keepAliveTimeout=1000;server.maxHeadersCount=20;
    await new Promise<void>((resolve,reject)=>{server!.once('error',reject);server!.listen(cfg.port as number,cfg.bindHost as string,resolve);});
    timer=setTimeout(()=>{void close();},Math.max(1,monotonicCutoff-performance.now()));
    return {close,role};
  }catch(error){await close();throw error;}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  if(process.argv.length!==3){process.stderr.write('Pilot configuration path required\n');process.exitCode=1;}
  else startPilotRuntime(process.argv[2]).then(runtime=>{
    process.stdout.write(JSON.stringify({event:'pilot_private_ready',role:runtime.role})+'\n');
    process.once('SIGTERM',()=>{void runtime.close();});process.once('SIGINT',()=>{void runtime.close();});
  }).catch(()=>{process.stderr.write('Pilot startup unavailable\n');process.exitCode=1;});
}
