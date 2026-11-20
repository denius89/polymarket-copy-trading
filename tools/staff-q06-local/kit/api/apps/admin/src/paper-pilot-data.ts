const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const version = /^[1-9]\d{0,18}$/;
const count = /^(0|[1-9]\d{0,18})$/;
const percent = /^(0|[1-9]\d*)\.\d{2}$/;
const timestamp = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
type RecordValue = Record<string, unknown>;

export type PilotSessionLink = { displayLabel: string; sessionId: string };
export type PilotEvent = { eventId: string; sessionId: string; kind: 'paper_session.started'; occurredAt: string };
export type Money = { n: string; d: string };

export type PilotSession = {
  summary: {
    sessionId: string;
    venueId: string;
    traderDisplayName: string;
    asOf: string;
    snapshotVersion: string;
    lifecycle: 'active';
    controlState: 'copying_not_connected';
    contentState: 'EMPTY';
    coverageState: 'no_trade_data';
  };
  settings?: {
    budget: Money;
    sizingMode: 'fixed' | 'percent';
    fixedAmount: Money | null;
    copyPercent: string | null;
    marketLimitPercent: string;
    dailyBuyLimitPercent: string;
  };
  financialSnapshot?: {
    initialFunding: Money;
    free: Money;
    reserved: Money;
    equity: Money;
    positionValue: Money;
    tradingResult: Money;
    tradeCount: string;
    positionCount: string;
    orderCount: string;
  };
};

function invalid(): never { throw new Error('Invalid pilot response'); }

function object(value: unknown): RecordValue {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return invalid();
  return value as RecordValue;
}

function text(value: unknown, pattern?: RegExp): string {
  if (typeof value !== 'string' || !value || (pattern && !pattern.test(value))) return invalid();
  return value;
}

function exact(value: unknown, keys: readonly string[]): RecordValue {
  const row = object(value);
  if (Object.keys(row).length !== keys.length || keys.some(key => !Object.hasOwn(row, key))) return invalid();
  return row;
}

function time(value: unknown) {
  const result = text(value, timestamp);
  if (!Number.isFinite(Date.parse(result)) || new Date(result).toISOString() !== result) return invalid();
  return result;
}

function money(value: unknown): Money {
  const item = exact(value, ['n', 'd']);
  return { n: text(item.n, /^(0|[1-9]\d{0,63})$/), d: text(item.d, /^[1-9]\d{0,63}$/) };
}

export function decodePilotLinks(value: unknown): PilotSessionLink[] {
  if (!Array.isArray(value) || value.length > 2) return invalid();
  const links = value.map(item => {
    const row = exact(item, ['displayLabel', 'sessionId']);
    return { displayLabel: text(row.displayLabel), sessionId: text(row.sessionId, uuid) };
  });
  if (new Set(links.map(row => row.sessionId)).size !== links.length) return invalid();
  return links;
}

export function decodePilotEvents(value: unknown, sessionId: string): PilotEvent[] {
  if (!Array.isArray(value) || value.length !== 1) return invalid();
  return value.map(item => {
    const row = exact(item, ['eventId', 'sessionId', 'kind', 'occurredAt']);
    if (row.sessionId !== sessionId || row.kind !== 'paper_session.started') return invalid();
    return { eventId: text(row.eventId, uuid), sessionId, kind: row.kind, occurredAt: time(row.occurredAt) };
  });
}

export function decodePilotSession(value: unknown, sessionId: string) {
  const envelope = object(value);
  const session = object(envelope.session);
  if (session.schemaVersion !== 'live-buy-session-v1') {
    return { kind: 'empty' as const, ...decodeEmptyPilotSession(value, sessionId) };
  }
  exact(envelope, ['session', 'restrictedGroups', 'nextAction', 'nextActionParams']);
  if (!Array.isArray(envelope.restrictedGroups) || envelope.restrictedGroups.length !== 1
    || envelope.restrictedGroups[0] !== 'user.minimal_context' || session.sessionId !== sessionId) return invalid();
  const finance = exact(session.financial, ['schemaVersion', 'sessionId', 'version', 'snapshotId', 'cash',
    'reservedCash', 'freeCash', 'cashExpenses', 'positions', 'daily']);
  if (finance.sessionId !== sessionId || finance.version !== session.snapshotVersion
    || finance.snapshotId !== session.snapshotId || !Array.isArray(finance.positions)) return invalid();
  const valuation = exact(session.valuation, ['status']);
  if (valuation.status !== 'unavailable') return invalid();
  const context = object(session.context);
  const summary = object(context.summary);
  if (summary.sessionId !== sessionId || summary.snapshotVersion !== session.snapshotVersion) return invalid();
  const amount = (raw: unknown): Money => {
    const item = exact(raw, ['n', 'd']);
    return {n:text(item.n,/^(0|[1-9]\d{0,255})$/),d:text(item.d,/^[1-9]\d{0,255}$/)};
  };
  return {
    kind: 'positions' as const,
    summary: {
      sessionId, venueId: text(summary.venueId, uuid), traderDisplayName: text(summary.traderDisplayName),
      asOf: time(session.asOf), snapshotVersion: text(session.snapshotVersion, version),
    },
    cash: amount(finance.cash), available: amount(finance.freeCash), reserved: amount(finance.reservedCash),
    positions: finance.positions.map(raw => {
      const position = exact(raw, ['conditionId', 'tokenId', 'cost', 'quantity', 'reserved']);
      return { conditionId: text(position.conditionId), tokenId: text(position.tokenId),
        cost: amount(position.cost), quantity: amount(position.quantity) };
    }).filter(position => position.quantity.n !== '0'),
  };
}

