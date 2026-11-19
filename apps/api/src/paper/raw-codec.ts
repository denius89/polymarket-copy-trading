import { Buffer } from 'node:buffer';
import { validUnicode, InputError } from '../http/input.ts';
import { StorageRecordUnavailable } from '../storage/transaction.ts';
import { RAW_FIELDS } from './requests.ts';

export const RAW_ENCODING = 'utf8-base64-v1';
/** Copy all fields; encode only raw, without coercion, NFC, trimming or floating point. */
export function encodeRaw(input: Record<string, unknown>): Record<string, unknown> {
  const output = {...input};
  for (const field of RAW_FIELDS) {
    const raw = input[field];
    if (raw === null) continue;
    if (typeof raw !== 'string' || !validUnicode(raw) || [...raw].length > 64) throw new InputError();
    output[field] = Buffer.from(raw, 'utf8').toString('base64');
  }
  return output;
}
export function decodeRaw(input: Record<string, unknown>, encoding: unknown): Record<string, unknown> {
  if (encoding !== RAW_ENCODING) throw new StorageRecordUnavailable();
  const output = {...input};
  for (const field of RAW_FIELDS) {
    const raw = input[field];
    if (raw === null) continue;
    if (typeof raw !== 'string' || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(raw)) {
      throw new StorageRecordUnavailable();
    }
    const bytes = Buffer.from(raw, 'base64');
    if (bytes.toString('base64') !== raw) throw new StorageRecordUnavailable();
    try {
      const decoded = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes);
      if (!validUnicode(decoded) || [...decoded].length > 64) throw new StorageRecordUnavailable();
      output[field] = decoded;
    } catch {throw new StorageRecordUnavailable();}
  }
  return output;
}
