# Polymarket: получение доступа и исполнимый spike-план

Дата: 25.09.2026. Статус: готово к выполнению после команды основателя.

Этот документ превращает [описание доступа к Polymarket API](19_polymarket_api_access.md) в последовательность конкретных действий. По [ADR-0008](decisions/0008_dual_venue_product_scope.md) Polymarket является обязательной площадкой продукта и исследуется параллельно с Limitless. Результат этого плана — не production-интеграция, а проверенный набор фактов для проектирования venue-neutral copy engine и отдельное решение `GO / CONSTRAIN / STOP` по Polymarket adapter.

## 1. Границы spike

В spike входят:

- создание проектного Builder profile;
- запрос доступа к Session Keys beta;
- проверка публичных REST и WebSocket данных;
- проверка L1/L2 authentication на отдельном тестовом signer;
- проверка полномочий, жизненного цикла session key и ордеров;
- проверка builder attribution, maker/taker классификации и доступных данных для сверки комиссий;
- оценка rate limits, relayer quota, задержек и поведения после ошибок;
- формирование доказательств для окончательной архитектуры.

В spike не входят пользовательские средства, массовый onboarding, production credentials, обход GEO-ограничений, автоматическое копирование реальных пользователей и обещание доступности функций, которые Polymarket ещё не подтвердил.

## 2. Что требуется от основателя

До старта регистрации нужны:

| Входные данные | Требование |
|---|---|
| Проектное имя | одно стабильное название для Builder profile, письма и презентации |
| Проектный email | адрес с доступом минимум у двух ответственных лиц либо с настроенным recovery |
| Project owner | имя человека, контролирующего Builder profile и общение с Polymarket |
| Публичные ссылки | GitHub, актуальная презентация и сайт/landing page, если уже существует |
| Описание пилота | copy trading с бюджетами, risk limits и прозрачной комиссией; без права вывода у сервиса |
| Ожидаемый масштаб | число тестовых кошельков, ордеров в день и предполагаемый объём; допускается диапазон |
| Тестовое GEO | фактически разрешённое местоположение основателя для технического теста |
| Тестовый owner wallet | отдельный кошелёк без личных активов и истории; адрес можно фиксировать, private key нельзя |
| Ответственные за recovery | кто восстанавливает Builder profile и кто имеет право отзывать session signer |

Основатель не передаёт в чат или Git seed phrase, private key, CLOB secret/passphrase, Builder secret/passphrase, session private key, recovery codes и подписанные payload, которые можно повторно использовать.

## 3. Политика безопасных данных

### Можно хранить в Git

- публичные адреса тестовых кошельков с явной меткой `test-only`;
- market, condition, token, order и transaction identifiers;
- timestamps, latency, HTTP status, обезличенные error codes;
- публичный builder code, подтверждённый как публичный идентификатор;
- очищенные request/response fixtures без auth headers, cookies и подписей;
- агрегированные результаты и критерии `GO / CONSTRAIN / STOP`.

### Запрещено хранить в Git, документах и задачах

- seed phrase и любые private keys;
- `apiKey`, `secret`, `passphrase` для CLOB или Builder API;
- session signer private key;
- `POLY_SIGNATURE`, HMAC signature и полные auth headers;
- cookies, access/refresh tokens и recovery codes;
- сырые дампы окружения, secrets manager или логов с авторизацией.

Секреты создаются локально, сохраняются в secrets manager, разделяются по назначению и удаляются или ротируются после spike. В репозитории разрешён только `.env.example` с пустыми значениями. Логи проходят автоматическое редактирование чувствительных заголовков и полей до сохранения.

## 4. Трек A — регистрация Builder profile

Ответственный: основатель или назначенный project owner.

1. Создать отдельный проектный аккаунт Polymarket, не связанный с личным торговым кошельком.
2. Войти в `Settings → Builders`.
3. Создать Builder profile с проектным названием и контактным email.
4. Выпустить Builder API credentials через `Create New`.
5. Сохранить `key`, `secret` и `passphrase` в secrets manager; проверить, что значения не попали в clipboard history, заметки, чат и shell history.
6. Скопировать публичный `bytes32` builder code в защищённый реестр конфигурации проекта. В Git фиксировать его только после подтверждения, что это публичный идентификатор, а не credential.
7. Зафиксировать дату создания, владельца, recovery-процесс и текущий tier без секретов.
8. Проверить доступные операции и отображаемую квоту Unverified tier в интерфейсе/ответах API. Не считать документированный лимит фактическим до проверки.