function decodeEmptyPilotSession(value: unknown, sessionId: string): PilotSession {
  const root = exact(value, ['session', 'restrictedGroups', 'nextAction', 'nextActionParams']);
  if (!Array.isArray(root.restrictedGroups)) return invalid();
  const restricted = root.restrictedGroups;
  const knownGroups = ['session.settings', 'session.financial_snapshot', 'user.minimal_context'];
  if (!restricted.includes('user.minimal_context') || restricted.some(group => !knownGroups.includes(group))
    || new Set(restricted).size !== restricted.length) return invalid();
  if (restricted.join(',') !== knownGroups.filter(group => restricted.includes(group)).join(',')) return invalid();
  const settingsAllowed = !restricted.includes('session.settings');
  const balanceAllowed = !restricted.includes('session.financial_snapshot');
  const session = exact(root.session, ['summary', ...(settingsAllowed ? ['settings'] : []), ...(balanceAllowed ? ['financialSnapshot'] : [])]);
  const summary = object(session.summary);
  if (summary.sessionId !== sessionId || summary.mode !== 'paper' || summary.dataOrigin !== 'synthetic'
    || summary.lifecycle !== 'active' || summary.controlState !== 'copying_not_connected'
    || summary.contentState !== 'EMPTY' || summary.coverageState !== 'no_trade_data') return invalid();
  const revision = text(summary.settingsRevisionId, uuid);
  const sessionVersion = text(summary.sessionVersion, version);
  const result: PilotSession = {
    summary: {
      sessionId,
      venueId: text(summary.venueId, uuid),
      traderDisplayName: text(summary.traderDisplayName),
      asOf: time(summary.asOf),
      snapshotVersion: text(summary.snapshotVersion, version),
      lifecycle: summary.lifecycle,
      controlState: summary.controlState,
      contentState: summary.contentState,
      coverageState: summary.coverageState,
    },
  };
  if (settingsAllowed) {
    const settings = object(session.settings);
    if (settings.sessionId !== sessionId || settings.settingsRevisionId !== revision || settings.recordSchemaVersion !== 'v1') return invalid();
    if (settings.sizingMode !== 'fixed' && settings.sizingMode !== 'percent') return invalid();
    const fixed = settings.sizingMode === 'fixed';
    if (fixed ? settings.copyPercent !== null : settings.fixedAmount !== null) return invalid();
    result.settings = {
      budget: money(settings.budget),
      sizingMode: settings.sizingMode,
      fixedAmount: fixed ? money(settings.fixedAmount) : null,
      copyPercent: fixed ? null : text(settings.copyPercent, percent),
      marketLimitPercent: text(settings.marketLimitPercent, percent),
      dailyBuyLimitPercent: text(settings.dailyBuyLimitPercent, percent),
    };
  }
  if (balanceAllowed) {
    const snapshot = object(session.financialSnapshot);
    if (snapshot.sessionId !== sessionId || snapshot.settingsRevisionId !== revision || snapshot.recordSchemaVersion !== 'v1'
      || snapshot.snapshotVersion !== summary.snapshotVersion || snapshot.sessionVersion !== sessionVersion || snapshot.asOf !== summary.asOf
      || snapshot.lifecycle !== summary.lifecycle || snapshot.controlState !== summary.controlState
      || snapshot.contentState !== summary.contentState || snapshot.coverageState !== summary.coverageState
      || snapshot.dataOrigin !== summary.dataOrigin || snapshot.unit !== 'virtual_USD') return invalid();
    if (snapshot.tradeCount !== '0' || snapshot.positionCount !== '0' || snapshot.orderCount !== '0') return invalid();
    result.financialSnapshot = {
      initialFunding: money(snapshot.initialFunding),
      free: money(snapshot.free),
      reserved: money(snapshot.reserved),
      equity: money(snapshot.equity),
      positionValue: money(snapshot.positionValue),
      tradingResult: money(snapshot.tradingResult),
      tradeCount: text(snapshot.tradeCount, count),
      positionCount: text(snapshot.positionCount, count),
      orderCount: text(snapshot.orderCount, count),
    };
  }
  return result;
}

export function decodePilotReadEnvelope(value: unknown, kind: 'sessions' | 'events', sessionId?: string) {
  const root = exact(value, [kind, 'observedAt', 'nextAction', 'nextActionParams', ...(kind === 'events' ? ['sessionId'] : [])]);
  if (root.nextAction !== null || (kind === 'events' && root.sessionId !== sessionId)) return invalid();
  exact(root.nextActionParams, []);
  time(root.observedAt);
  return root[kind];
}
