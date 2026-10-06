# CLOB: авторизация, собственные ордера и делегированная торговля

Дата проверки официальных источников: **2026-10-06**. Область: Predictions CLOB; Perps и Combo RFQ не включены в торговую матрицу. Статусы: **документировано** — текущие официальные страницы и схемы; **не проверено** — приватные REST/WS и торговые операции не выполнялись; **требует партнёрского доступа** — явно указанный допуск Builder API key к Session Key management. Все примеры ниже — схемы, а не результаты реального ордера. Это исследование не меняет бизнес-логику MVP.

## Версии и инструменты

Production CLOB: `https://clob.polymarket.com`; OpenAPI также перечисляет `https://clob-staging.polymarket.com`. Наличие staging в схеме не доказывает общедоступный sandbox с тестовыми средствами. У OpenAPI `info.version=1.0.0` — версия спецификации, **не** поколение контракта/протокола. [CLOB OpenAPI](https://docs.polymarket.com/api-spec/clob-openapi.yaml).

Официальные unified SDK: TypeScript `@polymarket/client`, Python `polymarket-client` (import `polymarket`). Текущий верхний release в SDK Changelog для обоих — `0.12.0`. Это подтверждение документации, не проверка npm/PyPI latest/dist-tag. Перед реализацией зафиксировать registry version и commit; старые `clob-client`, `py-clob-client` не считать текущим универсальным интерфейсом. SDK миграция отдельно от Protocol V2 и Data API v2. [TypeScript](https://docs.polymarket.com/getting-started/typescript), [Python](https://docs.polymarket.com/getting-started/python), [SDK changelog](https://docs.polymarket.com/changelog/sdks), [старые SDK → unified](https://docs.polymarket.com/migrate/clob-sdk-to-unified-sdk).

## Идентичность и подпись

Account wallet хранит средства и позиции; signer доказывает полномочия; `maker` ордера указывает кошелёк средств. Историческое SDK поле `funder` нельзя трактовать как отдельный пользовательский субсчёт. При unified client отдельно сохранять signer address, account wallet и wallet type. У CLOB `owner` в wire/order response — идентификатор API key, а не универсальный account address.

| Тип | signature_type | maker | signer в Order | Особенности |
|---|---:|---|---|---|
| EOA | 0 | EOA | EOA | Текущая документация требует allowlisted EOA; onchain операции напрямую, gas в POL |
| Proxy | 1 | Proxy Wallet | account signer | Legacy Magic Link/Google |
| Safe | 2 | Safe Wallet | account signer | Legacy external wallet account |
| Deposit Wallet | 3 | Deposit Wallet | Deposit Wallet | Реальный owner/session EOA подписывает обёрнутую typed data |

Deposit Wallet — default для account wallets deployed on/after **2026-05-04**. Определять тип по account resolution, не по предположению, что любой `proxyAddress` — legacy Proxy. [Wallets/Auth](https://docs.polymarket.com/trading/wallets-auth), [Place Orders](https://docs.polymarket.com/trading/place-orders).

L1 CLOB auth: EIP-712 `ClobAuthDomain`, version `1`, chainId `137`, address/timestamp/nonce/message. L1 используется для создания/derivation L2 credentials. L2: API key, secret, passphrase и `POLY_ADDRESS`, `POLY_API_KEY`, `POLY_PASSPHRASE`, `POLY_TIMESTAMP`, `POLY_SIGNATURE`. Request signature — URL-safe base64 HMAC-SHA256 от `timestamp + method + requestPath + exactSerializedBody`; не путать её с EIP-712 подписью самого ордера. Request timestamp — seconds; Order timestamp — milliseconds. [API authentication](https://docs.polymarket.com/getting-started/api#authentication).

Relayer API key разрешает gasless wallet operations; Builder credentials разрешают builder-authenticated Relayer operations. Ни тот, ни другой сам по себе не заменяет owner signature или CLOB L2 credentials. Не создавать `SecureClient` ради read-only discovery без оценки побочных действий: default flow может автоматически deploy Deposit Wallet. Для paper достаточно public client. [Wallets/Auth](https://docs.polymarket.com/trading/wallets-auth).

## CTF и Protocol V2 — разные маршруты

По **Gamma market.version**: `v1` → `clobTokenIds` (JSON-encoded array); `v2` → `positionIds` (array of decimal strings). Outcome ID берётся по индексу decoded `outcomes`. Если обе коллекции есть, выбирается только поле, соответствующее `version`. Missing/unsupported version, несовпадение outcome, отсутствующий/non-decimal ID — ошибка mapping. IDs сохранять строками. SDK neutral `assetId`; deprecated `tokenId` ещё поддерживается, wire `order.tokenId` остаётся даже для V2 position ID.

| Рынок | Order signing domain version | Exchange |
|---|---|---|
| CTF обычный | `2` | `0xE111180000d2663C0091e4f400237545B87B996B` |
| CTF negative risk | `2` | `0xe2222d279d744050d28e00520010520000310F59` |
| Protocol V2 | `3` | `0xe3333700cA9d93003F00f0F71f8515005F6c00Aa` |

Domain name для всех — `Polymarket CTF Exchange`, chainId `137`; **market version и EIP-712 domain version различны**. V2 Order сохраняет CTFExchangeV2 struct. V2 BUY требует pUSD approval ExchangeV3; SELL — PositionManager operator approval ExchangeV3. CTF approvals не дают V2 permissions. CLOB cache selector `COLLATERAL` для pUSD, `CONDITIONAL` для CTF и `CONDITIONAL-V2` для V2. В spec enum selector может отставать от migration guide — проверять обе страницы. [Protocol V2 direct API](https://docs.polymarket.com/migrate/polymarket-v2/api-integrations), [SDK migration](https://docs.polymarket.com/migrate/polymarket-v2/sdk-integrations), [Place Orders](https://docs.polymarket.com/trading/place-orders).

Deposit Wallet signing использует ERC-7739 typed-data wrapper. Session signature дополнительно оборачивается с signer ID и EIP-6492 magic suffix. Не переносить standard EOA signature как готовую Deposit Wallet signature. Полную реализацию брать из закреплённого официального SDK, не из сокращённых примеров этого справочника. [Session Keys](https://docs.polymarket.com/trading/session-keys).

## Session Keys: доступ не равен универсальному субсчёту

**Документировано / beta / требует партнёрского доступа для management:** отдельный EOA signer, авторизованный Deposit Wallet Owner; ключ не может withdraw. Поддерживаются только Deposit Wallet, миграция Safe/Proxy ещё planned. Authorization требует Builder API key и в initial rollout его allowlist через `builder@polymarket.com`. Scope: `CLOB`, `COMBOSRFQ`, либо `ALL` (включает будущие supported venues). Нет документированного per-market allowlist, денежного лимита или политики copy-risk внутри этих scope. Срок фиксированный **180 дней**, shorter expiry не поддерживается; окончить доступ раньше — revoke. [Session Keys](https://docs.polymarket.com/trading/session-keys).

Приватные чтения разделяются по signer activity: Session Key видит собственные orders/trades, notifications и WS user events; Deposit Wallet Owner **не может fetch orders submitted by authorized Session Keys**. Это явное ограничение текущего guide. Нельзя обещать owner unified ledger всех delegated executions без отдельного reconciliation design. Отзыв препятствует дальнейшей торговле ключа и отменяет его open orders, не чужих Session Keys; SDK resolve означает удаление ключа из active registry, а отмена и onchain finalization идут асинхронно. Для REST revoke завершение требует canceled key orders и confirmed transaction. [Session Keys — considerations/revoke](https://docs.polymarket.com/trading/session-keys#session-key-considerations), [SDK changelog](https://docs.polymarket.com/changelog/sdks).

Owner authorization → Relayer submission with Builder HMAC + Idempotency-Key → confirmed Relayer transaction → CLOB active signer registry. Только наличие ключа в active `signers` с ожидаемыми scopes/expiry подтверждает readiness; submitted response недостаточен. Registry показывает usable/unexpired/non-revoked signers. В raw REST `validUntil` требуется current whole Unix seconds +180 days; пример guide использует `4315 hours`, что расходится с `180×24=4320 hours`: **не копировать эту арифметику**, получить подтверждение партнёра/закреплённого SDK. [Session Keys](https://docs.polymarket.com/trading/session-keys).

## Ордер, match и settlement

Все ордера limit. GTC rests until filled/canceled; GTD expires; FOK all-or-nothing; FAK fills available and cancels remainder. `postOnly` допускается для GTC/GTD, crossing order отвергается. Minimum tick/order size, negRisk, fees, balance/allowance читаются до подписания. BUY FOK/FAK amount — collateral, SELL — shares; GTC/GTD size — shares. Учитывать fees all-in, не считать отображаемую цену полной стоимостью. [Order lifecycle](https://docs.polymarket.com/concepts/order-lifecycle), [Place Orders](https://docs.polymarket.com/trading/place-orders).

Post status `live`, `matched`, `delayed`, `unmatched` не равен final settlement. Собственный trade проходит `MATCHED → MINED → CONFIRMED` либо `RETRYING → …`/`FAILED`. Приватная REST schema содержит префиксы `TRADE_STATUS_*`, WS — короткие статусы; сохранить raw отдельно от normalized status. Partial fill оставляет remainder; cancel снимает только remainder и не отменяет settled fills. `CANCELED_MARKET_RESOLVED` тоже не обнуляет `size_matched` и не откатывает execution. Число matched shares не равно текущему wallet position после последующих операций. [Lifecycle](https://docs.polymarket.com/concepts/order-lifecycle), [OpenOrder schema](https://docs.polymarket.com/api-spec/clob-openapi.yaml).

Selected crypto/finance markets: lifecycle guide описывает 250 ms taker hold (`clob-markets/{condition_id}.itode=true`), final response после hold; configured sports markets могут иметь asynchronous seconds delay. Во время pending delay отмена недоступна, после delay проводится revalidation. Это причина не обещать мгновенную cancellation. Однако [Predictions changelog](https://docs.polymarket.com/changelog/predictions) от04.09.2026 указывает для crypto 150ms; guide/changelog расходятся. Фактическую применимую задержку нужно подтвердить по market/runtime, не фиксировать250ms как текущий crypto default. [Lifecycle](https://docs.polymarket.com/concepts/order-lifecycle).

**Вывод для адаптера, не API гарантия:** `UNKNOWN` нужен при timeout/transport failure после submit; отсутствие HTTP success не доказывает отсутствие принятого ордера. Persist intent, signer identity, exact signed order/hash, request/receive time; query known order ID and account trades, сверить WS/REST и chain до повторной отправки. В просмотренной CLOB order API нет документированного idempotency header и атомарного amend/replace endpoint. Replace следует моделировать cancel + новое signed order, с промежуточной сверкой исполнений и риском гонки. Session management Idempotency-Key нельзя переносить как гарантию order submit. 404 с другой signer credential не доказывает отсутствия ордера. [Manage Orders](https://docs.polymarket.com/trading/manage-orders), [CLOB OpenAPI](https://docs.polymarket.com/api-spec/clob-openapi.yaml).

## Собственный realtime и восстановление

Authenticated user WS: `wss://ws-subscriptions-clob.polymarket.com/ws/user`. Subscription frame содержит `auth.apiKey/secret/passphrase`, `type=user`, optional `markets` condition IDs. Отправить сразу после connect; неавторизованное/неподписанное соединение может закрыться. Application `PING` каждые 10 seconds, ответ `PONG`. Wire `event_type` distinguishes order/trade; order `type` = PLACEMENT/UPDATE/CANCELLATION. Orders carry original_size/size_matched/status/associate_trades; trades carry trade ID/taker order/maker_orders/status/transaction_hash (может null). [Realtime order updates](https://docs.polymarket.com/trading/realtime-order-updates).

Документирован user stream **собственных** authenticated executions. Это не канал любых сделок произвольного leader wallet. Public Data history не имеет такой же delivery/finality semantics. В read sources не найдено гарантии replay cursor, durable delivery, exactly-once или total ordering через reconnect. Это отсутствие подтверждённой гарантии, не доказательство её невозможности.

**Рекомендация адаптеру:** reconnect с backoff/jitter, новая authenticated subscription; параллельно REST full open orders и trades с overlap временного окна; deduplicate trade ID + relevant maker_order ID; upsert status transitions, не суммировать повторные MATCHED/MINED/CONFIRMED как новые fills. Reconcile unsettled trades до terminal state, wallet balances/positions и chain hash при наличии. Polling interval выбрать после rate-budget/design review; справочник не задаёт продуктовый SLA. SDK automatic reconnect не означает, что приложение восстановило потерянные события. [Realtime](https://docs.polymarket.com/trading/realtime-order-updates), [Manage Orders](https://docs.polymarket.com/trading/manage-orders).

**Отдельный механизм**, не WS PING: POST `/v1/heartbeats` включает auto-cancel open orders этих CLOB credentials; send every5s, timeout10s, cancellation sweep every5s (ещё до5s). После первого accepted heartbeat его нужно продолжать. У него stateful heartbeat_id: отправлять последний returned ID; при400 использовать expected ID response после анализа. Не включать в read-only исследования. [Order heartbeats](https://docs.polymarket.com/trading/manage-orders#order-heartbeats).

## Builder attribution и fees

Builder profile получает `bytes32` code, signed `builder` order field; attribution применяется для CTF и V2, onchain OrderFilled содержит code. Builder credentials и builder code — разные сущности. Public `/builder/trades?builder_code=…` — история attribution, не произвольный чужой аккаунт. [Builder fees](https://docs.polymarket.com/programs/builders/fees), [Manage Orders](https://docs.polymarket.com/trading/manage-orders).

Builder fee additive к platform fee. Builder fee = notional × bps/10000; default0, max taker100bps, maker50bps, granularity1bp. Изменение максимум раз/7days, advance notice3days, одно pending изменение. Platform fee per-market, currently taker-only, formula `C × feeRate × p × (1-p)`; не фиксировать универсальную feeRate. Покупатель должен покрывать collateral + обе applicable fees; SELL fees уменьшают proceeds. Maker/taker могут иметь разные builder codes/rates. Проверить disabled-code поведение и актуальный profile перед future live. [Builder fees](https://docs.polymarket.com/programs/builders/fees).

## Maintenance, quotas и Builder tiers

При рестарте matching engine временно отвергает order-related работу, затем документирован двухминутный post-only период: cancels доступны, новые orders только eligible post-only maker. `503` с generic trading-disabled ответом не различает cancel-only и fully-disabled; нельзя по нему объявлять cancels enabled. `code=post_only_mode`, `Retry-After`/`retry_after_seconds` раскрывают конкретное ограничение; batch HTTP success может содержать отдельные отказы. Retry рекомендован только при явном restart rejection. Transport timeout остаётся UNKNOWN по проектному контракту, независимо от примерного retry loop SDK. [Matching engine](https://docs.polymarket.com/trading/matching-engine).

| IP family | Документированный лимит |
|---|---|
| CLOB general |9000req/10s|
| `/book`, `/price`, `/midpoint` |1500req/10s каждый|
| `/books`, `/prices` |500req/10s каждый|
| `/data/orders`, `/data/trades` |500req/10s каждый|
| balance read / update |200 /50req/10s|
| API key routes |100req/10s|
| POST/DELETE `/order` |burst5000/10s, sustained120000/10min|
| POST `/orders` |burst2000/10s, sustained21000/10min|
| DELETE `/orders` |burst2000/10s, sustained15000/10min|
| DELETE `/cancel-all` |burst250/10s, sustained6000/10min|

Это IP limits Cloudflare, не signer budget и не SLA. Общие и route ceilings проверяются вместе. [Rate limits](https://docs.polymarket.com/api-reference/rate-limits).

Per-signer order/cancel buckets независимы. Standard: order40tokens/s, burst60; cancel80/s, burst120. Cost single1, batch=count; cancel-all/cancel-market1+успешно отменённые orders. Standard может уйти в отрицательный cancel balance. Volume tiers привязаны к maker wallet, окно30d и refresh3h; higher tiers смотреть в официальной таблице. `Poly-RateLimit-Remaining`, `Poly-RateLimit-Reset`, `Poly-RateLimit-Tier`, `Retry-After` важнее локальной догадки о доступной квоте. Batch admission all-or-none только на limiter, не гарантия одинакового order результата. Guide сохраняет историческую warning-mode запись с24.07; фактическое enforcement состояние для проекта не проверено. [Trading rate limits](https://docs.polymarket.com/api-reference/trading-rate-limits).

Builder quotas: Unverified100 relayer tx/day, Verified10000/day, Partner unlimited; non-relayer rate limits Standard/Standard/Highest. Нужен manual approval для Verified; Session management allowlist — отдельный gate. Эти tiers не заменяют per-signer bucket и не доказывают доступ нашего проекта. Регистрация и обращение партнёру в этом цикле не выполнялись. [Builder tiers](https://docs.polymarket.com/programs/builders/tiers).

## Расхождения источников и вопросы

1. DELETE `/orders`: guide говорит до3000 IDs; OpenAPI maxItems1000. Не обещать max3000 без подтверждения, conservatively batch≤1000 до проверки.
2. Post response schema enum live/matched/delayed; Lifecycle добавляет unmatched. Нормализатор должен сохранять незнакомые статусы и не падать на enum drift.
3. Trades wire/status/units отличаются от SDK normalized models; OpenAPI примеры некоторых trade sizes выглядят base units, guide показывает shares. Подтвердить units по конкретному response, не делить всё на1e6. OpenOrder original_size/size_matched явно normalized decimal shares; signed amounts и BalanceAllowance явно6 decimals.
4. Session expiry guide arithmetic4315h конфликтует с180days. Партнёр должен подтвердить validation tolerance/clock/source of truth; SDK версия должна быть pinned.
5. Error Codes называет L1 headers HMAC, тогда как authentication guide показывает EIP712. Использовать authentication protocol source, записать typo; generic error object не отменяет дополнительные `code/retry_after_seconds` в503 schema.
6. Вопрос партнёру: можно ли owner получить консолидированные session trades и как восстановить их при потере session credentials? Гарантии WS replay/retention/order; CLOB order dedupe и timeout recovery; confirmed finality/reorg handling; sandbox coverage; availability/migration Session Keys for legacy wallets; granular budgets/scopes; production fee eligibility для automated copy trading; current cancel batch limit.

## Матрица CLOB endpoints

Следующая таблица автоматически сверена с текущим официальным OpenAPI. Все строки **документированы, runtime не проверены**, включая публичный builder read. L1/L2 описаны выше. Pagination opaque: передавать возвращённый next_cursor без самостоятельного построения/декодирования. Для trades terminal `LTE=`; OrdersResponse описывает empty terminal, guide/SDK wrapper может иметь собственную форму cursor — проверять wire, не переносить SDK `{items,has_more}` на REST. Global429 и503 учитывать, даже когда отдельная response list их не перечисляет. [CLOB OpenAPI](https://docs.polymarket.com/api-spec/clob-openapi.yaml), [Errors](https://docs.polymarket.com/resources/error-codes).

| Метод/путь | Auth | Параметры/body | Pagination | 200 response | Errors(spec HTTP) | Источник |
|---|---|---|---|---|---|---|
| `POST /order` | L2 |  body:SendOrder(order,owner,orderType,deferExec,postOnly) | — | SendOrderResponse(success,orderID,status,makingAmount,takingAmount,transactionsHashes,tradeIDs,errorMsg) | 400,401,500,503 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `DELETE /order` | L2 |  body:CancelOrderPayload(orderID) | — | CancelOrdersResponse(canceled,not_canceled) | 400,401,500,503 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `POST /orders` | L2 |  body:array[SendOrder(order,owner,orderType,deferExec,postOnly)] max15 | — | array[SendOrderResponse(success,orderID,status,makingAmount,takingAmount,transactionsHashes,tradeIDs,errorMsg)] | 400,401,500,503 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `DELETE /orders` | L2 |  body:array[string] max1000 | — | CancelOrdersResponse(canceled,not_canceled) | 400,401,500,503 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `GET /data/orders` | L2 | id, market, asset_id, next_cursor | next_cursor | OrdersResponse(limit,next_cursor,count,data) | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `GET /data/order/{orderID}` | L2 | orderID* | — | OpenOrder(id,status,owner,maker_address,market,asset_id,side,original_size,size_matched,price,outcome,expiration,order_type,associate_trades,created_at) | 400,401,404,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `DELETE /cancel-all` | L2 | — | — | CancelOrdersResponse(canceled,not_canceled) | 401,500,503 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `DELETE /cancel-market-orders` | L2 |  body:OrderMarketCancelParams(market,asset_id) | — | CancelOrdersResponse(canceled,not_canceled) | 400,401,500,503 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `POST /auth/api-key` | L1 | — | — | ApiKeyResponse(apiKey,secret,passphrase) | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `DELETE /auth/api-key` | L2 | — | — | string | 401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `GET /auth/derive-api-key` | L1 | — | — | ApiKeyResponse(apiKey,secret,passphrase) | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `GET /balance-allowance` | L2 | asset_type*, token_id, signature_type | — | BalanceAllowanceResponse(balance,allowances) | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `PUT /balance-allowance` | L2 | asset_type*, token_id, signature_type | — | object | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `GET /balance-allowance/update` | L2 | asset_type*, token_id, signature_type | — | BalanceAllowanceResponse(balance,allowances) | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `GET /data/trades` | L2 | id, maker_address*, market, asset_id, before, after, next_cursor | next_cursor | TradesResponse(limit,next_cursor,count,data) | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `GET /builder/trades` | public | builder_code*, id, market, asset_id, before, after, next_cursor | next_cursor | BuilderTradesResponse(limit,next_cursor,count,data) | 400,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `POST /v1/heartbeats` | L2 |  body:HeartbeatRequest(heartbeat_id) | — | HeartbeatV1Response(heartbeat_id) | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `GET /notifications` | L2 | signature_type* | — | array[Notification(id,owner,type,payload,timestamp)] | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| `DELETE /notifications` | L2 | ids* | — | string | 400,401,500 | [spec](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |


`CancelOrdersResponse` содержит `canceled[]` и `not_canceled{orderId:reason}`: HTTP200 не означает, что все IDs отменены. Batch submit допускает mixed results; анализировать каждую строку, success/status/errorMsg/orderID вместе. Empty hash/errorMsg при success в spec example требует defensive parsing, а не автоматического принятия success как подтверждённого ордера.

## CLOB public market data

Все операции D, R только single `/book` из [evidence](evidence/manifest.json). Нет CLOB credentials; mutation verbs у `/books`/`prices` ниже означают batch reads, их не вызывали. Pagination отсутствует. Полные вложенные fields и request limits в [CLOB contracts](evidence/clob-contracts.json); [официальный OpenAPI](https://docs.polymarket.com/api-spec/clob-openapi.yaml).

| Метод/путь | Parameters/body | Response | HTTP errors schema |
|---|---|---|---|
| `GET /book` | `token_id*` | `OrderBookSummary` | 400, 404, 500 |
| `GET /books` | `token_ids*` | `array` | 400 |
| `POST /books` | `body schema` | `array` | 400 |
| `GET /price` | `token_id*`, `side*` | `object` | 400, 404, 500 |
| `GET /prices` | `token_ids*`, `sides*` | `object` | 400, 404, 500 |
| `POST /prices` | `body schema` | `object` | 400, 404, 500 |
| `GET /midpoint` | `token_id*` | `object` | 400, 404 |
| `GET /spread` | `token_id*` | `object` | 400, 404 |
| `GET /last-trade-price` | `token_id*` | `object` | 400, 500 |
| `GET /tick-size` | `token_id` | `TickSize` | 400, 404, 500 |
| `GET /fee-rate` | `token_id` | `FeeRate` | 400, 404, 500 |
| `GET /neg-risk` | `token_id` | `NegRisk` | 400, 404, 500 |
| `GET /clob-markets/{condition_id}` | `condition_id*` | `ClobMarketDetails` | 400, 500 |
| `GET /time` | — | `integer` | 400 |

`*` required; asset selection — по market version. `/book` раскрывает bids/asks, timestamp/hash, min_order_size/tick_size/neg_risk. `/clob-markets/{condition_id}` — площадочные параметры, не Gamma market ID. Price/midpoint/last fill не заменяют нужную глубину книги по ADR-0028. Результаты fee/tick reads должны иметь checkedAt и market provenance.

## Session/Relayer endpoints (документированы, management требует допуска)

Base `https://relayer-v2.polymarket.com`, кроме registry на CLOB. Pagination на этих operations не описана. Ошибки: schema endpoint-specific здесь не проверена; validation/scope/expiry/idempotency/Builder permissions и terminal transaction failure нужно изучить перед live.

| Метод/путь | Auth/params | Response | Источник |
|---|---|---|---|
| GET `/v1/account/transactions/params` | owner address, type=WALLET (guide public example без auth) | address, nonce | [Session Keys](https://docs.polymarket.com/trading/session-keys) |
| POST `/v1/session-signers/authorizations` | Builder HMAC + owner Batch EIP712 + Idempotency-Key; walletAddress, sessionSignerAddress, scopes, validUntil, nonce, deadline, signature | operationId/status/transactionHash/transactionId | [Session Keys](https://docs.polymarket.com/trading/session-keys) |
| POST `/v1/session-signers/revocations` | Builder HMAC + owner Batch EIP712 + Idempotency-Key; walletAddress/sessionSignerAddress/nonce/deadline/signature | fenced/operationId/status/transactionId | [Session Keys](https://docs.polymarket.com/trading/session-keys) |
| GET `/v1/account/transactions/{transaction_id}` | id returned operation (guide no auth headers) | transaction_id/transaction_hash/state/error_msg | [Session Keys](https://docs.polymarket.com/trading/session-keys) |
| GET CLOB `/v1/user/session-signers` | Owner CLOB L2 | wallet/signers(address/scopes/valid_until) | [Session Keys](https://docs.polymarket.com/trading/session-keys) |

Owner Batch domain DepositWallet/version1/chain137/verifyingContract=wallet; nonce obtained for owner; deadline at least10s remaining per guide. Idempotency-Key reused only for retry of the same session-management request. Do not execute any of these operations as a research check.

## Схемы безопасных примеров

REST собственных чтений (иллюстрация; placeholders, запрос не выполнен):

```http
GET https://clob.polymarket.com/data/trades?maker_address=<maker_wallet_address>&asset_id=<decimal_asset_id>&after=<unix_seconds>
POLY_ADDRESS: <authorized_signer_address>
POLY_API_KEY: <clob_api_key>
POLY_PASSPHRASE: <passphrase>
POLY_TIMESTAMP: <fresh_unix_seconds>
POLY_SIGNATURE: <computed_l2_hmac>
```

Схема cancellation result (иллюстрация):

```json
{"canceled":["<order_id>"],"not_canceled":{"<other_order_id>":"<reason>"}}
```

Схема user WS (иллюстрация; секреты не выводить в лог):

```json
{"type":"user","auth":{"apiKey":"<key>","secret":"<secret>","passphrase":"<passphrase>"},"markets":["<condition_id>"]}
```

Для paper trading auth/submit/cancel/heartbeat/session management **не нужны**: public market data + simulated executions. Future own-account execution требует отдельной авторизации пользователя, signer custody model и reconciliation. Future copy signal из чужой public history должен быть отдельно от authenticated follower execution и session-scoped visibility. Это карта технических возможностей, не изменение правил продукта.