Результат трека: Builder profile существует, секреты сохранены отдельно, владелец и recovery назначены, текущие права и квоты записаны.

## 5. Трек B — запрос Polymarket по Session Keys

Session Keys находятся в beta, работают только с Deposit Wallet и требуют отдельного разрешения Builder API key для session-key management. Запрос отправляется на `builder@polymarket.com` или в Builder Telegram после получения доступа к нему.

### Что сообщить

- название проекта и ссылку на Builder profile;
- Builder API key **identifier**, если Polymarket просит его для включения функции; secret и passphrase не отправляются;
- use case: controlled copy trading с пользовательским бюджетом, лимитами риска, возможностью остановки и прозрачным журналом;
- trust boundary: owner wallet остаётся у пользователя, backend не получает owner private key, execution signer не должен иметь права вывода;
- первый scope: только `CLOB`; `All` и Combos на spike не запрашиваются;
- способ хранения session private key: отдельный secrets manager, изоляция по пользователям, rotation и emergency revoke;
- ожидаемое число тестовых кошельков и relayer-транзакций в день;
- просьбу подтвердить совместимость copy-trading use case с текущей beta;
- GitHub, презентацию, сайт и контакт ответственного.

### Вопросы, на которые нужен письменный ответ

1. Разрешён ли описанный server-side execution с отдельным session signer для каждого Deposit Wallet?
2. Можно ли ограничить session signer только scope `CLOB` и гарантирует ли протокол отсутствие withdrawal capability?
3. Какой фактический срок session key поддерживается сейчас, и можно ли выбрать срок короче максимального?
4. Что происходит с открытыми ордерами при expiry и revoke: остаются, отменяются или требуют отдельной отмены?
5. Может ли revoked/expired signer читать собственные ордера и fills для reconciliation?
6. Какие операции расходуют relayer quota: создание Deposit Wallet, authorize, revoke, approve, cancel и settlement?
7. Какие rate limits применяются к Builder API, CLOB authenticated requests и session-key operations?
8. Какой рекомендуемый способ срочно отозвать signer и отменить открытые ордера при компрометации?
9. Какие данные доступны для сверки builder attribution и фактически начисленной builder fee?
10. Нужен ли Verified tier до ограниченного закрытого пилота и какие материалы потребуются для upgrade?

Результат трека: сохранён очищенный письменный ответ Polymarket, перечислены подтверждённые права, ограничения и нерешённые вопросы. Устное обещание не закрывает архитектурный gate.

## 6. Трек C — read-only data spike

Этот трек можно начать без Builder approval и торговых credentials. Он выполняется параллельно трекам Limitless и использует общий будущий формат событий с обязательным полем `venue = polymarket`.

### Проверяемые поверхности

| Поверхность | Базовый адрес | Минимальная проверка |
|---|---|---|
| Gamma REST | `https://gamma-api.polymarket.com` | список активных markets/events, metadata, token/condition identifiers, pagination |
| CLOB REST | `https://clob.polymarket.com` | price, midpoint, spread, order book, tick/minimum size и timestamp/consistency |
| Data REST | `https://data-api.polymarket.com` | публичные activity, positions/trades, cursor pagination и backfill |
| CLOB market WS | `wss://ws-subscriptions-clob.polymarket.com/ws/market` | book/price updates, reconnect, heartbeat и восстановление после разрыва |
| RTDS | `wss://ws-live-data.polymarket.com` | trade activity, event identifiers, порядок и задержка сообщений |
| GEO check | официальный geoblock endpoint | разрешённый, blocked и close-only ответы без попыток обхода |

### Набор данных

- 20–30 активных рынков разных типов;
- 3–5 публичных адресов активных трейдеров для наблюдения;
- минимум 72 часа непрерывной записи;
- контрольные budgets `$10`, `$50`, `$200` для симуляции достижимой копии;
- синхронизированное UTC-время и локальный receive timestamp для каждого события.

### Измерения

- полнота и стабильность identifiers между Gamma, CLOB, Data API и WebSocket;
- задержка от наблюдаемого fill/изменения до появления в каждом источнике: p50, p95, p99;
- дубли, перестановка, пропуски и поздние события;
- backfill после отключения на 1, 5 и 30 минут;
- pagination boundary, rate-limit response и безопасный retry/backoff;
- возможность отличить buy, sell, partial fill, cancel и market resolution;
- достижимая цена копии относительно видимой сделки лидера;
- минимальный размер, rounding и влияние глубины книги на малые бюджеты.

### Артефакты

