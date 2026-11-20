export interface MoneyValue { n: string; d: string }
type DemoOrigin = 'synthetic' | 'public_api';
type Data = Record<string, unknown>;

export interface DemoPosition {
  conditionId: string;
  tokenId: string;
  quantity: MoneyValue;
  cost: MoneyValue;
}
export interface CurrentSession {
  summary: {
    sessionId: string | null;
    dataOrigin: DemoOrigin;
    traderDisplayName: string;
    venueId: string;
    controlState: string;
    contentState: string;
    asOf: string;
  };
  settings: {
    sizingMode: 'fixed' | 'percent';
    budget: MoneyValue;
    fixedAmount: MoneyValue | null;
    copyPercent: string | null;
    marketLimitPercent: string;
    dailyBuyLimitPercent: string;
  };
  financialSnapshot: {
    free: MoneyValue;
    equity: MoneyValue | null;
    reserved: MoneyValue;
    positionValue: MoneyValue | null;
    positionCount: string;
  };
  positions: DemoPosition[];
}

const UUID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const HASH = /^0x[0-9a-f]{64}$/;
const UINT = /^(0|[1-9]\d{0,255})$/;
const SEQUENCE = /^(0|[1-9]\d{0,18})$/;
const fail = (): never => {throw new TypeError('Invalid demo response');};

function object(value: unknown): Data {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return fail();
  return value as Data;
}
function text(value: unknown, format?: RegExp): string {
  if (typeof value !== 'string' || !value.length || value.length > 2048 || (format && !format.test(value))) return fail();
  return value;
}
function time(value: unknown): string {
  const date = text(value);
  return Number.isFinite(Date.parse(date)) ? date : fail();
}
function origin(value: unknown): DemoOrigin {
  return value === 'synthetic' || value === 'public_api' ? value : fail();
}
function amount(value: unknown): MoneyValue {
  const {n, d} = object(value);
  return {n: text(n, UINT), d: text(d, /^[1-9]\d{0,255}$/)};
}
function readSettings(value: unknown): CurrentSession['settings'] {
  const settings = object(value);
  if (settings.sizingMode !== 'fixed' && settings.sizingMode !== 'percent') return fail();
  return {
    sizingMode: settings.sizingMode, budget: amount(settings.budget),
    fixedAmount: settings.fixedAmount === null ? null : amount(settings.fixedAmount),
    copyPercent: settings.copyPercent === null ? null : text(settings.copyPercent),
    marketLimitPercent: text(settings.marketLimitPercent), dailyBuyLimitPercent: text(settings.dailyBuyLimitPercent),
  };
}
function readSummary(value: unknown): CurrentSession['summary'] {
  const summary = object(value);
  if (summary.mode !== 'paper') return fail();
  return {
    sessionId: summary.sessionId === undefined ? null : text(summary.sessionId, UUID),
    dataOrigin: origin(summary.dataOrigin), traderDisplayName: text(summary.traderDisplayName),
    venueId: text(summary.venueId), controlState: text(summary.controlState),
    contentState: text(summary.contentState), asOf: time(summary.asOf),
  };
}

