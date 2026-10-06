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
| Funding/withdrawal | **Согласовано** | исключено из demo V1 и из торгового execution-worker; отдельный будущий контур |
| Реальные комиссии и выплаты | **Нужна проверка** | способ взимания, maker/taker classification, evidence поступления и возвратов |
| Live-финансы владельца | **Нужна проверка** | подтверждённые источники attribution, receiving accounts, payout completeness и FX |

## 4. Роли и права

Названия ролей **Owner, Operator, Support, Read only** согласованы в ADR-0011. Детальная матрица ниже — предложение до отдельного утверждения.

| Возможность | Owner | Operator | Support | Read only | Статус |
| --- | ---: | ---: | ---: | ---: | --- |
| Смотреть overview, пользователей, сессии и incidents | да | да | ограниченный контекст | да | **Предложено** |
| Поставить на паузу новые demo-действия | да | да | нет | нет | **Согласовано** для операционного контура |
| Отключить demo-сессию | да | да | нет | нет | **Согласовано** |
| Повторно прочитать состояние / запустить сверку | да | да | нет | нет | **Согласовано** |
| Назначить incident и записать resolution | да | да | нет | нет | **Согласовано** |
| Работать с тикетом и feedback | да | только просмотр контекста | да | просмотр по scope | **Предложено** |
| Смотреть owner finance | да | агрегированный operational view | нет | по отдельному scope | **Предложено** |
| Менять тариф/политику | будущая отдельная процедура | нет | нет | нет | **Нужна проверка** |
| Управлять ролями сотрудников | будущая отдельная процедура | нет | нет | нет | **Нужна проверка** |
| Видеть секреты, private keys, HMAC secrets | нет | нет | нет | нет | **Согласовано** |
| Выводить средства или совершать сделку за пользователя | нет | нет | нет | нет | **Согласовано** |
| Слепо повторять операцию с неизвестным итогом | нет | нет | нет | нет | **Согласовано** |

Каждое изменение состояния должно проверяться на сервере, запрашивать причину, показывать область влияния и создавать неизменяемую audit-запись. Dual control, отдельные Finance/Security роли и точный состав PII пока **не согласованы**.

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
| ADM-08 | Fees & policy | да, read-only | Proposed finance и старые схемы | version registry, effective dates, demo 0% vs future simulation | **Согласовано / отсутствует** |
| ADM-09 | Support | да | user-side lifecycle готов | admin queue, conversation, context, access/retention rules | **Предложено** |
| ADM-10 | Notifications | да, read-only | user-side notifications | delivery/failure/retry evidence, channel status | **Согласовано / отсутствует** |
| ADM-11 | Feedback | да | user-side form | очередь, связь с user/session, категории и status | **Согласовано / отсутствует** |
| ADM-12 | Audit log | да | только evidence в отдельных frames | общий append-only журнал, фильтры, correlation/reference IDs | **Согласовано / отсутствует** |
| ADM-13 | Owner finance | схема сейчас, данные позже | Proposed OF01–OF06 RU/EN | подтверждённые источники, ledger, reconciliation, права | **Предложено / источник не подключён** |
| ADM-14 | Staff & access | позже | нет | sign-in, 2FA, expiry, role assignment, permission denied | **Нужна проверка** |
| ADM-15 | Content/FAQ | позже | user FAQ есть | отдельная потребность и workflow публикации | **Предложено вне V1** |

## 6. Основные операторские сценарии

### 6.1 Разбор инцидента

`Overview → очередь → фильтр/поиск → incident → evidence → операция/сессия → read-only сверка → заметка/назначение → resolution`.

- **Согласовано:** unknown не превращается в success вручную.
- **Согласовано:** resolution фиксирует решение инцидента, но не переписывает финансовую или торговую истину.
- **Предложено:** обязательные поля resolution: причина, evidence, actor, время, затронутый scope, audit reference.

### 6.2 Поиск пользователя

`Users → user → sessions → session → positions / orders / activity / support timeline`.

