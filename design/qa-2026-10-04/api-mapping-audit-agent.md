# Read-only аудит соответствия UI официальным API — 04.10.2026

Статус: предложения, без реализации. Проверены актуальный PROJECT_STATE/ROADMAP, план55, ADR0013, API-планы14/21/22/23, отчёты63–80 и JSON fixtures. Макеты Figma в этом подпроходе напрямую не инспектировались; UI mapping основан на актуальных локальных отчётах и данных. Код, существующие документы, макеты и synced sources не менялись. Создан только этот новый отчёт.

## Доказательность

**D — documented**: актуальная официальная страница прочитана 04.10 через web. Это контракт, не проверка доступа нашего проекта. **R — runtime verified**: новый реальный ответ конкретного endpoint в этом цикле. **C — computed**: наше вычисление/ledger. **U — unconfirmed**: семантика, доступ, покрытие или SLA не доказаны. **P — partner access**: нужен фактически предоставленный доступ/capabilities. В этом цикле **R нет**: приватные API и сделки не вызывались. Старые публичные GET из документа14 — историческое свидетельство 24.09, не fresh verification. Их времена ответа не измеряют время обнаружения сделки.

Официальные индексы [Polymarket](https://docs.polymarket.com/llms.txt) и [Limitless](https://docs.limitless.exchange/llms.txt) использованы для поиска нынешних страниц. Прямое чтение raw OpenAPI через web не удалось; альтернативный read-only доступ из локального runtime также не имел DNS. Схемы читаются через опубликованные endpoint pages, но полный машинный snapshot OpenAPI не заявляется. Ошибки извлечения некоторых страниц устранялись переходом по ссылкам из официальной навигации. Дата crawl не трактуется как дата выпуска API.

## Самые существенные выводы

1. Унифицированный UI возможен поверх адаптеров, но период, единицы, PnL и доступ обязаны хранить venue-specific provenance. Площадочные показатели не эквивалентны нашему rating, closed-trade win rate, ROI и просадке.
2. Data API v1 Polymarket объявлен к отключению **24.10.2026**. План55 содержит пустое место вместо даты; предложение исправить в отдельном согласованном цикле. Для новой интеграции начать с v2. Исключение accounting snapshot остаётся на v1. [Migration](https://docs.polymarket.com/migrate/data-api-v1-to-v2).
3. Четыре кнопки 24h/7d/30d/90d не означают четыре готовых одинаковых API периода. У обеих площадок прямого общего 90d контракта просмотренные PnL endpoints не имеют. Восстановление из более длинной истории требует проверки покрытия/методики; пока недоступный период должен быть объяснён.
4. Limitless partner WebSocket не включает delegated subaccounts. Общая надпись «в реальном времени» для delegated исполнения и чужих лидеров требует другой доказательной базы. [Order events](https://docs.limitless.exchange/developers/websocket/order-events).
5. Polymarket Session Keys Beta ограничены Deposit Wallet и имеют жёсткий текущий срок 180 дней. Owner не читает ордера session key через свой CLOB контекст. Поэтому account reconciliation нельзя строить только на owner credential. [Session Keys](https://docs.polymarket.com/trading/session-keys).
6. Текущая официальная таблица Polymarket относит Somalia, Thailand, Poland к close-only на frontend и API. Предварительный GEO-shortlist не означает доступ к новым покупкам. [GEO](https://docs.polymarket.com/api-reference/geoblock).
7. Демо-арифметика и корректные переходы не доказывают API-ready контракт. Синтетический адрес, график, fee policy и USD cents должны оставаться обозначенными как demo.

## Матрица UI → источник → статус → предложение

### Каталог, профиль, показатели и графики

| UI поле/действие | Polymarket | Limitless | Классификация и корректировка |
|---|---|---|---|
| Имя, avatar, адрес, площадка | Gamma public profile; Data API rows | public profile/history/positions metadata | D/U. Address вместе с venue — identity; имя не уникально. Не гарантировать наличие avatar/username. Поиск каталога по нашим индексированным адресам и Gamma search — разные возможности. |
| Темы трейдера | Gamma market/event tags + исполненные /v2/trades или /v2/activity | market navigation/category + public history | C на D. Версионированная taxonomy обеих площадок; считать distinct executed markets за период. Не выводить специализацию из открытого ордера/одного рынка/прибыльности. |
| Публичный PnL | /v2/leaderboard — realized PnL, combos included; /v2/user-pnl имеет разные PnL компоненты | /portfolio/{account}/realized-pnl — realized series | D/U. Выбрать одно название и состав; не смешивать realized, economic и unrealized. «Публичный реализованный PnL» до гармонизации; personal copy PnL отдельно. |
| Дневной/недельный/месячный rank | /v2/leaderboard time_period day/week/month/all | documented unrealized leaderboard по одному market | D и C/U. Polymarket rank — площадочный board, не наш score. Limitless market ROI rank не глобальный trader rank. Доступность глобального realized board в просмотренной REST docs не подтверждена. |
| Rating /100, copied success, рекомендуемый бюджет | Готового copy score не подтверждено | Готового copy score не подтверждено | C/U. Пока `—`; версия модели, минимальное покрытие и калибровка нужны отдельно. Minimum executable order не равен рекомендуемому бюджету стратегии. |
| ROI трейдера за период | Готового cashflow-adjusted wallet ROI в прочитанном контракте не подтверждено | market unrealized ROI имеет scope MARKET | C/U. PnL/turnover не ROI. Требуется капитал/потоки/методика. Market ROI не переносить в портфель. |
| «Сделки» | /v2/user-stats `trades` = distinct markets; /v2/user-volume `trade_count` = fills | public history records; accuracy.total = resolved markets | D/C. Для «Закрытые сделки» нужна своя единица лота/round trip; не присваивать поле с похожим названием. Развести рынки, исполнения и закрытия. |
| Доля прибыльных закрытий | Нет готового одинакового поля | /user-stats/accuracy/{account} won/lost/total/since | C. Accuracy — выигранные разрешённые рынки, не прибыль после комиссии/частичного выхода. Назвать отдельно или вычислять собственный показатель по ledger. |
| Максимальная просадка | PnL series может дать входные наблюдения, не готовый wallet drawdown | realized timeline не account equity | C/U. Нельзя вычислять % просадку от положительного cumulative PnL без капитальной базы. `—` из отчёта78 правильно; нужен полный ряд, потоки, частота и mark source. |
| График PnL | /v2/user-pnl, cumulative points | /portfolio/{account}/realized-pnl, cumulative projection | D/C. Выбрать один PnL component; cumulative points не суммировать. Gaps/null сохранять, без красивой интерполяции отсутствующей истории. |
| 24h /7d /30d /90d | interval 1d/1w/1m/max/all/12h/6h, fidelity 1h/3h/12h/18h/1d | prose timeframe 1d/1w/1m/all; schema enum omits all | D/U. Прямой90d отсутствует. «Month» не обещать rolling30d без проверки границ; `all` Limitless имеет doc/schema contradiction. Свой90d — отдельный reconstruction contract. |
| Объём торгов $ | /v2/user-volume volume_usdc; volume — shares | /portfolio/{account}/traded-volume, published schema generic object | D/U/C. Не превращать shares в $. Limitless units/window нужно runtime подтвердить. Общий UI period должен учитывать UTC округление Polymarket user-volume. |
| Доступная история/as-of | Timestamp/source_fidelity + /v2/status | windowStart, five-minute buckets, projection asOf где применимо | D/C. Сохранять actual start/end/freshness отдельно от requested period. «90д» при coverage7d — не полноценное сравнение90d. |

Источники: [Polymarket profile stats](https://docs.polymarket.com/api-reference/wallet/get-a-users-profile-stats), [PnL series](https://docs.polymarket.com/api-reference/wallet/get-a-users-pnl-series), [wallet activity/volume](https://docs.polymarket.com/trading/wallet-activity), [leaderboard](https://docs.polymarket.com/api-reference/boards/get-the-trader-leaderboard), [Limitless realized PnL](https://docs.limitless.exchange/api-reference/public-portfolio/realized-pnl), [accuracy](https://docs.limitless.exchange/api-reference/public-portfolio/accuracy), [history](https://docs.limitless.exchange/api-reference/public-portfolio/history), [volume](https://docs.limitless.exchange/api-reference/public-portfolio/traded-volume), [market unrealized leaderboard](https://docs.limitless.exchange/api-reference/leaderboard/unrealized-pnl-market).

PnL Limitless — best-effort по закрытым пятиминутным buckets; all читает постоянную hourly историю без category breakdown. Его categories ранжированы по realized PnL, а topic badges проекта — по количеству distinct executed markets. Это разные оси: нельзя взять готовые categories как темы торговли без изменения определения. Accuracy: null означает отсутствие данных; feature-flag off возвращает404, успешный CDN ответ может кэшироваться15s. Обе ситуации требуют самостоятельного UI состояния. Публичная history Limitless имеет cursor/nextCursor, неактивный неизвестный адрес404 и malformed400; cursor привязан к тому же market filter. В v2 Polymarket nullable денежные поля — unknown, не ноль.

### Ордер, позиция, ручное управление

| UI поле/действие | Endpoint/источник | Классификация и корректировка |
|---|---|---|
| Цена заявки, первоначальный/исполненный/неисполненный объём | PM GET /data/order/{id}, /data/orders; LL POST /orders/status/batch, GET /markets/{slug}/user-orders | D/P/U. Результат исполнения и исход рынка — разные поля. Не вычислять remaining из размера позиции. |
| Partial fill | PM size_matched и account trades; LL order statuses, makerMatches, orderEvent | D/C. Локальные состояния нормализуются; каждое исполнение дедуплицируется отдельно. `orderId` недостаточен как единственный fill key. |
| Отмена остатка | PM DELETE /order (canceled/not_canceled); LL combined cancel и DELETE /orders/{id} | D/P. Сначала pending, затем проверенный результат. Запрос/HTTP200 не закрывает все риски. Filled lots остаются. |
| Изменить цену/объём | PM доказан cancel + new signed order, atomic edit не подтвержден; LL POST /orders/cancel-replace | D/C/P. LL cancel/replacement независимы. Показывать «остаток отменён, новая заявка не создана» и replacement UNKNOWN; не одно success toast. |
| UNKNOWN / повтор отправки | Order lookup, batch status, trades/backfill; internal submission ledger | C/U. Timeout не rejected; blind retry запрещён. Native clientOrderId capability проверять по venue; совпадение параметров не доказательство отсутствия первой заявки. |
| Статус исполнения и settlement | PM user trade events MATCHED/MINED/CONFIRMED/RETRYING/FAILED; LL OME + SETTLEMENT MATCHED/MINED/FAILED | D/C. Не переносить термин MINED одинаково: PM MINED ещё не finality. Политика finality venue-specific. |
| Позиция cost/value/PnL/outcome | PM /v2/positions status lifecycle; LL /portfolio/positions или public counterpart | D/C. Остаток долей, оценка рынка и доступный для продажи lot — разные величины. API RESOLVED LL не доказывает redeemable settlement. |
| «Передать себе», копирование/ручная позиция | Наш VirtualLot/policy ledger + venue positions/fills | C. Нет API ownership switch «from leader to user»: меняется наша политика, токены остаются на счёте. Передача требует fencing pending signal/order и quantity lock. |
| «Закрыть позицию» | Новый sell order соответствующего venue, market liquidity + final fills | D/P/C. Это попытка продажи; не гарантированный выход по mark. Partial close/failed/unknown остаются состояниями. |
| Stop/Pause/Disconnect | Наш policy state + площадочные cancel/revoke | C/P. Отдельно: остановка новых сигналов, открытые orders, открытые positions, отозванный signing. Stop не liquidation. |

Источники: [PM Manage orders](https://docs.polymarket.com/trading/manage-orders), [PM realtime own orders](https://docs.polymarket.com/trading/realtime-order-updates), [LL cancel-replace](https://docs.limitless.exchange/api-reference/trading/cancel-replace), [LL positions](https://docs.limitless.exchange/api-reference/portfolio/positions), [LL order events](https://docs.limitless.exchange/developers/websocket/order-events). Cancel-replace LL допускает STOP_ON_FAILURE/ALLOW_FAILURE; для нашего safe flow предлагать первый режим. Operation-level onBehalfOf применяется к обеим операциям; x-on-behalf-of этому endpoint не подходит. Нужны trading+delegated_signing для partner flow. Сам endpoint не доказывает, что проекту разрешён live.

Отчёт75 уже корректно показывает «Отмена проверяется» и последнее известное состояние. Но он явно оформляет только этап отмены; формы новой замещающей заявки нет. Полное действие «изменить» пока нельзя объявлять завершённым продуктовым маршрутом. Отчёты74/79 улучшают иерархию, а не создают persistent state/API semantics.

### Средства, валюты, сеть и вывод

| UI поле/действие | Endpoint/источник | Классификация и корректировка |
|---|---|---|
| Демо баланс/available/reserved | Наш paper ledger | C. USD cents допустимы только как формат демо. |
| Реальная стоимость счёта | Collateral onchain balance + позиционные оценки; PM /v2/value — marked portfolio value, LL positions.marketValue | C на D/U. Не считать /value готовым cash balance. Требуется подтвердить, включает ли конкретный endpoint cash, positions, rewards; исключить двойной учёт. |
| Доступно для торговли | Verified balance/allowance + venue live orders + internal reservations | C/U. Approval — permission cap, не деньги. Не вычитать резерв повторно, если endpoint уже net available. |
| В резерве | Live remaining order amounts/locked shares + fee estimate + наш submission/UNKNOWN ledger | C/U. BUY money reservation и SELL token reservation разные единицы. После cancel-request сохранять до сверки. |
| Можно вывести | Settled collateral, restrictions, route/quote, owner permissions | C/U/P. Available-to-trade не withdrawable; неподтверждённое поле `—`. Pending settlement/reward/bridge не «деньги готовы». |
| Сумма в шапке | Выбранный account/context | C. Отчёт77 убрал label по решению основателя: сохранить accessible name/demo context в деталях. Не складывать demo, PM и LL. |
| Polymarket asset/network | pUSD ERC20 Polygon, backed by USDC | D. Collateral token и displayed USD valuation разные поля. Старое USDC.e предположение пересмотреть. Не обещать USDT торговый collateral. |
| Limitless asset/network | USDC Base, market collateralToken metadata | D/U. В каждом snapshot token address/chain/decimals, не только символ. |
| Пополнение/вывод Polymarket | Bridge supported assets, quote, addresses, status + owner flow | D/U/P. Превью fees/amount/minimum/route и pending bridge. Список chains/tokens читать актуально. |
| Вывод LL managed wallet | POST /portfolio/withdraw, withdrawal-address allowlist | D/P. Отдельный token scope withdrawal. Destination — partner/approved treasury semantics, не доказанный arbitrary user withdrawal recovery. Trading worker без этого scope. |
| Выигрыш/claim | Redeem/settlement evidence | D/P/C. Resolved ≠ settled ≠ redeemed ≠ withdrawable. В UI нужны эти раздельные состояния. |

Источники: [pUSD](https://docs.polymarket.com/concepts/pusd), [PM supported assets](https://docs.polymarket.com/trading/bridge/supported-assets), [bridge quote](https://docs.polymarket.com/trading/bridge/quote), [LL withdraw](https://docs.limitless.exchange/api-reference/portfolio/withdraw), [LL programmatic flow](https://docs.limitless.exchange/developers/programmatic-api). Будущие счета в fixture имеют currency USD и state not_connected: это display placeholder, не контракт реального asset. Не менять существующие fixtures в этом цикле; предложить отдельный нормализованный money контракт `{amountRaw, decimals, assetId, chainId, valuationCurrency, observedAt}` до frontend интеграции.

### Realtime, auth, security, fees, GEO

| UI поле/действие | Источник | Классификация и корректировка |
|---|---|---|
| Публичный сигнал лидера PM | /v2/trades/activity и public market feeds | D/U. Market WS не гарантирует complete arbitrary-wallet fill stream. Нужны адресная атрибуция, backfill, измеренная detection latency. |
| Публичный сигнал лидера LL | Public history и market MINED events | D/U. Это уже финализированная история. Полный public leader WS не подтверждён. |
| Собственные события PM | Authenticated user WS | D/P. Credentials только server-side. Stream не replay missed events; после reconnect orders/trades read. |
| Delegated LL order events | REST /orders/status/batch или /markets/{slug}/user-orders с x-on-behalf-of | D/P. Partner socket scoped к подписавшему profile, не subaccounts; polling budget зависит от количества accounts. |
| Операционная задержка | Наш timestamps + source timestamps/status | C. Развести время discovery, risk/queue, submit/ack, match, finality. p95 HTTP response не p95 source-to-copy delay. |
| Свежесть API PM | /v2/status computed_at/age_seconds | D/C. Background snapshot может стареть с HTTP200;503 до первого snapshot. Не использовать зелёный «подключено» как trading readiness. |
| Maintenance LL | /maintenance/status?target=trading | D. post_only/cancel_only/disabled влияют на availability кнопок. Disabled блокирует также cancel;425 может быть receive-window, смотреть code. |
| PM Session Key | Builder relayer + Deposit Wallet owner authorization | D/P. Beta,180d; CLOB-only scope предпочтительнее ALL для текущего MVP. Своё session expiration UI не выдавать за configurable shorter venue grant. |
| Отзыв PM | Relayer session-signers revocations + transaction status | D/P/C. Local stop немедленно; fencing, отмена собственных key orders и chain confirmation асинхронно. «Отозвано» после одного SDK return преждевременно. |
| LL EOA vs managed wallet | HMAC token + EIP712 EOA signature либо partner delegated signer | D/P. HMAC не кошелёк. EOA per-order confirmation не автоматический copy. Managed trust boundary надо объяснить до live. |
| GEO PM | polymarket.com/api/geoblock + текущая restriction table + account closed-only | D/U. Проверяется requesting IP; backend-IP не доказательство GEO пользователя. Close-only/full block разные outcomes. |
| GEO LL | Terms/partner eligibility decision | U/P. Отсутствие публичного equivalent endpoint не ALLOW. Локальное право и коммерческий launch scope отдельно. |
| Комиссия PM | Market fee params + fills; Builder rates отдельно | D/C. Platform taker formula зависит от p и shares; maker platform fee0 не означает builder fee0. |
| Комиссия LL | execution.effectiveFeeBps/usdFee/contractsFee + profile feeRateBps | D/C. Buy fee в contracts, sell вUSDC. Нет published closed-form exact curve: preview estimate и фактическую fee сверять отдельно. |
| Наша комиссия и net result | Internal fee ledger + actual attributed fill | C/P/U. Дополнительный service charge не API platform fee. Не брать demo flat rate как реальный tariff. |

Источники: [PM realtime data](https://docs.polymarket.com/market-data/realtime-data), [PM freshness](https://docs.polymarket.com/api-reference/service/get-data-freshness), [LL auth](https://docs.limitless.exchange/developers/authentication), [LL maintenance](https://docs.limitless.exchange/developers/maintenance-mode), [PM fees](https://docs.polymarket.com/trading/fees), [LL fees](https://docs.limitless.exchange/user-guide/fees), [PM geoblock](https://docs.polymarket.com/api-reference/geoblock).

PM Session Keys также изолируют notification/trade/order visibility по signer: для полной сверки хранить key provenance и обращаться к соответствующему контексту. Не менять список open orders owner на «все orders счёта». LL token revoke ≠ доказанная отмена resting orders. Состояние «доступ отозван, есть неподтверждённые заявки» должно существовать, даже если новых submissions уже нет.

### Доход владельца и referrals

| UI поле/действие | Источник | Классификация и корректировка |
|---|---|---|
| Builder-attributed execution | PM GET /builder/trades?builder_code | D/C. Fill/order attribution и fee rows, не обещанная выплата. |
| Builder оборот | PM /v2/builders/volume/leaderboard | D. Оборот не выручка; units проверить по specific contract, не display total какUSD автоматически. |
| Builder fee начисление | Signed builder code, maker/taker configured rate, OrderFilled evidence | D/P/C. Flat notional fee additive к platform; настройки/доступ проекта не проверены. |
| Получено владельцем | Treasury transfers + linked accrual ledger | C/U. Полный payout-register endpoint этим чтением не подтверждён. Не считать любой входящий перевод revenue. |
| Referral own tier/earned | LL GET /referral/usdc/me | D/P/C. RawUSDC6 strings. Tier вычислить по API ladder, customTier — minimum floor. totalEarnedRaw — accrued. |
| Рефералы, комиссия с каждого | LL GET /referral/usdc/referrals | D/P/C. Авторизованная собственная область; внутренний client/subaccount не автоматически referred user. |
| Pending/payable/paid | LL referral policy + payout evidence | D/C/U. Earned total ≠ paid. Полный per-accrual split/payout API не подтверждён. |
| Внутренние приглашения Polyfox | Наш event/contract/ledger | C/U. Не подменять площадочным referral standing; billing/partner agreement отдельно. |

[PM Builder Fees](https://docs.polymarket.com/programs/builders/fees): maker/taker rate независимы, max50/100bps соответственно; изменяемый tariff имеет scheduled policy. UI должен показывать effective fee версию на момент fill, не последний тариф. Builder disabled может приводить к отказу order. [LL referral program](https://docs.limitless.exchange/user-guide/referral-program): permanent first-referrer attribution, eligible finalized taker fills; Community markets исключены, maker fills не дают taker revenue. Pending становится payable после market resolution, daily payout с minimum$1. [LL stats](https://docs.limitless.exchange/api-reference/referral/my-stats): данные ladder, own volume и accrued earnings. [LL referred users](https://docs.limitless.exchange/api-reference/referral/my-referrals). LP rewards — иная программа: не переносить её minute epoch/22:30UTC/no-minimum правила на referral payouts.

## Конкретные несоответствия и блокеры

**P0 для live, P1 для честного data-UI, P2 для контракта/документации.** Это приоритеты предложения; работа не разрешена этим отчётом.

| Приоритет | Наблюдение | Предлагаемый результат до интеграции |
|---|---|---|
| P0 | Partner managed signing/recovery и пользовательский вывод LL не runtime verified | Раздельный approved permission/recovery spike; исключить withdrawal у execution token; описать owner fallback и судьбу resting orders. |
| P0 | PM signer visibility и revoke lifecycle не моделируются одним owner poll | Multi-signer reconciliation contract + async revoke statuses; закрыть policy submission fence до ожидания внешнего revoke. |
| P0 | GEO target не равен unrestricted buy | Отдельный eligibility contract per venue/launchGEO; Somalia/Thailand PM не предлагать как live buy-ready. |
| P0 | UNKNOWN submission + cancel/replacement race | Durable intent/submission/fill/reservation ledger; не завершать экран по prototype transition; proof-of-absence и reconcile gate. |
| P1 | 90d и rolling windows обещают больше готовых API периодов | State unavailable/partial; единый explicit start/end/timezone contract, отдельный источник reconstructed90d. |
| P1 | Термины deals/winrate/ROI расходятся со значением source fields | Metric dictionary с denominator/unit/fees/period/coverage. Accuracy отдельно от profitable closed trades. |
| P1 | Баланс, резерв и можно вывести визуально похожи, но источники разные | Field provenance + completeness + reservation reconciliation; неизвестное `—`; отдельный settlement/bridge lifecycle. |
| P1 | LL subaccounts realtime не поддерживает partner socket | Polling/REST lifecycle design + rate-budget/SLO; degraded/stale блокировки и отсутствие ложного realtime badge. |
| P1 | Будущий flat demo fee не совпадает с venue dynamic/multiasset fees | Venue execution fee fields в нормализации и отдельные estimate/actual; cents только final display. |
| P1 | Graph/topic synthetic data не происходят из одной trade history | Нельзя заявлять API validation; добавить provenance/demo-state requirement в acceptance будущего интерфейса. |
| P1 | Owner accrued/paid/referral attribution не подтверждено | Отдельный accounting contract, active tariff версии, payout evidence, unknown split вместо фиктивных totals. |
| P2 | docs55 пустая v1 sunset дата и источник19.1 без URL | Исправить в отдельном разрешённом цикле с official link и checkedAt; сейчас24.10 documented, future не runtime shutdown. |
| P2 | LL all prose vs enum, volume generic schema | Зафиксировать API doc issue и runtime read-only probe до использования; не угадывать полный payload. |

## Fixture review: что реально доказано локально

`design/interactive-fixtures-2026-10-02.json`: synthetic true; account-demo USD и future venue accounts currencyUSD/not_connected; addresses у трейдеров synthetic. PnL charts явно `chartSyntheticIllustration` и note «not reconstructed market history». В исходных period snapshots repeated drawdownBasisPoints241/282 не доказывает периодный maxDD. Отчёт78 теперь отображает `—`, что соответствует отсутствию подтверждённого ряда.

`qa-2026-10-03/trader-topic-executions.json`: 35 независимых synthetic executions; purpose прямо исключает complete production trade history и PnL reconstruction. Старый `trader-topics.json` — fixture market membership, не executed30d history; использовать более новый executions contract как design reference, но не production evidence. Все trade topics требуют venue metadata mapping.

В orders/positions есть строки без outcomeId, в том числе closed orders и lots. Отчёт75 честно отображает missing outcome как demo gap; production контракт должен требовать outcome reference до submit/sell/cancel mapping. Future fixtures dollar cents и small quantity примеры не подтверждают market minSize/precision на каждой venue. Документ14 исторически измерял minSize50–200 shares в20 рынках: это selection snapshot24.09, не текущая универсальная норма.

## Минимальная следующая read-only проверка после отдельного разрешения интеграции

1. Сохранить versioned public schema/response snapshots; PM v2 пагинация/casing/miss, LL actual schema units/default windows.
2. На3–5 публичных активных адресах каждой venue вычитать cursor history минимум72ч, с overlapping replay, late fills, correction и completeness counters. Не заменять полноту successfulHTTP.
3. Сверить7/30/90d с actual boundaries, cashflow, реализованным/нереализованным, fees/rebates/referrals, split/merge/redeem; exclude unsupported asset/market types. Набор approved source markets и resolution правила одинаково фиксируются в demo и live.
4. Записать source-time→observed-time→decision-time; отдельно matching/finality и свежесть. Budget/price/minSize/depth использовать на actual observation, без lookahead.
5. Приватный access/capability/owner/session/subaccount/revenue read-only spike делать только с собственным разрешённым проектным аккаунтом. Нынешний audit не открывает registration/frontend/live gate.
6. До UI integration согласовать маленький data contract каждой карточки: source endpoint, field, amount unit, formula version, actual window, coverage, freshness, authorization, null/404/503 behavior, allowed actions. Readiness статус по каждой venue, не одна галочка «API работает».

Итог: текущие UI уточнения75/78 уже уменьшают риск ложных обещаний, но доказательств денежных контрактов, периода90d, owner payouts и delegated realtime недостаточно. Можно согласовать показанные предложения по структуре данных и состояниям; реальные интеграции должны пройти отдельные проектные gates21/22/23 и ADR0013.
