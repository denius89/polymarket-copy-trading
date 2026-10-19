# Проверка источников и обновление справочника

Дата проверки: **06.10.2026**. Ветки/коммиты этого исследования относятся только к `docs/api/limitless/**`. Общие README, ROADMAP, PROJECT_STATE, документ81, чужая API-директория, sources и references не изменялись. Исследование выполнялось в отдельном checkout; незакоммиченные изменения основного рабочего каталога не публиковались.

## Объём и пределы проверки

- Прочитаны применимые AGENTS.md, текущая очередь проекта и связанные20/22/23/81 и API-аудит04.10. Старые проектные документы использованы как список вопросов, не доказательство нынешнего API.
- Проверены92 прямых официальных source URLs:91 URL docs.limitless.exchange и зафиксированный package.json официального TypeScript SDK. Все их документальные representations дали HTTP200. Для human-friendly docs links проверялся соответствующий официальный `.md`; OpenAPI/llms читались напрямую. Результаты, время проверки и SHA256 в [source manifest](source-manifest.json).
- Получены9 успешных публичных GET без credentials: каталог; biggest positions; exact market; его orderbook/events; history/positions/realized-pnl/accuracy одного публичного адреса. Сохранены только URL/path, keys/counts и некоторые response headers в [public evidence](public-request-evidence.json), без имени/адреса трейдера и полного payload.
- Первые4 public GET с default Python User-Agent дали403 `error code: 1010`. Следующие стандартные headers дали200 на перечисленных routes; причина отказа не диагностирована. Referral leaderboard и trading feed из первых4 не перепроверены успешным API-запросом. Это не доказательство обязательной авторизации public methods.
- Полные cursor/pages, retention, completeness, rate ceilings, динамика задержек и reorg behavior **не проверялись**. Public-history первая страница limit1 показала nextCursor, но следующая страница не запрашивалась.
- Private/partner endpoints, WS handshake/subscription и production mutations не вызывались. Нет созданных аккаунтов, API keys, sessions, scopes, approvals, orders или transfer. Доступ партнёра проекту U/P, а не R.
- SDK не устанавливался и не запускался. Version1.1.0 — содержимое package.json в конкретном official commit, не утверждение о latest registry release или совместимости всех SDK languages.

Source retrieval через поисковый/браузерный инструмент на части страниц был недоступен; прочитан официальный llms index и использовано прямое read-only получение официальных markdown/spec. Итоговая HTTP-проверка92 источников успешна. Непроверенная runtime операция не становится проверенной из-за чтения документа.

## Версии и pin

| Компонент | Зафиксировано |
|---|---|
| Global OpenAPI | OpenAPI3.0.0, `info.version=1.0`; paths без универсального `/v1` prefix |
| OpenAPI snapshot SHA256 | `e7c26100d48ac78173524f9e287c64efc535f621a1ac99f7a57112845c4615d9` |
| TypeScript SDK package | `@limitless-exchange/sdk`, version1.1.0 |
| SDK commit | `8e4d897b9a2b0a9ee218ec0847aae70c620aa511` |
| EIP-712 domain | version1, Base chain8453; verifyingContract рынка из venue.exchange |
| WS projection schema | Endpoint-specific schemaVersion, не одна общая версия payload |
| Последняя просмотренная запись changelog |02.10.2026: correction book sizes; API behavior не объявлено изменённым |

