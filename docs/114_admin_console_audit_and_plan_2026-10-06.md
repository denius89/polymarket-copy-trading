# Аудит и план операционной консоли Shadow

Дата среза: **06.10.2026**.

Этот документ сводит действующие бизнес-решения, текущую Figma, пользовательские сценарии, API-исследования Polymarket и Limitless и формирует план операционной консоли. Это **план и аудит**, а не разрешение на дизайн, frontend, backend, подключение аккаунтов или реальные операции.

## 1. Как читать статусы

| Статус | Значение |
| --- | --- |
| **Согласовано** | закреплено прямым решением владельца или действующим ADR |
| **Предложено** | рекомендация этого аудита; требует принятия до реализации |
| **Нужна проверка** | зависит от незакрытого правила, фактических прав, API или пользовательской приёмки |

По возможностям площадок дополнительно различаем четыре уровня: **описано в документации → доступно нашему аккаунту → интегрировано → разрешено для live**. Наличие endpoint не подтверждает остальные три уровня.

## 2. Итог аудита

1. **Согласовано.** Первая версия продукта остаётся paper/shadow: без реальных денег и реальных ордеров. Админка первой версии управляет внутренними demo-сессиями и наблюдает публичные данные площадок.
2. **Согласовано.** Консоль нужна для наблюдения, поддержки, остановки новых demo-действий, разбора инцидентов и сверки. Она не является торговым терминалом, кошельком или платёжной системой.
3. **Согласовано.** Polymarket и Limitless — две самостоятельные площадки. Их идентификаторы, состояния, комиссии, ошибки и evidence нельзя смешивать или переносить между похожими рынками.
4. **Нужна проверка.** Публичные read-only API пригодны для каталога, публичной истории, цен и части диагностики. Партнёрские права, закрытые данные и полный lifecycle собственных операций нашим проектом не подтверждены.
5. **Предложено.** Первый полезный релиз админки строится вокруг внутренних сущностей Shadow и публичных чтений площадок. Все live-функции показываются только как будущие capability-gated состояния.
6. **Согласовано.** Доход владельца, расходы сервиса и партнёрские обязательства ведутся отдельно от paper-бюджетов, позиций, резервов и P&L пользователей.
7. **Нужна проверка.** Текущая Figma даёт связанную основу A01–A06 и Proposed owner finance, но не подтверждает backend, постоянное хранение, RBAC, финансовый учёт или полную UX-приёмку.

## 3. Границы версий

### 3.1 Demo / paper V1

| Область | Статус | Граница |
| --- | --- | --- |
| Paper-сессии, виртуальные заявки, позиции и резервы | **Согласовано** | только внутреннее состояние Shadow; одна активная сессия пользователя |
| Публичные данные Polymarket и Limitless | **Согласовано** | read-only с временем источника, свежестью и явным состоянием `unknown` |
| Пользователи, инциденты, сверка, feedback | **Согласовано** | минимальная операционная консоль ADR-0011 |
| Поддержка | **Предложено** | очередь тикетов и переписка на основе уже спроектированного пользовательского lifecycle |
| Безопасные действия | **Согласовано** | пауза новых demo-операций, отключение сессии, повторное чтение состояния, запуск сверки, запись решения |
| Тарифы | **Согласовано** | реальная комиссия alpha = 0%; будущие ставки видны отдельно как simulation/policy |
| Owner finance | **Предложено** | read-only пустые/отключённые состояния и схема будущего учёта; без ложной выручки в paper |
| Контент/FAQ | **Предложено** | максимум просмотр версии; полноценный CMS не обоснован |
| Реферальные выплаты | **Согласовано** | кабинет и выплаты агентам не входят в MVP |

### 3.2 Будущий live

| Область | Статус | Условие появления |
| --- | --- | --- |
| Собственные orders/fills площадок | **Нужна проверка** | фактические scopes, безопасные private reads, signer/profile provenance, fault tests |
| Submit/cancel | **Нужна проверка** | отдельное решение владельца, idempotency/reconciliation и security gates |
| Аккаунты/делегирование | **Нужна проверка** | Builder/Partner approval, ownership/recovery/revoke, GEO и eligibility |
| Funding/withdrawal | **Согласовано** | реальное исполнение исключено из demo V1 и торгового execution-worker; переключатели доступности пути через Shadow включены в ADM-17 по ADR-0030 |
| Реальные комиссии и выплаты | **Нужна проверка** | способ взимания, maker/taker classification, evidence поступления и возвратов |
| Live-финансы владельца | **Нужна проверка** | подтверждённые источники attribution, receiving accounts, payout completeness и FX |

## 4. Роли и права

Согласно [ADR-0029](decisions/0029_configurable_admin_roles_and_unified_operations.md), отдельные роли `Operator`, `Support`, `Read only` и `Auditor` не зашиваются в систему. Встроенной системной ролью остаётся **Owner**. Остальные роли создаются из permission scopes; для быстрого назначения админка предлагает изменяемые пресеты **Ops Lead**, **Operations**, **Marketer** и **Auditor**.

Пресет **Operations** объединяет прежние функции Operator и Support: работа с сессиями, incidents, health, reconciliation, тикетами и минимальным пользовательским контекстом. Пресеты можно копировать и ограничивать по разделам, окружению, площадке и типу данных.

| Группа разрешений | Примеры scopes | Стартовый пресет |
| --- | --- | --- |
| Операции и здоровье | `operations.view`, `session.pause`, `session.disconnect_demo`, `reconciliation.run`, `incident.assign`, `incident.resolve`, `health.view` | Operations; расширенный набор у Ops Lead |
| Поддержка | `support.view`, `support.reply`, `support.assign`, `feedback.manage`, `user_context.view_minimal` | Operations |
| Маркетинг и контент | `marketing.*`, `content.edit`, `content.publish` | Marketer; публикация по scopes без обязательного Owner approval, включая критические тексты (ADR-0031) |
| Аудит и экспорт | `audit.view`, `audit.export`, `finance.view_aggregate` | Auditor; по умолчанию только просмотр, экспорт выдаётся отдельно |
| Тарифы и финансы | `pricing.view/simulate/edit/review/publish/override`, `finance.view` | отдельное назначение; публикация и overrides ограничены утверждённым workflow |
| Доступ и безопасность | `staff.view`, `role.manage`, `access.revoke`, `emergency.activate`, `emergency.recover` | Owner; отдельные emergency scopes могут быть делегированы |

Правила RBAC: deny by default; проверка каждого scope на сервере; запрет самостоятельного повышения прав; явное разделение view/edit/review/publish/export; обязательный reason и append-only audit для назначения и отзыва доступа; срок действия и ограничения scope там, где это нужно. Ни одна роль не получает private keys, HMAC secrets, ручной вывод средств, сделку за пользователя или blind resend операции с неизвестным итогом.

## 5. Предлагаемая карта разделов

Стабильные IDs ниже вводятся для плана. Они не заменяют имена существующих Figma frames до отдельной дизайн-итерации.

