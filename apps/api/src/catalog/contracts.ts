/** Q02 wire boundary: backend-api-forms-addendum §§1,14. No DB/auth fixture. */
export type VenueCode = 'polymarket' | 'limitless';
export type CapabilityReason = 'PAPER_START_DISABLED' | 'CATALOG_SOURCE_DISABLED' | 'TRADER_START_DISABLED';
export type Availability = {available: true; capabilityReasonCode: null} |
  {available: false; capabilityReasonCode: CapabilityReason};
export interface Trader {
  traderId: string;
  venueId: string;
  catalogSourceId: string;
  venueCode: VenueCode;
  externalTraderId: string;
  displayName: string;
  traderRevisionId: string;
  traderRevision: string;
  dataOrigin: 'synthetic';
  sourceRef: string;
  observedAt: string;
  revisionCreatedAt: string;
  catalogVersionAtCreation: string;
  catalogVersion: string;
  traderControlVersion: string;
  paperControlVersion: string;
  startAvailability: Availability;
}
export interface ListRequest { venueCode: VenueCode; limit: number; cursor?: string }
export interface CardRequest { venueCode: VenueCode; traderId: string }
export interface CatalogPage { venueCode: VenueCode; items: Trader[]; nextCursor: string | null }

export class CatalogError extends Error {
  readonly status: 400 | 503;
  readonly reasonCode: 'INVALID_REQUEST' | 'RECORD_UNAVAILABLE';
  constructor(reasonCode: 'INVALID_REQUEST' | 'RECORD_UNAVAILABLE') {
    super(reasonCode);
    this.reasonCode = reasonCode;
    this.status = reasonCode === 'INVALID_REQUEST' ? 400 : 503;
  }
}
const invalid = (): never => { throw new CatalogError('INVALID_REQUEST'); };
const corrupt = (): never => { throw new CatalogError('RECORD_UNAVAILABLE'); };
const uuid = (v: unknown): v is string => typeof v === 'string' &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
const venue = (v: unknown): v is VenueCode => v === 'polymarket' || v === 'limitless';
const cursor = (v: unknown): v is string => typeof v === 'string' && /^[A-Za-z0-9_-]{1,2048}$/.test(v);
const positiveVersion = (v: unknown): v is string => typeof v === 'string' &&
  /^[1-9][0-9]{0,18}$/.test(v) && BigInt(v) <= 9223372036854775807n;