Источники: [OpenAPI](https://docs.limitless.exchange/openapi.json), [package.json в commit](https://github.com/limitless-labs-group/limitless-exchange-ts-sdk/blob/8e4d897b9a2b0a9ee218ec0847aae70c620aa511/package.json), [EIP-712](https://docs.limitless.exchange/developers/eip712-signing), [Changelog](https://docs.limitless.exchange/changelog). Полные оригиналы сохранены только в local work для анализа; справочник содержит собственное описание контрактов и ссылки.

## Фактические наблюдения публичных ответов

| Route / выборка | Наблюдение R | Чего это не доказывает |
|---|---|---|
| active page1/limit1 |200 data[] с market metadata | Всех рынков/типов, traded availability или полную pagination |
| biggest positions limit1 |200 projection fields, data[]; max-age1/s-maxage1 | Дополнительные metric=pnl/marketPageId параметры или всех лидеров |
| exact market без include |200 detail с tokens,prices,venue,collateralToken,settings | Что все include/filter варианты доступны |
| exact CLOB orderbook |200 bids/asks,tokenId,minSize,maxSpread,lastTradePrice | Fillability, book delay, rate budget или archived books |
| market events page1/limit1 |200 events/totalRows/totalPages; cache30s + stale-while-revalidate30s | Maker-side full wallet history или новый realtime leader signal |
| public history limit1 |200 только data/nextCursor, totalCount отсутствует; cache max-age60/s-maxage60 | Полную account history, следующие страницы или60-second delivery SLA |
| public positions |200 amm/clob/group; cache max-age5/s-maxage15 | Spendable balance, источник virtual lot и немедленный redeem |
| public realized-pnl1d |200 timeframe/windowStart/current/categories/data; cache max-age15/s-maxage30 | all/90d/lifetime completeness, private ledger или ROI копии |
| public accuracy |200 won/lost/total/since; cache s-maxage15 | Универсальную методику нашего closed-trade win rate |

Кеш может добавлять задержку к наблюдению; polling чаще TTL не обеспечивает более свежих данных. TTL header — наблюдение одного ответа, не гарантия max end-to-end latency. Для оценки пригодности измерять source fact → publication → observedAt → decision → submit → terminal, а не просто HTTP response time.

## Расхождения и пробелы, которые нельзя скрыть

| Область | Расхождение / пробел | Практическое правило |
|---|---|---|
| Авторизация | Global info.description говорит API keys required и cookie removal «within weeks»; нынешний auth guide рекомендует HMAC и новые legacy keys не выдаются | Не придумывать дату миграции; новая интеграция scoped HMAC |
| Privy derive/capabilities | Prose Privy identity, security metadata HmacAuth | Не генерировать auth flow только из metadata; actual project capabilities U/P |
| withdrawal | Current guide/withdraw page поддерживают scope, global derive enum его не содержит | Runtime allowlist/scopes уточнить до денежного flow |
| Fee signing | Profile page/schema говорит rank.feeRateBps; changelog23.09 требует effectiveFeeRateBps | Не подписывать rank-only на fee-enabled рынке; mismatch/child flow см.execution |
| Public history | limit optional default20 в prose, required=true в spec; public generic schema, private required totalCount, observed public totalCount absent | Explicit limit, tolerate missing totalCount; opaque cursor с тем же filter |
| Realized PnL all | Current prose:1d/1w/1m/all, all permanent hourly history без category breakdown; global enum только1d/1w/1m | all D/prose, runtime U; не выдавать1d/1w current за lifetime |
| Biggest positions | Prose metric/pnl/page scope, spec толькоlimit | Новые варианты D/U, не runtime claim |
| Market include | Spec required, observed detail без include200 | Зафиксировать одно наблюдение, не вывести все include semantics |
| Private history Claim | Page включает Claim, global strategy enum нет; deposits/withdrawals исключены | Unknown strategy сохранять; отдельная chain transfer сверка |
| Async status | `/v2/orders/status/{id}` только partner prose, нет global spec/page | Schema/retention/errors U; предпочтительно documented status batch до ответа партнёра |
| Example chain84532 | Partner allowance illustration отличается от production introduction8453 | Не объявлять существование testnet; chain читать из actual deployment |
| Source event completeness | Market events taker-only finalized CLOB, own WS profile-only; universal leader stream не найден | REST public history observation и completeness/lag spike |
| Cancellation | Historical status не сохраняет все cancel/STP details; cancel-replace partial/unknown | Journaling + user-orders + status + settled history; без blindly retry |
| GEO/recovery/deposits | Нет доказанного universal eligibility endpoint, child recovery без сервиса, transfer history и transactionId completion routes | UNKNOWN/P до отдельного контракта и проверки |

Прямые ссылки на каждое расхождение находятся в [authorization-partner](authorization-partner.md), [execution](execution.md) и [public-data](public-data.md). Более ранний API-аудит04.10 не заменяет эту проверку; например актуальный realized-pnl prose теперь описывает all, что требуется перепроверять при использовании.

## Checklist проверки изменений API

- [ ] Убедиться, что новая задача разрешена текущим ROADMAP/решением пользователя; документальный read не разрешает mutation.
- [ ] Скачать свежие llms/OpenAPI/changelog; записать UTC observedAt, hash, schema info.version, deployment/base URL и точный SDK commit/package version.
- [ ] Сверить endpoint-specific prose, global schema и SDK code; каждое расхождение пометить, не сглаживать автоматически.
- [ ] Проверить ссылки; источник unavailable отметить явно и сохранить последнюю известную дату.
- [ ] Для public GET сохранить безопасную выборку raw shape/status/cache/coverage; отличить403proxy от endpoint401/403. Не использовать чужие credentials.
- [ ] Проверить точный path/method, параметр required/optional, enum/default, pagination/cursor binding, response unions/null и ошибки.
- [ ] Проверить actual scopes/ownership/wallet mode, supported delegation routes, revoke/expiry отдельно от logout; без access не отмечать R.
- [ ] Перепроверить market routing, verifyingContract, collateral/chain, tick/min-size, все raw scales и parser discriminator.
- [ ] Отдельно сверить effective fees, estimate vs realized, maker/taker, totalsRaw и upstream referral vs наш service fee.
- [ ] Проверить new/deprecated order states, partial/cancel race, cancel-replace independent outcomes, lookup/idempotency retention и unknown recovery.
- [ ] Перепроверить own/delegated/public stream scope, subscriptions/reconnect/replay, REST gap recovery, caches и rate budgets.
- [ ] Проверить positions/history/PnL/accuracy semantics, all/90d coverage, transfers/redeem/settlement; missing data не считать нулём.
- [ ] Обновить D/R/U/P, вопросы партнёру и [adapter map](adapter-map.md); изменение product rule оформить отдельно, не вписать в API reference.
- [ ] Запустить проектную проверку ссылок и whitespace; diff ограничить owned docs/api/limitless/**, публикация отдельным draft PR.

## Основные официальные источники

[Индекс](https://docs.limitless.exchange/llms.txt), [OpenAPI](https://docs.limitless.exchange/openapi.json), [Changelog](https://docs.limitless.exchange/changelog), [Introduction](https://docs.limitless.exchange/developers/introduction), [Authentication](https://docs.limitless.exchange/developers/authentication), [Programmatic API](https://docs.limitless.exchange/developers/programmatic-api), [CLOB orders](https://docs.limitless.exchange/api-reference/trading/create-order), [AMM](https://docs.limitless.exchange/developers/amm-trading), [Own order stream](https://docs.limitless.exchange/developers/websocket/order-events), [Public history](https://docs.limitless.exchange/api-reference/public-portfolio/history), [Public PnL](https://docs.limitless.exchange/api-reference/public-portfolio/realized-pnl), [Fees](https://docs.limitless.exchange/user-guide/fees), [Withdraw](https://docs.limitless.exchange/api-reference/portfolio/withdraw), [Referral](https://docs.limitless.exchange/user-guide/referral-program), [ToS](https://docs.limitless.exchange/user-guide/terms-of-service). Полный список92 проверенных source URLs приведён в manifest, пооперационные ссылки — в матрицах.