| ID | Раздел | V1 | Что уже есть | Чего не хватает | Статус |
| --- | --- | --- | --- | --- | --- |
| ADM-01 | Operations overview | да | Figma A01 `51:3` | health двух площадок, freshness, session/incident counters, scope pause | **Согласовано / расширить** |
| ADM-02 | Users | да | только detail одной сессии | список, поиск, user detail, locale, timeline, связанные тикеты | **Согласовано / отсутствует** |
| ADM-03 | Sessions | да | A04 `51:222`, A06 `1879:25495` | общий список, stable lifecycle, version/effective policy | **Согласовано / частично** |
| ADM-04 | Incidents | да | A02 `51:89`, A03 `51:159`, состояния очереди | severity model, ownership policy, resolution contract | **Согласовано / частично** |
| ADM-05 | Reconciliation | да | A05 `121:1513` | журнал попыток, late result, mismatch, durable evidence | **Согласовано / частично** |
| ADM-06 | Venues & data | да | отдельного раздела нет | API/feed health, freshness, latency, last success/error, capability evidence | **Согласовано / отсутствует** |
| ADM-07 | Traders & ingestion | да, read-only | данные видны в user UI | quality/completeness, rating method/version, gaps | **Предложено** |
| ADM-08 | Tariffs & commissions | simulation/read-only V1; управление позже | Proposed finance и старые схемы | version registry, calculation rules, referral tiers, overrides, preview/publish/rollback | **Согласована потребность; контракт предложен** |
| ADM-09 | Support | да | user-side lifecycle готов | admin queue, conversation, context, access/retention rules | **Предложено** |
| ADM-10 | Notifications | да, read-only | user-side notifications | delivery/failure/retry evidence, channel status | **Согласовано / отсутствует** |
| ADM-11 | Feedback | да | user-side form | очередь, связь с user/session, категории и status | **Согласовано / отсутствует** |
| ADM-12 | Audit log | да | только evidence в отдельных frames | общий append-only журнал, фильтры, correlation/reference IDs | **Согласовано / отсутствует** |
| ADM-13 | Owner finance | схема сейчас, данные позже | Proposed OF01–OF06 RU/EN | подтверждённые источники, ledger, reconciliation, права | **Предложено / источник не подключён** |
| ADM-14 | Staff & access | базовый контур V1 | нет | staff list, sign-in, 2FA, expiry, role builder, presets, permission scopes, assignment, permission denied, access history | **Согласована модель; детальные scopes уточняются** |
| ADM-15 | Integrations & security | health/read-only metadata V1 | нет | connection registry, capabilities, API/WS/signer health, key metadata; credential rotation/revoke позже | **Согласовано — ADR-0032** |
| ADM-16 | Content & localization | модель данных до разработки; редактор позже | RU/EN тексты и user FAQ есть в Figma | locale registry, translation catalog, workflow, preview/publish/rollback; модульный landing builder позже | **Предложено, архитектурная основа обязательна** |
| ADM-17 | Emergency control center | базовый global/scoped stop V1 | kill switch упомянут в ранней карте, рабочего экрана нет | независимый control plane, server-side enforcement, status page, recovery checklist, DEPOSITS_OFF / WITHDRAWALS_OFF для пути через Shadow | **Согласована потребность; контракт предложен** |
| ADM-18 | Marketing & communications | transactional/in-app foundation V1; кампании позже | notifications и Telegram есть на user side | consent, segments, campaigns, channel delivery, frequency caps, analytics | **Согласована потребность; контракт предложен** |

## 6. Основные операторские сценарии

### 6.1 Разбор инцидента

`Overview → очередь → фильтр/поиск → incident → evidence → операция/сессия → read-only сверка → заметка/назначение → resolution`.

- **Согласовано:** unknown не превращается в success вручную.
- **Согласовано:** resolution фиксирует решение инцидента, но не переписывает финансовую или торговую истину.
- **Предложено:** обязательные поля resolution: причина, evidence, actor, время, затронутый scope, audit reference.

### 6.2 Поиск пользователя

`Users → user → sessions → session → positions / orders / activity / support timeline`.

- **Согласовано:** данные каждой площадки и каждой сессии сохраняют собственный venue и identifiers.
- **Согласовано:** доступ Operations к пользовательским данным ограничивается минимальным контекстом, необходимым для операции или тикета; расширение выдаётся отдельными scopes.
- **Нужна проверка:** PII, retention, экспорт и удаление.

### 6.3 Unknown или partial result

`Incident → operation identity → reread той же операции → late-fill check → reserve/exposure → reconcile`.

- **Согласовано:** никакого blind resend.
- **Согласовано:** резерв удерживается, пока исход неизвестен; дополнительные fills уменьшают только подтверждённый остаток.
- **Нужна проверка:** сроки повторных чтений, источник окончательности и terminal state по каждой площадке.

### 6.4 Проблема площадки или данных

`Venue health → stale/feed incident → affected sessions → pause new demo BUY → read-only recheck → controlled recovery`.

- **Согласовано:** missing/unknown не равен нулю и не отображается зелёным healthy.
- **Предложено:** capability, account access и runtime health показываются разными полями.
- **Нужна проверка:** точные пороги freshness/latency и правила снятия паузы.

### 6.5 Поддержка

`Ticket queue → user/session context → conversation → waiting state → resolution`.

- **Согласовано:** lifecycle пользователя: open / waiting_support / waiting_user / resolved / closed; draft/submitting/send_unknown — отдельное состояние доставки.
- **Предложено:** тикет может ссылаться на incident, но не заменяет reconciliation.
- **Нужна проверка:** assignment, SLA, reopen/close rights, attachments, retention.

### 6.6 Финансы владельца

`Overview → journal → basis/evidence → receiving account → reconciliation discrepancy → append-only correction`.

- **Согласовано:** внутренний transfer не является revenue; partial receipt не закрывает весь accrual.
- **Предложено:** в paper V1 показывать честные empty/source disconnected состояния.
- **Нужна проверка:** источники фактического начисления, получения, payout, FX и attribution.

### 6.7 Сотрудники, роли и доступ

`Staff & access → сотрудник → пресет или кастомная роль → scopes и ограничения → активные сессии → история изменений → revoke`.

- **Предложено:** Owner видит сотрудников, роли, статус 2FA, последний вход, активные admin-сессии и историю прав.
- **Согласовано:** отдельный Support отсутствует; Operations объединяет операционные и support-задачи.
- **Согласовано:** Owner — встроенная роль; Ops Lead, Operations, Marketer и Auditor — изменяемые пресеты кастомных ролей.
- **Согласовано:** выдача, изменение и отзыв роли создают append-only audit event; пользователь не может повысить собственные права.
- **Согласовано:** Auditor по умолчанию имеет только просмотр разрешённых разделов; экспорт и любые mutations выдаются отдельными scopes.
- **Нужна проверка:** кто может приглашать сотрудников, нужен ли dual approval, срок admin-сессии и break-glass procedure.

### 6.8 Интеграции, ключи и здоровье подключений

`Integrations → connection → capability/access → runtime health → incidents → key metadata → rotation/revoke history`.

- **Предложено:** одна карточка подключения соответствует конкретным `venue + environment + account/profile + signer context + credential set`; общий зелёный статус без этого контекста запрещён.
- **Предложено:** публичный API, private REST, WebSocket, signer/relayer, RPC/indexer и внутренний adapter контролируются отдельными health checks.
- **Согласовано — ADR-0032:** V1 показывает health/metadata обеих площадок и read-only диагностику. Отзыв admin-сессий доступен в ADM-14; создание, ротация и отзыв credentials интеграций остаются отдельным следующим этапом.
- **Согласовано:** secret/private key/passphrase никогда не показывается, не копируется и не возвращается из админки.
- **Нужна проверка:** фактические Builder/Partner scopes, ownership, rate limits, срок жизни ключей, revoke propagation и аварийный recovery.

### 6.9 Контент, языки и лендинг

`Content & localization → surface → content key/page → locale → draft → preview/validation → publish/schedule → rollback`.

- **Предложено:** все пользовательские тексты получают стабильные content keys до разработки; текст не зашивается непосредственно в компоненты.
- **Предложено:** языки включаются отдельно для landing, application, admin, notifications, email/Telegram, help и legal surfaces.
- **Предложено:** управление текстами приложения строится раньше визуального редактора лендинга. Лендинг позже собирается из заранее разрешённых блоков, а не из произвольного HTML/JavaScript.
- **Предложено:** публикация создаёт неизменяемую версию; работающие сессии, уведомления и важные действия сохраняют `content_version`, чтобы восстановить показанный пользователю текст.
- **Предложено:** финансовые, риск-, согласительные и юридические тексты защищены повышенным workflow и не могут менять смысл действующей policy без связанной версии правила.
- **Согласовано:** edit/publish выдаются отдельно, сотрудник публикует самостоятельно; автоматические проверки, история и rollback обязательны. Языки после EN/RU остаются открытым вопросом.

### 6.10 Аварийное отключение проекта

`Emergency control center → scope и уровень → impact preview → причина/incident → activate → verify enforcement → monitor/reconcile → recovery review → restore`.

- **Согласовано:** проекту нужен аварийный рубильник, который немедленно прекращает новые действия при критической ситуации.
- **Предложено:** рубильник работает на сервере и применяется до очередей, adapters и workers; скрытие кнопок в интерфейсе не считается отключением.
- **Предложено:** сбор evidence, market/account reads, audit log, health telemetry и reconciliation продолжаются, чтобы не потерять состояние системы.
- **Предложено:** аварийный stop сам по себе не закрывает позиции, не отменяет unknown, не снимает reserves, не удаляет данные и не отзывает ключи.
- **Предложено:** пользователь получает maintenance/read-only экран с честным status ID; операционная консоль остаётся доступна отдельным авторизованным сотрудникам.
- **Нужна проверка:** полномочия активации и восстановления, scoped levels, правила безопасного уменьшения риска и out-of-band доступ.

