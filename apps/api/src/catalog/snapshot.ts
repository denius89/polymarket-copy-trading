import { createHash } from 'node:crypto';
import { exactObject, positiveVersion, uuid, validUnicode } from '../http/input.ts';
import { StorageRecordUnavailable } from '../storage/transaction.ts';
import { availability, decodeTrader } from './contracts.ts';
import type { Trader, VenueCode } from './contracts.ts';

/** RFC8785 subset: strings/scalars, safe integers and closed objects used by Q02; no monetary numbers. */
export function canonical(value: unknown): string {
  if (value === null || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'string' && validUnicode(value)) return JSON.stringify(value);
  if (typeof value === 'number' && Number.isSafeInteger(value) && !Object.is(value, -0)) return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') {
    const v = value as Record<string, unknown>;
    return '{' + Object.keys(v).sort().map(k => canonical(k) + ':' + canonical(v[k])).join(',') + '}';
  }
  throw new StorageRecordUnavailable();
}
const hash = (value: unknown) => createHash('sha256').update(canonical(value), 'utf8').digest('hex');
const bad = (): never => {throw new StorageRecordUnavailable();};
function bool(v: unknown): asserts v is boolean {if (typeof v !== 'boolean') bad();}
export interface CatalogSnapshot {
  environmentBinding: string;
  readerBinding: string;
  catalogFingerprint: string;
  venueId: string;
  venueCode: VenueCode;
  items: Trader[];
}

export function decodeSnapshot(value: unknown, venueCode: VenueCode): CatalogSnapshot {
  try {
    const root = exactObject(value, ['http','read_binding','descriptor','items']);
    if (root.http !== 200 || !Array.isArray(root.items)) return bad();
    const binding = exactObject(root.read_binding, ['environment','realm','read_context_id','scope_id','scope_revision']);
    if (typeof binding.environment !== 'string' || !binding.environment || !validUnicode(binding.environment) ||
        binding.realm !== 'user' || !uuid(binding.read_context_id) || !uuid(binding.scope_id) ||
        typeof binding.scope_revision !== 'string' || !binding.scope_revision.startsWith(`q02-read-scope-v1:${binding.scope_id}:`) ||
        !positiveVersion(binding.scope_revision.slice(`q02-read-scope-v1:${binding.scope_id}:`.length))) return bad();
    const d = exactObject(root.descriptor, ['venueId','venueCode','paperControl','sources']);
    if (!uuid(d.venueId) || d.venueCode !== venueCode || !Array.isArray(d.sources) || d.sources.length > 100) return bad();
    const paper = exactObject(d.paperControl, ['id','version','startEnabled']);
    if (!uuid(paper.id) || !positiveVersion(paper.version)) return bad();
    bool(paper.startEnabled);
    const sourceIds = new Set(), traderIds = new Set(), revisionIds = new Set();
    const visible = new Map<string, {source: Record<string, unknown>; trader: Record<string, unknown>}>();
    const sources = d.sources.map((raw): Record<string, unknown> => {
      const s = exactObject(raw, ['sourceId','venueId','version','readVisible','startEnabled','traders']);
      if (!uuid(s.sourceId) || s.venueId !== d.venueId || !positiveVersion(s.version) ||
          sourceIds.has(s.sourceId) || !Array.isArray(s.traders)) return bad();
      sourceIds.add(s.sourceId); bool(s.readVisible); bool(s.startEnabled);
      const traders = s.traders.map(rawTrader => {
        const t = exactObject(rawTrader, ['traderId','version','currentRevisionId','currentRevision','readVisible','startAllowed']);
        if (!uuid(t.traderId) || !uuid(t.currentRevisionId) || !positiveVersion(t.version) || !positiveVersion(t.currentRevision) ||
            traderIds.has(t.traderId) || revisionIds.has(t.currentRevisionId)) return bad();
        traderIds.add(t.traderId); revisionIds.add(t.currentRevisionId); bool(t.readVisible); bool(t.startAllowed);
        if (s.readVisible && t.readVisible) visible.set(t.traderId, {source: s, trader: t});
        return t;
      }).sort((a,b) => (a.traderId as string) < (b.traderId as string) ? -1 : 1);
      return {...s, traders};
    }).sort((a,b) => (a.sourceId as string) < (b.sourceId as string) ? -1 : 1);
    if (traderIds.size > 1000 || root.items.length !== visible.size) return bad();
    const seen = new Set();
    const items = root.items.map(raw => {
      const item = decodeTrader(raw, venueCode);
      const pair = visible.get(item.traderId);
      if (!pair || seen.has(item.traderId)) return bad();
      seen.add(item.traderId);
      const {source: s, trader: t} = pair;
      if (item.venueId !== d.venueId || item.catalogSourceId !== s.sourceId || item.catalogVersion !== s.version ||
          item.traderControlVersion !== t.version || item.traderRevisionId !== t.currentRevisionId ||
          item.traderRevision !== t.currentRevision || item.paperControlVersion !== paper.version ||
          canonical(item.startAvailability) !== canonical(availability(paper.startEnabled as boolean, s.startEnabled as boolean, t.startAllowed as boolean))) return bad();
      return item;
    }).sort((a,b) => a.traderId < b.traderId ? -1 : 1);
    const environmentBinding = hash(['shadow.q02.environment.v1',binding.environment]);
    const readerBinding = hash(['shadow.q02.reader.v1',environmentBinding,binding.realm,binding.read_context_id]);
    const catalogFingerprint = hash({purpose:'shadow.q02.catalog-state.v1',environmentBinding,readerBinding,
      venueId:d.venueId,venueCode,scopeRevision:binding.scope_revision,paperControl:paper,sources});
    return {environmentBinding,readerBinding,catalogFingerprint,venueId:d.venueId,venueCode,items};
  } catch {return bad();}
}
