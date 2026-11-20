import { exactObject, InputError, parseCommandJson, uuid } from '../http/input.ts';

/** D02 wire decoder only; a decoded credential is not a verified identity. */
export function base64url(value:unknown,min:number,max:number):Buffer {
  if(typeof value!=='string'||!/^[A-Za-z0-9_-]+$/.test(value))throw new InputError();
  const bytes=Buffer.from(value,'base64url');
  if(bytes.length<min||bytes.length>max||bytes.toString('base64url')!==value)throw new InputError();
  return bytes;
}
function clientData(value:unknown):void {
  const bytes=base64url(value,1,4096),parsed=parseCommandJson(bytes);
  if(parsed===null||typeof parsed!=='object'||Array.isArray(parsed))throw new InputError();
  // Exact challenge/origin/type and cross-origin policy are verification checks,
  // performed only after an authorized, live, operation-bound snapshot is read.
}
function credentialEnvelope(value:unknown):Record<string,unknown> {
  const v=exactObject(value,['id','rawId','type','response','clientExtensionResults']);
  base64url(v.id,1,1023);base64url(v.rawId,1,1023);
  if(v.id!==v.rawId||v.type!=='public-key')throw new InputError();
  exactObject(v.clientExtensionResults,[]);return v;
}
export function assertion(value:unknown):Record<string,unknown> {
  const v=credentialEnvelope(value),r=exactObject(v.response,['clientDataJSON','authenticatorData','signature','userHandle']);
  clientData(r.clientDataJSON);base64url(r.authenticatorData,1,2048);base64url(r.signature,1,1024);
  if(r.userHandle!==null)base64url(r.userHandle,1,64);
  return v;
}
export function registration(value:unknown):Record<string,unknown> {
  const v=credentialEnvelope(value),r=exactObject(v.response,['clientDataJSON','attestationObject']);
  clientData(r.clientDataJSON);base64url(r.attestationObject,1,32768);return v;
}
export function verifyRequest(bytes:Uint8Array,kind:'staff_login'|'registration_verify'):Record<string,unknown> {
  const limit=kind==='registration_verify'?65536:8192;
  if(bytes.byteLength>limit)throw new InputError(413,'REQUEST_TOO_LARGE');
  const field=kind==='staff_login'?'assertion':'credential';
  const v=exactObject(parseCommandJson(bytes),['requestSchemaVersion','operationId','challengeId',field]);
  if(v.requestSchemaVersion!=='v1'||!uuid(v.operationId)||!uuid(v.challengeId))throw new InputError();
  if(kind==='staff_login')assertion(v[field]);else registration(v[field]);
  return v;
}