### 6.11 Тарифы, комиссии и партнёрские условия

`Tariffs & commissions → policy set → tariff version → scope/rules → simulator → review → schedule/publish → monitoring/correction`.

- **Согласовано:** фактическая комиссия закрытой alpha равна 0%; будущие paid-тарифы не должны случайно стать активными в demo.
- **Согласовано:** комиссия Shadow начисляется только на фактически исполненную часть автоматического buy/sell; unfilled remainder и отменённая часть не являются базой.
- **Согласовано:** расходы площадки/сети, комиссия Shadow и партнёрское вознаграждение — разные строки и разные ledger entries.
- **Предложено:** изменение тарифа всегда создаёт новую неизменяемую версию с `effective_at`; прошлые начисления не пересчитываются молча.
- **Предложено:** индивидуальные и VIP-условия задаются ограниченным override с началом/окончанием, причиной, Owner approval и audit; произвольное ручное изменение начисления запрещено.
- **Предложено:** до публикации обязательны симуляция, сравнение с текущей версией и проверка ceiling/invariants.
- **Нужна проверка:** tier thresholds, eligibility VIP, валюта расчёта/оплаты, точные rounding/minimum rules и механизм фактического взимания в live.

### 6.12 Маркетинг, уведомления и рассылки

`Marketing → audience → campaign → channels/locales → preview/test → validation → schedule/send → delivery/analytics → pause/close`.

- **Согласовано:** нужен отдельный маркетинговый раздел для клиентских уведомлений и будущих рассылок.
- **Предложено:** обязательные операционные сообщения, support, security и marketing communications хранятся раздельно и имеют разные consent/unsubscribe rules.
- **Предложено:** первая версия поддерживает in-app announcements и системные шаблоны; массовые email/Telegram/push-кампании подключаются после consent, provider и legal checks.
- **Предложено:** текст и переводы кампаний берутся из ADM-16, но каждая отправка фиксирует неизменяемую content version.
- **Предложено:** сегменты строятся из разрешённых продуктовых признаков и сохраняют snapshot/definition; чувствительные данные и произвольная выгрузка контактов не используются.
- **Согласовано:** коммуникация не обещает доход, не скрывает paper/demo режим и не подменяет уведомления об инцидентах или финансовой операции.
- **Нужна проверка:** допустимые каналы/consent по GEO, provider, retention, attribution window и роли публикации кампаний.

## 7. Данные, API и права

| Функция | Источник | Права сейчас | V1 | Пробел / состояние ошибки | Статус |
| --- | --- | --- | --- | --- | --- |
| Demo users/sessions/orders/lots | внутренняя БД, ledger, event log Shadow | внутренний RBAC | RO + согласованные demo-действия | площадки не знают наши сессии; коррекции только добавочной записью | **Согласовано** |
| Polymarket health/catalog/book | Data/Gamma/CLOB public APIs | публичное чтение | RO | HTTP 200 не равен trading ready; snapshot может устареть | **Описано, частично проверено** |
| Limitless catalog/book/history | public markets/portfolio APIs | публичное чтение | RO | универсальный health contract не подтверждён; nullable/partial data | **Описано, частично проверено** |
| Public trader history/positions | PM Data и LL portfolio | публичное чтение | RO | cache, retention, cursor completeness и realtime не доказаны | **Нужна проверка** |
| Rating | внутренний расчёт + публичные данные | внутренний | RO | venue metrics не равны нашей методике | **Нужна проверка** |
| PM own orders/fills/session keys | CLOB private + user WS + Relayer | Builder/L2/signer context | future RO | доступ проекта и видимость между signer contexts не подтверждены | **Нужна проверка** |
| LL own/delegated orders | private portfolio/orders/WS | scoped HMAC, partner/delegated capabilities | future RO | REST/WS видимость child accounts различается; capabilities не подтверждены | **Нужна проверка** |
| Submit/cancel | private APIs обеих площадок | подпись + scoped credentials | вне V1 | unknown outcome, no proven universal idempotency, partial/cancel races | **Будущее, отдельный GO** |
| GEO/eligibility | PM geoblock + venue rules; LL restrictions | публичные правила/контекст запроса | RO gate | IP check не доказывает eligibility пользователя; отсутствие запрета не является разрешением | **Нужна проверка** |
| Funding/withdrawal | отдельные bridge/relayer/withdraw APIs | отдельные высокорисковые права | исключено | credential isolation, recovery и compliance | **Согласовано вне V1** |
| Owner attribution/revenue | venue builder/referral data + внутренний ledger | partner/builder + Owner | future RO | venue rewards не равны комиссии Shadow | **Нужна проверка** |
| Support/notifications/content | только внутренние сервисы | внутренний RBAC | internal | площадки не предоставляют наши тикеты и контент | **Предложено** |
| Secrets metadata | KMS/secret manager metadata | изолированный security scope | только status/ID/expiry | secret/private key никогда не рендерится и не экспортируется | **Согласовано** |

### 7.1 Реестр подключений

**Предложено:** каждое подключение хранится как отдельная запись `ConnectionProfile`, а не как один флаг «Polymarket работает» или «Limitless работает».

| Поле | Что показывает |
| --- | --- |
| `venue`, `environment` | площадка и production/sandbox/test контекст |
| `account_id`, `profile_id`, `wallet_id` | публичные или маскированные идентификаторы владельца подключения |
| `signer_context` | какой signer/session/delegated child имеет доступ к данным и операциям |
| `capabilities` | documented, account-granted и runtime-verified возможности раздельно |
| `credential_ref` | только внутренний ID секрета в KMS, без значения секрета |
| `scopes`, `expires_at`, `last_used_at` | права и жизненный цикл доступа |
| `adapter_version`, `config_version` | какая версия интеграции и конфигурации обслуживает соединение |
| `owner_team`, `runbook_url` | ответственный и инструкция реакции |

### 7.2 Компоненты health status

Единый статус подключения вычисляется из отдельных проверок, но оператор всегда может раскрыть составляющие.

| Проверка | Что измеряем | Пример состояния |
| --- | --- | --- |
| API reachability | DNS/TLS/HTTP, status code, latency, timeout | healthy / degraded / unavailable |
| Authentication | credential accepted, expiry, scope mismatch | healthy / expiring / permission missing / revoked |
| Account capability | builder/partner/delegated permission фактически доступна | verified / documented only / denied / unknown |
| Market data freshness | source time, observed time, age, gaps | fresh / stale / partial / disconnected |
| WebSocket | connected, reconnect count, last message, sequence gaps | healthy / reconnecting / stale / gap detected |
| Signer/relayer | signer identity, authorization, revoke state, heartbeat | ready / restricted / expired / unknown |
| RPC/indexer | chain height/lag, last success, provider errors | healthy / lagging / unavailable |
| Adapter | process/version, queue lag, error rate, circuit breaker | healthy / degraded / paused / failed |
| Reconciliation | last successful run, unresolved mismatches, oldest unknown | healthy / attention / critical |
| Rate limits | remaining budget, reset time, throttles | normal / constrained / exhausted |

**Предложено:** агрегированный статус использует порядок `critical → unavailable → permission_missing → stale → degraded → healthy`; `unknown` остаётся отдельным состоянием и не превращается в healthy.

### 7.3 Что видит оператор

На карточке подключения показываются:

- текущий агрегированный статус и затронутые функции;
- время последней успешной и последней неуспешной проверки;
- latency, freshness, reconnects, rate-limit budget и adapter version;
- account/profile/signer context без секретов;
- granted scopes и отсутствующие обязательные scopes;
- количество затронутых demo/live-сессий и связанных incidents;
- последние изменения конфигурации, ротации и revoke;
- ссылка на runbook и audit/reference ID.

### 7.4 Контролируемые действия

| Действие | V1 | Ограничение | Статус |
| --- | --- | --- | --- |
| Повторить безопасный health check | да | read-only, rate-limited, с audit reference | **Предложено** |
| Переподключить WebSocket adapter | да, после технического контракта | не меняет orders/financial truth | **Предложено** |
| Поставить adapter на паузу | да | scope preview, affected sessions, reason | **Предложено** |
| Перевести affected demo sessions в запрет новых BUY | да | не закрывает позиции и не снимает reserve | **Согласованная операционная граница** |
| Изменить scopes или account binding | нет в V1 | отдельное подтверждение Owner и повторная авторизация | **Нужна проверка** |
| Создать/ротировать/отозвать credential | нет в первой demo-версии | KMS workflow, dual control рекомендуется, audit обязателен | **Предложено позже** |
| Показать или экспортировать secret | никогда | действие отсутствует | **Согласовано** |

