# Polymarket Predictions: средства, позиции, realtime

Проверено чтением официальных документов 2026-10-06. Все утверждения ниже — **документировано**, поведение операций — **не проверено**. Публичный GET Bridge supported-assets через web оказался недоступен; первоначальный shell DNS был недоступен; позднее официальные Bridge/Relayer OpenAPI прочитаны безопасным GET. Дополнительные публичные probes основного агента: supported-assets HTTP403, geoblock timeout25s ([evidence manifest](evidence/manifest.json)); eligibility не определена. Ни аккаунты, ни адреса пополнения, ни credentials не создавались; денежные/contract операции и WebSocket подключения не выполнялись. Perps и Combo/RFQ вне области. Версия Bridge в URL отсутствует; OpenAPI info.version=1.0.0 — версия спецификации, не API semver. SDK использован только как документированный интерфейс, не установлен.

## Collateral и точность

pUSD — ERC-20 на Polygon mainnet, 6 знаков, обеспечен USDC; это collateral торговли. **pUSD / USDC native / USDC.e нельзя считать одним contract asset**. Onramp/Offramp обеспечивают wrapping; указанная прямая функция `wrap(address _asset,address _to,uint256 _amount)` принимает USDC.e, требует allowance Onramp и может revert `OnlyUnpaused()`. `unwrap(...)` требует allowance Offramp, выдаёт USDC.e и имеет pause gate. В API суммы хранить integer base-unit strings, отдельно chainId/address/decimals; не binary float. Официальные contract адреса перепроверять перед реализацией. [pUSD](https://docs.polymarket.com/concepts/pusd).

Deposit-guide допускает исходные native USDC и USDC.e с последующим wrapping; это не разрешение подставлять любой токен в низкоуровневую функцию. Bridge переводит поддержанный source asset в pUSD на Polygon. [Deposit](https://docs.polymarket.com/trading/bridge/deposit).

## Bridge endpoint matrix

Base `https://bridge.polymarket.com`. В опубликованных request примерах нет обязательной CLOB/HMAC авторизации; отсутствие auth в схеме не доказывает право списать чужие средства. Создание withdrawal address только конфигурирует маршрут; перевод средств отдельная подписанная операция.

| Метод/путь | Вход, auth, pagination | Ответ/ошибки | Источник |
|---|---|---|---|
| GET `/supported-assets` | Без body/pagination, auth не указан | 200 `supportedAssets[]`: `chainId`, `chainName`, `token{name,symbol,address,decimals}`, `minCheckoutUsd`; 500 `error` | [Schema](https://docs.polymarket.com/api-reference/bridge/get-supported-assets) |
| POST `/deposit` | JSON `address` Polymarket wallet; optional `X-Builder-Code` bytes32 hex; pagination нет | 201 `address{evm,svm,btc,tron}`, `note`; 400/500 `error`; omitted builder code → warning `missing_builder_code`, malformed →400 | [Schema](https://docs.polymarket.com/api-reference/bridge/create-bridge-addresses) |
| POST `/withdraw` | JSON required strings `address`, `toChainId`, `toTokenAddress`, `recipientAddr`; optional builder header; pagination нет | 201 bridge `address` object, `note`; 400/500 `error`; аналогичная builder validation | [Schema](https://docs.polymarket.com/api-reference/bridge/create-withdrawal-addresses) |
| POST `/quote` | JSON `fromAmountBaseUnit`, `fromChainId`, `fromTokenAddress`, `recipientAddress`, `toChainId`, `toTokenAddress`; no pagination/auth shown | estimate output/time/fees, `quoteId`; документированы400/500error; schema в приложении | [Schema](https://docs.polymarket.com/api-reference/bridge/get-a-quote) |
| GET `/status/{address}` | **bridge address**, не wallet; `limit=1..100` default50; opaque `cursor`; compatibility `paginate=true` или omit | `transactions[]`, `nextCursor`; invalid cursor400 `error: invalid request`; остальные ошибки не экспериментально проверены | [Schema](https://docs.polymarket.com/api-reference/bridge/get-transaction-status) |

Source/destination chain IDs — строки, включая не-EVM; EVM/SVM/BTC/Tron address family выбирать по supported source. Список активов изменяется: GET проверять перед переводом. Guide даёт примеры minima Ethereum $7, Polygon/L2 $2, BTC/Tron $9; API page показывает **иллюстративный** Ethereum `minCheckoutUsd:45`. Эти значения не фиксировать как продуктовые константы. [Assets guide](https://docs.polymarket.com/trading/bridge/supported-assets), [schema](https://docs.polymarket.com/api-reference/bridge/get-supported-assets).

Quote включает `estCheckoutTimeMs`, `estInputUsd`, `estOutputUsd`, `estToTokenBaseUnit`, `quoteId`, `estFeeBreakdown` (gas, app fee, fill cost, slippage, swap impact, total impact). Это оценка, не гарантия суммы/срока. Quote id не заменяет bridge address для tracking. [Quote](https://docs.polymarket.com/trading/bridge/quote).

Status: `DEPOSIT_DETECTED`, `PROCESSING`, `ORIGIN_TX_CONFIRMED`, `SUBMITTED`; terminal `COMPLETED` или `FAILED`. `txHash` destination появляется при completed; `createdTimeMs` — milliseconds, может отсутствовать до processing. Poll рекомендуют каждые10–30s. History newest-first; cursor URL-encode, не конструировать и не переносить к другому адресу; конец только `nextCursor:null`, даже после короткой/пустой страницы. Compliance hold/stuck требует поддержки bridge provider. [Status](https://docs.polymarket.com/trading/bridge/status).

Withdrawal address создавать непосредственно перед исполнением для конкретного destination. Guide описывает unwrapping и native-USDC swap через pool; нехватка liquidity может задерживать вывод. UI threshold <10bp — характеристика UI, **не универсальная API гарантия**. Документирован direct pUSD withdrawal, но совместимость получателя нужно проверить отдельно. [Withdraw](https://docs.polymarket.com/trading/bridge/withdraw).

## Split / merge / redeem: CTF и Protocol V2

Для обычной бинарной пары Split:1pUSD→1YES+1NO; merge обратный, требует одинакового количества. Redeem после обычного binary resolution: winner1pUSD/share, loser0; fractional/void payout проверять по resolution, не подставлять1 автоматически; deadline redemption не указан — guide говорит его нет. Для Deposit Wallet API путь — ABI-calldata в подписанном batch POST `https://relayer-v2.polymarket.com/submit` с `RELAYER_API_KEY` и `RELAYER_API_KEY_ADDRESS`; fields `type:WALLET`, `from`, `to`, `nonce`, `signature`, `depositWalletParams{depositWallet,deadline,calls[{target,value,data}]}`. Pagination нет. Ждать `STATE_CONFIRMED`, не ответ submit. Полный REST error contract/receipt flow уточняется в Relayer разделе справочника. SDK `redeemPositions` без amount выкупает обе стороны; это не ABI Router. [Manage positions](https://docs.polymarket.com/trading/positions/manage).

V2 — отдельный ledger PositionManager, approvals CTF туда не переносятся; holdings CTF сохраняются для V1. Router ABI: `split(bytes31,uint256)`, `merge(bytes31,uint256)`, `redeem(bytes31,uint256 outcomeIndex,uint256 amount)`. V2 conditionId31bytes; padded32bytes с последним zero байтом нужно валидировать; outcome0YES/1NO вместо CTF indexSets1/2; base precision6. Split требует pUSD approveRouter; merge/redeem — PositionManager operator approvalRouter. `getPayout(positionId,amount)` возвращает pUSD base units; unresolved может revert, zero losing valid. V2 neg-risk результаты могут быть derivable без отдельного ConditionResolved. Не удваивать Router/module events. AutoRedeemer approval не назначает redemption. [Contract migration](https://docs.polymarket.com/migrate/polymarket-v2/contract-integrations).

Практическое правило адаптера (рекомендация, не бизнес-изменение): position system хранить вместе с market/asset mapping; не применять CTF decoding к любому assetId. Settlement, redemption, wrapping, transfer и bridge — отдельные состояния и операции; успешный match не означает выполненный bridge/redeem.

## Realtime matrix

| Канал/base | Доступ и subscription | События/назначение |
|---|---|---|
| `wss://ws-subscriptions-clob.polymarket.com/ws/market` | Публичный; `type:market`, `assets_ids:[...]`; текст PING10s→PONG | book, price changes и рыночные обновления по outcome assets; не own fills | [Realtime data](https://docs.polymarket.com/market-data/realtime-data) |
| `wss://ws-subscriptions-clob.polymarket.com/ws/user` | CLOB `apiKey/secret/passphrase`; subscribe сразу; PING10s→PONG; optional markets condition IDs | Authenticated own order/trade events. Wire `event_type:order/trade`; order `type:PLACEMENT/UPDATE/CANCELLATION`; не публичная подписка на любой wallet | [Order updates](https://docs.polymarket.com/trading/realtime-order-updates) |
| `wss://ws-live-v2.polymarket.com/ws` PolyBolt | CLOB auth frame→authed→subscribe; `op`, `channel`, object`filter` | `price.crypto`, `price.crypto.twap`, `price.equity`: reference prices, не цены outcome orderbook | [Live channel](https://docs.polymarket.com/api-reference/wss/polybolt) |
| `wss://ws-live-data.polymarket.com` RTDS | Legacy activity topic остаётся; исчерпывающая current activity schema/filter здесь не проверена | Не считать доступным универсальным потоковым API лидера | [Migration](https://docs.polymarket.com/migrate/rtds-to-polybolt) |

PolyBolt миграция: SDK support начинается с `@polymarket/client`/`polymarket-client`0.11.0; removal deprecated RTDS price topics планируется через месяц после release. **24.10.2026 не подтверждён этим источником**. Activity не имеет PolyBolt replacement; comments stream retiring без replacement. Crypto symbols lowercaseUSD `btcusd`; BinanceUSDT→defaultChainlinkUSD меняет источник/quote. TWAP60 поддерживается, TWAP30 replacement нет. [Migration](https://docs.polymarket.com/migrate/rtds-to-polybolt).

PolyBolt envelope `v:1`, `channel`, `seq`, `ts`, optional `snapshot`, `dropped`, `payload`; snapshot может быть пуст. Server ping25s; old PING5s убрать. Limits64subscriptions,20subscribe frames/s,64KB,8auth frames; closes4001auth,4002slow consumer,4003draining,4008policy. Seq сравнивать внутри channel/connection, после reconnect повторять auth/subscription и seed snapshot; `full_accuracy_value` предпочтительнее float. Это документировано, resilience экспериментально не проверена. [Migration](https://docs.polymarket.com/migrate/rtds-to-polybolt).

Рекомендация адаптера: независимые reconnect/heartbeat стратегии для каждого транспорта; exponential backoff+jitter; connection-generation fencing и dedup; событие — триггер сверки REST, а не гарантия полной доставки. Собственные ордера сверять с authenticated REST и chain/relayer settlement; публичную историю лидера читать Data API с overlap/dedup. Не переносить PolyBolt sequence semantics на CLOB/RTDS. SLA, replay, полнота public activity, delivery lag и гарантии wallet filtering — **не проверено**, вопросы партнёру.

## Fees, ограничения и география

Taker fee применяется при match, maker0; formula `C×feeRate×p×(1-p)`, параметры рынка получать актуально. Guide rates: crypto0.07; sports0.05; finance/politics/mentions/tech0.04; economics/culture/weather/other0.05; geopolitics0. Fee rounding5decimal, min0.00001USDC. Страница называет единицу USDC, другие страницы collateral pUSD: ledger currency/charged amounts проверять в фактическом fill/SDK перед расчётами. «Нет Polymarket deposit/withdraw fee» не исключает provider gas/swap/bridge fee. [Fees](https://docs.polymarket.com/trading/fees), [Quote](https://docs.polymarket.com/trading/bridge/quote).

Bridge general50req/10s; relayer submit25/min. Cloudflare IP limits sliding-window, превышение delayed/queued; signer trading limits отдельные. Не трактовать general quota как SLA или endless permission. [Rate limits](https://docs.polymarket.com/api-reference/rate-limits).

GET `https://polymarket.com/api/geoblock` без pagination возвращает `blocked`, `ip`, `country`, `region`; попытка live GET завершилась timeout; ответа с eligibility нет. Документы различают completely blocked, frontend+API close-only, frontend-only close-only. **Poland PL входит frontend+API close-only** на дату чтения. Это не вывод о конкретном пользователе из timezone. Own-account colocation доступен по KYC/KYB, документирован как недоступный Builder/third-party applications, торгующим за end-users. [Geo](https://docs.polymarket.com/api-reference/geoblock).

## Для paper и будущего copy trading

Paper использует публичный market stream и REST как входы модели, не реальные funding/redeem. Funding capability как read-only catalog/quote/status можно спроектировать отдельно; исполнение средств не следует из capability copy-order. Session Keys нельзя считать разрешением на вывод. Нужно согласовать с партнёром scopes custodial/delegated wallet, доступность bridge/relayer для приложения, fees currency, completeness activity, minimums, provider hold/recovery, replay и close-only geography. Требует партнёрского подтверждения — вопросы возможностей/условий, а не обещанный существующий partner endpoint.

Схема запроса, **иллюстрация, не выполненный запрос**:

```http
GET https://bridge.polymarket.com/status/<bridge_address>?limit=50
```

```json
{"transactions":[],"nextCursor":null}
```

Перед следующей задачей: reread llms/changelog/migrations, обновить checked date и SDK pins; сравнить contracts/chain/decimals/ABI, assets list, limits, geo; проверить public endpoints без secrets; authenticated и money операции оставлять отдельному разрешённому этапу. Отсутствие ошибки в документации не означает отсутствие ошибки в production.

## Relayer REST и вложенные схемы

Официальные [Bridge OpenAPI](https://docs.polymarket.com/api-spec/bridge-openapi.yaml) и [Relayer OpenAPI](https://docs.polymarket.com/api-spec/relayer-openapi.yaml) прочитаны06.10; обе info.version1.0.0. Все calls ниже D/U, **не выполнены**. Полные поля body/response, required/enums и constraints — [Bridge contracts](evidence/bridge-contracts.json), [Relayer contracts](evidence/relayer-contracts.json).

| Метод/путь | Вход/auth/pagination | Ответ/HTTP errors |
|---|---|---|
| POST `/submit` | Signed transaction body + Builder HMAC либо Relayer API key/address; нет pagination | transactionID/state;400/401/429/500 |
| GET `/transaction` | required query id; auth не объявлен; нет pagination | array RelayerTransaction, не один object;400/404/500 |
| GET `/transactions` | Builder HMAC либо Relayer key/address; cursor в этой schema не указан | array RelayerTransaction;401/500 |
| GET `/nonce` | address/type PROXY или SAFE, public example; нет pagination | nonce;400/500 |
| GET `/deployed` | address, type SAFE/WALLET, defaultSAFE; нет pagination | deployed flag;400/500 |

Relayer OpenAPI не содержит новых `/v1/session-signers/*` и `/v1/account/transactions/*` путей: они документированы отдельно в Session guide, не экстраполировать noncePROXY/SAFE на WALLET. `security` declaration отсутствует у части операций, но `/submit`/`transactions` требуют один из явных auth sets в header schema. Перечень states/transaction fields читать в contract JSON; возвращённый ID/stateNEW не доказывает chain confirmation. Никаких wallet permission операций в этом исследовании не выполнено.
