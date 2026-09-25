# Контракт адаптеров Polymarket и Limitless

Дата: 25.09.2026. Статус: предлагаемая спецификация для paper-spikes и последующего утверждения. Production-код и реальные сделки этим документом не разрешаются.

## 1. Назначение и границы

Документ определяет границу между venue-neutral core и двумя обязательными площадками продукта: Polymarket и Limitless. Он дополняет техническую концепцию, карту блокеров, модель доверия и ADR-0008.

Цель контракта — позволить общему copy engine, risk engine, virtual lot ledger и журналу работать с одинаковыми внутренними моделями, не скрывая различия площадок. Адаптер переводит API конкретной площадки в нормализованные факты и команды. Он не принимает продуктовые решения, не рассчитывает размер копии и не ослабляет risk gates.

В первую версию не входят:

- автоматическое сопоставление похожих рынков разных площадок;
- перенос сделки лидера с одной площадки на другую;
- объединение ликвидности или позиций Polymarket и Limitless;
- общий platform order id, wallet id или market id без namespace площадки;
- optimistic execution при неизвестном статусе или устаревших данных.

## 2. Разделение ответственности

### Venue-neutral core

Core отвечает за:

- подписки на лидеров и `CopyPolicy`;
- дедупликацию нормализованных событий;
- расчёт размера, срока действия и допустимой цены;
- все пользовательские и системные risk gates;
- атомарное резервирование бюджета;
- создание `CopyIntent` до сетевого вызова;
- virtual lots, P&L, сервисные комиссии и партнёрские начисления;
- kill switches, журнал и пользовательские уведомления;
- решение, можно ли начать или продолжить автоматизацию.

### Venue adapter

Каждый adapter отвечает за:

- обнаружение своих capabilities и текущего operational mode;
- чтение и нормализацию markets, order book, leader activity, user orders, fills, positions и platform fees;
- проверку GEO/eligibility тем официальным способом, который предоставляет площадка;
- подготовку, подпись через разрешённый signer, отправку и отмену ордеров;
- отображение platform states и ошибок в общий словарь;
- идемпотентный поиск результата после timeout;
- reconciliation с API площадки и доступным settlement/on-chain источником;
- сохранение ссылок на сырой payload и доказательства нормализации.

Adapter не имеет права:

- увеличивать рассчитанный core размер;
- заменять venue или market;
- повторно отправлять ордер при неизвестном результате;
- обходить maintenance, GEO, permission или balance check;
- выбирать taker ради более высокой сервисной комиссии;
- выполнять withdrawal, если эта команда не вынесена в отдельный пользовательский процесс;
- переводить платформенную корректировку в подтверждённый fill без доказательства.

## 3. Namespace и точность данных

Все внешние идентификаторы хранятся парой `{venue, externalId}`. `externalId` нельзя сравнивать между площадками.

```text
Venue = POLYMARKET | LIMITLESS
VenueRef<T> = {
  venue: Venue
  externalId: string
}
```

Деньги, цена и количество представлены decimal-строками либо целыми минимальными единицами с явным scale. Binary floating point запрещён. Времена хранятся в UTC с точностью источника; отдельно сохраняются `sourceTime`, `observedAt` и `normalizedAt`.

Сырой ответ площадки не становится бизнес-истиной сам по себе. Каждая нормализованная запись содержит `schemaVersion`, `adapterVersion`, ссылку либо hash сырого payload и время получения.

## 4. Capability snapshot

Capabilities являются runtime-снимком, а не константами в коде. Один adapter может иметь разные возможности для public reader, конкретного user wallet, builder/partner account и текущего maintenance mode.

