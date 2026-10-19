# Проверка источников и границы результата

Дата: **06.10.2026**. [Индекс](README.md). Источники исследованы через официальную навигацию, web и безопасные HTTPS GET. Старые [19](../../19_polymarket_api_access.md), [21](../../21_polymarket_access_and_spike_plan.md), [23](../../23_dual_venue_adapter_contract.md), [81](../../81_full_figma_business_api_and_ui_audit_2026-10-04.md) и [API-аудит 04.10](../../../design/qa-2026-10-04/api-mapping-audit-agent.md) использованы как список вопросов, а не доказательство текущего wire contract.

## Реально выполненные публичные проверки

Сырые публичные ответы и manifest находятся в [evidence](evidence/manifest.json). Сохранён SHA256 тела, точный URL, HTTP result и безопасные response headers; cookies/auth headers не сохранены. Времена server Date указаны как серверные, а не как измерение клиентской задержки. GET с cursor использует opaque `next_cursor` первой страницы без декодирования или изменения.

| Проверка | Наблюдение | Что не доказано |
|---|---|---|
| Data `/v2/status` | HTTP200, `data`, computed_at/age, serving и ingestion | Не SLA и не permission/trading availability; freshness snapshot может устареть |
| Data `/v2/trades?limit=1` | HTTP200, snake_case, `data` и pagination.next_cursor | Глобальная одна строка, не полный leader history; один HTTP200 не coverage |
| Следующая trades cursor page | HTTP200 с другой строкой и новым cursor | Не доказаны произвольная глубина, reordering, late correction и retention |
| Data trades с `offset` | Реальная validation error сохранена | Другие invalid/filter/private/429/503 ошибки runtime не проверены |
| Gamma `/markets?...limit=1` | HTTP200 и mixed ID arrays на v1 market | Legacy маршрут всё ещё отвечает; header sunset не означает фактическое выключение |
| Gamma `/markets/keyset?...limit=1` | HTTP200, markets/next_cursor | Не полный discovery coverage и не универсальная filter compatibility |
| CLOB `/book?token_id=...` | HTTP200 для выбранного v1 asset, string amounts, timestamp/hash, levels | Не book WS, не V2 book, не order execution; snapshot не гарантия исполнимой глубины позже |
| Bridge `/supported-assets` | HTTP403 из этой среды | Документированный public endpoint не удалось проверить; актуальные доступные маршруты/minimum не подтверждены |
| `polymarket.com/api/geoblock` | Timeout после25с | Eligibility пользователя/проекта неизвестна. Timeout не DENY/ALLOW и не подтверждение GEO по timezone |

Ни CLOB L1/L2, ни credentials derive, ни user WS/PolyBolt, ни order/cancel/session/relayer/bridge POST не вызывались. Аккаунты не зарегистрированы, permissions не менялись, денежные операции не выполнялись. 72 часа на 3–5 лидерах не наблюдались. p95 source-to-copy, reliability, reconnect/replay и monetary rounding не измерены.

## Существенные расхождения и наблюдения