Автоматический recovery допустим только для доказанно безопасных транспортных действий: reconnect с backoff, переключение на заранее утверждённый read-only endpoint и повтор health check. Автоматическая отправка ордера, снятие unknown или изменение финансовой записи запрещены.

### 7.5 История и оповещения

**Предложено:** health measurements хранятся как time series, а значимые переходы — как append-only события. Оповещение создаётся при смене состояния, превышении порога, истечении credential, потере scope, длительном stale, sequence gap или reconciliation mismatch. Повторяющиеся события группируются, но исходные evidence не удаляются.

Точные пороги latency, freshness, reconnect rate и incident severity зависят от площадки и функции. Они должны быть versioned configuration, а не зашиты в интерфейс. До утверждения порога UI показывает измерение и `threshold not configured`.

### 7.6 Архитектура Content & Localization

#### 7.6.1 Типы управляемого контента

| Тип | Примеры | Как управлять | Статус |
| --- | --- | --- | --- |
| System UI copy | кнопки, поля, empty/error/permission states | стабильные keys, typed placeholders, versioned locale bundle | **Предложено до разработки** |
| Product explanations | onboarding, подсказки, help, FAQ | structured entries, links и media references | **Предложено** |
| Transactional copy | order/session/incident/fee/risk статусы | только утверждённые templates, связанные с state/policy version | **Предложено с усиленной защитой** |
| Notifications | in-app, email, Telegram | template + channel variants + required variables | **Предложено** |
| Legal and consent | terms, privacy, risk acknowledgement | отдельная версия, effective date, обязательный re-consent при необходимости | **Нужна проверка legal** |
| Landing pages | hero, trust, how it works, venues, FAQ, CTA, footer, SEO | predefined blocks и reusable content entries | **Предложено позже** |
| Media | изображения, видео, иконки, документы | media library с alt text, locale и usage references | **Предложено позже** |

#### 7.6.2 Реестр языков

Каждый язык описывает `locale`, название, направление `LTR/RTL`, fallback locale, формат даты/числа/валюты, plural rules и включённые surfaces. EN и RU остаются первыми языками; новые локали не публикуются, пока обязательные keys и критические шаблоны не достигли 100% completeness.

**Предложено:** язык может иметь состояния `draft`, `translation`, `review`, `ready`, `published`, `paused`. Отключение языка прекращает новые показы, но не удаляет версии и historical evidence.

#### 7.6.3 Translation catalog

Минимальная запись `ContentEntry`:

| Поле | Назначение |
| --- | --- |
| `key`, `namespace`, `surface` | стабильная идентичность и область использования |
| `description`, `screenshot/context` | что означает строка и где она показана |
| `source_locale`, `source_text` | исходный текст текущей версии |
| `translations[locale]` | локализованные значения и их статусы |
| `variables` | типизированные placeholders: amount, currency, date, venue, count и другие |
| `constraints` | maximum length, single-line, allowed links/markup, tone |
| `risk_class` | normal, transactional, financial, legal, security |
| `version`, `effective_at` | неизменяемая опубликованная версия и время применения |
| `author`, `publisher` | автор изменения и публикации, audit trail; reviewer не обязателен |

Placeholder удалять, переименовывать или менять его тип без validation нельзя. Форматирование суммы, валюты, числа, даты и множественного числа выполняется locale-aware formatter, а не вручную внутри перевода.

#### 7.6.4 Workflow публикации

Рекомендуемый lifecycle: `draft → translation → validated → scheduled/published → superseded/archived`. Любую опубликованную версию можно откатить созданием новой версии, но нельзя переписать задним числом.

Перед публикацией автоматически проверяются:

- completeness обязательных keys и отсутствие пустых критических строк;
- сохранность и типы placeholders;
- запрещённый HTML/скрипты и допустимые ссылки;
- длина, переносы и ограничения компонента;
- plural/date/currency formatting и RTL readiness;
- наличие alt text у обязательных media;
- соответствие transactional templates допустимым states;
- preview на целевых surface, locale и размерах экрана.

**Согласовано:** сотрудник с `content.edit` и `content.publish` самостоятельно редактирует и публикует разрешённые тексты, включая financial/legal/security. Обязательных review/approval и Owner approval нет. Изменения, автор публикации, before/after и версии логируются; откат создаёт новую версию. Тексты не меняют торговые или тарифные правила. См. [ADR-0031](decisions/0031_admin_permissions_and_autonomous_publishing.md).

#### 7.6.5 Доставка в приложение

Приложение получает подписанный/версионированный locale bundle. Последняя валидная версия кэшируется; при недоступности content service используется bundled baseline, поэтому ошибка CMS не блокирует вход и управление сессией.

Каждая публикация проходит `staging preview → production publish → propagation check`. Health ADM-15 показывает версию по surface/locale, время публикации, долю клиентов на новой версии, ошибки загрузки и fallback usage. Несовпадение ожидаемой и фактической версии создаёт incident.

#### 7.6.6 Будущий landing builder

Лендинг строится из разрешённой схемы блоков: `Header`, `Hero`, `Trust`, `How it works`, `Venues`, `Benefits`, `Safety`, `FAQ`, `CTA`, `Footer`, SEO metadata и legal links. Для каждого блока доступны порядок, visibility, locale variants, media, CTA target и preview responsive widths.

В первой версии builder не допускает произвольный код, изменение authentication/payment/trading flows или публикацию внешнего скрипта. Новые типы блоков добавляются через разработку и проходят дизайн/доступность; редактор управляет экземплярами уже разрешённых блоков.

Landing workflow поддерживает draft, preview URL, schedule, publish, rollback, canonical URL, title/description, Open Graph, robots/noindex и redirect map. A/B testing, personalization и GEO-targeting остаются отдельным будущим решением, чтобы не смешивать CMS с аналитикой и eligibility.

### 7.7 Архитектура emergency stop

#### 7.7.1 Область действия

`EmergencyControlState` должен поддерживать иерархический scope:

- весь проект;
- environment: demo / future live;
- конкретная площадка Polymarket или Limitless;
- adapter/worker/subsystem;
- новые регистрации и новые сессии;
- действия, увеличивающие риск;
- отдельный публичный surface: landing/application/API.

Более строгий верхний уровень всегда имеет приоритет. Effective emergency state вычисляется на сервере и возвращается вместе с причиной, временем активации, actor, incident ID и config version.

#### 7.7.2 Уровни

| Уровень | Поведение | Что продолжает работать | Статус |
| --- | --- | --- | --- |
| `NORMAL` | обычная работа | всё разрешённое текущей policy | **Предложено** |
| `READ_ONLY` | блокируются новые сессии и mutations | вход, просмотр, support, health, audit | **Предложено** |
| `RISK_PAUSED` | блокируются новые BUY и другие risk-increasing actions | чтение, ingestion, reconciliation; safe reduction только по отдельному контракту | **Предложено** |
| `VENUE_ISOLATED` | отключается конкретная площадка/adapter | другая площадка работает только если её собственный health и policy разрешают | **Предложено** |
| `TECH_MODE` | пользовательские интерфейсы, продуктовый API и продуктовые задания закрыты; availability state отдельно от торгового state | emergency console, monitoring, audit, evidence, incidents, reconciliation и recovery | **Согласовано — ADR-0031** |
| `GLOBAL_STOP` | проект отвергает все новые пользовательские и фоновые mutations | admin control plane, evidence, telemetry, reconciliation, status communication | **Согласована потребность; точный контракт предложен** |

В paper V1 `GLOBAL_STOP` прекращает создание новых виртуальных операций и запуск demo-сессий. Существующие данные и отчёты остаются доступными read-only. Для будущего live точный перечень допустимых cancel/close/settlement действий определяется отдельными доказанными runbooks; универсальная команда «закрыть всё» не допускается.

#### 7.7.3 Исполнение

**Предложено:** emergency state хранится в отказоустойчивом независимом control plane и проверяется:

1. на API gateway до принятия команды;
2. при постановке задания в очередь;
3. worker перед каждым внешним side effect;
4. scheduler перед запуском фоновой операции;
5. при старте/restart каждого adapter и worker.

Risk-increasing путь работает fail-closed: если актуальный emergency state невозможно прочитать, новая mutation не выполняется. Read-only и reconciliation paths могут использовать последнюю доказанную безопасную конфигурацию и явно показывают degraded control-plane health.

