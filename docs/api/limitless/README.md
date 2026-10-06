# Limitless API: справочник для Copy Trading MVP

Проверено **06.10.2026**. Это документационное исследование для коллеги и будущего агента. Порядок проекта остаётся: закрыть вопросы дизайна → проверить бизнес-логику → админка → технический план → реализация. Справочник не является разрешением разработки, регистрации или live-торговли.

## Как использовать в следующих задачах

1. Прочитать этот вход и [отчёт проверки](verification.md), затем раздел нужной операции.
2. Передать следующему агенту конкретный файл, endpoint и [карту адаптера](adapter-map.md), а не старый предположительный API-план целиком.
3. Перейти по прямой официальной ссылке и сверить текущую схему. Дата справочника не гарантирует неизменность API.
4. Выбрать контекст: произвольный публичный адрес, собственный профиль или принадлежащий партнёру субсчёт. Эти полномочия не взаимозаменяемы.
5. Зафиксировать единицы, идентификаторы, pagination, полноту, свежесть и raw status до нормализации. Не заменять отсутствие данных нулём.
6. Для paper использовать публичные записи и явно помеченные локальные fixtures; не отправлять команды production. Для live сначала закрыть вопросы доступа и отдельные gates проекта.

## Навигация и доказательность

| Файл | Содержание |
|---|---|
| [public-data.md](public-data.md) | Рынки, публичная история лидера, позиции, PnL, accuracy, referral, GEO |
| [authorization-partner.md](authorization-partner.md) | HMAC, API key/session, scopes, субсчета, funding/withdrawal/redeem |
| [execution.md](execution.md) | CLOB/AMM, lifecycle, cancel-replace, streams, polling, комиссии и точность |
| [examples.md](examples.md) | Публичный запрос и явно помеченные схемы private status/precision |
| [adapter-map.md](adapter-map.md) | Сопоставление с документом 23, paper/live gaps, вопросы партнёру |
| [verification.md](verification.md) | Версии, прямые источники, публичные GET, расхождения, checklist обновления |
| [public-request-evidence.json](public-request-evidence.json) | Обезличенная сводка фактических read-only запросов |
| [source-manifest.json](source-manifest.json) | Проверенные URL, время, HTTP-результат и hash прочитанных источников |

**D — документировано:** прочитана актуальная официальная страница/схема. **R — проверено публичным запросом:** получен конкретный ответ без авторизации, указанный в evidence. **U — не проверено:** нет runtime-доказательства поведения или полноты. **P — требует партнёрского доступа:** возможность описана, но для нашего аккаунта не активирована и не проверена. D и P могут сочетаться. Любые псевдозапросы/ответы в тексте — схемы или иллюстрации, кроме явно названного R. Договорённость или историческая запись проекта не становится D/R текущего API.

## Карта сервисов и версий

