import {createHmac, randomBytes, timingSafeEqual} from 'node:crypto';
import sodium from 'libsodium-wrappers';
import {uuid, exactObject} from '../http/input.ts';
import {canonicalSecret} from './requests.ts';

export class PilotCryptoUnavailable extends Error {
  constructor() { super('Pilot crypto unavailable'); }
}
export interface PilotKeys {
  permit: Uint8Array; context: Uint8Array; login: Uint8Array; cipher: Uint8Array;
  cipherKeyId: string;
}
export interface PilotBinding {runId: string; deploymentDigest: string}
export interface LoginBinding {contextId: string; operationId: string; loginId: string}
export interface CookieEnvelope {key_id: string; nonce: string; ciphertext: string}
const fail = (): never => { throw new PilotCryptoUnavailable(); };
function frame(domain: string, parts: readonly (string|Uint8Array)[]) {
  const chunks = [Buffer.from(domain+'\0','ascii')];
  for (const value of parts) {
    const bytes = typeof value === 'string' ? Buffer.from(value,'utf8') : Buffer.from(value);
    const length = Buffer.alloc(4); length.writeUInt32BE(bytes.length);
    chunks.push(length,bytes);
  }
  return Buffer.concat(chunks);
}

/** Local secret-only profile, separate from all C7 and user key domains.
 * Call explicitly at runtime startup with operator-owned key material. */
export async function createPilotCrypto(binding: PilotBinding, supplied: PilotKeys) {
  if (!uuid(binding.runId) || !/^[a-f0-9]{64}$/.test(binding.deploymentDigest) || !uuid(supplied.cipherKeyId)) fail();
  const {runId, deploymentDigest} = binding;
  const {cipherKeyId} = supplied;
  const names = ['permit','context','login','cipher'] as const;
  const keys = Object.fromEntries(names.map(name => {
    const value = supplied[name];
    if (!(value instanceof Uint8Array) || value.length !== 32) fail();
    return [name, Buffer.from(value)];
  })) as Record<typeof names[number],Buffer>;
  for (let a=0;a<names.length;a++) for(let b=a+1;b<names.length;b++)
    if (timingSafeEqual(keys[names[a]],keys[names[b]])) { for(const k of Object.values(keys)) k.fill(0); fail(); }
  await sodium.ready;
  let closed = false;
  const active = () => { if(closed) fail(); };
  function proof(purpose: 'permit'|'context'|'logout'|'login', id: string, secret: unknown) {
    active(); if(!uuid(id) || !canonicalSecret(secret)) return fail();
    const bytes = Buffer.from(secret,'base64url');
    try {
      return createHmac('sha256',keys[purpose === 'logout' ? 'context' : purpose])
        .update(frame('shadow.pilot.'+purpose+'-proof.v1',[runId,deploymentDigest,id,bytes])).digest('hex');
    } finally { bytes.fill(0); }
  }
  function ad(value: LoginBinding) {
    active(); if(!uuid(value.contextId)||!uuid(value.operationId)||!uuid(value.loginId)) return fail();
    return frame('shadow.pilot.login-cookie.v1',[runId,deploymentDigest,
      value.contextId,value.operationId,value.loginId,cipherKeyId]);
  }
  return {
    proof,
    issue(purpose: 'context'|'logout'|'login', id: string) {
      active(); const secret = randomBytes(32);
      try {const cookie=secret.toString('base64url'); return {cookie,digest:proof(purpose,id,cookie)};}
      finally {secret.fill(0);}
    },
    seal(value: LoginBinding, cookie: string): CookieEnvelope {
      active(); if(!canonicalSecret(cookie)) return fail();
      const nonce = randomBytes(24), secret = Buffer.from(cookie,'base64url');
      try {
        const encrypted = sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(secret,ad(value),null,nonce,keys.cipher);
        return {key_id:cipherKeyId,nonce:nonce.toString('hex'),ciphertext:Buffer.from(encrypted).toString('hex')};
      } finally {secret.fill(0);}
    },
    open(value: LoginBinding, input: unknown): string {
      active(); let plain: Uint8Array|undefined;
      try {
        const e=exactObject(input,['key_id','nonce','ciphertext']);
        if(e.key_id!==cipherKeyId||typeof e.nonce!=='string'||!/^[a-f0-9]{48}$/.test(e.nonce)
          ||typeof e.ciphertext!=='string'||!/^[a-f0-9]{96}$/.test(e.ciphertext)) return fail();
        plain=sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(null,Buffer.from(e.ciphertext,'hex'),ad(value),Buffer.from(e.nonce,'hex'),keys.cipher);
        if(plain.length!==32) return fail();
        return Buffer.from(plain).toString('base64url');
      } catch {return fail();} finally {plain?.fill(0);}
    },
    close() {if(!closed){closed=true;for(const key of Object.values(keys))key.fill(0);}},
  };
}

/** Reader owns no permit, auth-context or cipher key. Logout has its own key. */
export function createPilotReaderCrypto(binding: PilotBinding, supplied: {login:Uint8Array; logout:Uint8Array}) {
  const {runId,deploymentDigest}=binding;
  if(!uuid(runId)||!/^[a-f0-9]{64}$/.test(deploymentDigest)||supplied.login.length!==32||supplied.logout.length!==32)fail();
  const login=Buffer.from(supplied.login), logout=Buffer.from(supplied.logout);
  if(timingSafeEqual(login,logout)){login.fill(0);logout.fill(0);fail();}
  let closed=false;
  function proof(purpose:'login'|'logout',id:string,secret:unknown) {
    if(closed||!uuid(id)||!canonicalSecret(secret))return fail();
    const bytes=Buffer.from(secret,'base64url');
    try {return createHmac('sha256',purpose==='login'?login:logout)
      .update(frame('shadow.pilot.'+purpose+'-proof.v1',[runId,deploymentDigest,id,bytes])).digest('hex');}
    finally {bytes.fill(0);}
  }
  return {proof,issue(id:string){const bytes=randomBytes(32);try{const cookie=bytes.toString('base64url');return {cookie,digest:proof('logout',id,cookie)};}finally{bytes.fill(0);}},
    close(){closed=true;login.fill(0);logout.fill(0);}};
}