#### 7.7.4 Активация

Перед активацией показываются scope, затронутые функции и сессии, а также действия, которые продолжат выполняться. Для `GLOBAL_STOP` приоритет — скорость: авторизованный Owner или заранее назначенная роль со scope `emergency.activate` может активировать stop после 2FA/re-auth, выбора причины и incident ID без ожидания второго человека.

Активация создаёт append-only audit event, отправляет оповещение Owner и назначенной incident-группе, открывает incident и запускает автоматическую проверку enforcement на API, queue и workers. Если часть компонентов не подтвердила stop, состояние отображается как `STOP PARTIALLY ENFORCED`, а не как успешное.

#### 7.7.5 Восстановление

Восстановление не является обратным нажатием той же кнопки. Оно проходит checklist:

- причина устранена и evidence приложен;
- health обязательных подключений подтверждён;
- unknown operations и reserves перечислены;
- очередь отложенных команд очищена или доказанно безопасна;
- reconciliation завершена либо явно оставлена открытой;
- новая config/policy version подготовлена;
- для GLOBAL_STOP/TECH_MODE Owner повторно авторизован и второй независимый сотрудник подтверждает recovery; один человек не даёт оба подтверждения;
- выполняется staged restore: read-only → один adapter/небольшой scope → normal.

Emergency state не имеет автоматического срока истечения. Автоматическое самовключение проекта запрещено.

#### 7.7.6 Доступность control plane

**Предложено:** emergency control доступен из админки и через отдельный out-of-band защищённый путь, не зависящий от пользовательского frontend. Он использует отдельную authentication policy, короткую admin-сессию, 2FA и резервный runbook. Секреты и ключи площадок для активации stop не нужны.

Публичная status communication отделена от control plane: пользователи видят локализованное сообщение, время обновления и status reference, но не внутренние причины, ключи или security details. Текст берётся из заранее опубликованного emergency bundle ADM-16, поэтому доступен даже при сбое основного content service.

#### 7.7.7 Отключение пополнения и вывода через Shadow

**Согласовано:** [ADR-0030](decisions/0030_shadow_funding_interface_emergency_controls.md). В Emergency Control присутствуют независимые `DEPOSITS_OFF` и `WITHDRAWALS_OFF` со scope весь продукт / environment / Polymarket / Limitless.

| Переключатель | Что блокируется через Shadow | Что продолжается |
| --- | --- | --- |
| `DEPOSITS_OFF` | кнопка запуска пополнения, создание новых инструкций и соответствующие запросы продукта | наблюдение и учёт фактических поступлений, reconciliation и audit |
| `WITHDRAWALS_OFF` | кнопка запуска вывода, новые запросы и ещё не отправленные задания | наблюдение за уже отправленными транзакциями, reconciliation и audit |

Блокировка применяется на UI, backend и непосредственно перед внешним действием worker. Отсутствие актуального emergency state блокирует новые действия. Пользователь видит причину временной недоступности. Локальное включение не обходит `GLOBAL_STOP` или другие активные запреты.

Прямые действия пользователя в кошельке или на площадке остаются вне контроля Shadow. Известный адрес продолжает принимать переводы; уже отправленная транзакция не становится отменённой. Фактические поступления фиксируются и сверяются независимо от положения переключателей.

Переключатели входят в текущий план админки. В paper/demo показано «функция не подключена»; настоящее исполнение остаётся за отдельными capability/live-gates каждой площадки. Activation/recovery используют emergency scopes, re-auth, reason, incident ID и append-only audit; автоматическое снятие запрещено. Это управление доступностью пути через продукт, без treasury и доступа сотрудников к private keys.

### 7.8 Архитектура тарифов и комиссий

#### 7.8.1 Разделение денежных компонентов

| Компонент | Кто определяет | Можно ли менять в Shadow | Как учитывать |
| --- | --- | --- | --- |
| `service_fee` | тарифная политика Shadow | только новой версией policy | собственное начисление Shadow |
| `venue_fee` | Polymarket/Limitless | нет; только получить и доказать применимую ставку | отдельный внешний расход/fee component |
| `network_cost` | сеть/provider/фактическая транзакция | нет | отдельный подтверждённый расход |
| `partner_reward` | партнёрская политика Shadow | новой версией referral policy | обязательство Shadow, не уменьшает исходную запись service fee |
| `venue_referral_reward` | программа площадки | нет | отдельный внешний доход/атрибуция |
| `refund/correction` | подтверждённое событие | только добавочной записью | ссылка на исходное начисление, без переписывания истории |

UI никогда не показывает одну объединённую «комиссию», если её компоненты имеют разные источники или получателей. Неизвестная внешняя комиссия отображается как `unknown`, а не 0.

#### 7.8.2 Сущности

Минимальный `TariffPolicySet` содержит:

| Поле | Назначение |
| --- | --- |
| `policy_set_id`, `version`, `status` | стабильная идентичность, версия и draft/scheduled/active/superseded |
| `environment`, `mode` | demo simulation или future live |
| `effective_from`, `effective_to` | точное время действия в UTC |
| `scope` | venue, plan/segment и optional approved user/partner override |
| `action_type` | automatic buy/sell и явно исключённые manual/protective/emergency actions |
| `liquidity_role` | maker/taker/unknown с правилом для неизвестной классификации |
| `rate`, `calculation_base` | ставка и база только от confirmed executed amount |
| `currency`, `rounding_rule`, `minimum`, `maximum` | денежный контракт и ограничения |
| `partner_policy_version` | связанная версия правил партнёрского вознаграждения |
| `author`, `reviewer`, `publisher`, `reason` | ответственность и audit trail |

Каждое начисление хранит `tariff_policy_version`, `partner_policy_version`, исходные fill IDs, maker/taker evidence, calculation inputs, rounding result и breakdown. Повторный расчёт на тех же входных данных и версиях должен давать тот же результат.

#### 7.8.3 Действующие и будущие версии

| Этап | Service fee | Partner share | Статус |
| --- | --- | --- | --- |
| Закрытая alpha | 0% | 0% | **Согласовано, единственная фактически активная версия сейчас** |
| Первый paid | taker 0,50%; maker 0,25% | 25% | **Согласованная будущая policy, запуск не разрешён** |
| Подтверждённый продукт | taker 0,75%; maker 0,35% | 25–30% | **Согласованная будущая policy, критерии перехода не утверждены** |
| VIP ceiling | taker до 1%; maker до 0,50% | не более 35% | **Согласованные пределы, eligibility и конкретные значения требуют версии** |

Manual/protective/emergency close, corrections, funding/withdrawal, analytics, trader connection и cancelled/unfilled remainder имеют `service_fee = 0`. Venue/network costs при этом не маскируются под нулевую service fee.

#### 7.8.4 Приоритет правил

**Предложено:** effective tariff выбирается детерминированно:

1. environment/mode и обязательный emergency/legal restriction;
2. конкретный approved user/VIP override;
3. конкретный partner/plan override;
4. venue-specific rule;
5. global default текущей policy version.

В одном scope и времени не допускаются две одинаково специфичные активные версии. Если однозначный тариф определить нельзя, новая fee-bearing операция блокируется как `TARIFF_AMBIGUOUS`; система не выбирает более выгодную или более дорогую ставку случайно.

#### 7.8.5 Партнёрская лестница

Referral policy хранится отдельно от service tariff и содержит:

- basis: доля только от фактически начисленной/полученной комиссии Shadow по принятому правилу;
- attribution window и источник закрепления пользователя;
- lifetime cumulative metric: число подтверждённых клиентов и/или оборот;
- tiers с порогами, ставкой и ceiling 35%;
- hold period, payout cadence, minimum payout и currency;
- self-referral/conflict, refund/reversal и dispute rules;
- индивидуальный strategic VIP override с отдельным сроком и причиной.

Действующая политика задаёт 24 месяца attribution, lifetime только для strategic VIP, доступность начисления через 7 дней и monthly payout при минимуме $25. Конкретные thresholds партнёрской лестницы ещё **не утверждены**. Повышение уровня применяется только к новым начислениям после effective time и не пересчитывает историю.

#### 7.8.6 Симулятор

Перед публикацией Owner видит current/proposed side-by-side и рассчитывает обязательные сценарии:

- maker/taker buy и sell;
- full, partial и cancelled remainder;
- manual/protective/emergency close;
- partner 25%, 30%, 35% и пользователь без партнёра;
- VIP/user override и его expiry;
- unknown liquidity role, missing venue fee и stale policy;
- refund/correction и partial receipt;
- минимальные суммы и rounding boundaries.

