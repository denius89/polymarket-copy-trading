# Polymarket: публичные данные Gamma и Data API

Проверено 2026-10-06. Область — Predictions; Perps не включён. «Документировано» означает прочитан официальный источник; «проверено публичным запросом» означает один безопасный GET с сохранённым ответом, а не интеграционную проверку или SLA. Торговые запросы, ключи и аккаунты не создавались.

## Версии и миграции

Gamma base URL `https://gamma-api.polymarket.com`, OpenAPI `info.version=1.0.0`. Это версия схемы, а не обозначение торгового протокола. Data base URL `https://data-api.polymarket.com`, новые маршруты `/v2`, OpenAPI `info.version=0.1.0`. Data API v2 и Polymarket Protocol V2 — разные вещи: Data v2 читает данные разных систем позиций. Официальные unified SDK `@polymarket/client` и `polymarket-client` поддерживают Data v2 начиная с `0.10.0`; SDK в этой задаче не запускался.

[Migration](https://docs.polymarket.com/migrate/data-api-v1-to-v2) прямо документирует retirement Data API v1 **24 октября 2026**. Исключение `GET /v1/accounting/snapshot`: не имеет аналога v2 и не входит в retirement. [Changelog](https://docs.polymarket.com/changelog/predictions) фиксирует release Data v2 4 сентября 2026 и перенос price history на Data host. Это подтверждённый документами срок; фактическое выключение ещё не наступило и не проверено.

Data v2 заменяет bare arrays/objects v1 на `{data, pagination?}`, camelCase response fields на snake_case, `market` filter на `condition`, offset на opaque cursor. `/closed-positions` → `/v2/positions?status=CLOSED`; `/traded` → `/v2/user-stats`, где `trades` означает **число различных рынков**, не число исполнений.

## Разграничение сервисов и идентификаторов

Gamma — каталог, event/market metadata, discovery, profile. Data — публичная история кошелька, позиции, индексированные исполнения, PnL, агрегаты, resolution/freshness. Собственные незавершённые заявки, полномочия signer и статус исполнения собственной заявки требуют CLOB/его authenticated user channel; Data не предоставляет доступ к чужим pending orders или гарантированную доставку действий лидера.

Event ID — Gamma ID группы рынков. Market ID — Gamma ID отдельного рынка. Slug — человекочитаемый путь, не торговый идентификатор. Condition ID — onchain ID; `condition` query aliases `condition_id`, `conditionId`. В SDK trading identifier называется assetId, в Data response `token_id`, CLOB REST использует `token_id`. Proxy/funder wallet — адрес владельца позиций для `user`; signer EOA может быть другим. Название профиля не надёжный primary key.

[Market Details](https://docs.polymarket.com/market-data/market-details) документирует: по `market.version` выбирать `v1` → JSON.parse(`clobTokenIds`), `v2` → массив `positionIds`. `outcomes` и `outcomePrices` — JSON-encoded strings; связать label, price, выбранный asset ID **по одному индексу**. Оба набора ID могут присутствовать: наличие поля не выбирает protocol. Неизвестная версия/отсутствующий выбранный ID — unsupported/unavailable. Документированные binary YES/NO индексы 0/1 не позволяют исправлять Data sentinel `outcome_index=999`: это означает enrichment unavailable. В реальном trade GET встречен label `Up`, index999; ответ сохранить и повторно сверить с Gamma, не угадывать направление. Числовые ID хранить строками, не JS Number.

## Общий контракт Data v2

Все routes публичные, auth не требуется. Все параметры допускают snake_case/camelCase; значения перечислений зависят от route. Все responses имеют `data`; miss обычно пустой массив либо `null`, не автоматически ошибка. Нет `offset` query: HTTP400; `pagination.offset` в **ответе** сохраняется и не разрешает offset paging. Cursor signed, opaque, typed per endpoint. Не декодировать/модифицировать, идти до `next_cursor=null`; `has_more` exact.

Trades/activity keyset order `(block_timestamp, sequence_id)`; повторять фильтры на каждой странице, иначе cohort может молча измениться. Internal sequence_id не опубликован как стабильный external fill ID в Trade schema. Boards/holders и часть combo sorts могут повторять/пропускать строки между refresh. Positions требует вместе с cursor прежний user/condition anchor; status/sort/direction pinned. Не обещать все страницы атомарным снимком.

Data REST epoch timestamps — **секунды**; unified TypeScript Trade timestamp — EpochMilliseconds, Python datetime: нормализовать границу адаптера явно. Bare `size`/`volume` — shares; `_usdc` — monetary amount. В документах встречается USDC naming при торговом pUSD collateral: имя поля не является токеном funding, не переименовывать молча. JSON money values number: raw payload сохранять, для вычислений использовать decimal-совместимый парсер. Null/omitted numeric = unavailable, не 0.

Trades user-filter default window 3 года; `start=1` для full history. `end=0`/omitted → now+1day. Condition/event trade shapes игнорируют start/end и дают fixed3year window; bare feed — current+previous month. `taker_only=true` default пропускает maker rows; для истории действий конкретного лидера рассмотреть `false`, сверять покрытие, не считать tx_hash уникальным fill ID: одна транзакция может содержать несколько rows/side/outcomes. Эти правила взяты из OpenAPI; историческая полнота, reorg поведение и ровно-однократность не проверены.

## Ошибки и частота

Data errors `{error,code,retryable,trace_id,parameter?}`, header `x-trace-id`. 400 invalid_request, 404 not_found, 405 method_not_allowed, 429 rate_limited, 500 internal, 503 request_timeout/dependency_unavailable. Для retryable429/503 читать Retry-After seconds; не считать server connection shortage клиентским rate limit. [Rate Limits](https://docs.polymarket.com/api-reference/rate-limits): IP-based Cloudflare queue/delay sliding windows + server per-client/heavy query admission. Численный server per-client budget в OpenAPI не указан.

| Family | Документировано, запросов/10с |
|---|---:|
| Gamma general |4000|
| Gamma `/markets` |300|
| Gamma `/events` |500|
| Gamma listings combined |900|
| Gamma public-search |350|
| Data v2 all |800|
| Data v2 trades |300|
| Data v2 positions(+combos) |200|
| Data v2 activity(+combos) |200|
| Data v2 prices-history |200|
| Data v2 status |100|

Gamma keyset-specific отдельный численный limit rate page не даёт: не переносить `/markets` лимит на keyset как подтверждённый факт. Нагрузочная проверка не выполнялась.

## PnL и позиции

Positions: current_size = текущий остаток; total_size = lifetime acquired/bought WAC denominator. entry_cost_usdc — fee-exclusive remaining basis; entry_fees_usdc — раскрытие компонента; total_cost_usdc = их сумма. unrealized_pnl = current_value-entry_cost_usdc; total_pnl = realized+unrealized. Не вычитать раскрытые fees повторно. percent_pnl — unrealized/fee-exclusive basis, не total_pnl/total_cost. Поле percent_realized_pnl исторически compatibility formula, не realized_pnl/basis. Смотреть schema descriptions.

OPEN включает settled/unredeemed inventory; REDEEMABLE не означает выигрыш (losing tokens также redeemable). REDEEMABLE_LOST/ MERGEABLE являются фильтрами с особенностями row.status. CLOSED — exited. Archived исключены по default; include_archived не допускается с CLOSED; inactive excluded независимо от него. Dust/filters могут исключать небольшие остатки, поэтому нельзя объявлять нулевую onchain balance по отсутствию row.

User PnL cumulative: realized_market_pnl + realized_lp_pnl + realized_combo_pnl = realized_pnl; position_pnl = realized+unrealized; wallet_income = rebates+reward+yield+referral; economic_pnl = position_pnl+wallet_income; settled_pnl = realized+wallet_income. cashflow_net=deposits-withdrawals не прибыль. fees_paid = refunds-charges, disclosure, не ещё одно вычитание. trade_pnl — compatibility series и имеет отдельную формулу. source_fidelity отражает исходную частоту: finer output grid не превращает исторические daily observations в реальные часовые measurements.

Leaderboard finite day/week/month — marked equity change net of flows, включает unrealized marks; `all` — realized-only lifetime ledger. Ранги ties/skip; rank0 в user arm = unranked. Biggest winners — одна winning position, не пользователь; combo rows kind=combo, event_id0, event_slug empty. Не строить event URL без branch kind.

Value включает одиночные holdings MTM и unresolved combos at cost basis; condition filter исключает portfolio combo term. Portfolio value не withdrawable collateral и не CLOB available balance.

## История цены и freshness

Data prices-history: token_id плюс ровно один selector start[/end], interval или as_of. start inclusive/end exclusive; explicit window ≤15days, нулевые bounds недопустимы. interval=max/all даёт whole life at coarse resolution; finer resolutions имеют retention floors:60sec≥7days,300sec≥60days,1800sec≥90days;10800/43200sec permanent back to2022-11-18. Explicit bucket_seconds обслуживается без молчаливой подмены и может дать empty; omitted выбирает подходящий tier. terminal real tick не обязан лежать на bucket boundary; settled series добавляет payout point resolution_seconds0 только на final page, payout может быть fractional. Это sampled chart data, не ticks for execution simulator.

`/v2/status`: computed_at и age_seconds snapshot freshness отдельно от serving.lag_seconds и ingestion cursor lag. Total ingestion stall может выглядеть зелёным относительно своего max_synced_block: обязательно смотреть serving и возраст snapshot. HTTP200 не доказывает свежую торговую историю; probe trades получил `Age:52`, `Cache-Control:public,max-age=300`. Endpoint status measured instant не SLA всех клиентов.

## Public GET evidence

Сохранены raw public bodies, безопасные headers (Set-Cookie удалён), manifest с URL/status/serverDate/SHA256 в [evidence](evidence/manifest.json). HTTP200 status, trade page1/page2, Gamma legacy markets, Gamma keyset, v1-selected CLOB book. HTTP400 unsupported Data offset. Gamma legacy markets дополнительно вернул Deprecation:true, Sunset:2026-05-01, Warning use /markets/keyset: новый discovery должен использовать keyset. Keyset response `{markets,next_cursor}`, input `after_cursor`; Data response `{data,pagination}`, input `cursor`: не смешивать.

В проверенном CLOB book bids шли ascending, asks descending. Best price вычислять по значению (max bid/min ask), не предполагать first element; это рекомендация нормализации по одному наблюдению, не заявление о глобальном ordering. Получение book не доказывает исполнение по displayed size.

## Для paper/copy MVP и вопросы

Paper: каталог и outcome mapping Gamma, стакан CLOB, факты Data для истории и сверки, freshness-aware ingestion. Source activity не исполнимая заявка; собственный ledger simulation и наблюдаемая price/liquidity должны быть раздельны. Будущий copy: detect delayed wallet executions через Data polling с overlap, фильтры maker/taker, повторная проверка mappings и risk rules. Гарантированный low-latency feed чужих исполнений не документирован этим набором API. Authenticated собственный CLOB user stream не универсальный leader stream; наличие public wallet не даёт delegation/subaccounts.

Уточнить: SLA индексатора и cache для user-filter feed; внешний стабильный fill/event ID для дедупликации; история/реорганизации/коррекции; семантика pUSD и USDC-labelled accounting fields; native V2 migration history mapping; доступность и условия partner delegated accounts и leader stream. Не приписывать partner-only возможности публичному Data API.


## Матрица Data endpoints

Все строки D — документировано, public GET без auth; R только для перечисленных probes. Имена параметров, required/default/bounds и HTTP response codes ниже взяты как функциональные факты текущей спецификации. Полные nested response fields и ограничения — в [Data contracts](evidence/data-contracts.json), официальный источник — [OpenAPI](https://data-api.polymarket.com/v2/openapi.json). Неподтверждённые error branches runtime не проверялись.

| Метод/путь | Параметры / pagination | Ответ200 | Документированные ошибки | Источник |
|---|---|---|---|---|
| `GET /v2/activity` | `user`, `limit`, `cursor`, `type`, `condition`, `event_id`, `side`, `start`, `end`, `sort_by`, `sort_direction`, `exclude_deposits_withdrawals`; paging: cursor | `ActivityPage` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1activity/get) |
| `GET /v2/approvals` | `user`; paging: нет | `Envelope_Approvals` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1approvals/get) |
| `GET /v2/biggest-winners` | `time_period`, `category`, `limit`, `cursor`; paging: cursor | `BiggestWinnersPage` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1biggest-winners/get) |
| `GET /v2/builders/leaderboard` | `time_period`, `limit`, `cursor`; paging: cursor | `BuildersLeaderboardPage` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1builders~1leaderboard/get) |
| `GET /v2/builders/volume` | `interval`, `limit`; paging: нет | `Envelope_Vec_BuilderVolumePoint` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1builders~1volume/get) |
| `GET /v2/holders` | `condition`, `limit`, `cursor`, `min_balance`, `include_pnl`; paging: cursor | `HoldersPage` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1holders/get) |
| `GET /v2/leaderboard` | `time_period`, `category`, `sort_by`, `user`, `limit`, `cursor`; paging: cursor | `LeaderboardResponse` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1leaderboard/get) |
| `GET /v2/live-volume` | `event_id`; paging: нет | `Envelope_LiveVolume` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1live-volume/get) |
| `GET /v2/oi` | `condition`; paging: нет | `Envelope_Vec_OpenInterest` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1oi/get) |
| `GET /v2/positions` | `user`, `condition`, `limit`, `cursor`, `status`, `event_id`, `title`, `filter_type`, `filter_amount`, `include_archived`, `sort_by`, `start`, `end`, `sort_direction`; paging: cursor | `PositionsPage` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1positions/get) |
| `GET /v2/prices-history` | `token_id`, `start`, `end`, `interval`, `bucket_seconds`, `as_of`, `limit`, `cursor`; paging: cursor | `PricesHistoryPage` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1prices-history/get) |
| `GET /v2/resolutions` | `question_id`, `condition`, `event_id`; paging: нет | `Envelope_Vec_Resolution` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1resolutions/get) |
| `GET /v2/status` | ; paging: нет | `Envelope_ServiceStatus` | 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1status/get) |
| `GET /v2/trades` | `user`, `limit`, `cursor`, `taker_only`, `filter_type`, `filter_amount`, `start`, `end`, `condition`, `event_id`, `side`; paging: cursor | `TradesPage` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1trades/get) |
| `GET /v2/user-pnl` | `user`, `interval`, `fidelity`; paging: нет | `Envelope_UserPnlSeries` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1user-pnl/get) |
| `GET /v2/user-stats` | `user`; paging: нет | `Envelope_Option_UserStats` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1user-stats/get) |
| `GET /v2/user-volume` | `user`, `start`, `end`; paging: нет | `Envelope_UserVolume` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1user-volume/get) |
| `GET /v2/value` | `user`, `condition`; paging: нет | `Envelope_PortfolioValue` | 400, 429, 500, 503 | [spec](https://data-api.polymarket.com/v2/openapi.json#/paths/~1v2~1value/get) |

`*` — required в схеме; некоторые anchors обязательны по сочетанию параметров. Во всех Data responses payload обёрнут в `data`; для lists добавляется `pagination`, terminal `next_cursor=null`. Gamma keyset использует `markets`/`events` и `next_cursor`, не Data envelope. На обычных Gamma endpoints может быть offset.

### Ограничения параметров по route

| Route | Функциональные constraints |
|---|---|
| `/v2/activity` | `user` type=['string', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=1000; `cursor` type=['string', 'null']; `type` type=['string', 'null']; `condition` type=['string', 'null']; `event_id` type=['string', 'null']; `side` type=['string', 'null']; `start` type=['integer', 'null']; `end` type=['integer', 'null']; `sort_by` type=['string', 'null']; `sort_direction` type=['string', 'null']; `exclude_deposits_withdrawals` type=['boolean', 'null'] |
| `/v2/approvals` | `user` type=['string', 'null'] |
| `/v2/biggest-winners` | `time_period` type=['string', 'null']; `category` type=['string', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=1000; `cursor` type=['string', 'null'] |
| `/v2/builders/leaderboard` | `time_period` type=['string', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=1000; `cursor` type=['string', 'null'] |
| `/v2/builders/volume` | `interval` type=['string', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=90 |
| `/v2/holders` | `condition` type=['string', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=1000; `cursor` type=['string', 'null']; `min_balance` type=['number', 'null']; `include_pnl` type=['boolean', 'null'] |
| `/v2/leaderboard` | `time_period` type=['string', 'null']; `category` type=['string', 'null']; `sort_by` type=['string', 'null']; `user` type=['string', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=1000; `cursor` type=['string', 'null'] |
| `/v2/live-volume` | `event_id` type=['string', 'null'] |
| `/v2/oi` | `condition` type=['string', 'null'] |
| `/v2/positions` | `user` type=['string', 'null']; `condition` type=['string', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=1000; `cursor` type=['string', 'null']; `status` type=['string', 'null']; `event_id` type=['string', 'null']; `title` type=['string', 'null']; `filter_type` type=['string', 'null']; `filter_amount` type=['number', 'null']; `include_archived` type=['boolean', 'null']; `sort_by` type=['string', 'null']; `start` type=['integer', 'null']; `end` type=['integer', 'null']; `sort_direction` type=['string', 'null'] |
| `/v2/prices-history` | `token_id` type=['string', 'null']; `start` type=['integer', 'null']; `end` type=['integer', 'null']; `interval` type=['string', 'null']; `bucket_seconds` type=['integer', 'null']; `as_of` type=['integer', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=10000; `cursor` type=['string', 'null'] |
| `/v2/resolutions` | `question_id` type=['string', 'null']; `condition` type=['string', 'null']; `event_id` type=['string', 'null'] |
| `/v2/status` | — |
| `/v2/trades` | `user` type=['string', 'null']; `limit` type=['integer', 'null'], minimum=0, maximum=1000; `cursor` type=['string', 'null']; `taker_only` type=['boolean', 'null']; `filter_type` type=['string', 'null']; `filter_amount` type=['number', 'null']; `start` type=['integer', 'null']; `end` type=['integer', 'null']; `condition` type=['string', 'null']; `event_id` type=['string', 'null']; `side` type=['string', 'null'] |
| `/v2/user-pnl` | `user` type=['string', 'null']; `interval` type=['string', 'null']; `fidelity` type=['string', 'null'] |
| `/v2/user-stats` | `user` type=['string', 'null'] |
| `/v2/user-volume` | `user` type=['string', 'null']; `start` type=['integer', 'null']; `end` type=['integer', 'null'] |
| `/v2/value` | `user` type=['string', 'null']; `condition` type=['string', 'null'] |

Response payload schemas и nullable/required fields полностью раскрыты по `$ref` в приложенном JSON. Эта таблица не меняет defaults и не создаёт дополнительные filters.

## Матрица Gamma endpoints

Все строки D — документировано, public GET без auth; R только для перечисленных probes. Имена параметров, required/default/bounds и HTTP response codes ниже взяты как функциональные факты текущей спецификации. Полные nested response fields и ограничения — в [Gamma contracts](evidence/gamma-contracts.json), официальный источник — [OpenAPI](https://docs.polymarket.com/api-spec/gamma-openapi.yaml). Неподтверждённые error branches runtime не проверялись.

| Метод/путь | Параметры / pagination | Ответ200 | Документированные ошибки | Источник |
|---|---|---|---|---|
| `GET /tags` | `limit`, `offset`, `order`, `ascending`, `include_template`, `is_carousel`; paging: limit/offset | `array[Tag]` | не перечислены | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1tags/get) |
| `GET /events` | `limit`, `offset`, `order`, `ascending`, `id`, `tag_id`, `exclude_tag_id`, `slug`, `tag_slug`, `related_tags`, `active`, `archived`, `featured`, `cyom`, `include_chat`, `include_template`, `recurrence`, `closed`, `liquidity_min`, `liquidity_max`, `volume_min`, `volume_max`, `start_date_min`, `start_date_max`, `end_date_min`, `end_date_max`; paging: limit/offset | `array[Event]` | не перечислены | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1events/get) |
| `GET /events/{id}` | `id*`, `include_chat`, `include_template`; paging: нет | `Event` | 404 | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1events~1{id}/get) |
| `GET /markets` | `limit`, `offset`, `order`, `ascending`, `id`, `slug`, `clob_token_ids`, `condition_ids`, `liquidity_num_min`, `liquidity_num_max`, `volume_num_min`, `volume_num_max`, `start_date_min`, `start_date_max`, `end_date_min`, `end_date_max`, `tag_id`, `related_tags`, `cyom`, `uma_resolution_status`, `game_id`, `sports_market_types`, `rewards_min_size`, `question_ids`, `include_tag`, `closed`; paging: limit/offset | `array[Market]` | не перечислены | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1markets/get) |
| `GET /markets/{id}` | `id*`, `include_tag`; paging: нет | `Market` | 404 | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1markets~1{id}/get) |
| `GET /markets/{id}/tags` | `id*`; paging: нет | `array[Tag]` | 404 | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1markets~1{id}~1tags/get) |
| `GET /markets/slug/{slug}` | `slug*`, `include_tag`; paging: нет | `Market` | 404 | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1markets~1slug~1{slug}/get) |
| `GET /markets/keyset` | `limit`, `order`, `ascending`, `after_cursor`, `offset`, `id`, `slug`, `closed`, `decimalized`, `clob_token_ids`, `condition_ids`, `question_ids`, `liquidity_num_min`, `liquidity_num_max`, `volume_num_min`, `volume_num_max`, `start_date_min`, `start_date_max`, `end_date_min`, `end_date_max`, `tag_id`, `related_tags`, `tag_match`, `cyom`, `rfq_enabled`, `uma_resolution_status`, `game_id`, `sports_market_types`, `include_tag`, `locale`; paging: after_cursor → next_cursor | `KeysetMarketsResponse` | 422, 500, 503 | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1markets~1keyset/get) |
| `GET /events/keyset` | `limit`, `order`, `ascending`, `after_cursor`, `offset`, `id`, `slug`, `closed`, `live`, `featured`, `cyom`, `title_search`, `liquidity_min`, `liquidity_max`, `volume_min`, `volume_max`, `start_date_min`, `start_date_max`, `end_date_min`, `end_date_max`, `start_time_min`, `start_time_max`, `tag_id`, `tag_slug`, `exclude_tag_id`, `related_tags`, `tag_match`, `series_id`, `game_id`, `event_date`, `event_week`, `featured_order`, `recurrence`, `created_by`, `parent_event_id`, `include_children`, `partner_slug`, `include_chat`, `include_template`, `include_best_lines`, `locale`; paging: after_cursor → next_cursor | `KeysetEventsResponse` | 422, 500, 503 | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1events~1keyset/get) |
| `GET /public-profile` | `address*`; paging: нет | `PublicProfileResponse` | 400, 404 | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1public-profile/get) |
| `GET /public-search` | `q*`, `cache`, `events_status`, `limit_per_type`, `page`, `events_tag`, `keep_closed_markets`, `sort`, `ascending`, `search_tags`, `search_profiles`, `recurrence`, `exclude_tag_id`, `optimized`; paging: нет | `Search` | не перечислены | [spec](https://docs.polymarket.com/api-spec/gamma-openapi.yaml#/paths/~1public-search/get) |

`*` — required в схеме; некоторые anchors обязательны по сочетанию параметров. Во всех Data responses payload обёрнут в `data`; для lists добавляется `pagination`, terminal `next_cursor=null`. Gamma keyset использует `markets`/`events` и `next_cursor`, не Data envelope. На обычных Gamma endpoints может быть offset.

### Ограничения параметров по route

| Route | Функциональные constraints |
|---|---|
| `/tags` | `limit` type=integer, minimum=0; `offset` type=integer, minimum=0; `order` type=string; `ascending` type=boolean; `include_template` type=boolean; `is_carousel` type=boolean |
| `/events` | `limit` type=integer, minimum=0; `offset` type=integer, minimum=0; `order` type=string; `ascending` type=boolean; `id` type=array; `tag_id` type=integer; `exclude_tag_id` type=array; `slug` type=array; `tag_slug` type=string; `related_tags` type=boolean; `active` type=boolean; `archived` type=boolean; `featured` type=boolean; `cyom` type=boolean; `include_chat` type=boolean; `include_template` type=boolean; `recurrence` type=string; `closed` type=boolean; `liquidity_min` type=number; `liquidity_max` type=number; `volume_min` type=number; `volume_max` type=number; `start_date_min` type=string; `start_date_max` type=string; `end_date_min` type=string; `end_date_max` type=string |
| `/events/{id}` | `id` required, type=integer; `include_chat` type=boolean; `include_template` type=boolean |
| `/markets` | `limit` type=integer, minimum=0; `offset` type=integer, minimum=0; `order` type=string; `ascending` type=boolean; `id` type=array; `slug` type=array; `clob_token_ids` type=array; `condition_ids` type=array; `liquidity_num_min` type=number; `liquidity_num_max` type=number; `volume_num_min` type=number; `volume_num_max` type=number; `start_date_min` type=string; `start_date_max` type=string; `end_date_min` type=string; `end_date_max` type=string; `tag_id` type=integer; `related_tags` type=boolean; `cyom` type=boolean; `uma_resolution_status` type=string; `game_id` type=string; `sports_market_types` type=array; `rewards_min_size` type=number; `question_ids` type=array; `include_tag` type=boolean; `closed` type=boolean, default=False |
| `/markets/{id}` | `id` required, type=integer; `include_tag` type=boolean |
| `/markets/{id}/tags` | `id` required, type=integer |
| `/markets/slug/{slug}` | `slug` required, type=string; `include_tag` type=boolean |
| `/markets/keyset` | `limit` type=integer, default=20, minimum=1, maximum=100; `order` type=string; `ascending` type=boolean, default=True; `after_cursor` type=string; `offset` type=integer; `id` type=array; `slug` type=array; `closed` type=boolean, default=False; `decimalized` type=boolean; `clob_token_ids` type=array; `condition_ids` type=array; `question_ids` type=array; `liquidity_num_min` type=number; `liquidity_num_max` type=number; `volume_num_min` type=number; `volume_num_max` type=number; `start_date_min` type=string; `start_date_max` type=string; `end_date_min` type=string; `end_date_max` type=string; `tag_id` type=array; `related_tags` type=boolean; `tag_match` type=string; `cyom` type=boolean; `rfq_enabled` type=boolean; `uma_resolution_status` type=string; `game_id` type=string; `sports_market_types` type=array; `include_tag` type=boolean; `locale` type=string |
| `/events/keyset` | `limit` type=integer, default=20, minimum=1, maximum=100; `order` type=string; `ascending` type=boolean, default=True; `after_cursor` type=string; `offset` type=integer; `id` type=array; `slug` type=array; `closed` type=boolean; `live` type=boolean; `featured` type=boolean; `cyom` type=boolean; `title_search` type=string; `liquidity_min` type=number; `liquidity_max` type=number; `volume_min` type=number; `volume_max` type=number; `start_date_min` type=string; `start_date_max` type=string; `end_date_min` type=string; `end_date_max` type=string; `start_time_min` type=string; `start_time_max` type=string; `tag_id` type=array; `tag_slug` type=string; `exclude_tag_id` type=array; `related_tags` type=boolean; `tag_match` type=string; `series_id` type=array; `game_id` type=array; `event_date` type=string; `event_week` type=integer; `featured_order` type=boolean; `recurrence` type=string; `created_by` type=array; `parent_event_id` type=integer; `include_children` type=boolean; `partner_slug` type=string; `include_chat` type=boolean; `include_template` type=boolean; `include_best_lines` type=boolean; `locale` type=string |
| `/public-profile` | `address` required, type=string, pattern=^0x[a-fA-F0-9]{40}$ |
| `/public-search` | `q` required, type=string; `cache` type=boolean; `events_status` type=string; `limit_per_type` type=integer; `page` type=integer; `events_tag` type=array; `keep_closed_markets` type=integer; `sort` type=string; `ascending` type=boolean; `search_tags` type=boolean; `search_profiles` type=boolean; `recurrence` type=string; `exclude_tag_id` type=array; `optimized` type=boolean |

Response payload schemas и nullable/required fields полностью раскрыты по `$ref` в приложенном JSON. Эта таблица не меняет defaults и не создаёт дополнительные filters.
