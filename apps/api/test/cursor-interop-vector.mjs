// Public deterministic test material only. Never import this file from runtime.
import sodium from 'libsodium-wrappers';
await sodium.ready;
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const plaintext={requestSchemaVersion:'v1',environmentBinding:'a'.repeat(64),readerBinding:'b'.repeat(64),
  venueId:id(10),venueCode:'polymarket',limit:2,lastTraderId:id(2),catalogFingerprint:'c'.repeat(64)};
const ordered=Object.fromEntries(Object.entries(plaintext).sort(([a],[b])=>a<b?-1:1));
const bytes=Buffer.from(JSON.stringify(ordered),'utf8');
const header=Buffer.concat([Buffer.from([1]),Buffer.alloc(16,1)]),nonce=Buffer.from(Array.from({length:24},(_,i)=>i));
const key=Buffer.from(Array.from({length:32},(_,i)=>i)),aad=Buffer.concat([Buffer.from('shadow.q02.cursor.v1\0','ascii'),header]);
const encrypted=sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(bytes,aad,null,nonce,key);
process.stdout.write(JSON.stringify({purpose:'public-test-vector-only',wire:Buffer.concat([header,nonce,encrypted]).toString('base64url')})+'\n');
