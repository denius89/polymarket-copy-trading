import { randomInt } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import type { Pool, PoolClient, QueryConfig, QueryResult } from 'pg';

const functions = ['current_identity', 'catalog_read', 'c04_save', 'c05_validate', 'c06_prepare',
  'c06_finish', 'q03_draft', 'q04_session', 'q05_command'] as const;
export type PolygonFunction = typeof functions[number];
export type TransactionMode = 'read' | 'command';
export type RpcValue = Record<string, unknown> & {http: number};

export class StorageUnavailable extends Error {
  readonly outcome: 'unknown' | 'not_committed';
  constructor(outcome: 'unknown' | 'not_committed' = 'not_committed') {
    super('Storage unavailable'); this.name = 'StorageUnavailable'; this.outcome = outcome;
  }
}
export class StorageRecordUnavailable extends Error {
  constructor() { super('Stored record unavailable'); this.name = 'StorageRecordUnavailable'; }
}
export class RpcRefusal extends Error {
  readonly response: RpcValue;
  constructor(response: RpcValue) { super('RPC refused'); this.name = 'RpcRefusal'; this.response = response; }
}

export interface PolygonTransaction {
  call(name: PolygonFunction, input: Record<string, unknown>): Promise<RpcValue>;
}
const errors: Record<string, number> = {
  AUTH_REQUIRED: 401, AUTH_EXPIRED: 401, AUTH_REVOKED: 401, ACCESS_DENIED: 403,
  RESOURCE_NOT_FOUND: 404, INVALID_REQUEST: 400, KEY_REUSE_CONFLICT: 409,
  VERSION_CONFLICT: 409, DRAFT_USED: 409, DRAFT_EXPIRED: 409,
  SERVICE_UNAVAILABLE: 503, RECORD_UNAVAILABLE: 503,
};

function rpcValue(result: QueryResult): RpcValue {
  if (result.rows.length !== 1 || Object.keys(result.rows[0]).join(',') !== 'reply') throw new StorageRecordUnavailable();
  const value: unknown = result.rows[0].reply;
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new StorageRecordUnavailable();
  const v = value as RpcValue;
  if (!Number.isInteger(v.http) || v.http < 200 || v.http > 599) throw new StorageRecordUnavailable();
  if ('reason' in v) {
    if (Object.keys(v).sort().join(',') !== 'http,reason' || typeof v.reason !== 'string' ||
        !Object.hasOwn(errors, v.reason) || errors[v.reason] !== v.http) throw new StorageRecordUnavailable();
    // Roll back even for an early finish refusal; a prepared START may already exist in this transaction.
    throw new RpcRefusal(v);
  }
  return v; // Operation-specific closed decoding must happen inside the callback, before COMMIT.
}

/** A single 5-second monotonic budget includes pool wait, all queries, CPU and permitted backoff.
 * Success is returned only after COMMIT acknowledgement. No pool.query and no network calls inside work.
 */
export async function withPolygonTransaction<T>(
  pool: Pick<Pool, 'connect'>,
  mode: TransactionMode,
  work: (tx: PolygonTransaction) => Promise<T>,
  executionStartedAt = performance.now(),
): Promise<T> {
  const now = performance.now();
  if (!Number.isFinite(executionStartedAt) || executionStartedAt > now) throw new StorageUnavailable();
  const deadline = executionStartedAt + 5000;
  const remaining = () => {
    const ms = Math.floor(deadline - performance.now());
    if (ms <= 0) throw new StorageUnavailable();
    return ms;
  };
  const bounded = async <R>(promise: Promise<R>, ms: number): Promise<R> => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      return await Promise.race([promise, new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new StorageUnavailable()), ms);
      })]);
    } finally { if (timer !== undefined) clearTimeout(timer); }
  };
  for (let attempt = 1; attempt <= (mode === 'command' ? 3 : 1); attempt++) {
    let client: PoolClient | undefined;
    let released = false;
    let acquiring = true;
    let commitSent = false;
    let begun = false;
    let active = true;
    let acceptingCalls = true;
    const release = (destroy: boolean) => {
      if (client && !released) { released = true; client.release(destroy); }
    };
    const query = async (text: string, values?: string[]): Promise<QueryResult> => {
      const ms = remaining();
      if (!active || !client || released) throw new StorageUnavailable();
      // pg 8.16.3 supports per-query timeout; @types/pg exposes it only on ClientConfig.
      const config: QueryConfig & {query_timeout: number} = {text, values, query_timeout: ms};
      return bounded(client.query(config), ms);
    };
    try {
      const acquireBudget = remaining();
      // A timed-out pool wait can still resolve later: never leak that connection or execute on it.
      const pending = pool.connect().then(c => {
        if (!acquiring) { c.release(true); throw new StorageUnavailable(); }
        return c;
      });
      try { client = await bounded(pending, acquireBudget); }
      finally { acquiring = false; }
      await query('BEGIN ISOLATION LEVEL SERIALIZABLE');
      begun = true;
      const tx: PolygonTransaction = {
        call: async (name, input) => {
          if (!acceptingCalls || !(functions as readonly string[]).includes(name) ||
              (mode === 'read' && ['c04_save', 'c05_validate', 'c06_prepare', 'c06_finish'].includes(name))) {
            throw new StorageUnavailable();
          }
          const ms = String(remaining());
          await query("SELECT set_config('statement_timeout', $1, true), set_config('lock_timeout', $1, true)", [ms]);
          // Identifiers come exclusively from the allowlist; only JSON is a parameter.
          return rpcValue(await query(`SELECT polygon.${name}($1::jsonb) AS reply`, [JSON.stringify(input)]));
        },
      };
      const result = await bounded(work(tx), remaining());
      acceptingCalls = false;
      remaining();
      commitSent = true;
      await query('COMMIT');
      active = false;
      release(false);
      return result;
    } catch (error) {
      acceptingCalls = false;
      const code = error && typeof error === 'object' && 'code' in error ? error.code : undefined;
      const retryable = code === '40001' || code === '40P01';
      // A COMMIT transport failure is unknown. Only a definite server rollback code permits retry.
      if (commitSent && !retryable) {
        active = false;
        release(true);
        throw new StorageUnavailable('unknown');
      }
      let rollbackConfirmed = false;
      if (client && begun) {
        try { await query('ROLLBACK'); rollbackConfirmed = true; } catch { /* destroy below */ }
      }
      active = false;
      release(!rollbackConfirmed);
      if (retryable && rollbackConfirmed && mode === 'command' && attempt < 3) {
        const pause = randomInt(50, 151);
        if (deadline - performance.now() <= pause) throw new StorageUnavailable();
        await new Promise(resolve => setTimeout(resolve, pause));
        continue;
      }
      if (error instanceof RpcRefusal || error instanceof StorageRecordUnavailable) throw error;
      throw new StorageUnavailable();
    } finally {
      acquiring = false;
      acceptingCalls = false;
      active = false;
      release(true);
    }
  }
  throw new StorageUnavailable();
}
