# Polymarket → общий контракт адаптера

Проверено 06.10.2026. [Индекс и статусы D/R/U/P/C](README.md). Этот файл связывает источники с [документом 23](../../23_dual_venue_adapter_contract.md), не изменяя его интерфейсы. Ни один boolean capability не повышается до runtime verified по одному прочтению документации.

## Методы и границы ответственности

| Метод документа 23 / модель | Polymarket источник | Статус и обязательная граница |
|---|---|---|
| `listMarkets`, `getMarket` → Market | Gamma events/markets/keyset + market detail | D/R частично. Market version, active/closed/acceptingOrders, outcome mapping и resolution system раздельны |
| `getOrderBook` → OrderBookSnapshot | CLOB `/book`, market WS по выбранному asset ID | D/R частично. Timestamp/hash, bids/asks, tick/minSize, версия market; source age отдельно от HTTP latency |
| `backfillLeaderEvents` → LeaderEvent | Data v2 `/trades`, `/activity` с user/cursor | D/R частично. Адрес кошелька лидера, не owner credential. Транзакция может содержать несколько действий; tx hash сам по себе не fill ID |
| `streamLeaderEvents?` | RTDS activity / public book trades / chain indexing | D/U. Не доказан универсальный адресный поток с replay, completeness и SLA; capability остаётся неподтверждённой |
| `listPositions` → PositionSnapshot | Data v2 `/positions`, onchain position system | D/U. Агрегированная внешняя позиция не наш VirtualLot и не sellable allocation конкретной сессии |
| `capabilities`, `operationalMode` | Версионные docs + market flags, freshness, CLOB restart responses | D/C/U. Data freshness не единый trading-maintenance endpoint; состояние API нельзя выдавать за новые orders enabled |
| `eligibility` → EligibilityDecision | Official geoblock + account policy | D/U. Requesting IP и пользовательский GEO различаются; account restrictions требуют отдельной проверки |
| `permissionSnapshot` | Owner/session registration, scopes, expiry/revoke, relayer tx status | D/P/U. Owner/session/funder provenance; локальный fence сразу, chain revoke отдельно |
| `validateOrder` | CLOB market params/book, balance/allowance, protocol/signature version, fees/GEO | D/U. minSize/tick/fee не универсальные константы, balance cache не банковский ledger |
| `submit` | CLOB `POST /order` / `/orders` + order signature + L2 | D/U. HTTP ack не settlement; timeout → неизвестность, без слепого повторения |
| `findSubmission` | Signed-order identity/hash, own order reads и trades в том же signer context | C/U. Native произвольный clientOrderId и proof-of-absence не подтверждены; совпадение price/size/time недостаточно |
| `getOrder`, `listOrders`, `listFills` | CLOB `/data/order/{id}`, `/data/orders`, `/data/trades` | D/U. Own signer scope, cursor, fills и order updates отдельно; не Data public history substitute |
| `cancel`, `cancelAll` | CLOB DELETE endpoints | D/U. `canceled/not_canceled` по ID; отмена не откатывает исполненную часть |
| `incremental`, `full`, `reconcileSubmission` | User WS + own REST + Data/chain + internal ledger | C/U. Сверять все задействованные signer contexts и fills; не только owner open orders |
| `settlementEvidence` | Trade status/hash + chain receipt + resolution/position operations | D/U. Match, mined, confirmed, resolution, redemption и bridge completion — разные этапы |