- **Согласовано:** данные каждой площадки и каждой сессии сохраняют собственный venue и identifiers.
- **Предложено:** Support видит только минимальный контекст, необходимый для тикета.
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
7. **Нужна проверка:** admin authentication, 2FA, session expiry, retention, export policy, dual control, incident severity и break-glass process.

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

Полные Users/Sessions lists, Venues & data, traders ingestion, policy registry, notifications delivery, support queue, feedback operations, audit log, staff/access, admin auth/2FA, permission denied, scope kill switch, bulk-result states и безопасный export.

Текущая админка EN-only, использует sample data и не имеет backend. Пользовательские экраны прошли структурный и визуальный QA, но последняя итерация ещё не прошла свежий ручной Present. Полная приёмка админки также не подтверждена.

## 12. Открытые решения владельца

До начала дизайн-итерации достаточно четырёх решений:

1. **Нужна проверка:** принимаем ли предложенную RBAC-матрицу и ограниченный контекст Support.
2. **Нужна проверка:** входит ли support queue в первую demo-админку; рекомендация — да, без SLA и attachments.
3. **Нужна проверка:** показываем ли owner finance в первой Figma-итерации как source disconnected/empty; рекомендация — да, без operational payout controls.
4. **Нужна проверка:** оставляем ли generic content/FAQ за пределами V1; рекомендация — да.

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
| Support access/retention lifecycle | нужен безопасный Support scope | **Нужна проверка** |
| Finance evidence/attribution/FX | нужен owner ledger без ложных сумм | **Нужна проверка** |
| Referral thresholds и conflict rules | нужна версия партнёрской политики | **Нужна проверка** |
| GEO/legal/security/live gates | обязательны только перед live | **Нужна проверка позднее** |

## 14. Этапы работы без автоматического перехода

### Этап 0. Принять карту

**Результат:** утверждены V1/out-of-scope, ADM-01–ADM-15, четыре решения владельца и терминология.

**Готово, когда:** нет конфликтов со свежими ADR; каждый пункт имеет status; существующие Figma frames сопоставлены со стабильными IDs.

### Этап 1. Спроектировать demo-админку в Figma

**Объём:** ADM-01–ADM-12; ADM-13 только empty/source disconnected; desktop-first, критические emergency reads позже можно адаптировать для mobile.

**Результат:** карта flow, экраны, роли, все data/action states, RU/EN, кликабельные пути и список неиспользуемых элементов.

**Готово, когда:** Owner, Operator, Support и Read only проходят свои сценарии; запрещённые controls отсутствуют; unknown/partial/stale/permission states проверены в Present.

**Переход:** только по отдельной команде владельца. Этот аудит Figma не меняет.

### Этап 2. Утвердить технический дизайн

**Объём:** сущности, state machines, append-only ledger/audit, RBAC, API contracts, capability evidence, error taxonomy, retention и observability.

**Результат:** технический документ и ADR по оставшимся решениям BL-05–BL-08; API PR #14/#15 безопасно обновлены от main и review пройден.

**Готово, когда:** каждой ячейке интерфейса назначен источник; каждой mutation — permission, idempotency и reconciliation; секреты и PII имеют границы.

**Переход:** только по отдельной команде владельца.

### Этап 3. Реализовать read-only foundation

**Предложенный порядок:** auth/RBAC → internal demo read models → audit log → public venue adapters → overview/users/sessions/incidents → support/notifications → finance empty states.

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
| P1 | overview, users, sessions, incidents | средняя–высокая | основная ежедневная работа |
| P1 | venue/data health и capability evidence | высокая | разные API, cache и права |
| P1 | support/feedback/notifications | средняя | полезно для первой проверки продукта |
| P2 | fee/policy registry и owner finance read-only | высокая | нужны versioning и доказуемые источники |
| P3 | live private reads и mutations | очень высокая | signer, scopes, GEO, recovery и деньги |
| P3 | CMS, partner cabinet, payouts | высокая | вне первого demo scope |

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

