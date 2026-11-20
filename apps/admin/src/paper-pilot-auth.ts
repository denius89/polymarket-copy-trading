import { confirmStaff, staffRequest, StaffError } from './staff-api';

const root = '/api/admin/pilot/auth/contexts';
const query = '?requestSchemaVersion=v1';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const secretFormat = /^[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$/;

export type PilotLogin = { contextId: string; operationId: string };
export type PilotRecovery = { operation: PilotLogin; loginId: string };

function invalid(): never { throw new StaffError('unavailable'); }

function object(value: unknown, keys: readonly string[]) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return invalid();
  const row = value as Record<string, unknown>;
  if (Object.keys(row).length !== keys.length || keys.some(key => !Object.hasOwn(row, key))) return invalid();
  return row;
}

function id(value: unknown) {
  return typeof value === 'string' && uuid.test(value) ? value : invalid();
}

function time(value: unknown) {
  if (typeof value !== 'string' || !Number.isFinite(Date.parse(value)) || new Date(value).toISOString() !== value) return invalid();
  return value;
}

function envelope(value: unknown, keys: readonly string[]) {
  const row = object(value, [...keys, 'observedAt', 'nextAction', 'nextActionParams']);
  if (row.nextAction !== null) return invalid();
  object(row.nextActionParams, []);
  time(row.observedAt);
  return row;
}

function operationPath(operation: PilotLogin) {
  return root + '/' + operation.contextId + '/operations/' + operation.operationId;
}

async function confirmOriginal(operation: PilotLogin, loginId: string) {
  try {
    return { kind: 'confirmed' as const, staff: await confirmStaff(loginId, true) };
  } catch (error) {
    if (error instanceof StaffError && error.kind === 'unconfirmed') {
      return { kind: 'recover' as const, recovery: { operation, loginId } };
    }
    throw error;
  }
}

export async function pilotSignIn(permitId: string, secret: string, started: (operation: PilotLogin) => void) {
  if (!uuid.test(permitId) || !secretFormat.test(secret)) throw new StaffError('rejected');
  const prepared = await staffRequest(root, {});
  if (prepared.status !== 201) return invalid();
  const row = envelope(await prepared.json(), ['staffContext']);
  const context = object(row.staffContext, ['contextId', 'expiresAt']);
  if (Date.parse(time(context.expiresAt)) <= Date.now()) return invalid();
  const operation = { contextId: id(context.contextId), operationId: crypto.randomUUID() };
  started(operation);
  const response = await staffRequest(root + '/' + operation.contextId + '/login', {
    operationId: operation.operationId, permitId, secret,
  });
  if (response.status === 401) {
    const refusal = object(await response.json(), ['reasonCode', 'reasonDetails', 'nextAction', 'nextActionParams']);
    if (refusal.nextAction !== null) return invalid();
    object(refusal.nextActionParams, []);
    const details = object(refusal.reasonDetails, ['code', 'params']);
    if (refusal.reasonCode !== 'AUTH_REQUIRED' || details.code !== refusal.reasonCode) return invalid();
    object(details.params, []);
    return { kind: 'rejected' as const };
  }
  if (response.status !== 200) return invalid();
  const result = envelope(await response.json(), ['completion']);
  const completion = object(result.completion, ['contextId', 'operationId', 'realm', 'loginId', 'completedAt']);
  if (completion.contextId !== operation.contextId || completion.operationId !== operation.operationId || completion.realm !== 'staff') return invalid();
  time(completion.completedAt);
  const loginId = id(completion.loginId);
  if (response.headers.get('X-Shadow-Login-Id') !== loginId) return invalid();
  return confirmOriginal(operation, loginId);
}

export async function checkPilotLogin(operation: PilotLogin) {
  const response = await staffRequest(operationPath(operation) + query);
  if (response.status !== 200 && response.status !== 202) return invalid();
  const row = envelope(await response.json(), ['operationRef', 'status', ...(response.status === 200 ? ['result'] : [])]);
  const ref = object(row.operationRef, ['contextId', 'operationId']);
  if (ref.contextId !== operation.contextId || ref.operationId !== operation.operationId) return invalid();
  if (response.status === 202 && row.status === 'unresolved') return { kind: 'pending' as const };
  if (response.status !== 200 || row.status !== 'resolved') return invalid();
  const raw = row.result as { kind?: unknown } | null;
  if (raw?.kind === 'pilot_login_rejected') {
    const result = object(raw, ['kind', 'operationId', 'reasonCode', 'completedAt']);
    if (result.operationId !== operation.operationId || result.reasonCode !== 'AUTH_REQUIRED') return invalid();
    time(result.completedAt);
    return { kind: 'rejected' as const };
  }
  const result = object(raw, ['kind', 'operationId', 'loginId', 'completedAt']);
  if (result.kind !== 'pilot_login_completed' || result.operationId !== operation.operationId) return invalid();
  time(result.completedAt);
  return confirmOriginal(operation, id(result.loginId));
}

export async function recoverPilotCookie(recovery: PilotRecovery) {
  const response = await staffRequest(operationPath(recovery.operation) + '/cookie', {});
  if (response.status === 401 || response.status === 409) throw new StaffError('unconfirmed');
  if (response.status !== 200) return invalid();
  const row = envelope(await response.json(), ['loginId']);
  if (row.loginId !== recovery.loginId || response.headers.get('X-Shadow-Login-Id') !== recovery.loginId) return invalid();
  return confirmStaff(recovery.loginId, true);
}
