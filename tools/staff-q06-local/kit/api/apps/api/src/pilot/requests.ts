import {exactObject, InputError, parseCommandJson, parseQuery, uuid} from '../http/input.ts';
import {parseStaffRequest, type StaffRequest} from '../staff/requests.ts';

type Base = {payload: Record<string, unknown>};
export type PilotRequest =
  | (Base & {route: 'pilot_context'})
  | (Base & {route: 'pilot_login'; contextId: string})
  | (Base & {route: 'pilot_outcome'|'pilot_cookie'; contextId: string; operationId: string})
  | (Base & {route: 'pilot_list'})
  | (Base & {route: 'pilot_session'|'pilot_events'; sessionId: string})
  | {route: 'staff_existing'; request: StaffRequest};

const root = '/api/admin/pilot/auth/contexts';
const routes = [
  ['pilot_context', 'POST', new RegExp(`^${root}$`)],
  ['pilot_login', 'POST', new RegExp(`^${root}/([^/]+)/login$`)],
  ['pilot_outcome', 'GET', new RegExp(`^${root}/([^/]+)/operations/([^/]+)$`)],
  ['pilot_cookie', 'POST', new RegExp(`^${root}/([^/]+)/operations/([^/]+)/cookie$`)],
  ['pilot_list', 'GET', /^\/api\/admin\/pilot\/sessions$/],
  ['pilot_session', 'GET', /^\/api\/admin\/sessions\/([^/]+)$/],
  ['pilot_events', 'GET', /^\/api\/admin\/pilot\/sessions\/([^/]+)\/events$/],
] as const;

export function canonicalSecret(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value)
    && Buffer.from(value, 'base64url').length === 32
    && Buffer.from(value, 'base64url').toString('base64url') === value;
}

/** Parsing only. Returned login payload is sensitive: never log or persist it. */
export function parsePilotRequest(method: string, target: string, body: Uint8Array): PilotRequest|null {
  if (!target.startsWith('/') || target.startsWith('//') || /[\\#\x00-\x20]/.test(target)) throw new InputError();
  const pos = target.indexOf('?');
  const path = pos < 0 ? target : target.slice(0, pos);
  const query = pos < 0 ? '' : target.slice(pos + 1);
  for (const [route, verb, pattern] of routes) {
    const match = path.match(pattern);
    if (method !== verb || !match) continue;
    for (const id of match.slice(1)) if (!uuid(id)) throw new InputError();
    let payload: Record<string, unknown>;
    if (method === 'GET') {
      if (body.byteLength) throw new InputError();
      payload = parseQuery(query, ['requestSchemaVersion']);
    } else {
      if (pos >= 0) throw new InputError();
      if (body.byteLength > 8192) throw new InputError(413, 'REQUEST_TOO_LARGE');
      payload = exactObject(parseCommandJson(body), route === 'pilot_login'
        ? ['requestSchemaVersion', 'operationId', 'permitId', 'secret'] : ['requestSchemaVersion']);
      if (payload.requestSchemaVersion !== 'v1') throw new InputError();
      if (route === 'pilot_login' && (!uuid(payload.operationId) || !uuid(payload.permitId) || !canonicalSecret(payload.secret)))
        throw new InputError();
    }
    switch (route) {
      case 'pilot_context': case 'pilot_list': return {route, payload};
      case 'pilot_login': return {route, contextId: match[1], payload};
      case 'pilot_outcome': case 'pilot_cookie': return {route, contextId: match[1], operationId: match[2], payload};
      case 'pilot_session': case 'pilot_events': return {route, sessionId: match[1], payload};
    }
  }
  // Reuse accepted R28/C07 shapes only. WebAuthn, bootstrap and absence stay closed.
  if (path === '/api/admin/me' || path === '/api/admin/auth/logout' ||
      path === '/api/admin/auth/logout-contexts' || path.startsWith('/api/admin/auth/logout-contexts/')) {
    const request = parseStaffRequest(method, target, body);
    if (request && (request.route === 'R28' || request.route.startsWith('logout_'))) return {route: 'staff_existing', request};
  }
  return null;
}