```text
VenueCapabilities = {
  venue: Venue
  environment: PROD | SANDBOX | PAPER_FIXTURE
  observedAt: Instant
  validUntil: Instant?
  evidence: CapabilityEvidence[]

  publicMarkets: boolean
  publicOrderBook: boolean
  publicWalletHistory: boolean
  publicWalletPositions: boolean
  publicLeaderRealtimeStream: boolean
  authenticatedUserOrderStream: boolean
  historicalBackfill: boolean

  clientOrderId: NONE | NATIVE | REQUEST_ID | EMULATED
  orderTypes: Set<GTC | FAK | FOK | POST_ONLY>
  partialFills: boolean
  cancelSingle: boolean
  cancelAll: boolean
  makerTakerClassification: boolean
  fillFeeBreakdown: NONE | AGGREGATE | PER_FILL

  authModes: Set<EOA_PER_ORDER | SESSION_KEY | PARTNER_HMAC | DELEGATED_SIGNING>
  tradingPermissionRevocable: boolean
  withdrawalPermissionSeparable: boolean
  permissionExpiryObservable: boolean

  maintenanceStatus: boolean
  geoEligibilityCheck: NONE | OFFICIAL_ENDPOINT | ACCOUNT_POLICY
  onchainSettlementObservable: boolean
  platformFeeAttribution: boolean
  serviceFeeAttribution: boolean
}
```

`CapabilityEvidence` указывает источник: официальный endpoint, документацию, договорённость с площадкой или результат spike. Возможность, требующая partner approval, не считается доступной, пока она не подтверждена для нашего аккаунта.

Ожидаемый начальный профиль, который ещё надо доказать:

| Capability | Polymarket | Limitless |
|---|---|---|
| Публичные markets/order book | Да | Да |
| Публичная история/позиции адреса | Да, проверить полноту Data API | Да, подтверждено read-only аудитом |
| Публичный realtime stream сделок произвольного лидера | Не подтверждён | Не подтверждён |
| Автоматическая подпись | Session Key beta для Deposit Wallet после разрешения Builder | Partner `delegated_signing` для server wallet |
| Отделение withdrawal | Session Key не может выводить | Отдельный scope; execution worker получает токен без `withdrawal` |
| GEO check | Официальный geoblock endpoint | Требуется письменное правило/доступный platform signal |
| Maintenance mode | Статус API и health должны быть формализованы spike | `maintenance/status`, включая `post_only`, `cancel_only`, `disabled` |
| Ордерные типы | Фактический набор фиксируется spike | GTC, FAK, FOK |
| Fee evidence | Platform fee + Builder Fee, maker/taker | `effectiveFeeBps`, `usdFee`, `contractsFee` на fill |

## 5. Нормализованные модели

Ни одна модель не теряет `venue`, исходный идентификатор и доказательство происхождения.

### Market

```text
Market = {
  id: VenueRef<Market>
  title: string
  outcomes: Outcome[]              // каждый с venue-scoped id/token id
  status: SCHEDULED | OPEN | PAUSED | RESOLVING | RESOLVED | CANCELLED | UNKNOWN
  opensAt: Instant?
  closesAt: Instant?
  resolutionSource: string?
  settlementRef: string?
  collateral: Asset
  tickSize: Decimal
  minOrderSize: Decimal
  orderBookEnabled: boolean
  rawVersion: string
  observedAt: Instant
}
```

Совпадение `title` не означает эквивалентность рынков. Cross-venue mapping отсутствует.

### LeaderEvent

```text
LeaderEvent = {
  id: InternalId
  venue: Venue
  sourceEventKey: string
  sourceKind: TRADE_FILL | POSITION_CHANGE | REDEMPTION | CORRECTION
  leader: VenueRef<Account>
  market: VenueRef<Market>
  outcome: VenueRef<Outcome>
  side: BUY | SELL
  price: Decimal?
  quantity: Decimal?
  notional: Money?
  sourceTime: Instant?
  observedAt: Instant
  finality: PROVISIONAL | CONFIRMED | CORRECTED
  rawPayloadHash: string
  adapterVersion: string
}
```

`sourceEventKey` строится из наиболее устойчивого venue id. Если у источника нет уникального trade/fill id, adapter формирует детерминированный составной ключ и документирует поля и риск коллизии. Event отражает наблюдаемое исполнение или изменение, а не предполагаемое намерение лидера.

