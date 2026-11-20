import { exactObject, InputError, parseCommandJson, parseQuery, uuid } from '../http/input.ts';
import { base64url, verifyRequest } from './webauthn-input.ts';

export type StaffRoute = 'R22'|'R23'|'R24'|'R25'|'R26'|'R28'|'R29'|'R30'|'R31'|'R32'|
  'logout_prepare'|'logout_execute'|'logout_read'|'logout_continue';
export interface StaffRequest {
  route: StaffRoute;
  contextId?: string;
  operationId?: string;
  action?: string;
  payload: Record<string, unknown>;
}
const root = '/api/admin/auth/contexts';
const bootstrap = '/api/admin/auth/bootstrap/contexts';
const logout = '/api/admin/auth/logout-contexts';
const patterns: readonly [StaffRoute, string, RegExp][] = [
  ['R22','POST',new RegExp(`^${root}$`)],
  ['R23','GET',new RegExp(`^${root}/([^/]+)$`)],
  ['R24','POST',new RegExp(`^${root}/([^/]+)/options$`)],
  ['R25','POST',new RegExp(`^${root}/([^/]+)/verify$`)],
  ['R26','GET',new RegExp(`^${root}/([^/]+)/operations/([^/]+)$`)],
  ['R28','GET',/^\/api\/admin\/me$/],
  ['R29','POST',new RegExp(`^${bootstrap}$`)],
  ['R30','POST',new RegExp(`^${bootstrap}/([^/]+)/options$`)],
  ['R31','POST',new RegExp(`^${bootstrap}/([^/]+)/verify$`)],
  ['R32','GET',new RegExp(`^${bootstrap}/([^/]+)/operations/([^/]+)$`)],
  ['logout_prepare','POST',new RegExp(`^${logout}$`)],
  ['logout_execute','POST',/^\/api\/admin\/auth\/logout$/],
  ['logout_continue','POST',new RegExp(`^${logout}/continue$`)],
  ['logout_read','GET',new RegExp(`^${logout}/([^/]+)/operations/([^/]+)$`)],
];

/** Closed wire parsing, not admission. No URL normalisation or generic RPC names.
 * null means this isolated profile has no route (including R27/Q06/recovery).
 * Payload may contain a bootstrap proof; do not log this object.
 */
export function parseStaffRequest(method: string, target: string, body: Uint8Array): StaffRequest | null {
  if (!target.startsWith('/') || target.startsWith('//') || /[\\#\x00-\x20]/.test(target)) throw new InputError();
  const separator = target.indexOf('?');
  const path = separator === -1 ? target : target.slice(0,separator);
  const query = separator === -1 ? '' : target.slice(separator+1);
  let selected: StaffRoute | undefined; let captures: RegExpMatchArray | null = null;
  for (const [route,verb,pattern] of patterns) {
    if (verb === method && (captures=path.match(pattern))) {selected=route;break;}
  }
  if (!selected || !captures) return null;
  const contextId=captures[1], operationId=captures[2];
  if ((contextId !== undefined && !uuid(contextId)) || (operationId !== undefined && !uuid(operationId))) throw new InputError();
  const ids = {...(contextId ? {contextId} : {}),...(operationId ? {operationId} : {})};
  if (method === 'GET') {
    if (body.byteLength) throw new InputError();
    const isOutcome=selected==='R26'||selected==='R32';
    const values=parseQuery(query,isOutcome?['requestSchemaVersion','action']:['requestSchemaVersion']);
    if (isOutcome && !(selected==='R26'?['login_options','staff_login']:
      ['bootstrap_create','registration_options','registration_verify']).includes(values.action!)) throw new InputError();
    return {route:selected,...ids,...(isOutcome?{action:values.action}:{}),payload:values};
  }
  if (separator !== -1) throw new InputError();
  if (selected==='R25'||selected==='R31') return {route:selected,...ids,
    payload:verifyRequest(body,selected==='R25'?'staff_login':'registration_verify')};
  if (body.byteLength>8192) throw new InputError(413,'REQUEST_TOO_LARGE');
  const fields=selected==='R22'||selected==='logout_prepare'?[]:
    selected==='R29'?['bootstrapHandle','operationId']:
    selected==='logout_execute'?['commandType','logoutContextId','authOperationId']:
    selected==='logout_continue'?['sourceLogoutContextId','authorizationMode']:['operationId'];
  const payload=exactObject(parseCommandJson(body),['requestSchemaVersion',...fields]);
  if (payload.requestSchemaVersion!=='v1') throw new InputError();
  for (const field of ['operationId','logoutContextId','authOperationId','sourceLogoutContextId'])
    if (Object.hasOwn(payload,field)&&!uuid(payload[field])) throw new InputError();
  if (selected==='R29') base64url(payload.bootstrapHandle,32,32);
  if (selected==='logout_execute'&&payload.commandType!=='C07') throw new InputError();
  if (selected==='logout_continue'&&!['original_login','current_staff'].includes(payload.authorizationMode as string)) throw new InputError();
  return {route:selected,...ids,payload};
}
