import sodium from 'libsodium-wrappers';
import { Buffer } from 'node:buffer';
import { randomBytes } from 'node:crypto';
import { exactObject, InputError, parseCommandJson, uuid } from '../http/input.ts';
import { StorageRecordUnavailable, StorageUnavailable } from '../storage/transaction.ts';
import { canonical } from './snapshot.ts';
import type { CatalogSnapshot } from './snapshot.ts';
import type { CatalogPage, ListRequest } from './contracts.ts';

export interface CursorKeySet {
  available: boolean;
  issuerKeyId: string; // 16 bytes, lowercase hex. Key material never appears in output/logs.
  keys: ReadonlyMap<string, Uint8Array>;
  revoked: ReadonlySet<string>;
}
interface PlainCursor {
  requestSchemaVersion: 'v1'; environmentBinding: string; readerBinding: string;
  venueId: string; venueCode: string; limit: number; lastTraderId: string; catalogFingerprint: string;
}
const aad = (header: Uint8Array) => Buffer.concat([Buffer.from('shadow.q02.cursor.v1\0','ascii'),header]);
const invalid = (): never => {throw new InputError();};
const validKeyId = (id: unknown): id is string => typeof id === 'string' && /^[0-9a-f]{32}$/.test(id);
function keySet(value: CursorKeySet): CursorKeySet {
  if (!value || value.available !== true || !validKeyId(value.issuerKeyId) ||
      !(value.keys instanceof Map) || !(value.revoked instanceof Set)) throw new StorageUnavailable();
  for (const [id,key] of value.keys) if (!validKeyId(id) || !(key instanceof Uint8Array) || key.length !== 32) throw new StorageUnavailable();
  for (const id of value.revoked) if (!validKeyId(id)) throw new StorageUnavailable();
  if (!value.keys.has(value.issuerKeyId) || value.revoked.has(value.issuerKeyId)) throw new StorageUnavailable();
  return value;
}
function decodePlain(bytes: Uint8Array): PlainCursor {
  try {
    const p = exactObject(parseCommandJson(bytes), ['requestSchemaVersion','environmentBinding','readerBinding',
      'venueId','venueCode','limit','lastTraderId','catalogFingerprint']);
    if (p.requestSchemaVersion !== 'v1' || !uuid(p.venueId) || !uuid(p.lastTraderId) ||
        !['polymarket','limitless'].includes(p.venueCode as string) || !Number.isInteger(p.limit) ||
        (p.limit as number) < 1 || (p.limit as number) > 50 ||
        !['environmentBinding','readerBinding','catalogFingerprint'].every(k => typeof p[k] === 'string' && /^[0-9a-f]{64}$/.test(p[k] as string)) ||
        !Buffer.from(canonical(p),'utf8').equals(Buffer.from(bytes))) return invalid();
    return p as unknown as PlainCursor;
  } catch {return invalid();}
}

/** Initialise before accepting HTTP, never during a DB transaction. No TTL and no key generation here. */
export async function createCursorCodec(readKeys: () => CursorKeySet) {
  await sodium.ready;
  return {
    page(request: ListRequest, snapshot: CatalogSnapshot): CatalogPage {
      if (!Number.isInteger(request.limit) || request.limit < 1 || request.limit > 50) return invalid();
      const keys = keySet(readKeys()); // Current authoritative key status; unknown availability is never a cache fallback.
      let start = 0;
      if (request.cursor !== undefined) {
        const token = request.cursor;
        if (!/^[A-Za-z0-9_-]{1,2048}$/.test(token)) return invalid();
        const bytes = Buffer.from(token, 'base64url');
        if (bytes.toString('base64url') !== token || bytes.length < 58 || bytes[0] !== 1) return invalid();
        const id = bytes.subarray(1,17).toString('hex');
        if (keys.revoked.has(id) || !keys.keys.has(id)) return invalid();
        let clear: Uint8Array;
        try {clear = sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(null, bytes.subarray(41), aad(bytes.subarray(0,17)), bytes.subarray(17,41), keys.keys.get(id)!);}
        catch {return invalid();}
        const p = decodePlain(clear);
        if (p.environmentBinding !== snapshot.environmentBinding || p.readerBinding !== snapshot.readerBinding ||
            p.venueId !== snapshot.venueId || p.venueCode !== request.venueCode || p.limit !== request.limit) return invalid();
        if (p.catalogFingerprint !== snapshot.catalogFingerprint) throw new InputError(409, 'CATALOG_CHANGED');
        start = snapshot.items.findIndex(item => item.traderId === p.lastTraderId) + 1;
        if (start === 0 || start >= snapshot.items.length) return invalid();
      }
      if (snapshot.venueCode !== request.venueCode) throw new StorageRecordUnavailable();
      const items = snapshot.items.slice(start, start + request.limit);
      let nextCursor: string | null = null;
      if (start + items.length < snapshot.items.length) {
        const plaintext = canonical({requestSchemaVersion:'v1',environmentBinding:snapshot.environmentBinding,
          readerBinding:snapshot.readerBinding,venueId:snapshot.venueId,venueCode:snapshot.venueCode,
          limit:request.limit,lastTraderId:items.at(-1)!.traderId,catalogFingerprint:snapshot.catalogFingerprint});
        try {
          const header = Buffer.concat([Buffer.from([1]),Buffer.from(keys.issuerKeyId,'hex')]);
          const nonce = randomBytes(24);
          const ciphertext = sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(Buffer.from(plaintext,'utf8'),aad(header),null,nonce,keys.keys.get(keys.issuerKeyId)!);
          nextCursor = Buffer.concat([header,nonce,ciphertext]).toString('base64url');
          if (nextCursor.length > 2048) throw new StorageUnavailable();
        } catch {throw new StorageUnavailable();}
      }
      return {venueCode:snapshot.venueCode,items,nextCursor};
    },
  };
}