Simulator показывает gross executed amount, service fee, venue/network costs, partner liability, net revenue Shadow и все версии/источники. Результат симуляции не создаёт финансовую запись.

#### 7.8.7 Публикация и rollback

Lifecycle: `draft → simulated → reviewed → approved → scheduled → active → superseded`. Прямое редактирование `active` запрещено. Публикация требует:

- успешных invariant tests и обязательных simulation scenarios;
- diff ставок, scope, exclusions и партнёрских обязательств;
- preview затронутых будущих пользователей/планов без показа PII;
- локализованных пользовательских disclosure texts ADM-16;
- Owner re-auth; для future live рекомендуется второе подтверждение;
- точного `effective_at` и audit reason.

Rollback создаёт новую версию с прежними правилами на новое effective time. Backdating и изменение исторических `RevenueAccrual` запрещены; ошибка исправляется `Correction/Refund` с evidence.

#### 7.8.8 Права и наблюдаемость

**Предложено:** использовать permission scopes `pricing.view`, `pricing.simulate`, `pricing.edit`, `pricing.review`, `pricing.publish`, `pricing.override`. Operations видит только effective tariff и объяснение для конкретного случая, если выдан `pricing.view`; публиковать и создавать override может Owner или специально назначенная роль в рамках утверждённого workflow.

Health ADM-15 контролирует:

- наличие ровно одной effective policy для каждой разрешённой комбинации;
- расхождение вычисленной и записанной комиссии;
- fills без tariff version или calculation evidence;
- неизвестную maker/taker classification;
- превышение ceilings и неожиданный ненулевой fee для excluded actions;
- propagation новой policy version по workers;
- несоответствие service accrual, partner liability и receipt.

Критическое нарушение останавливает новые fee-bearing operations через policy gate и создаёт incident; оно не переписывает уже подтверждённые начисления.

### 7.9 Архитектура Marketing & Communications

#### 7.9.1 Классы сообщений

| Класс | Пример | Consent / отключение | Приоритет |
| --- | --- | --- | --- |
| `security` | вход, смена доступа, критический риск | обязательность определяется security/legal policy; не смешивать с рекламой | критический |
| `operational` | session paused, unknown, reconciliation, venue incident | часть продукта; пользователь управляет каналом только там, где это безопасно | высокий |
| `support` | ответ по обращению, ожидание ответа | в рамках активного тикета | высокий |
| `service` | изменение условий, planned maintenance, language/account notice | зависит от содержания и требований GEO | средний–высокий |
| `product` | новая функция, новый язык, доступность площадки | marketing/product consent | средний |
| `marketing` | образовательная серия, referral campaign, re-engagement | отдельный opt-in и простой unsubscribe | обычный |

Одна кампания не может одновременно считаться обязательной и маркетинговой. Рекламный CTA нельзя прятать внутри security/operational сообщения для обхода consent.

#### 7.9.2 Каналы

| Канал | V1 | Особенности |
| --- | --- | --- |
| In-app inbox/banner | да | основа для product/service announcements; versioned read state |
| Email | после provider/consent gate | verified address, bounce/complaint/suppression, unsubscribe |
| Telegram | после явного подключения | chat binding, delivery failure, disconnect, locale |
| Web/mobile push | позже | device token lifecycle, permission state, deep links |
| Landing banner/modal | позже через ADM-16 | публичный content, schedule, locale/GEO visibility |
| SMS/WhatsApp | вне первого scope | отдельная стоимость, provider и legal review |

#### 7.9.3 Согласия и предпочтения

`CommunicationPreference` хранит user, purpose/class, channel, locale, status, source, policy/content version, timestamp и evidence. Состояния: `unknown`, `opted_in`, `opted_out`, `required`, `channel_unavailable`, `suppressed`.

Пользователь управляет marketing/product channels отдельно от обязательных service/security сообщений. Unsubscribe вступает в силу до следующей marketing send attempt. Suppression list применяется централизованно ко всем campaigns и не удаляется импортом нового audience.

**Нужна проверка:** правила согласий зависят от GEO и канала; отсутствие opt-out нельзя автоматически считать opt-in. До legal validation маркетинговая отправка разрешена только пользователям с доказанным явным opt-in.

#### 7.9.4 Аудитории и сегменты

Разрешённые примеры сегментов:

- язык, подтверждённая страна/регион и часовой пояс;
- guest/registered, demo not started/active/completed;
- выбранная площадка или интерес к теме;
- наличие подключённого канала и consent;
- дата последней активности и факт использования функции;
- партнёрская attribution как отдельный фильтр без раскрытия PII партнёру.

До отправки сохраняются `segment_definition_version`, estimated recipients и финальный recipient snapshot/hash. Segment preview показывает агрегаты и причины исключения: no consent, suppressed, invalid channel, GEO restriction, frequency cap.

Не использовать для маркетинга финансовые трудности, точные balances/PnL, security incidents, содержание support tickets или иные чувствительные признаки без отдельного обоснования и решения.

#### 7.9.5 Кампания и workflow

Минимальная `CampaignVersion` содержит objective, class, owner, audience definition, channels, locale variants, template/content versions, CTA/deep link, schedule, frequency policy, experiment flag, budget/cost ceiling и tracking plan.

Lifecycle: `draft → audience estimated → test sent → validated → scheduled → sending → paused/completed/cancelled → archived`.

Перед отправкой обязательны:

- preview для каждого locale/channel и проверка placeholders/deep links;
- test send только на разрешённый внутренний список;
- consent/suppression/GEO validation;
- audience size и estimated provider cost;
- frequency cap, quiet hours и timezone strategy;
- проверка demo/live формулировок и отсутствия обещаний дохода;
- наличие `marketing.publish` у запускающего сотрудника; обязательное согласование внутри проекта отсутствует;
- emergency stop hook и rollback/landing target readiness.

После старта кампанию можно pause/cancel. Это прекращает новые постановки в очередь, но не обещает отмену уже принятого provider сообщения; UI показывает queued/sent boundary.

#### 7.9.6 Частота и время

**Предложено:** policy задаёт maximum per user per channel/class, quiet hours по локальному времени, minimum interval и global fatigue cap. Security/operational messages используют отдельный приоритет и не расходуют marketing cap, но дедуплицируются по incident/event ID.

Если timezone неизвестен, используется безопасное централизованное окно, записанное в policy. Кампания не отправляется автоматически после долгой задержки, если её актуальность истекла.

#### 7.9.7 Доставка и наблюдаемость

`MessageDelivery` хранит campaign/version, user pseudonymous ID, channel, locale/content version, provider message ID, queued/sent/delivered/read/clicked/bounced/complained/unsubscribed/failed status, timestamps и error category.

ADM-15 показывает health каждого channel provider: authentication, quota/rate limits, latency, bounce/complaint rate, webhook freshness, queue lag и template propagation. `unknown` delivery не превращается в delivered. Повтор разрешён только по channel-specific idempotency/deduplication contract.

Threshold breach автоматически приостанавливает соответствующий канал кампании и создаёт incident; остальные каналы не продолжаются вслепую, если это создаёт дубли.

#### 7.9.8 Аналитика и атрибуция

Базовые показатели: eligible audience, excluded, queued, sent, delivered, read/open, click, bounce, complaint, unsubscribe и целевое продуктовое событие. Доходность трейдинга не является маркетинговым обещанием или KPI кампании.

Conversion связывается с campaign/version и заранее объявленным окном, но не доказывает причинность. A/B testing и автоматическая оптимизация аудитории остаются отдельным будущим решением после достаточного объёма данных и privacy review.

#### 7.9.9 Права

**Предложено:** scopes `marketing.view`, `marketing.segment`, `marketing.edit`, `marketing.test_send`, `marketing.publish`, `marketing.pause`, `marketing.export_aggregate`. Экспорт полного списка контактов по умолчанию запрещён. Marketer самостоятельно запускает кампании по `marketing.publish`; подготовка и запуск выдаются отдельно. Внутренние согласования проходят вне админки. Operations может получить emergency pause без права публикации. Consent/отписки клиентов и автоматические проверки сохраняются — ADR-0031.

Текущая документация Polymarket указывает для Сомали и Таиланда режим close-only на frontend и API. Это изменяемый внешний факт, поэтому перед любым live-планом требуется свежая проверка по фактическому пользователю, площадке и моменту доступа. Он не влияет на paper-демо, но блокирует обещание live-доступности для этих GEO.