1. **Outcome index.** Первая trades row вернула `outcome="Up"`, `outcome_index=999`. Это реальный ответ, а не нормальный 0/1 mapping. Не переносить индекс в submit; сначала найти version/condition/selected asset и сверить metadata. Мы не определили причину и не исправляли данные площадки.
2. **Caching.** В первой trades странице `Age:52`, `Cache-Control:public,max-age=300`. Это наблюдение одного cached response, не утверждение, что каждый Data response задерживается на300с. История не доказана как источник сигналов моложе30с. Повтор одного URL может возвращать кэш; changing query не разрешает обход rate/eligibility.
3. **Legacy Gamma.** `/markets` ответил с `deprecation:true`, `sunset: Fri,01 May2026...`, warning use `/markets/keyset`. Несмотря на прошлый sunset, сейчас HTTP200. Для будущего discovery использовать документированный keyset, не выводить новый deadline из старого заголовка. Сохранены headers и body.
4. **Mixed IDs.** Проверенный Gamma market `version=v1` содержит одновременно `clobTokenIds` и `positionIds`. По официальному [Protocol API migration](https://docs.polymarket.com/migrate/polymarket-v2/api-integrations) выбирать нужно по market version, а не по наличию поля.
5. **Book ordering.** Проверенный snapshot выдаёт bid levels от меньшей цены к большей, ask от большей к меньшей. Для прохода по глубине отсортировать bids descending/asks ascending как часть нашей нормализации; не считать первый элемент best bid/ask. Это C вывод из R, не обещание общего wire ordering.
6. **Документация и spec расходятся.** CLOB batch cancellation bound и post-order raw states подробно перечислены в [trading](trading.md). Нужны conservative bound и свежая сверка, а не выдуманный новый контракт. Trading reads не проверялись.
7. **Readability ограничена транспортом.** Web extraction некоторых `.md` страниц возвращала unsupported content type/internal error; прямой безопасный HTTPS GET позволил прочитать migration pages. Это не недоступность самой функции API. Локальные DNS ошибки устранены разрешённым сетевым доступом; Bridge403/geoblock timeout остались зафиксированными ограничениями.

## Официальные источники и версии

Полный список прочитанных/проверенных ссылок с HTTP статусом и временем — [sources](evidence/sources.json). Ссылки доступны рядом с соответствующими утверждениями в тематических файлах. Главные входы:

- [Documentation index](https://docs.polymarket.com/llms.txt), [API overview](https://docs.polymarket.com/getting-started/api).
- [Data v1→v2](https://docs.polymarket.com/migrate/data-api-v1-to-v2), [Data OpenAPI](https://data-api.polymarket.com/v2/openapi.json), [Gamma OpenAPI](https://docs.polymarket.com/api-spec/gamma-openapi.yaml), [CLOB OpenAPI](https://docs.polymarket.com/api-spec/clob-openapi.yaml).
- [Protocol V2 overview](https://docs.polymarket.com/migrate/polymarket-v2/overview), [API migration](https://docs.polymarket.com/migrate/polymarket-v2/api-integrations), [Contracts](https://docs.polymarket.com/resources/contracts).
- [Wallet authentication](https://docs.polymarket.com/trading/wallets-auth), [Session Keys](https://docs.polymarket.com/trading/session-keys), [Order lifecycle](https://docs.polymarket.com/concepts/order-lifecycle).
- [Fees](https://docs.polymarket.com/trading/fees), [Builder fees](https://docs.polymarket.com/programs/builders/fees), [Rate limits](https://docs.polymarket.com/api-reference/rate-limits), [GEO](https://docs.polymarket.com/api-reference/geoblock).
- [pUSD](https://docs.polymarket.com/concepts/pusd), [Bridge supported assets](https://docs.polymarket.com/trading/bridge/supported-assets), [Resolution](https://docs.polymarket.com/concepts/resolution).
- [Realtime](https://docs.polymarket.com/market-data/realtime-data), [RTDS→PolyBolt](https://docs.polymarket.com/migrate/rtds-to-polybolt), [Predictions changelog](https://docs.polymarket.com/changelog/predictions), [SDK changelog](https://docs.polymarket.com/changelog/sdks).

Data OpenAPI `info.version=0.1.0` и CLOB OpenAPI `info.version=1.0.0` — версии документов спецификаций. Они не определяют market protocol generation или package release. SDK совместимость и актуальная documented release зафиксированы в trading/public-data; зависимости в проект не добавлены.

Полные функциональные параметры, request/response schemas, required fields, defaults, enum и bounds выбранных endpoint families сохранены в [Data contracts](evidence/data-contracts.json), [Gamma contracts](evidence/gamma-contracts.json), [CLOB contracts](evidence/clob-contracts.json). Это извлечение из скачанных официальных OpenAPI; описательный текст и примеры удалены. [Schema manifest](evidence/schema-manifest.json) хранит URL, `info.version`, raw и derived SHA256. Spec тоже может отставать от guide/runtime: чтение этих файлов не снимает перечисленные расхождения. `security:null` в оболочке извлечения означает отсутствие глобального declaration в исходном файле, а не универсальную публичность всех операций; смотреть operation-level security и тематическую матрицу.

## Как воспроизвести без секретов

Иллюстрация безопасных чтений, **не новый сохранённый ответ**:

```sh
curl 'https://gamma-api.polymarket.com/markets/keyset?limit=1&active=true&closed=false'
curl 'https://data-api.polymarket.com/v2/status'
curl 'https://data-api.polymarket.com/v2/trades?limit=1'
# Для next page передать pagination.next_cursor как opaque cursor с URL encoding.
# Для book выбрать token_id по market.version и outcomes из metadata.
```

При следующем GET фиксировать client start/end отдельно, HTTP status/cache headers и body timestamp. Не публиковать cookies, подписи или auth payload. Примеры торговых запросов читать только как схемы; повторная проверка private endpoints/денег требует отдельного проектного gate.

## Проверка публикационного набора

Проверки 06.10.2026: `npm run check` (структура и внутренние Markdown links), `git diff --cached --check`, SHA256 всех7 реальных public response bodies, все локальные `$ref` в5 extracted contract files. Повторный доступ к52 official URLs/base references:50 доступны; bare Data base URL и повторный GET Data OpenAPI вернули403. Data OpenAPI ранее успешно получен и прочитан — raw hash сохранён; этот повторный отказ не скрыт. Source ledger различает API base URL от документации. Эти проверки подтверждают справочник и provenance, не API integration/live readiness. Изменён только `docs/api/polymarket/**`; общие документы и чужие незакоммиченные файлы не входят в ветку.