| Поверхность | URL / версия на дату проверки | Назначение и предел |
|---|---|---|
| REST production | `https://api.limitless.exchange` | Один глобальный endpoint, публичные reads и аутентифицированные команды. Нет региональных mirrors |
| WebSocket / Socket.IO | `wss://ws.limitless.exchange`, namespace `/markets` | Цены/книга, позиции и собственные CLOB order events; delegated REST-only |
| Документация | [официальный индекс](https://docs.limitless.exchange/llms.txt), [REST reference](https://docs.limitless.exchange/api-reference/introduction) | Страницы иногда расходятся с глобальной схемой; проверять endpoint-specific текст |
| OpenAPI | [openapi.json](https://docs.limitless.exchange/openapi.json), OpenAPI **3.0.0**, `info.version=1.0` | Метаданные спецификации, а не обещание `/v1` base path. Нынешние пути преимущественно без version prefix |
| TypeScript SDK | `@limitless-exchange/sdk` **1.1.0**, commit `8e4d897b9a2b0a9ee218ec0847aae70c620aa511` | [Зафиксированный package.json](https://github.com/limitless-labs-group/limitless-exchange-ts-sdk/blob/8e4d897b9a2b0a9ee218ec0847aae70c620aa511/package.json); код SDK в исследовании не запускался, установленный npm release не проверен |
| Сеть / расчётный актив | Base mainnet, chain ID **8453**, USDC | Нет sandbox, testnet, mock API или Base Sepolia deployment по текущему официальному introduction |
| Локальное paper | Только наш fixture/simulator | Не отдельный сервер Limitless, не исполнение production |

Источники карты: [For Developers](https://docs.limitless.exchange/developers/introduction), [WS overview](https://docs.limitless.exchange/developers/websocket/overview), [TypeScript SDK](https://docs.limitless.exchange/developers/sdk/typescript/getting-started), [Order events](https://docs.limitless.exchange/developers/websocket/order-events). Python, Go и Rust также перечислены официальным индексом; их версии здесь не фиксировались.

## Сущности и словарь

| Понятие / идентификатор | Значение и правило хранения |
|---|---|
| `account` | Ethereum wallet address в public portfolio paths; не numeric profile ID. Checksum учитывать в auth/signing, исходное написание хранить |
| `profileId`, private profile `id`, `ownerId` | Внутренний профиль. `ownerId` используется в signed order flow; `x-on-behalf-of` выбирает принадлежащий партнёру child profile. Не выводить ID из адреса самостоятельно |
| Partner / sub-account | Связь владения профилями на Limitless, а не произвольная возможность торговать за любой адрес |
| `market.id` | Числовой ID; например market leaderboard использует marketId. Не подставлять вместо slug во все пути |
| `slug` / exact market | Конкретный рынок/раунд. История и книга зависят от точного slug |
| Stable slug | Алиас повторяющегося рынка; сначала resolve, затем закрепить точный рынок. Иначе новый раунд может подменить intent |
| Group / NegRisk | Группа связанных исходов/рынков. Group price/history semantics отличаются от standalone рынка; не считать группу одним CLOB token |
| `conditionId` | On-chain идентификатор условия; не market address, slug или outcome token ID |
| Outcome / tokenId | Конкретная сторона и conditional token. Хранить как строку, large integers нельзя переводить в unsafe JS number |
| Venue / `venue.exchange`, `venue.adapter` | Контракт маршрутизации и EIP-712 verifyingContract конкретного рынка, а не торговая площадка в нашем namespace |
| `orderId`, `clientOrderId` | ID заявки площадки и наш корреляционный ключ. Не заменяют idempotency/reflection/settlement гарантии |
| `x-request-id` | Корреляция сетевого запроса; не обещание exactly-once исполнения |
| `eventId` / tradeId | ID события/сделки. OME terminal frame и settlement frame требуют разных ключей дедупликации |
| CLOB / AMM | Книга лимитных заявок / пул автоматического маркет-мейкера. Routes, quantities и fee models различаются |
| GTC / FAK / FOK | Оставить остаток в книге / исполнить доступное и отменить остаток / исполнить весь объём либо не исполнить |
| OME / settlement | Факт matching engine / состояние расчёта на chain. MATCHED не равен MINED |
| Realized / unrealized PnL | Закрытый результат / оценка открытой позиции; не равно свободным USDC, доходности копии или нашей просадке |
| Allowance / allowlist | Разрешение контракту распоряжаться токеном / разрешённый адрес вывода. Одно не заменяет другое |
| Reconcile / unknown | Сверка независимых источников / отсутствие достоверного результата операции; unknown сохраняет риск и резерв |

Определения опираются на [Market detail](https://docs.limitless.exchange/api-reference/markets/get-market), [Venue system](https://docs.limitless.exchange/developers/venue-system), [Programmatic API](https://docs.limitless.exchange/developers/programmatic-api), [Order events](https://docs.limitless.exchange/developers/websocket/order-events). Все внешние ID хранятся с `venue=LIMITLESS`, raw payload, observedAt и версией mapping по [контракту 23](../../23_dual_venue_adapter_contract.md).