## 8. Жизненный цикл и состояния интерфейса

### 8.1 Общие состояния данных

**Предложено:** каждый список и detail view поддерживает `loading`, first-use empty, filtered empty, error, offline, stale, source disconnected, partial data, permission denied и auth expired.

`Unavailable`, `unknown`, `degraded` и `permission_missing` должны различаться. Последний успешный ответ всегда сопровождается `source_time`, `observed_at`, age и current error.

### 8.2 Состояния действия

**Предложено:** confirmation со scope и причиной → submitting → succeeded / partially succeeded / skipped / failed / result unknown → late result / reconciliation mismatch. В результате всегда есть audit reference ID.

### 8.3 Финансовые состояния

**Предложено:** source disconnected → estimate → accrued → receivable → partially received → received → correction/refund; отдельно unmatched, FX unavailable/stale и liability pending/paid/disputed.

## 9. Owner finance: отдельный контур

| Сущность | Назначение | Статус |
| --- | --- | --- |
| `TariffVersion` | ставка, maker/taker, база, режим, получатель, effective dates | **Согласована политика; реализация не проверена** |
| `RevenueAccrual` | начисление с source/venue/currency/amount/status/evidence | **Предложено** |
| `Receipt` | фактическое поступление на service account, включая partial | **Предложено** |
| `ServiceAccount` | назначение, venue/network/currency, публичный ID, balance и last reconciliation; без ключей | **Предложено** |
| `PartnerLiability` | внутренняя обязанность Shadow перед партнёром | **Согласовано как отдельный смысл; механизм не готов** |
| `Expense` | операционный расход сервиса | **Предложено** |
| `Refund/Correction` | добавочная связанная запись без переписывания прошлого | **Предложено** |
| `ReconciliationCase` | расхождение между начислением, поступлением и evidence | **Предложено** |
| `FXSnapshot` | курс, источник, время и метод | **Предложено / источник не выбран** |

Текущая тарифная политика:

- **Согласовано:** закрытая alpha — service fee 0%, partner 0%; виртуальная комиссия хранится отдельно.
- **Согласовано:** первые paid — taker 0,50%, maker 0,25%, partner 25%; подтверждённый продукт — 0,75% / 0,35%, partner 25–30%; VIP ceiling — 1% / 0,50%, partner не более 35%.
- **Согласовано:** fee только с фактически исполненного автоматического buy/sell; manual/protective/emergency close, correction, funding/withdrawal, analytics, connection и unfilled remainder — 0% service fee.
- **Нужна проверка:** запуск paid/live, техническое взимание, maker/taker classification, tier thresholds, refunds и доказательство получения.

## 10. Безопасность и неизменяемость

1. **Согласовано:** private keys, HMAC secrets, passphrases и session keys не попадают в UI, логи, экспорт или тикеты.
2. **Предложено:** в UI видны только key ID, scope, expiry, last used, account/signer provenance и status.
3. **Согласовано:** unknown — самостоятельное состояние; нельзя вручную отметить операцию исполненной или повторить её без evidence.
4. **Предложено:** ledger, incident notes, policy history и финансовые correction entries append-only.
5. **Предложено:** audit event содержит actor, role, action, scope, before/after, reason, timestamp, correlation ID и ссылки на evidence.
6. **Предложено:** опасные будущие действия изолируются от read-only диагностики; отсутствие capability выключает control на сервере, а не только в интерфейсе.
7. **Предложено:** ключи хранятся в KMS/secret manager; админка хранит только непривилегированную ссылку `credential_ref` и metadata.
8. **Предложено:** ротация/revoke требуют повторной авторизации Owner, scope preview, reason и audit; dual control рекомендуется для production/live.
9. **Нужна проверка:** admin authentication, 2FA, session expiry, retention, export policy, dual control, incident severity и break-glass process.

## 11. Текущая Figma: что переиспользовать

### Current prototype

| Экран | Figma ID | Решение |
| --- | --- | --- |
| A01 Operations overview | `51:3` | сохранить как основу ADM-01 |
| A02 Incident queue | `51:89` | сохранить как основу ADM-04 |
| A03 Incident detail | `51:159` | сохранить evidence и assignment; добавить полный lifecycle |
| A04 User session | `51:222` | развить в ADM-03 и связать с ADM-02 |
| A05 Reconciliation preview | `121:1513` | сохранить read-only смысл; развить в ADM-05 |
| A06 Session controls and evidence | `1879:25495` | сохранить effective rules/unknown/reserve; переименовать, потому что старый A06 означал Venues & data |

Существующие queue states (`needs review`, search result, no results, loading, load error, assigned) можно переиспользовать. Текущий путь `Overview → Incident → Reconciliation → User session → Controls/evidence` остаётся основой operator flow.

### Proposed owner finance

OF01–OF06 RU/EN можно использовать как визуальную основу для overview, journal, basis, service accounts, referral liabilities и discrepancies. Эти экраны остаются **Proposed**, их источник отключён.

### Что отсутствует

Полные Users/Sessions lists, Venues & data, traders ingestion, policy registry, notifications delivery, support queue, feedback operations, audit log, staff/access, integrations/security, connection health history, content/localization, admin auth/2FA, permission denied, emergency control center, проверка enforcement, out-of-band recovery, bulk-result states и безопасный export.

Текущая админка EN-only, использует sample data и не имеет backend. Пользовательские экраны прошли структурный и визуальный QA, но последняя итерация ещё не прошла свежий ручной Present. Полная приёмка админки также не подтверждена.

## 12. Открытые решения владельца

До начала дизайн-итерации осталось пять решений. Health/metadata обеих площадок и отзыв admin-сессий согласованы в ADR-0032; ротация credentials интеграций отложена. Публикация текстов, самостоятельный маркетинг по scopes и аварийное восстановление согласованы в ADR-0031. Модель ролей зафиксирована в ADR-0029: Owner встроен, Operations объединяет операции и поддержку, остальные доступы создаются как кастомные роли и изменяемые пресеты.

1. **Нужна проверка:** входит ли support queue в первую demo-админку; рекомендация — да, без SLA и attachments.
2. **Нужна проверка:** показываем ли owner finance в первой Figma-итерации как source disconnected/empty; рекомендация — да, без operational payout controls.
3. **Нужна проверка:** принимаем ли архитектуру content keys, locale registry и versioned publishing до разработки, а визуальный landing builder оставляем на потом; рекомендация — да.
4. **Нужна проверка:** принимаем ли versioned tariff/referral policy, предложенный приоритет overrides и Owner-only publish; рекомендация — да, а tier thresholds, VIP eligibility и rounding закрыть отдельным решением до paid/live.
5. **Нужна проверка:** какой marketing scope входит в первую админку; рекомендация — in-app announcements, preference/consent model и delivery monitoring в foundation, а массовые email/Telegram/push кампании — после provider/legal gates.

Остальные вопросы можно решать внутри этапов без преждевременного расширения scope.

## 13. Зависимости до разработки

| Зависимость | Почему блокирует | Статус |
| --- | --- | --- |
| BL-05 virtual lots и ручные/detached части | нужна корректная session/position timeline | **Нужна проверка** |
| BL-06 freshness, price/depth, minimums, rounding и fees | нужна честная диагностика и причины skip | **Нужна проверка** |
| BL-07 terminal session и открытые операции | нужна безопасная остановка/закрытие | **Нужна проверка** |
| BL-08 effective policy и приоритет ограничений | нужны read-only rules и объяснимый блок | **Нужна проверка** |
| Durable operation journal и idempotency | нужен restart/retry/unknown contract | **Нужна проверка** |
| Подтверждённые account capabilities PM/LL | нужны private reads и будущие live controls | **Нужна проверка** |
| Operations user-context/retention lifecycle | нужен минимальный support scope внутри объединённой роли | **Нужна проверка** |
| Finance evidence/attribution/FX | нужен owner ledger без ложных сумм | **Нужна проверка** |
| Referral thresholds и conflict rules | нужна версия партнёрской политики | **Нужна проверка** |
| Content key/schema и locale bundle contract | нужны управляемые тексты без переписывания компонентов | **Предложено закрыть до frontend** |
| Content permissions и historical version evidence | самостоятельная публикация по scopes, история и rollback | **Согласовано; требуется технический контракт** |
| Independent emergency control plane | рубильник должен работать при отказе основного приложения | **Предложено закрыть до backend** |
| Effective policy hierarchy и safe-reduction contract | emergency state должен предсказуемо перекрывать user/session/venue policy | **Нужна проверка** |
| Tariff/referral policy schema и override precedence | комиссия должна быть однозначной и воспроизводимой | **Предложено закрыть до backend** |
| Maker/taker evidence, rounding и tier thresholds | нужны для фактического paid начисления | **Нужна проверка до paid/live** |
| Communication consent/purpose model | обязательные и маркетинговые сообщения должны быть разделены | **Предложено закрыть до notification backend** |
| Channel providers, GEO rules и suppression policy | нужны до массовых внешних рассылок | **Нужна проверка** |
| GEO/legal/security/live gates | обязательны только перед live | **Нужна проверка позднее** |

