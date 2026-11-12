import { createHmac } from 'node:crypto';
import { Buffer } from 'node:buffer';
import { closeSync, constants, fstatSync, openSync, readFileSync } from 'node:fs';
import { InputError, uuid } from './input.ts';
import { StorageUnavailable } from '../storage/transaction.ts';
import type { TrustedUserProof } from '../paper/service.ts';

/** Reload for every use: removal, permissions or mismatched key ID close the gate. Never log the file. */
export function credentialKeyReader(path: string): () => Uint8Array {
  return () => {
    let fd: number|undefined;
    try {
      fd=openSync(path,constants.O_RDONLY|constants.O_NOFOLLOW);
      const stat=fstatSync(fd);
      if(!stat.isFile()||(stat.mode&0o077)!==0||stat.size>16384)throw new Error();
      const value=JSON.parse(readFileSync(fd,'utf8'));
      const entry=value.credential;
      if(entry?.id!=='credential-1'||typeof entry.hex!=='string'||!/^[0-9a-f]{64}$/.test(entry.hex))throw new Error();
      return Buffer.from(entry.hex,'hex');
    }catch{throw new StorageUnavailable();}
    finally{if(fd!==undefined)closeSync(fd);}
  };
}
export function selectedUserProof(loginId: unknown, cookieHeader: string|undefined, readKey:()=>Uint8Array): TrustedUserProof {
  if(!uuid(loginId))throw new InputError();
  const name=`__Host-shadow-user-login-${loginId}`;
  const values=(cookieHeader??'').split(';').map(x=>x.trim()).filter(x=>x.startsWith(name+'=')).map(x=>x.slice(name.length+1));
  if(values.length>1)throw new InputError();
  if(values.length!==1||!/^[A-Za-z0-9_-]{43}$/.test(values[0]))throw new InputError(401,'AUTH_REQUIRED');
  const secret=Buffer.from(values[0],'base64url');
  if(secret.length!==32||secret.toString('base64url')!==values[0])throw new InputError(401,'AUTH_REQUIRED');
  const key=readKey();if(!(key instanceof Uint8Array)||key.length!==32)throw new StorageUnavailable();
  const mac=createHmac('sha256',key).update('shadow.v00.login-verify.v1\0','ascii');
  for(const value of ['v00-d03-07','user',loginId,'v00-test-login-cookie-v1',values[0]]) {
    const bytes=Buffer.from(value,'utf8'),length=Buffer.alloc(4);length.writeUInt32BE(bytes.length);
    mac.update(length).update(bytes);
  }
  return {login_id:loginId,cookie_digest:mac.digest('hex')};
}
