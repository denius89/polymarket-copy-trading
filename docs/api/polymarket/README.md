# Polymarket API: справочник для Copy Trading MVP

Проверка: **06.10.2026**. Область: международная площадка Polymarket Predictions; Perps, Polymarket US, Combos/RFQ и другие продукты не входят в подтверждённый execution scope MVP. Это документационное исследование для коллеги и следующего агента, не реализация адаптера и не разрешение live.

## Как использовать в следующих задачах

1. Прочитать этот индекс, затем нужную endpoint-матрицу ниже. Для продуктовых правил использовать действующие ADR и [общий контракт адаптеров](../../23_dual_venue_adapter_contract.md), а не примеры площадки.
2. Проверить дату, API family, market version, signer scope и статус доказательства каждого используемого поля. Перечитать прямую официальную ссылку перед реализацией; сверить [журнал проверки](verification.md) и [checklist изменений](adapter-map.md#checklist-проверки-изменений-api).
3. Для paper читать публичные Gamma/CLOB/Data, сохранять snapshot/покрытие и применять ADR-0024–0028. Для live отдельно закрыть permission, GEO, fees, reconciliation и проектные gates из [плана 21](../../21_polymarket_access_and_spike_plan.md).
4. Не переносить публичную историю лидера в собственный order ledger. Связывать данные по venue/account/version/condition/asset, сохранять raw IDs, время источника и получения. Нет доказанной универсальной доставки всех действий произвольного лидера.
5. Новые находки записывать в этой директории с официальным URL, checkedAt, документированной версией и точным объёмом runtime проверки. Общие README/ROADMAP/PROJECT_STATE обновляет основной диалог проекта.

Актуальная очередь по поручению основателя: дизайн с коллегой → бизнес-логика → админка → технический план → реализация. Историческое «админка первой» заменено. Справочник не меняет интерфейсы, бизнес-правила и эту очередь.

## Навигация

| Файл | Что найти |
|---|---|
| [Public data](public-data.md) | Gamma/Data, сущности, v1→v2, pagination, история адреса, позиции/PnL и ограничения метрик |
| [Trading](trading.md) | CLOB, подписи, wallet/funder, Session Keys, private endpoints, partial/cancel/unknown, builder fees |
| [Funding и realtime](funding-realtime.md) | pUSD, bridge/withdrawal, settlement/redeem, сети, GEO, RTDS/PolyBolt и WebSocket |
| [Карта общего адаптера](adapter-map.md) | Возможности paper/live, нормализация, glossary, незакрытые вопросы и checklist |
| [Журнал проверки](verification.md) | Официальные источники, реально выполненные GET, расхождения, ограничения и воспроизводимость |

## Статусы доказательства

| Метка | Смысл |
|---|---|
| D — документировано | Прочитан текущий официальный контракт 06.10.2026; это не доказательство работы на нашем аккаунте |
| R — проверено публичным запросом | Выполнен конкретный безопасный GET; доказан только его ответ/страница в зафиксированный момент |
| U — не проверено | Runtime, семантика, полнота, SLA либо доступ проекта не подтверждены |
| P — требует партнёрского доступа | Нужен Builder tier/allowlist/одобрение для соответствующей функции; доступ проекта не получен |
| C — вычисляется проектом | Наша нормализация, ledger или показатель; не готовое поле площадки и не новое принятое бизнес-правило |

Endpoint-матрицы описывают D, если рядом нет R. Все подписанные запросы, payload и ответы, не связанные с файлом evidence, — **схемы/иллюстрации**. В этом исследовании нет credentials, ордеров, денежных действий, регистрации аккаунтов и изменения permissions.

## Карта сервисов и независимых версий

| Сервис | Base URL / транспорт | Версия и роль |
|---|---|---|
| Gamma | `https://gamma-api.polymarket.com` | Метаданные/discovery. Market `version` определяет position system, не версию Gamma API |
| CLOB | `https://clob.polymarket.com` | Рыночные данные и собственная торговля. CLOB V2/CTFExchangeV2 и Protocol V2/ExchangeV3 — разные поколения |
| Data | `https://data-api.polymarket.com/v2` | Публичная аналитика, история, позиции. Data API v2 не означает Protocol V2 market |
| Data legacy | `https://data-api.polymarket.com` | Мигрируемые старые маршруты; отдельное исключение accounting snapshot описано в public-data |
| Relayer | `https://relayer-v2.polymarket.com` | Wallet transactions; Builder auth, Session management beta. Никакие вызовы не выполнены |
| Bridge | `https://bridge.polymarket.com` | Quote, supported-assets, deposit/withdraw route/status; это отдельный money lifecycle |
| Market WS | `wss://ws-subscriptions-clob.polymarket.com/ws/market` | Public книги/цены/market events по asset IDs |
| User WS | `wss://ws-subscriptions-clob.polymarket.com/ws/user` | Authenticated собственные orders/trades по signer context |
| RTDS | `wss://ws-live-data.polymarket.com` | Legacy live feed; учитывать миграцию отдельных topics |
| PolyBolt | `wss://ws-live-v2.polymarket.com/ws` | Authenticated reference-price feeds; не заменяет книгу и не доказывает leader stream |

Источники: [API overview](https://docs.polymarket.com/getting-started/api), [Bridge](https://docs.polymarket.com/trading/bridge/deposit), [RTDS migration](https://docs.polymarket.com/migrate/rtds-to-polybolt), [Protocol V2 API migration](https://docs.polymarket.com/migrate/polymarket-v2/api-integrations). Точные версии SDK и OpenAPI описаны в профильных файлах; SDK не установлен и не запускался.

## Проверенные уточнения к старым материалам

- **24.10.2026** заново подтверждено как документированный срок прекращения мигрируемых Data v1 routes, с исключением `/v1/accounting/snapshot`. Это будущая дата из [migration guide](https://docs.polymarket.com/migrate/data-api-v1-to-v2), не наблюдённое отключение.
- **pUSD** заново подтверждён как trading collateral, ERC-20 на Polygon, 6 decimals и USDC backing. Публичные `_usdc` названия метрик не доказывают USDC.e collateral. [pUSD](https://docs.polymarket.com/concepts/pusd).
- **Market version обязательна для ID selection:** `v1` выбирает декодированный `clobTokenIds`, `v2` — `positionIds`, даже если оба присутствуют. Новые V2 holdings не заменяют прежние CTF holdings. [Protocol migration](https://docs.polymarket.com/migrate/polymarket-v2/overview).
- **Session Key не даёт owner общую видимость всех его orders.** Нужны отдельные signer contexts и provenance для сверки; beta доступ не подтверждён для проекта. [Session Keys](https://docs.polymarket.com/trading/session-keys).
- **Успешный GET не доказывает свежий сигнал.** В публичном probe trades обнаружен cache TTL; outcome index требует сверки с market metadata. См. [evidence и расхождения](verification.md).

## Что справочник разрешает заключить

Публичные поверхности документированы для будущего paper research. Отдельные GET проверены; полнота 72-часовой истории, задержка доставки лидера, дедупликация, WS reconnect и модель комиссий пока не прошли проектные критерии. Будущий copy execution технически предполагает отдельный permission flow, но его доступность и надёжность для нашего проекта не доказаны. Подробная [матрица readiness](adapter-map.md) не выставляет GO автоматически.