## 14. Этапы работы без автоматического перехода

### Этап 0. Принять карту

**Результат:** утверждены V1/out-of-scope, ADM-01–ADM-18, пять оставшихся решений владельца и терминология.

**Готово, когда:** нет конфликтов со свежими ADR; каждый пункт имеет status; существующие Figma frames сопоставлены со стабильными IDs.

### Этап 1. Спроектировать demo-админку в Figma

**Объём:** ADM-01–ADM-12, включая ADM-08 с registry/simulator/diff без публикации paid-тарифа; ADM-13 только empty/source disconnected; ADM-14 базовые роли и состояния доступа; ADM-15 read-only health/metadata без секретов и credential mutations; ADM-16 — карта locale/content workflow без реализации landing builder; ADM-17 — emergency levels, activation, partial enforcement, staged recovery и DEPOSITS_OFF / WITHDRAWALS_OFF с honest disconnected-state в demo; ADM-18 — campaign map, consent/preferences и delivery states без массовой внешней отправки; desktop-first, отдельный emergency path адаптируется для защищённого мобильного доступа позже.

**Результат:** карта flow, экраны, роли, все data/action states, RU/EN, кликабельные пути и список неиспользуемых элементов.

**Готово, когда:** Owner и сотрудники с пресетами Ops Lead, Operations, Marketer, Auditor, а также одной кастомной ролью проходят свои разрешённые сценарии; запрещённые controls отсутствуют; unknown/partial/stale/permission states проверены в Present.

**Переход:** только по отдельной команде владельца. Этот аудит Figma не меняет.

### Этап 2. Утвердить технический дизайн

**Объём:** сущности, state machines, append-only ledger/audit, RBAC, API contracts, `ConnectionProfile`, health checks, capability evidence, credential metadata, content key/schema, locale bundles, publishing/version contract, `TariffPolicySet`, referral policy, deterministic calculation/rounding, simulator, `CommunicationPreference`, `CampaignVersion`, `MessageDelivery`, suppression/deduplication, `EmergencyControlState`, server-side enforcement points, out-of-band access, error taxonomy, retention и observability.

**Результат:** технический документ и ADR по оставшимся решениям BL-05–BL-08; API PR #14/#15 безопасно обновлены от main и review пройден.

**Готово, когда:** каждой ячейке интерфейса назначен источник; каждой mutation — permission, idempotency и reconciliation; секреты и PII имеют границы.

**Переход:** только по отдельной команде владельца.

### Этап 3. Реализовать read-only foundation

**Предложенный порядок:** auth/RBAC → emergency control plane и server-side enforcement → content key и emergency locale baseline → internal demo read models → audit log → connection registry и health telemetry → public venue adapters → overview/users/sessions/incidents → support/notifications → finance empty states → content editor; landing builder отдельным поздним пакетом.

**Готово, когда:** контрактные и role tests пройдены; stale/partial/error состояния воспроизводимы; никакие реальные orders/funds недоступны.

### Этап 4. Добавить контролируемые demo-действия

**Объём:** pause new demo actions, disable session, reread internal/external state, start reconciliation, incident resolution.

**Готово, когда:** confirmation, reason, scope, before/after, unknown и audit evidence подтверждены тестами; restart и duplicate request не искажают ledger.

### Этап 5. Подготовить live отдельно

**Объём:** private read-only evidence прежде любых mutations; затем отдельные решения по signer/delegation, execution, fees, GEO, security, recovery и finance.

**Готово, когда:** права проекта проверены фактически, lifecycle и failure modes записаны, security/legal review пройдены, владелец дал отдельный GO.

## 15. Приоритеты и относительная сложность

| Приоритет | Пакет | Сложность | Причина |
| --- | --- | --- | --- |
| P0 | карта, RBAC, operator flows, states | средняя | определяет границы до дизайна |
| P0 | operation journal, unknown/reconciliation, audit | высокая | основа безопасности и правды системы |
| P0 | emergency control plane и enforcement | высокая | должен работать до любых фоновых mutations |
| P1 | overview, users, sessions, incidents | средняя–высокая | основная ежедневная работа |
| P1 | venue/data health и capability evidence | высокая | разные API, cache и права |
| P1 | staff/access и integrations/security | высокая | RBAC, KMS metadata, health telemetry и audit |
| P1 | support/feedback/notifications | средняя | полезно для первой проверки продукта |
| P1 | content keys, locale registry и versioned bundles | высокая | влияет на все экраны и historical evidence |
| P1 | tariff/referral registry, simulator и evidence | высокая | влияет на каждое будущее начисление и обязательство |
| P1 | communication purpose/consent и in-app announcements | высокая | затрагивает пользователей, языки, privacy и delivery evidence |
| P2 | fee/policy registry и owner finance read-only | высокая | нужны versioning и доказуемые источники |
| P2 | content editor, preview, publish и rollback | средняя–высокая | workflow, permissions и validation |
| P2 | email/Telegram campaign orchestration | высокая | providers, suppression, GEO, cost и deliverability |
| P3 | live private reads и mutations | очень высокая | signer, scopes, GEO, recovery и деньги |
| P3 | landing builder, partner cabinet, payouts | высокая | отдельные будущие продукты внутри админки |

Точные календарные сроки до технического дизайна будут выдуманными. Планировать лучше короткими review-пакетами: один законченный flow с evidence, проверкой ролей и критериями готовности за итерацию.

## 16. Проверка API-исследований

- PR [#14 Polymarket](https://github.com/denius89/polymarket-copy-trading/pull/14) открыт, не слит, reviews отсутствуют; ветка содержит один собственный commit и отстаёт от текущего `main`.
- PR [#15 Limitless](https://github.com/denius89/polymarket-copy-trading/pull/15) открыт, не слит, reviews отсутствуют; ветка также содержит один собственный commit и отстаёт от текущего `main`.
- **Предложено:** перед merge переносить на свежий `main` только собственные API-документы. Удаления новых общих документов, возникающие из-за старой базы веток, переносить нельзя.
- **Согласовано:** оба PR — documentation only; они не означают готовую интеграцию или разрешение на live.

## 17. Решение по итогам аудита

Проект готов к **согласованию карты и следующей дизайн-итерации админки**. Проект не готов к реализации live-консоли, реальным торговым действиям, движению средств или финансовому учёту на данных площадок.

Следующий безопасный шаг после принятия этого документа — отдельно поручить обновление Figma по этапу 1. Технический план и разработка не начинаются автоматически.

## 18. Основные источники

- [MVP_BUSINESS_LOGIC](MVP_BUSINESS_LOGIC.md)
- [Каноническая карта экранов и состояний](34_screen_and_state_map.md)
- [Консолидированный продуктовый план](55_consolidated_product_plan_2026-10-02.md)
- [Полный Figma/business/API/UI аудит](81_full_figma_business_api_and_ui_audit_2026-10-04.md)
- [ADR-0005: комиссия и партнёрская политика](decisions/0005_execution_fee_and_partner_policy.md)
- [ADR-0007: Limitless first integration](decisions/0007_limitless_first_integration.md)
- [ADR-0008: две площадки](decisions/0008_dual_venue_product_scope.md)
- [ADR-0009: novice-first direct MVP](decisions/0009_novice_first_direct_mvp.md)
- [ADR-0010: paper MVP](decisions/0010_design_direction_and_paper_mvp.md)
- [ADR-0011: controls, roles and admin](decisions/0011_shadow_controls_rating_admin_and_ui_foundation.md)
- [ADR-0012: paper defaults](decisions/0012_paper_mvp_defaults.md)
- [API PR #14](https://github.com/denius89/polymarket-copy-trading/pull/14)
- [API PR #15](https://github.com/denius89/polymarket-copy-trading/pull/15)