### Order request и Order

```text
NormalizedOrderRequest = {
  venue: Venue
  wallet: VenueRef<Account>
  market: VenueRef<Market>
  outcome: VenueRef<Outcome>
  side: BUY | SELL
  orderType: GTC | FAK | FOK | POST_ONLY
  limitPrice: Decimal
  quantity: Decimal
  timeInForceUntil: Instant?
  clientOrderId: string
  requestId: string
  intentId: InternalId
  purpose: AUTOMATIC_COPY | MANUAL_CLOSE | PROTECTIVE_CLOSE | EMERGENCY_CLOSE | ERROR_CORRECTION
  feePolicyVersion: string?
}

Order = {
  id: InternalId
  venueOrder: VenueRef<Order>?
  clientOrderId: string
  requestId: string
  intentId: InternalId
  state: NormalizedOrderState
  requestedPrice: Decimal
  requestedQuantity: Decimal
  filledQuantity: Decimal
  remainingQuantity: Decimal
  submittedAt: Instant?
  lastObservedAt: Instant
  rawState: string?
}
```

### Fill и Fee

```text
Fill = {
  id: InternalId
  venueFill: VenueRef<Fill>
  orderId: InternalId
  market: VenueRef<Market>
  outcome: VenueRef<Outcome>
  side: BUY | SELL
  price: Decimal
  quantity: Decimal
  grossNotional: Money
  liquidityRole: MAKER | TAKER | UNKNOWN
  sourceTime: Instant
  observedAt: Instant
  settlementRef: string?
  correctionOf: InternalId?
}

FeeBreakdown = {
  fillId: InternalId
  platformFee: Money?
  venueDiscount: Money?
  serviceFee: Money
  serviceFeeMode: REAL | VIRTUAL_ALPHA | ZERO_EXEMPTION
  serviceFeeReason: ReasonCode
  feePolicyVersion: string
  upstreamValues: Map<string, Decimal>
}
```

Platform fee и сервисная комиссия всегда разделены. `UNKNOWN` liquidity role запрещает начислять ставку по предположению: fill блокируется для fee settlement до reconciliation или применяется заранее утверждённое безопасное правило с отдельным reason code.

### Position

```text
PositionSnapshot = {
  venue: Venue
  account: VenueRef<Account>
  market: VenueRef<Market>
  outcome: VenueRef<Outcome>
  quantity: Decimal
  averagePrice: Decimal?
  realizedPnl: Money?
  unrealizedPnl: Money?
  collateral: Money?
  snapshotAt: Instant
  source: PLATFORM | BLOCKCHAIN | DERIVED
  rawPayloadHash: string?
}
```

`PositionSnapshot` не содержит происхождение позиции. Эта информация остаётся во внутреннем `VirtualLot` ledger.

## 6. Жизненный цикл и перевод состояний

### Event и intent

Adapter возвращает факты; переходы `LeaderEvent` и `CopyIntent` остаются определёнными в документе 13. В частности, `SUBMISSION_UNKNOWN` запрещает повторную отправку до поиска существующего ордера.

### NormalizedOrderState

```text
PENDING_ACK
OPEN
PARTIALLY_FILLED
FILLED
CANCEL_REQUESTED
CANCELLED
REJECTED
EXPIRED
UNKNOWN
```

Правила перевода:

- terminal state площадки не меняется на другой terminal state без `ReconciliationIssue` и корректирующей записи;
- частичные fills сохраняются при `CANCELLED` и `EXPIRED`;
- timeout HTTP/RPC не означает `REJECTED`;
- неизвестный или новый raw status переводится в `UNKNOWN`, а не в ближайший знакомый статус;
- fill может появиться после запроса отмены; `CANCEL_REQUESTED` не освобождает резерв до доказанного остатка;
- adapter хранит исходное состояние, версию mapping и время наблюдения.