export function decodeCurrentSession(value: unknown): {session: CurrentSession | null} {
  const body = object(value);
  if (body.session === null) return {session: null};
  const session = object(body.session);
  if (session.schemaVersion === 'live-buy-session-v1') {
    const context = object(session.context);
    const summary = readSummary(context.summary);
    const financial = object(session.financial);
    const sessionId = text(session.sessionId, UUID);
    const snapshotId = text(session.snapshotId, UUID);
    if (summary.sessionId !== sessionId || financial.sessionId !== sessionId || financial.snapshotId !== snapshotId
      || financial.schemaVersion !== 'paper-buy-core-state-v1' || text(session.snapshotVersion, SEQUENCE) !== financial.version
      || object(session.valuation).status !== 'unavailable' || !Array.isArray(financial.positions)) return fail();
    const positions = financial.positions.map(value => {
      const row = object(value);
      return {
        conditionId: text(row.conditionId, HASH), tokenId: text(row.tokenId, UINT),
        quantity: amount(row.quantity), cost: amount(row.cost),
      };
    });
    const ids = new Set(positions.map(position => position.conditionId + ':' + position.tokenId));
    if (ids.size !== positions.length || positions.some(position => position.quantity.n === '0')) return fail();
    return {session: {
      summary, settings: readSettings(context.settings), positions,
      financialSnapshot: {
        free: amount(financial.freeCash), reserved: amount(financial.reservedCash),
        equity: null, positionValue: null, positionCount: String(positions.length),
      },
    }};
  }
  const summary = readSummary(session.summary);
  const snapshot = object(session.financialSnapshot);
  if (snapshot.dataOrigin !== summary.dataOrigin || snapshot.controlState !== summary.controlState
    || snapshot.contentState !== summary.contentState || typeof snapshot.coverageState !== 'string') return fail();
  const positionCount = text(snapshot.positionCount, SEQUENCE);
  const orderCount = text(snapshot.orderCount, SEQUENCE);
  if (summary.contentState === 'EMPTY' && (summary.controlState !== 'copying_not_connected' || positionCount !== '0' || orderCount !== '0')) return fail();
  amount(snapshot.tradingResult);
  return {session: {
    summary, settings: readSettings(session.settings), positions: [],
    financialSnapshot: {
      free: amount(snapshot.free), equity: amount(snapshot.equity), reserved: amount(snapshot.reserved),
      positionValue: amount(snapshot.positionValue), positionCount,
    },
  }};
}

export interface DemoEvent {
  id: string;
  sequence: string;
  occurredAt: string;
  venueCode: string;
  conditionId: string | null;
  tokenId: string;
  title: string | null;
  outcome: string | null;
  side: 'BUY' | 'SELL';
  status: 'filled' | 'pending' | 'skipped';
  detail: string | null;
  notional: MoneyValue | null;
  cashFee: MoneyValue | null;
  quantity: MoneyValue | null;
}
export interface DemoActivityPage {
  events: DemoEvent[];
  highWatermark: string;
  observation: string;
}

function optionalText(value: unknown, format?: RegExp): string | null {
  return value === null ? null : text(value, format);
}

export function decodeDemoActivity(value: unknown, sessionId: string, afterSequence: string, limit: number): DemoActivityPage {
  const response = object(value);
  if (response.sessionId !== sessionId || !Array.isArray(response.items) || response.items.length > limit) return fail();
  const page = object(response.page);
  const highWatermark = text(page.highWatermark, SEQUENCE);
  const nextAfterSequence = text(page.nextAfterSequence, SEQUENCE);
  if (page.afterSequence !== afterSequence || BigInt(highWatermark) < BigInt(nextAfterSequence)
    || BigInt(nextAfterSequence) !== BigInt(afterSequence) + BigInt(response.items.length)
    || page.hasMore !== (BigInt(nextAfterSequence) < BigInt(highWatermark))) return fail();
  const events = response.items.map((raw, index) => {
    const item = object(raw), source = object(item.source), trade = object(item.trade), decision = object(item.decision);
    if (trade.side !== 'BUY' && trade.side !== 'SELL') return fail();
    if (decision.status !== 'filled' && decision.status !== 'pending' && decision.status !== 'skipped') return fail();
    const sequence = text(item.sequence, SEQUENCE);
    if (BigInt(sequence) !== BigInt(afterSequence) + BigInt(index + 1)) return fail();
    const copy = decision.status === 'filled' ? object(decision.copy) : null;
    if (copy && copy.kind !== 'filled') return fail();
    return {
      id: text(item.activityId, UUID), sequence, occurredAt: time(source.sourceOccurredAt), venueCode: text(source.venueCode),
      conditionId: optionalText(trade.conditionId, HASH), tokenId: text(trade.tokenId, UINT),
      title: optionalText(trade.marketTitle), outcome: optionalText(trade.outcome), side: trade.side, status: decision.status,
      detail: optionalText(decision.detailCode), notional: copy ? amount(copy.notional) : null,
      cashFee: copy ? amount(copy.cashFee) : null, quantity: copy ? amount(copy.quantityNet) : null,
    } satisfies DemoEvent;
  });
  return {events, highWatermark, observation: text(object(response.observation).status)};
}