const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0 && !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(v);
const timestamp = (v: unknown): v is string => {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(v)) return false;
  const ms = Date.parse(v);
  return Number.isFinite(ms) && new Date(ms).toISOString() === v;
};
function object(value: unknown, keys: readonly string[]): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return corrupt();
  const entries = Object.keys(value);
  if (entries.length !== keys.length || entries.some(key => !keys.includes(key))) return corrupt();
  return value as Record<string, unknown>;
}
/** Decode percent escapes strictly; URLSearchParams alone replaces malformed UTF-8. */
function query(raw: string, allowed: readonly string[], bodyBytes: number): Map<string, string> {
  if (bodyBytes !== 0 || typeof raw !== 'string') return invalid();
  const values = new Map<string, string>();
  const source = raw.startsWith('?') ? raw.slice(1) : raw;
  if (!source) return invalid();
  for (const pair of source.split('&')) {
    const separator = pair.indexOf('=');
    if (separator < 0) return invalid();
    let key: string, value: string;
    try {
      key = decodeURIComponent(pair.slice(0, separator).replaceAll('+', ' '));
      value = decodeURIComponent(pair.slice(separator + 1).replaceAll('+', ' '));
    } catch { return invalid(); }
    if (!allowed.includes(key) || values.has(key)) return invalid();
    values.set(key, value);
  }
  if (values.get('requestSchemaVersion') !== 'v1') return invalid();
  return values;
}
export function parseListRequest(rawQuery: string, bodyBytes = 0): ListRequest {
  const q = query(rawQuery, ['requestSchemaVersion', 'venueCode', 'limit', 'cursor'], bodyBytes);
  const code = q.get('venueCode');
  if (!venue(code)) return invalid();
  const rawLimit = q.get('limit');
  if (rawLimit !== undefined && !/^(?:[1-9]|[1-4][0-9]|50)$/.test(rawLimit)) return invalid();
  const token = q.get('cursor');
  if (token !== undefined && !cursor(token)) return invalid();
  return {venueCode: code, limit: rawLimit === undefined ? 20 : Number(rawLimit), ...(token === undefined ? {} : {cursor: token})};
}
export function parseCardRequest(venueCode: string, traderId: string, rawQuery: string, bodyBytes = 0): CardRequest {
  query(rawQuery, ['requestSchemaVersion'], bodyBytes);
  if (!venue(venueCode) || !uuid(traderId)) return invalid();
  return {venueCode, traderId};
}
export function availability(paperEnabled: boolean, sourceEnabled: boolean, traderEnabled: boolean): Availability {
  if ([paperEnabled, sourceEnabled, traderEnabled].some(v => typeof v !== 'boolean')) return corrupt();
  if (!paperEnabled) return {available: false, capabilityReasonCode: 'PAPER_START_DISABLED'};
  if (!sourceEnabled) return {available: false, capabilityReasonCode: 'CATALOG_SOURCE_DISABLED'};
  if (!traderEnabled) return {available: false, capabilityReasonCode: 'TRADER_START_DISABLED'};
  return {available: true, capabilityReasonCode: null};
}
export function decodeTrader(value: unknown, expectedVenue: VenueCode): Trader {
  const keys = ['traderId','venueId','catalogSourceId','venueCode','externalTraderId','displayName',
    'traderRevisionId','traderRevision','dataOrigin','sourceRef','observedAt','revisionCreatedAt',
    'catalogVersionAtCreation','catalogVersion','traderControlVersion','paperControlVersion','startAvailability'];
  const v = object(value, keys);
  if (!['traderId','venueId','catalogSourceId','traderRevisionId'].every(k => uuid(v[k])) ||
      v.venueCode !== expectedVenue || !venue(v.venueCode) || v.dataOrigin !== 'synthetic' ||
      !['externalTraderId','displayName','sourceRef'].every(k => text(v[k])) ||
      !['traderRevision','catalogVersionAtCreation','catalogVersion','traderControlVersion','paperControlVersion'].every(k => positiveVersion(v[k])) ||
      !timestamp(v.observedAt) || !timestamp(v.revisionCreatedAt)) return corrupt();
  const a = object(v.startAvailability, ['available','capabilityReasonCode']);
  if (!(a.available === true && a.capabilityReasonCode === null) &&
      !(a.available === false && ['PAPER_START_DISABLED','CATALOG_SOURCE_DISABLED','TRADER_START_DISABLED'].includes(a.capabilityReasonCode as string))) return corrupt();
  // A sourceRef is data, never an automatically permitted browser navigation URL.
  return structuredClone(v) as unknown as Trader;
}
/** Repository projection only, before safe navigation/diagnostics are added. */
export function decodePage(value: unknown, request: ListRequest): CatalogPage {
  const v = object(value, ['venueCode','items','nextCursor']);
  if (!venue(v.venueCode) || v.venueCode !== request.venueCode || !Array.isArray(v.items) ||
      !Number.isInteger(request.limit) || request.limit < 1 || request.limit > 50 ||
      v.items.length > request.limit || !(v.nextCursor === null || cursor(v.nextCursor))) return corrupt();
  const items = v.items.map(item => decodeTrader(item, request.venueCode));
  if ((v.nextCursor !== null && items.length !== request.limit) ||
      (items.length === 0 && (v.nextCursor !== null || request.cursor !== undefined))) return corrupt();
  const revisions = new Set<string>();
  const sourceVersions = new Map<string, string>();
  for (const item of items) {
    if (revisions.has(item.traderRevisionId)) return corrupt();
    revisions.add(item.traderRevisionId);
    const sourceVersion = sourceVersions.get(item.catalogSourceId);
    if (sourceVersion !== undefined && sourceVersion !== item.catalogVersion) return corrupt();
    sourceVersions.set(item.catalogSourceId, item.catalogVersion);
  }
  for (let i = 1; i < items.length; i++) {
    if (items[i - 1].traderId >= items[i].traderId || items[i - 1].venueId !== items[i].venueId ||
        items[i - 1].paperControlVersion !== items[i].paperControlVersion) return corrupt();
  }
  return {venueCode: request.venueCode, items, nextCursor: v.nextCursor as string | null};
}