### OperationalMode

```text
OperationalMode = {
  read: ENABLED | DEGRADED | DISABLED
  newOrders: ENABLED | POST_ONLY | CANCEL_ONLY | DISABLED
  cancels: ENABLED | DEGRADED | DISABLED
  reason: ReasonCode?
  observedAt: Instant
  validUntil: Instant?
}
```

`CANCEL_ONLY` разрешает reconciliation и отмену, но запрещает новые orders. `POST_ONLY` допускается только для явно совместимого order type; core не меняет FAK/FOK на resting order автоматически. Устаревший operational snapshot запрещает новые risk-increasing submissions.

## 7. Идемпотентность

Используются четыре независимых ключа:

1. `sourceEventKey = venue + stable source trade/fill id` либо документированный deterministic composite.
2. Уникальность intent: `(userId, copyPolicyVersionId, venue, sourceEventKey)`.
3. `clientOrderId` неизменяем для intent и попытки, если площадка гарантирует его уникальность.
4. `requestId` идентифицирует один сетевой вызов и попадает в журнал и platform headers, если это поддерживается.

Порядок отправки:

1. Core транзакционно создаёт intent, reservations и submission record.
2. Adapter валидирует capability, permission и operational snapshots.
3. Выполняется один сетевой submit.
4. Достоверный ответ связывает platform order id.
5. Timeout/connection loss создаёт `SUBMISSION_UNKNOWN`.
6. `findSubmission` ищет ордер по native client id, request id, account, market, параметрам и ограниченному временному окну.
7. Повтор допустим только после доказательства отсутствия первого ордера и создания новой явно связанной attempt record. Слепой retry запрещён.

Fill уникален по `{venue, venueFillId}`. Если площадка не предоставляет стабильный fill id, adapter использует versioned composite и обязан доказать его устойчивость на backfill, перестановке и повторной выдаче страниц.

## 8. Reconciliation

Источники истины разделяются:

- platform API — order lifecycle и fills;
- blockchain/settlement — владение токенами, settlement и доступный баланс, когда применимо;
- internal ledger — происхождение virtual lots, reservations, purpose и service fees.

```text
ReconciliationReport = {
  venue: Venue
  account: VenueRef<Account>
  startedAt: Instant
  completedAt: Instant
  cursorBefore: string?
  cursorAfter: string?
  ordersCompared: integer
  fillsDiscovered: integer
  positionDiffs: PositionDiff[]
  issues: ReconciliationFinding[]
  freshness: FRESH | STALE | INCOMPLETE
}
```

Минимальные режимы сверки:

- после каждого submit/cancel и неоднозначного ответа;
- периодический incremental poll/stream reconciliation;
- полный backfill по аккаунту и market;
- сверка после reconnect, token rotation, revoke, maintenance и deployment;
- сверка перед конфликтующим sell или снятием блокировки `UNKNOWN`.

Блокирующие расхождения: неизвестный order result, недостающий fill, внешний balance меньше суммы лотов, необъяснимый внешний sell, разный market/outcome, неизвестная fee role, просроченная permission/position freshness. Adapter только сообщает finding и доказательства; корректировку ledger применяет core через явную запись.

## 9. GEO, maintenance и permission boundary

Перед risk-increasing live order adapter обязан вернуть свежие результаты:

```text
EligibilityDecision = {
  decision: ALLOW | CLOSE_ONLY | DENY | UNKNOWN
  reason: ReasonCode
  checkedAt: Instant
  evidenceRef: string?
}

PermissionSnapshot = {
  state: ACTIVE | EXPIRING | REVOKING | REVOKED | EXPIRED | UNKNOWN
  authMode: EOA_PER_ORDER | SESSION_KEY | PARTNER_HMAC | DELEGATED_SIGNING
  scopes: Set<string>
  withdrawalAllowed: boolean
  expiresAt: Instant?
  checkedAt: Instant
}
```

Правила:

- `DENY` и `UNKNOWN` запрещают новые live orders;
- `CLOSE_ONLY` может разрешать только доказанно уменьшающие риск действия по правилам площадки;
- отсутствие официального GEO endpoint не трактуется как `ALLOW`;
- adapter не хранит owner seed/private key;
- execution credential изолирован по venue и среде;
- Limitless execution token имеет `trading`, `account_creation`, `delegated_signing`, но не `withdrawal`;
- Polymarket session signer ограничен доступными trading scopes и не заменяет owner signer;
- revoke немедленно блокирует новые submissions в core, но открытые ордера остаются активными до подтверждённой отмены;
- admin и partner интерфейсы не могут вызвать raw sign, trade или withdrawal.

Withdrawal/recovery не входят в `TradingAdapter`. Если они появятся, это отдельный интерфейс, credential, журнал, user confirmation и security review.

## 10. Ошибки и reason codes

Adapter никогда не отдаёт core произвольный текст как основание решения. Он возвращает стабильный `ReasonCode`, retry classification, сырой platform code и безопасные диагностические данные.

```text
AdapterError = {
  reason: ReasonCode
  retry: NEVER | AFTER_BACKOFF | AFTER_REFRESH | AFTER_RECONCILIATION | USER_ACTION
  platformCode: string?
  requestId: string?
  safeMessage: string?
  occurredAt: Instant
}
```

Минимальный словарь:

| Группа | Reason codes |
|---|---|
| Событие | `EVENT_DUPLICATE`, `EVENT_STALE`, `EVENT_UNSUPPORTED`, `EVENT_ID_UNSTABLE`, `SOURCE_DATA_INCOMPLETE` |
| Market/order | `MARKET_CLOSED`, `MARKET_PAUSED`, `OUTCOME_UNKNOWN`, `ORDER_TYPE_UNSUPPORTED`, `MIN_SIZE_NOT_MET`, `PRICE_OUT_OF_RANGE`, `INSUFFICIENT_LIQUIDITY` |
| Риск | `DAILY_LIMIT_REACHED`, `LEADER_BUDGET_REACHED`, `PORTFOLIO_LIMIT_REACHED`, `SLIPPAGE_LIMIT`, `REENTRY_BLOCKED` |
| Доступ | `GEO_DENIED`, `GEO_CLOSE_ONLY`, `GEO_UNKNOWN`, `PERMISSION_MISSING`, `PERMISSION_EXPIRED`, `PERMISSION_REVOKING`, `WITHDRAWAL_SCOPE_FORBIDDEN` |
| Площадка | `MAINTENANCE_POST_ONLY`, `MAINTENANCE_CANCEL_ONLY`, `MAINTENANCE_DISABLED`, `RATE_LIMITED`, `VENUE_UNAVAILABLE`, `CAPABILITY_NOT_CONFIRMED` |
| Отправка | `ORDER_REJECTED`, `SUBMISSION_TIMEOUT`, `SUBMISSION_UNKNOWN`, `CANCEL_UNKNOWN`, `CLIENT_ORDER_ID_CONFLICT` |
| Сверка | `ORDER_STATE_MISMATCH`, `FILL_MISSING`, `FILL_DUPLICATE`, `POSITION_MISMATCH`, `BALANCE_BELOW_LEDGER`, `FEE_UNRESOLVED`, `RECONCILIATION_STALE` |
| Security | `CREDENTIAL_INVALID`, `CREDENTIAL_COMPROMISED`, `SIGNATURE_FAILED`, `KILL_SWITCH_ACTIVE` |

UI переводит reason codes через i18n и показывает рекомендуемое действие. Новые неизвестные platform errors по умолчанию относятся к безопасному отказу или `UNKNOWN`, а не к retryable success.

## 11. Интерфейсы adapters

Псевдотипы описывают требуемое поведение, а не язык реализации.

