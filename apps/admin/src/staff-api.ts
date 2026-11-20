import { activeStaffDeployment } from './staff-deployment';

const logoutContexts = '/api/admin/auth/logout-contexts';
const version = 'requestSchemaVersion=v1';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

type ObjectValue = Record<string, unknown>;
export type Pending = {
  contextId: string;
  operationId: string;
  loginId: string;
};
export type ConfirmedStaff = { loginId: string; staffId: string };

export class StaffError extends Error {
  constructor(readonly kind: 'unavailable' | 'rejected' | 'cancelled' | 'unconfirmed' | 'bootstrap-unknown') {
    super(kind);
  }
}

function object(value: unknown): ObjectValue {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new StaffError('unavailable');
  return value as ObjectValue;
}

function id(value: unknown): string {
  if (typeof value !== 'string' || !uuid.test(value)) throw new StaffError('unavailable');
  return value;
}

async function request(path: string, body?: ObjectValue, loginId?: string, timeoutMs = 5000, signal?: AbortSignal) {
  if (!activeStaffDeployment()) throw new StaffError('unavailable');
  const headers = new Headers({ Accept: 'application/json' });
  if (body) {
    headers.set('Content-Type', 'application/json');
    headers.set('X-Shadow-Auth-Request', '1');
  }
  if (loginId) headers.set('X-Shadow-Login-Id', loginId);
  try {
    return await fetch(path, {
      method: body ? 'POST' : 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      redirect: 'error',
      headers,
      body: body ? JSON.stringify({ requestSchemaVersion: 'v1', ...body }) : undefined,
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(timeoutMs)]) : AbortSignal.timeout(timeoutMs),
    });
  } catch {
    throw new StaffError('unavailable');
  }
}

async function read(response: Response, expected: number) {
  if (response.status !== expected) throw new StaffError(response.status >= 500 ? 'unavailable' : 'rejected');
  try {
    return object(await response.json());
  } catch {
    throw new StaffError('unavailable');
  }
}

export async function confirmStaff(loginId: string, distinguishUnauthorized = false): Promise<ConfirmedStaff> {
  const response = await request('/api/admin/me?' + version, undefined, loginId);
  if (response.status === 401) throw new StaffError('unconfirmed');
  const value = await read(response, 200);
  if (response.headers.get('X-Shadow-Login-Id') !== loginId || value.authenticated !== true) throw new StaffError(distinguishUnauthorized ? 'unavailable' : 'unconfirmed');
  return { loginId, staffId: id(object(value.staff).staffId) };
}

export async function signOut(loginId: string, onExecute: (pending: Pending) => void) {
  const response = await read(await request(logoutContexts, {}, loginId), 201);
  const context = object(response.logoutContext);
  if (context.realm !== 'staff' || context.loginId !== loginId) throw new StaffError('unavailable');
  const pending: Pending = { contextId: id(context.logoutContextId), operationId: crypto.randomUUID(), loginId };
  onExecute(pending);
  const result = await request('/api/admin/auth/logout', {
    commandType: 'C07', logoutContextId: pending.contextId, authOperationId: pending.operationId,
  });
  if (result.status !== 204) throw new StaffError('unavailable');
}


export async function checkOutcome(pending: Pending): Promise<'signed-out' | 'pending'> {
  const path = logoutContexts + '/' + pending.contextId + '/operations/' + pending.operationId;
  const response = await request(path + '?' + version);
  if (response.status === 202) return 'pending';
  if (response.status !== 200) throw new StaffError('unavailable');
  const value = await read(response, 200);
  const ref = object(value.operationRef);
  if (value.status !== 'completed' || typeof value.confirmedAt !== 'string' || ref.commandType !== 'C07'
    || ref.logoutContextId !== pending.contextId || ref.authOperationId !== pending.operationId || ref.loginId !== pending.loginId) {
    throw new StaffError('unavailable');
  }
  return 'signed-out';
}

export { request as staffRequest };
