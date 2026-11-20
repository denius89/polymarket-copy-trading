import {decodeBuySessionReply} from '../live-buy/reader.ts';
import {exactObject, uuid, validUnicode} from '../http/input.ts';
import {decodeSession, timestamp} from '../paper/responses.ts';

export class PilotRecordUnavailable extends Error {
  constructor() { super('Pilot record unavailable'); }
}
const bad = (): never => { throw new PilotRecordUnavailable(); };
function closed(value: unknown, keys: readonly string[]) {
  try { return exactObject(value, keys); } catch { return bad(); }
}
function label(v: unknown): v is string {
  return typeof v === 'string' && [...v].length > 0 && [...v].length <= 80 && validUnicode(v) && !/[\x00-\x1f\x7f]/.test(v);
}
export interface PilotSessionItem {displayLabel: string; sessionId: string}
export interface PilotEvent {eventId: string; sessionId: string; kind: 'paper_session.started'; occurredAt: string}

export function decodePilotList(value: unknown): {sessions: PilotSessionItem[]; observedAt: string} {
  const root = closed(value, ['sessions', 'observedAt']);
  if (!timestamp(root.observedAt) || !Array.isArray(root.sessions) || root.sessions.length > 2) return bad();
  const seen = new Set<string>();
  const sessions = root.sessions.map(value => {
    const row = closed(value, ['displayLabel', 'sessionId']);
    if (!label(row.displayLabel) || !uuid(row.sessionId) || seen.has(row.sessionId)) return bad();
    seen.add(row.sessionId);
    return {displayLabel: row.displayLabel, sessionId: row.sessionId};
  });
  return {sessions, observedAt: root.observedAt as string};
}

export function decodePilotEvents(value: unknown, sessionId: string): {sessionId: string; events: PilotEvent[]; observedAt: string} {
  const root = closed(value, ['sessionId', 'events', 'observedAt']);
  // Accepted source has exactly one complete C06 start bundle per authorized session.
  if (!uuid(sessionId) || root.sessionId !== sessionId || !timestamp(root.observedAt)
      || !Array.isArray(root.events) || root.events.length !== 1) return bad();
  const row = closed(root.events[0], ['eventId', 'sessionId', 'kind', 'occurredAt']);
  if (!uuid(row.eventId) || row.sessionId !== sessionId || row.kind !== 'paper_session.started'
      || !timestamp(row.occurredAt) || (row.occurredAt as string) > (root.observedAt as string)) return bad();
  return {sessionId, events: [row as unknown as PilotEvent], observedAt: root.observedAt as string};
}

/** This fixed pilot grants all three data groups or denies the whole read.
 * It does not implement arbitrary product grant subsets or current/absence. */
export function decodePilotSession(value: unknown, sessionId: string) {
  const root = closed(value, ['session', 'restrictedGroups']);
  if (!uuid(sessionId) || !Array.isArray(root.restrictedGroups) || root.restrictedGroups.length !== 1
      || root.restrictedGroups[0] !== 'user.minimal_context') return bad();
  try {
    const candidate=root.session as Record<string,unknown>;
    const decoded=candidate?.schemaVersion==='live-buy-session-v1'
      ?{session:decodeBuySessionReply({http:200,...candidate},sessionId)}
      :decodeSession({http:200,session:root.session},sessionId);
    if(decoded.session===null)return bad();
    return {...decoded, restrictedGroups: ['user.minimal_context']};
  } catch { return bad(); }
}