- очищенные recorded fixtures;
- таблица сопоставления identifiers;
- отчёт latency/data quality;
- предварительный `source_event_key` и правила дедупликации;
- список источников истины и недоступных данных;
- решение, пригоден ли источник для alert, shadow copy и live copy.

## 7. Трек D — permission и authentication lifecycle

Выполняется после регистрации Builder profile и только на отдельном тестовом owner wallet.

### D1. CLOB L1/L2

1. Подписать L1 EIP-712 сообщение owner/test signer локально.
2. Создать или derive CLOB credentials.
3. Проверить authenticated read открытых ордеров и fills.
4. Повторить derive с тем же nonce и проверить ожидаемую идемпотентность.
5. Проверить неверную подпись, неверный timestamp, неверный nonce, просроченный запрос и отсутствующий header.
6. Ротировать credentials либо документировать подтверждённый механизм их замены/отзыва.

Проходной результат: owner control доказан подписью; private key не передавался backend; L2 credential изолирован; ошибки авторизации различимы и не запускают бесконечные retries.

### D2. Deposit Wallet и Session Key

После письменного enablement от Polymarket:

1. Создать или подключить отдельный Deposit Wallet.
2. Сгенерировать новый EOA session signer внутри контролируемого окружения.
3. Авторизовать его только со scope `CLOB` и обязательным expiry.
4. Убедиться, что signer виден как active и может выполнять только заявленные торговые операции.
5. Проверить, что signer не может вывести средства или расширить собственные полномочия.
6. Проверить повторную авторизацию, конфликт expiry и попытку использовать неподдерживаемый scope.
7. Выполнить revoke и подтвердить, что новые торговые операции отклоняются.
8. Проверить чтение состояния, отмену открытых ордеров и reconciliation после revoke/expiry.
9. Сгенерировать новый signer и проверить recovery/rotation без потери истории.

Проходной результат: полномочия ограничены `CLOB`, withdrawal недоступен, revoke проверен фактически, rotation восстанавливает торговлю без смешения signer identity.

## 8. Трек E — order lifecycle

Этот трек начинается только после успешных треков C и D. Любая минимальная реальная транзакция требует отдельной команды основателя и разрешённого GEO. До этого используется локальная симуляция или доступная тестовая среда.

Проверить следующие сценарии:

| Сценарий | Что зафиксировать |
|---|---|
| Place и полный fill | client intent id, platform order id, fills, maker/taker, цена, размер, fees |
| Partial fill | исполненная и оставшаяся части, повторные updates, безопасная отмена остатка |
| Cancel до fill | подтверждение отмены из REST и user channel, отсутствие позднего fill |
| Cancel/fill race | конечное состояние по источнику истины, отсутствие двойного ордера |
| FAK/FOK/GTC | поддержка, rejection semantics и mapping в общий adapter contract |
| Unknown result | таймаут после submit, поиск по idempotency/client intent, запрет слепого retry |
| Reconnect | восстановление user WebSocket, backfill и устранение дублей |
| Session revoke/expiry | поведение новых и открытых ордеров, отдельная emergency cancellation |
| Maintenance/restart | остановка новых покупок, сохранение журнала, последующая reconciliation |
| Resolution/settlement | изменение позиции и баланса, источник истины, связь с virtual lot |

Builder code добавляется только к специально отмеченным тестовым ордерам. Для каждого fill сверяются attribution, maker/taker status, platform fee, builder fee и сервисный fee ledger. Execution strategy не имеет права выбирать taker ради большей комиссии.

## 9. Fault injection и отрицательные тесты

Без этих тестов положительный happy path не закрывает spike:

- повтор одного source event;
- перестановка двух событий;
- пропуск сообщения WebSocket и последующий REST backfill;
- HTTP 429, 5xx и сетевой таймаут до/после отправки;
- неизвестный результат submit;
- частичный fill после cancel request;
- истёкший или отозванный session signer;
- неверный scope;
- несовпадение внутреннего ledger и platform state;
- смена geoblock результата до новой покупки;
- падение worker между записью intent и API call, а также после API call до записи ответа.

Каждый тест должен показать, что система переходит в явное состояние `BLOCKED`, `RECONCILIATION_REQUIRED` или эквивалентное, не создаёт повторный ордер и не продолжает новые покупки при неизвестном состоянии.

## 10. Критерии успеха

### `GO` на Polymarket paper-trading adapter

