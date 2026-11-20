import { activeStaffDeployment } from './staff-deployment';

const contexts = '/api/admin/auth/contexts';
const bootstrap = '/api/admin/auth/bootstrap/contexts';
const logoutContexts = '/api/admin/auth/logout-contexts';
const version = 'requestSchemaVersion=v1';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

type ObjectValue = Record<string, unknown>;
export type Pending = {
  kind: 'login' | 'registration' | 'logout';
  contextId: string;
  operationId: string;
  loginId?: string;
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

// R25/R31 allow a 10-second server operation and 2 seconds for response delivery.
const verificationTimeoutMs = 12000;

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

function encode(bytes: ArrayBuffer) {
  return btoa(Array.from(new Uint8Array(bytes), byte => String.fromCharCode(byte)).join(''))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function decode(value: unknown, min: number, max: number) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value) || value.length > Math.ceil(max * 4 / 3)) {
    throw new StaffError('unavailable');
  }
  let bytes: Uint8Array<ArrayBuffer>;
  try {
    bytes = Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/')), byte => byte.charCodeAt(0));
  } catch {
    throw new StaffError('unavailable');
  }
  if (bytes.length < min || bytes.length > max || encode(bytes.buffer) !== value) throw new StaffError('unavailable');
  return bytes;
}

function descriptors(value: unknown): PublicKeyCredentialDescriptor[] {
  if (!Array.isArray(value)) throw new StaffError('unavailable');
  return value.map(entry => {
    const descriptor = object(entry);
    if (descriptor.type !== 'public-key') throw new StaffError('unavailable');
    return { type: 'public-key', id: decode(descriptor.id, 1, 1023) };
  });
}

function timeout(value: unknown) {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 1 || value > 300000) throw new StaffError('unavailable');
  return value;
}

async function options(path: string, contextId: string, action: 'login_options' | 'registration_options') {
  const operationId = crypto.randomUUID();
  const response = await read(await request(path + '/options', { operationId }), 200);
  const ref = object(response.operationRef);
  const result = object(response.result);
  if (response.status !== 'resolved' || ref.namespace !== 'context' || ref.scopeId !== contextId
    || ref.operationId !== operationId || ref.action !== action
    || result.kind !== (action === 'login_options' ? 'staff_authentication_options' : 'staff_registration_options')
    || typeof result.challengeExpiresAt !== 'string' || !(Date.parse(result.challengeExpiresAt) > Date.now())) {
    throw new StaffError('unavailable');
  }
  return { challengeId: id(result.challengeId), key: object(result.publicKey) };
}

