export class InputError extends Error {
  readonly status: number;
  readonly reasonCode: string;
  constructor(status = 400, reasonCode = 'INVALID_REQUEST') {
    super(reasonCode); this.name = 'InputError'; this.status = status; this.reasonCode = reasonCode;
  }
}
export const validUnicode = (s: string): boolean =>
  !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(s);
export const uuid = (v: unknown): v is string => typeof v === 'string' &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
export const positiveVersion = (v: unknown): v is string => typeof v === 'string' &&
  /^[1-9][0-9]{0,18}$/.test(v) && BigInt(v) <= 9223372036854775807n;
export function exactObject(value: unknown, keys: readonly string[]): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).length !== keys.length || Object.keys(value).some(k => !keys.includes(k))) throw new InputError();
  return value as Record<string, unknown>;
}

/** Strict JSON retains key multiplicity until checked. No reviver can detect duplicates after JSON.parse. */
export function parseCommandJson(bytes: Uint8Array): unknown {
  if (bytes.byteLength > 65536) throw new InputError(413, 'REQUEST_TOO_LARGE');
  let source: string;
  try { source = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes); }
  catch { throw new InputError(); }
  let i = 0;
  const ws = () => { while (/[ \t\r\n]/.test(source[i] ?? '\0')) i++; };
  const bad = (): never => { throw new InputError(); };
  function string(): string {
    if (source[i] !== '"') return bad();
    const start = i++;
    while (i < source.length) {
      if (source[i] === '\\') { i += 2; continue; }
      if (source[i++] === '"') {
        try {
          const value: unknown = JSON.parse(source.slice(start, i));
          if (typeof value !== 'string' || !validUnicode(value)) return bad();
          return value;
        } catch { return bad(); }
      }
    }
    return bad();
  }
  function value(depth: number): unknown {
    ws();
    const ch = source[i];
    if (ch === '"') return string();
    if (ch === '{' || ch === '[') {
      if (depth > 8) return bad();
      i++; ws();
      if (ch === '{') {
        const result: Record<string, unknown> = Object.create(null);
        if (source[i] === '}') {i++; return result;}
        while (true) {
          ws(); const key = string(); ws();
          if (Object.hasOwn(result, key) || source[i++] !== ':') return bad();
          result[key] = value(depth + 1); ws();
          const separator = source[i++];
          if (separator === '}') return result;
          if (separator !== ',') return bad();
        }
      }
      const result: unknown[] = [];
      if (source[i] === ']') {i++; return result;}
      while (true) {
        result.push(value(depth + 1)); ws();
        const separator = source[i++];
        if (separator === ']') return result;
        if (separator !== ',') return bad();
      }
    }
    for (const [token, literal] of [['null', null], ['true', true], ['false', false]] as const) {
      if (source.startsWith(token, i)) {i += token.length; return literal;}
    }
    const number = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(source.slice(i));
    if (!number) return bad();
    i += number[0].length;
    const n = Number(number[0]);
    return Number.isFinite(n) ? n : bad();
  }
  const result = value(1); ws();
  if (i !== source.length) return bad();
  return result;
}

export function parseQuery(raw: string, keys: readonly string[]): Record<string, string> {
  const result: Record<string, string> = Object.create(null);
  for (const part of (raw.startsWith('?') ? raw.slice(1) : raw).split('&')) {
    const at = part.indexOf('=');
    if (at < 0) throw new InputError();
    let key: string, val: string;
    try {
      key = decodeURIComponent(part.slice(0, at).replaceAll('+', ' '));
      val = decodeURIComponent(part.slice(at + 1).replaceAll('+', ' '));
    } catch {throw new InputError();}
    if (!keys.includes(key) || Object.hasOwn(result, key)) throw new InputError();
    result[key] = val;
  }
  if (Object.keys(result).length !== keys.length || result.requestSchemaVersion !== 'v1') throw new InputError();
  return result;
}