- 72-часовая запись завершена без необъяснимых систематических пропусков;
- определён стабильный `source_event_key` и детерминированная дедупликация;
- identifiers и основные состояния нормализуются в venue-neutral contract;
- измерены latency и глубина книги для `$10/$50/$200`;
- reconnect/backfill воспроизводимо закрывает разрывы;
- все fixtures и логи очищены от секретов.

### `GO` на ограниченный live spike

- Builder profile и CLOB credentials работают;
- Polymarket письменно подтвердил Session Keys use case;
- scope `CLOB`, expiry, revoke и отсутствие withdrawal capability проверены фактически;
- неизвестный submit не создаёт повторный ордер;
- place/partial/cancel/fill/reconnect проходят reconciliation;
- geoblock проверяется перед торговлей и блокирует новые позиции согласно ответу площадки;
- builder attribution и полная стоимость сделки наблюдаемы и сверяемы;
- есть emergency stop, rotation runbook и назначенные ответственные;
- основатель отдельно разрешил минимальный реальный тест.

### `CONSTRAIN`

Polymarket остаётся обязательным adapter, но live-функции ограничиваются, если:

- Session Keys доступны не всем пользователям или требуют ручного enablement;
- latency подходит для shadow mode, но недостаточна для части быстрых стратегий;
- малый бюджет не проходит minimum size/slippage gate;
- relayer/rate limits требуют очереди, меньшего пилота или Verified tier;
- revoke не отменяет открытые ордера и нужен отдельный обязательный cancellation workflow.

### `STOP` для live execution до изменения условий

- session signer получает или может получить withdrawal capability;
- невозможно надёжно отозвать signer;
- неизвестный результат запроса нельзя безопасно reconcile;
- GEO-проверку нельзя выполнить до торговли;
- публичные данные не позволяют воспроизводимо определить событие лидера;
- фактическая комиссия или attribution не поддаются сверке;
- Polymarket не разрешает заявленный use case.

`STOP` относится к live execution. Read-only аналитика и paper trading могут продолжаться, если это разрешено условиями площадки.

## 11. Итоговые артефакты и решение

После spike в репозитории должны появиться только очищенные материалы:

1. `polymarket-access-result` — фактические права, tier, квоты и ответы Polymarket;
2. `polymarket-data-quality-report` — completeness, latency, дубли и backfill;
3. `polymarket-identifier-map` — market/event/condition/token/order/fill identifiers;
4. `polymarket-permission-matrix` — owner, Builder, CLOB credential и session signer;
5. `polymarket-order-lifecycle-report` — состояния, ошибки и reconciliation;
6. `polymarket-security-runbook` — create, rotate, revoke, emergency stop и redaction;
7. обновлённый venue adapter contract;
8. подписанное основателем решение `GO / CONSTRAIN / STOP` отдельно для paper и live.

Результаты сопоставляются с параллельным Limitless spike по одной матрице: data latency, permission boundary, order lifecycle, fees, reconciliation, GEO и операционная стоимость. Выбор порядка live-включения делается по проверенным результатам, а не по известности бренда или наличию партнёрского контакта.

## 12. Рекомендуемый порядок выполнения

| Этап | Зависимость | Можно выполнять параллельно |
|---:|---|---|
| 1. Подготовить входные данные основателя | нет | Limitless registration |
| 2. Создать Builder profile | этап 1 | read-only data spike |
| 3. Отправить Session Keys request | этап 2 | 72-часовая запись и симулятор |
| 4. Завершить read-only отчёт | 72 часа данных | Limitless latency report |
| 5. Проверить L1/L2 и Deposit Wallet | этап 2, разрешённое GEO | adapter contract |
| 6. Проверить Session Key lifecycle | письменный enablement | fault-injection harness |
| 7. Выполнить simulated order lifecycle | этапы 4–6 | Limitless permission tests |
| 8. Запросить разрешение на minimal live test | пройдены gates | нет |
| 9. Провести минимальный live test | отдельная команда основателя | нет |
| 10. Принять `GO / CONSTRAIN / STOP` | все отчёты | итог Limitless spike |

## 13. Официальные источники

- API surfaces и authentication: https://docs.polymarket.com/getting-started/api
- Wallets and Authentication: https://docs.polymarket.com/trading/wallets-auth
- Session Keys Beta: https://docs.polymarket.com/trading/session-keys
- Builder Program: https://docs.polymarket.com/programs/builders/overview
- Builder tiers: https://docs.polymarket.com/programs/builders/tiers
- Builder Fees: https://docs.polymarket.com/programs/builders/fees
- Geographic Restrictions: https://docs.polymarket.com/api-reference/geoblock