```text
interface VenueReadAdapter {
  venue(): Venue
  capabilities(ctx): Result<VenueCapabilities, AdapterError>
  operationalMode(ctx): Result<OperationalMode, AdapterError>
  eligibility(ctx, account?, locationContext): Result<EligibilityDecision, AdapterError>

  listMarkets(cursor?, filter?): Page<Market>
  getMarket(marketRef): Result<Market, AdapterError>
  getOrderBook(marketRef, outcomeRef): Result<OrderBookSnapshot, AdapterError>

  backfillLeaderEvents(leaderRef, from, to, cursor?): Page<LeaderEvent>
  streamLeaderEvents?(leaderRef, checkpoint): Stream<LeaderEvent>
  listPositions(accountRef, cursor?): Page<PositionSnapshot>
}

interface VenueTradingAdapter {
  permissionSnapshot(accountRef): Result<PermissionSnapshot, AdapterError>
  validateOrder(request, snapshots): Result<ValidatedVenueOrder, AdapterError>
  submit(validatedOrder): Result<SubmitAccepted | SubmitUnknown, AdapterError>
  findSubmission(submissionProbe): Result<Order | ProvenAbsent | Inconclusive, AdapterError>
  getOrder(orderRef): Result<Order, AdapterError>
  listOrders(accountRef, from, cursor?): Page<Order>
  listFills(accountRef, from, cursor?): Page<Fill>
  cancel(orderRef, requestId): Result<CancelAccepted | CancelUnknown, AdapterError>
  cancelAll(accountRef, scope, requestId): Result<CancelBatchResult, AdapterError>
}

interface VenueReconciliationAdapter {
  incremental(accountRef, checkpoint): Result<ReconciliationReport, AdapterError>
  full(accountRef, scope): Result<ReconciliationReport, AdapterError>
  reconcileSubmission(submissionProbe): Result<Order | ProvenAbsent | Inconclusive, AdapterError>
  settlementEvidence(fillRef): Result<SettlementEvidence | NotApplicable, AdapterError>
}
```

Отсутствующая optional stream-функция означает polling/backfill с измеренной задержкой. Core получает одинаковые модели, но учитывает capability и freshness при решении.

### Реализации Polymarket

`PolymarketReadAdapter` объединяет Gamma, CLOB market data, Data API и доступные WebSocket feeds. `PolymarketTradingAdapter` разделяет пользовательские L1/L2 credentials, Builder credentials и session signer. Builder attribution и Builder Fee сохраняются как отдельные evidence fields. Geoblock вызывается до live order согласно официальным правилам.

### Реализации Limitless

`LimitlessReadAdapter` использует публичные markets, portfolio/history и позиции. При отсутствии публичного leader stream он использует backfill/polling с checkpoint. `LimitlessTradingAdapter` использует partner HMAC и `x-on-behalf-of`; delegated signer изолирован от withdrawal. Adapter отражает `post_only`, `cancel_only`, `disabled`, `425`, `429`, `clientOrderId`, `x-request-id` и фактический fee breakdown.

## 12. Критерии готовности paper adapter

Paper adapter готов только если для каждой площадки:

1. Есть recorded fixtures минимум для buy, sell, partial fill, cancel, duplicate, reordered page и correction.
2. Все fixtures проходят versioned normalization без потери venue ids и timestamps.
3. `sourceEventKey` устойчив при повторном backfill и pagination overlap.
4. Измерены полнота и задержка leader data минимум 72 часа на 3–5 адресах.
5. Order book simulator применяет venue tick size, min size, depth и platform fee.
6. Paper order lifecycle воспроизводит partial fill, expiry, cancel race, timeout и unknown state.
7. Fault injection не создаёт двойной intent, order или fill.
8. Full reconciliation на fixtures обнаруживает пропуск, дубль, внешний sell и position mismatch.
9. Capability, operational и permission snapshots можно протухнуть и проверить safe stop.
10. Contract tests одинаковы для Polymarket и Limitless, а venue-specific исключения задокументированы.

Paper readiness не требует trading credentials и не разрешает live funds.