Конкретные параметры, pagination и error contracts: [public-data](public-data.md), [trading](trading.md), [funding-realtime](funding-realtime.md). Основания: [market details](https://docs.polymarket.com/market-data/market-details), [manage orders](https://docs.polymarket.com/trading/manage-orders), [realtime order updates](https://docs.polymarket.com/trading/realtime-order-updates), [wallet activity](https://docs.polymarket.com/trading/wallet-activity).

## Сущности и правила нормализации

1. `venue=POLYMARKET` хранится во всех IDs. Gamma event ID объединяет рынки; Gamma market ID, slug, condition ID и asset ID не взаимозаменяемы. `condition` Data и `market` CLOB могут обозначать condition ID, а не Gamma ID.
2. `market.version` выбирает position system. `v1` использует JSON-decoded `clobTokenIds`; `v2` использует `positionIds`. `outcomes` нужно декодировать, проверить длину, соответствие и decimal strings. Нельзя выбирать первую из двух присутствующих ID arrays или предполагать Yes/No порядок по названию. [Migration](https://docs.polymarket.com/migrate/polymarket-v2/api-integrations).
3. Торговый asset ID сохраняется decimal string; `Number` для uint256 недопустим. Condition IDs и outcome index сохраняются raw и сравниваются с выбранной системой; не дополнять/обрезать ID по собственной догадке. Неподтверждённый mapping блокирует submit.
4. Owner, signer, maker/funder/deposit/proxy wallet — разные ссылки. Public leader query обычно относится к custody wallet. L2 API key относится к signer context. Session подписант видит только свою область CLOB, не все действия owner. [Wallet/auth](https://docs.polymarket.com/trading/wallets-auth), [Session](https://docs.polymarket.com/trading/session-keys).
5. Цена, quantity, notional, fee, currency и scale независимы. JSON numbers Data не разрешают binary floating point в ledger; сохранять исходный текст/decimal parse. `_usdc` аналитики — USD field contract, collateral pUSD отдельный asset. Shares и USD объём не складываются.
6. `sourceTime`, `observedAt`, `normalizedAt`, snapshot computedAt/age, actual period boundaries и schema/adapter/fee version обязательны для provenance. Нет поля — unavailable; null не превращается в zero.
7. Public trade rows, maker fills и activity rows требуют разных dedup namespaces. Прежде чем выбрать composite key, доказать устойчивость на overlap/reordering/corrections. Один tx hash может включать несколько fills/redemptions; один order может иметь несколько fills.

## Пригодность для paper и будущего live

| Возможность | Для paper | Для будущего live | Что ещё требуется |
|---|---|---|---|
| Каталог и книги | Документированы, отдельные GET проверены | Public input, не execution approval | Active v1/v2 samples; metadata mapping; book freshness threshold |
| BUY signal sizing | Public fill price/size служат входом | Цена лидера не гарантирует execution копии | Unique action key, actual amount/fee semantics, measured detection lag |
| SELL proportional exit | Position history потенциально даёт контекст | Не выдавать текущее состояние за объём непосредственно перед sell | Pre-sale history reconstruction, external actions, coverage proof |
| Paper fill price | Book в момент принятия решения по ADR-0028 | Реальный fill — источник actual | Depth/slippage/tick/minimum/fees evidence; no lookahead |
| Частичность и отмена | Синтетическая модель по ADR-0026/27 | Authenticated lifecycle отдельно | Recorded fills/cancel race/finality, remaining reservation |
| PnL/rating/ROI/drawdown | Публичные метрики с явной методикой | Собственный copy PnL по ledger | Cashflows, fee completeness, denominator/capital series и metric version |
| Автоматическая подпись | Не нужна | Session beta и allowlist Builder | Written permission/access, revoke/expiry/recovery test, no withdrawal |
| Builder attribution/revenue | Не симулировать реальные earnings | Отдельный builder code/fee evidence | Approved tariff/version, attributed fills, accrual≠paid reconciliation |

Документированный вход не означает готовность paper: критерии документа 23 требуют 72 часа на 3–5 адресах, recorded fault fixtures и доказанную нормализацию. В этом исследовании это **не выполнено**. Денежные операции и live tests не разрешены.

## Отсутствующие доказательства и вопросы площадке

| Вопрос | Зачем нужен / граница |
|---|---|
| Полный источник событий произвольного адреса, replay, стабильный fill/action ID, correction/finality и retention | Public Data/RTDS нельзя объявлять universal leader delivery; multi-fill tx и duplicates |
| Can `findSubmission` prove absence? Native idempotency/client-order ID, order hash и retention lookup | После timeout не создавать duplicate; negative REST result может быть scope/cache issue |
| Owner/session cross-visibility, aggregate account recovery, owner emergency cancel session orders | Owner CLOB контекст не объединяет orders session signers |
| Session management доступен конкретно нашему Builder? Scope/180d/renewal/rotation и поведение resting orders после revoke | Beta docs не доказывают onboarding/runtime возможности проекта |
| Fee calculation/rounding для CTF и Protocol V2, maker/taker/builder overlap, authoritative actual fill fees | min/tick/fees runtime contract; payout register и accrued/paid отдельно |
| Batch cancel 1000 vs 3000, new raw statuses и version rollout | Расхождения docs/spec, не угадывать контракт; подробности в trading |
| Data caching, cursor consistency during writes, late corrections, v1 shutdown exception, stale503 | Срок и successful200 не гарантируют полноту/свежесть |
| Protocol V2 condition/outcome index и смешанные Gamma arrays | Наблюдаемый anomaly требует сверки, не automatic ID repair |
| GEO close-only user/account policy через backend, allowed reducing actions и market scope | Backend-IP не eligibility end user; timezone не location |
| Quotas для проекта/tiers: realtime, per-wallet reconcile, relayer daily limits | Рассчитать scale budget отдельно, не принять rate table за SLA |
| Bridge supported route minimum/current fees/recovery/status retention | Wallet withdrawal не TradingAdapter, executor без права вывода |

Никому не отправлялись письма/заявки. Таблица — список для следующего согласованного контакта, не зарегистрированный партнёрский доступ.

## Словарь

| Термин | Значение в этом справочнике |
|---|---|
| Event / market | Группа рынков / отдельный вопрос с исходами |
| Condition | Идентификатор разрешаемого условия в выбранной position system |
| Outcome / asset | Исход и его торгуемый token/position ID |
| CTF | Прежняя система outcome ERC-1155, сохраняется параллельно с Protocol V2 |
| Protocol V2 | Новая position system с PositionManager/Router/ExchangeV3; не Data v2 |
| CLOB V2 | Поколение exchange/order format; не равно market version v2 |
| Funder / maker | Кошелёк, обеспечивающий средства и позиции ордера |
| Owner / signer | Владелец кошелька / подписант конкретного auth/order контекста |
| L1 / L2 / Builder | Wallet proof / CLOB request HMAC / независимая builder authorisation-attribution |
| Session Key | Ограниченный отдельный signer Deposit Wallet, beta, без withdrawal |
| Fill / match / settlement | Исполнение / сопоставление / окончательное расчётное подтверждение |
| Cancel requested | Запрос отмены остатка, ещё не доказанный final outcome |
| UNKNOWN | Недостаточно доказательств; не rejection, zero balance или безопасный retry |
| Redeem | Получение payout по settled positions, отдельно от продажи и resolution |
| pUSD / USD | Collateral token / единица финансового отображения; USDC backing не permission spend USDC |
| Mark / basis / PnL | Оценка позиции / учётная стоимость / результат с конкретной методикой |
| Attribution / accrual / paid | Привязка к builder / начислено / подтверждённо выплачено |
| Freshness / coverage | Давность данных / полнота периода и действий; HTTP200 не доказывает ни то ни другое |

## Checklist проверки изменений API

- [ ] Перечитать official index, Predictions/SDK changelogs и migration guides; записать checkedAt и URL.
- [ ] Развести Data/CLOB/protocol/SDK/OpenAPI версии; pin dependency по подтверждённой совместимости, не по слову latest.
- [ ] Скачать schema, сохранить SHA256/time, diff methods/paths/auth/required/enums/units/nullability/pagination/errors.
- [ ] Повторить safe GET для Gamma keyset/detail, book, Data first+next page/status; отметить cache Age/TTL и body timestamp.
- [ ] Проверить v1 и v2 market mapping, mixed arrays, unsupported version, non-decimal ID, missing outcome и condition mismatch.
- [ ] Отдельно подтвердить wallet/signer scope и проектный доступ перед приватными тестами; публичный ответ его не доказывает.
- [ ] Проверить PnL component, fees/basis, actual window, shares/USD, omission/null и reconstruction90d.
- [ ] Перечитать fees/GEO/limits/bridge assets; значения могут меняться независимо от package release.
- [ ] На следующем разрешённом spike проверить reconnect/backfill/sequence gap, dedup, late fill, stale snapshots, submit/cancel UNKNOWN.
- [ ] Новый status/error/field несовместимой семантики → явный UNKNOWN/unavailable, отдельный mapping review.
- [ ] Обновить этот справочник и evidence; не объявлять readiness без критериев документа23 и отдельного live GO.