async function authenticator(action: () => Promise<Credential | null>) {
  try {
    const credential = await action();
    if (!(credential instanceof PublicKeyCredential)) throw new StaffError('cancelled');
    return credential;
  } catch (error) {
    if (error instanceof DOMException && ['NotAllowedError', 'AbortError'].includes(error.name)) throw new StaffError('cancelled');
    if (error instanceof StaffError) throw error;
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

function completedLogin(value: unknown, pending: Pending) {
  const completion = object(value);
  if (completion.contextId !== pending.contextId || completion.operationId !== pending.operationId || completion.realm !== 'staff') {
    throw new StaffError('unavailable');
  }
  return id(completion.loginId);
}

export async function signIn(onVerify: (pending: Pending) => void) {
  const start = await read(await request(contexts, {}), 201);
  const contextId = id(object(start.staffContext).contextId);
  const path = contexts + '/' + contextId;
  const confirmed = await read(await request(path + '?' + version), 200);
  if (object(confirmed.staffContext).contextId !== contextId) throw new StaffError('unavailable');
  const { challengeId, key } = await options(path, contextId, 'login_options');
  if (typeof key.rpId !== 'string' || key.rpId !== activeStaffDeployment()?.rpId || key.userVerification !== 'required' || !Array.isArray(key.allowCredentials) || key.allowCredentials.length) {
    throw new StaffError('unavailable');
  }
  const publicKey: PublicKeyCredentialRequestOptions = {
    challenge: decode(key.challenge, 32, 32), rpId: key.rpId, timeout: timeout(key.timeout),
    userVerification: 'required', allowCredentials: [],
  };
  const credential = await authenticator(() => navigator.credentials.get({ publicKey }));
  const assertion = credential.response;
  if (!(assertion instanceof AuthenticatorAssertionResponse)) throw new StaffError('unavailable');
  const pending: Pending = { kind: 'login', contextId, operationId: crypto.randomUUID() };
  onVerify(pending);
  const rawId = encode(credential.rawId);
  const result = await read(await request(path + '/verify', {
    operationId: pending.operationId,
    challengeId,
    assertion: {
      id: rawId, rawId, type: 'public-key', clientExtensionResults: {},
      response: {
        clientDataJSON: encode(assertion.clientDataJSON),
        authenticatorData: encode(assertion.authenticatorData),
        signature: encode(assertion.signature),
        userHandle: assertion.userHandle === null ? null : encode(assertion.userHandle),
      },
    },
  }, undefined, verificationTimeoutMs), 200);
  return confirmStaff(completedLogin(result.completion, pending));
}

export async function prepareRegistration(bootstrapHandle: string, operationId: string) {
  try {
    decode(bootstrapHandle, 32, 32);
  } catch {
    throw new StaffError('rejected');
  }
  try {
    const start = await request(bootstrap, { bootstrapHandle, operationId: id(operationId) });
    const context = object((await read(start, start.status === 200 ? 200 : 201)).registrationContext);
    if (context.purpose !== 'bootstrap') throw new StaffError('unavailable');
    return id(context.contextId);
  } catch (error) {
    if (error instanceof StaffError && error.kind === 'rejected') throw error;
    throw new StaffError('bootstrap-unknown');
  }
}

export async function register(contextId: string, onVerify: (pending: Pending) => void) {
  const path = bootstrap + '/' + contextId;
  const { challengeId, key } = await options(path, contextId, 'registration_options');
  const rp = object(key.rp);
  const user = object(key.user);
  const selection = object(key.authenticatorSelection);
  if (typeof rp.id !== 'string' || rp.id !== activeStaffDeployment()?.rpId || rp.name !== 'Shadow' || typeof user.name !== 'string' || typeof user.displayName !== 'string'
    || user.name !== user.id || key.attestation !== 'none' || selection.residentKey !== 'required'
    || selection.userVerification !== 'required' || key.timeout !== 300000
    || !Array.isArray(key.pubKeyCredParams) || key.pubKeyCredParams.length !== 2
    || key.pubKeyCredParams.some((value, index) => {
      const param = object(value);
      return param.type !== 'public-key' || param.alg !== (index === 0 ? -7 : -257);
    })) throw new StaffError('unavailable');
  const publicKey: PublicKeyCredentialCreationOptions = {
    rp: { id: rp.id, name: rp.name },
    user: { id: decode(user.id, 1, 64), name: user.name, displayName: user.displayName },
    challenge: decode(key.challenge, 32, 32),
    pubKeyCredParams: [{ type: 'public-key', alg: -7 }, { type: 'public-key', alg: -257 }],
    timeout: timeout(key.timeout), attestation: 'none',
    authenticatorSelection: { residentKey: 'required', userVerification: 'required' },
    excludeCredentials: descriptors(key.excludeCredentials),
  };
  const credential = await authenticator(() => navigator.credentials.create({ publicKey }));
  const attestation = credential.response;
  if (!(attestation instanceof AuthenticatorAttestationResponse)) throw new StaffError('unavailable');
  const pending: Pending = { kind: 'registration', contextId, operationId: crypto.randomUUID() };
  onVerify(pending);
  const rawId = encode(credential.rawId);
  const response = await read(await request(path + '/verify', {
    operationId: pending.operationId,
    challengeId,
    credential: {
      id: rawId, rawId, type: 'public-key', clientExtensionResults: {},
      response: { clientDataJSON: encode(attestation.clientDataJSON), attestationObject: encode(attestation.attestationObject) },
    },
  }, undefined, verificationTimeoutMs), 200);
  const result = operationResult(response, pending, 'registration_verify');
  if (result.kind !== 'staff_credential_registered') throw new StaffError('rejected');
  id(result.credentialRef);
}

function operationResult(value: ObjectValue, pending: Pending, action: string) {
  const ref = object(value.operationRef);
  if (value.status !== 'resolved' || ref.namespace !== 'context' || ref.scopeId !== pending.contextId
    || ref.operationId !== pending.operationId || ref.action !== action) throw new StaffError('unavailable');
  return object(value.result);
}

export async function signOut(loginId: string, onExecute: (pending: Pending) => void) {
  const response = await read(await request(logoutContexts, {}, loginId), 201);
  const context = object(response.logoutContext);
  if (context.realm !== 'staff' || context.loginId !== loginId) throw new StaffError('unavailable');
  const pending: Pending = { kind: 'logout', contextId: id(context.logoutContextId), operationId: crypto.randomUUID(), loginId };
  onExecute(pending);
  const result = await request('/api/admin/auth/logout', {
    commandType: 'C07', logoutContextId: pending.contextId, authOperationId: pending.operationId,
  });
  if (result.status !== 204) throw new StaffError('unavailable');
}

export async function checkOutcome(pending: Pending): Promise<ConfirmedStaff | 'registered' | 'signed-out' | 'pending'> {
  const root = pending.kind === 'login' ? contexts : pending.kind === 'registration' ? bootstrap : logoutContexts;
  const action = pending.kind === 'login' ? 'staff_login' : 'registration_verify';
  const path = root + '/' + pending.contextId + '/operations/' + pending.operationId;
  const response = await request(path + '?' + version + (pending.kind === 'logout' ? '' : '&action=' + action));
  if (response.status === 202) return 'pending';
  if (response.status !== 200) throw new StaffError('unavailable');
  const value = await read(response, 200);
  if (pending.kind === 'logout') {
    const ref = object(value.operationRef);
    if (value.status !== 'completed' || typeof value.confirmedAt !== 'string' || ref.commandType !== 'C07'
      || ref.logoutContextId !== pending.contextId || ref.authOperationId !== pending.operationId || ref.loginId !== pending.loginId) {
      throw new StaffError('unavailable');
    }
    return 'signed-out';
  }
  const result = operationResult(value, pending, action);
  if (result.kind === 'verification_rejected' && result.reasonCode === 'AUTH_VERIFICATION_FAILED') throw new StaffError('rejected');
  if (pending.kind === 'registration' && result.kind === 'staff_credential_registered') {
    id(result.credentialRef);
    return 'registered';
  }
  if (pending.kind === 'login' && result.kind === 'staff_login_completed') {
    const loginId = completedLogin(result.completion, pending);
    try {
      return await confirmStaff(loginId);
    } catch (error) {
      if (error instanceof StaffError && ['rejected', 'unconfirmed'].includes(error.kind)) throw new StaffError('unconfirmed');
      throw error;
    }
  }
  throw new StaffError('unavailable');
}

export { request as staffRequest };