## 13. Критерии готовности live adapter

Live разрешается отдельно для каждой площадки и только после paper readiness. Требуются:

1. Capabilities подтверждены для проектного Builder/Partner аккаунта.
2. GEO/eligibility проверен для выбранного launch GEO; обход ограничений исключён.
3. Owner, trading signer, recovery, revoke и withdrawal boundary пройдены end-to-end.
4. Execution worker технически не может вывести средства.
5. Submit/find/cancel/reconcile доказаны в sandbox либо на минимальном личном тесте, отдельно разрешённом основателем.
6. Unknown submission восстанавливается без двойного ордера.
7. Revoke/expiry/maintenance/redeploy не приводят к скрытому возобновлению торговли.
8. Maker/taker, platform fee, service fee и attribution сверяются по каждому fill.
9. Мониторинг freshness, error rates, latency, reconciliation lag и open `UNKNOWN` issues включает venue kill switch.
10. Secrets хранятся раздельно, ротация и incident procedure проверены.
11. Выполнены security review, fault injection и проверка денежных инвариантов документа 13.
12. Основатель принимает отдельное решение GO с лимитом пользователей, капитала и дневного оборота.

Прохождение Limitless gate не разрешает Polymarket live и наоборот.

## 14. Contract-test matrix

Одинаковый набор тестов запускается против fixture adapter и каждой venue реализации:

| Сценарий | Ожидаемый инвариант |
|---|---|
| Повтор leader page | Один `LeaderEvent` и один intent на policy |
| Timeout при submit | `SUBMISSION_UNKNOWN`, без автоматического retry |
| Ордер найден после timeout | Связать существующий order, не создавать новый |
| Partial fill + cancel | Сохранить fills; отменить только остаток |
| Fill после cancel request | Учесть fill и пересчитать остаток |
| Неизвестный raw state | `UNKNOWN` и блокировка конфликтующей операции |
| Просроченный capability/maintenance snapshot | Запрет новой risk-increasing операции |
| Revoke при открытом GTC | Запрет новых orders; cancel и reconciliation до terminal state |
| Повтор fill/webhook | Один fill и одно fee event |
| Внешняя ручная продажа | Blocking issue; лоты не переписываются молча |
| Fee role отсутствует | Fee settlement не угадывается |
| Новый platform error | Стабильный fallback reason и safe stop |

## 15. Открытые вопросы перед утверждением

### Общие

- Какой максимальный возраст capability, eligibility, order book и permission snapshots допустим для buy и risk-reducing sell?
- Какой доказательный порог позволяет `findSubmission` вернуть `ProvenAbsent`, если native client id отсутствует?
- Какие допустимые position/fee variance можно принять автоматически, а какие всегда блокируют торговлю?
- Какие leader actions считаются correction и могут ли они изменить уже нормализованную историю только новой записью?

### Polymarket

- Какие order types и client-id гарантии реально доступны выбранному CLOB flow?
- Какова полнота и задержка событий произвольного лидера через Data API/WebSocket/on-chain комбинацию?
- Какие данные видит owner и session key по ордерам друг друга?
- Как выглядит подтверждённый порядок revoke, отмены открытых ордеров и reconciliation?
- Как получать единый operational/maintenance status, достаточный для safe stop?

### Limitless

- Есть ли partner webhook или authenticated stream, уменьшающий задержку публичного leader polling?
- Гарантируется ли уникальность `clientOrderId` на sub-account и как долго хранится дедупликация?
- Как platform рекомендует доказывать отсутствие ордера после timeout?
- Что происходит с resting orders после revoke HMAC/delegated signing?
- Как пользователь выполняет recovery и безопасный вывод без нашего backend и без `withdrawal` у execution worker?
- Какой официальный сигнал использовать для GEO/eligibility каждого пользователя?

До ответов соответствующие capabilities имеют значение `false`, `UNKNOWN` или partner-only и не могут использоваться как основание live-доступа.

