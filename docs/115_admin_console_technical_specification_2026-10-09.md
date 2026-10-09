# Shadow: техническая спецификация админки

Срез: **9 октября 2026**. Версия документа: **1.0 для проектирования и реализации после отдельного GO**.

## 1. Назначение, статус и приоритет источников

Документ описывает полную целевую админку: модули, данные, права, API, фоновые процессы, финансы, управление контентом, безопасность, аварийные режимы, эксплуатацию и критерии приёмки. Он дополняет [план 114](114_admin_console_audit_and_plan_2026-10-06.md) конкретными техническими контрактами. Сверка с пользовательским интерфейсом — [отчёт 116](116_admin_user_interface_consistency_2026-10-09.md).

**Согласованные продуктовые требования** взяты из последних прямых решений основателя и ADR-0029–0041. **Предлагаемые технические решения** ниже — проект спецификации, а не утверждение работающей реализации. Названия таблиц, внутренних endpoints, структуры пакетов и выбор инфраструктуры предлагаются этим документом. Конкретные provider-права, сети, активы, receiving accounts и payout routes проверяются при интеграции API. Наличие endpoint в документации не означает доступ проекта или разрешение live.

При конфликте действует: последнее решение основателя → действующие ADR → этот технический документ → актуальная бизнес-логика → исторический план/макет. Состояние «согласовано» в старом отчёте не отменяет новое решение. Подготовка документа не разрешает реальные сделки, выплаты, регистрацию аккаунтов или изменение Figma.

### 1.1 Неизменяемые границы

- Две площадки с начала архитектуры: `polymarket`, `limitless`. Данные и действия сохраняют площадку и окружение.
- Первый работающий выпуск — paper/demo; live и денежные операции выключены по умолчанию и требуют отдельных площадочных gates.
- Админка и пользовательское приложение используют одну доменную модель. Админка не создаёт альтернативный баланс, статус заявки или версию тарифов.
- Деньги пользователей, виртуальная экономика demo и собственные финансы сервиса — раздельные контуры.
- Два личных Owner-аккаунта; Owner встроен, остальные роли — изменяемые пресеты и кастомные права. Operations объединяет поддержку и операции.
- Тексты и in-app маркетинг публикуются самостоятельно по scopes, с журналом; обязательное согласование Owner для них отсутствует.
- Численные тарифные/реферальные правила, публикация тарифов, VIP и выплаты — только Owner. Пресет не обходит эту границу.
- Выплаты: весь доступный баланс выбранной площадки, без частичной суммы; pending в доступный баланс не входит. Owner подтверждает в админке, система исполняет и сверяет.
- Денежная сводка в `$`; внутренний расчёт `1 USDT = $1`. Другие активы не получают это правило автоматически.
- При неизвестном результате нельзя повторить опасное действие, освободить резерв или вручную объявить успех.

### 1.2 Объём по этапам

| Контур | Первый рабочий выпуск | Будущий интеграционный/live этап |
| --- | --- | --- |
| Users, sessions, incidents, reconciliation | внутренние paper-данные и разрешённые demo-команды | private reads/доказанные операции по отдельному gate |
| Health двух площадок | публичные чтения, metadata, honest disconnected/unknown | проверки доступов, signer, private feeds |
| Staff/access | роли, scopes, admin-session revoke, журнал | расширение провайдеров доступа при необходимости |
| Content/localization | управляемые тексты, переводы, версии, публикация | конструктор лендинга позже |
| Marketing | in-app announcements и delivery/read evidence | массовые email/Telegram/push позже |
| Support/feedback | очередь, переписка, назначения, session context | вложения и SLA позже |
| Pricing/VIP | версии, симулятор, Owner-конфигурация; alpha fee 0 | активация paid после отдельного gate |
| Service finance/payouts | полная схема, формы и честный disconnected; только подтверждённые источники | реальное получение комиссий и автоматическая выплата после gates |
| Emergency | server-side paper stop, availability, funding UI controls | доказанный enforcement каждой live-интеграции |

## 2. Архитектура приложения

### 2.1 Предлагаемый стартовый стек и границы

TypeScript — согласованный язык. Для первой реализации предлагается модульный backend с общей PostgreSQL и отдельными процессами API/worker; отдельный emergency endpoint/process и изолированный payout executor. Один репозиторий и общий доменный пакет позволяют развиваться небольшими проверяемыми срезами. Разбиение всех модулей на микросервисы не является условием первого выпуска.

| Компонент | Ответственность | Запрещённые зависимости/действия |
| --- | --- | --- |
| `apps/web` | пользовательские экраны, API read models, content bundle | прямой доступ к внутреннему ledger, секретам и admin API |
| `apps/admin` — новый пакет | desktop-first console, permissions preview, confirmation, monitoring | самостоятельный расчёт окончательного fee/balance, хранение ключей |
| `apps/api` — новый пакет | user/admin маршруты с отдельной аутентификацией; доменные команды | внешний денежный side effect внутри HTTP-транзакции |
| `apps/worker` | ingestion, paper execution, reconciliation, projections, delivery | blind retry unknown, исправление денег SQL-редактированием |
| emergency control process | независимый stop/recovery path, state/acks, status bundle | зависимость от user frontend, маркетинговой публикации или доступности venue API |
| payout executor | только подтверждённые сервисные выплаты и readback | чтение пользовательских signer secrets, произвольная команда «send(address, amount)» из UI |
| `packages/core` | состояния, policy, risk, команды, инварианты | imports UI/provider SDK |
| `packages/platforms` | адаптеры площадок, provenance, capabilities | внутренняя бизнес-политика ролей/рефералов |
| `packages/contracts` — новый | типы запросов/ответов/событий и runtime-схемы | provider secrets, SDK-типы как публичный контракт |

Redis/внешний broker не обязателен для первого среза. Durable outbox и очередь в БД достаточны как предлагаемая основа; транспорт можно заменить без изменения доменных event IDs. CDN/object storage — для опубликованных bundles и immutable evidence, без публичного раскрытия личных данных. Конкретные библиотеки, версии, hosting и identity provider выбираются перед реализацией и проверяются отдельно.

### 2.2 Путь команды

`Admin UI → authentication/CSRF → authorization → schema/stateVersion → emergency/capability → domain transaction → audit + outbox → worker recheck → external action → observation → reconciliation → shared projection → user/admin UI`.

Внешний запрос не входит в SQL-транзакцию. Успешный приём команды возвращает operation ID, но не `paid`, `filled` или `delivered`. Переходы проекций происходят только по доменным событиям с evidence. DB record и outbox создаются атомарно; event delivery может повторяться, поэтому consumers дедуплицируют.

## 3. Общие контракты данных и API

### 3.1 Идентичность и provenance

В каждой venue-сущности обязательны `venue`, `environment`, `account_context_id`, внутренний `id`; provider identifiers хранятся отдельными строковыми полями. Uniqueness provider objects включает площадку, окружение, тип объекта и account context там, где идентификатор не глобален. Одинаковые названия рынков не являются общей идентичностью.

Общие поля: `created_at`, `updated_at`, `state_version`, `correlation_id`. Время хранится в UTC; локальная зона пользователя хранится явно для дневных лимитов и UI. Evidence добавляет `source_time`, `observed_at`, `source_ref`, `adapter_version`, `completeness`, `freshness`, `verification_status`.

`data_status` (`complete`, `partial`, `stale`, `unavailable`, `unknown`, `disconnected`) отдельно от бизнес-статуса объекта. Отсутствие значения — `null + reason`, а не `0`. Список пустой по фильтру, отсутствие источника и отсутствие событий — разные ответы.

### 3.2 Деньги

В JSON суммы/количества — строки; внутренний расчёт — целые минимальные единицы или decimal arithmetic с явной precision, без binary floating point. `Money` содержит `asset_id`, `chain_id` при необходимости, `amount_atomic`, `decimals`; отчётная оценка — `usd_amount`, `valuation_policy_version`, `valuation_source`, `valued_at`.

Для USDT valuation policy равна fixed 1:1. Это не универсальный курс USDC/pUSD/native gas и не обещание внешнего обмена. Token identity — chain + contract, символ недостаточен. Точность USD, округление каждого компонента, ограничения минимальных сумм и conversion quotes требуют версионированного calculation profile до активации live; отсутствие профиля блокирует соответствующий расчёт, не подставляет случайное округление.

### 3.3 Внутренний API

Все endpoints ниже — предлагаемые внутренние маршруты Shadow под `/admin/v1`, а не endpoints площадок. User API использует отдельный `/app/v1` и не принимает admin scopes. REST reads используют cursor pagination, whitelist фильтров/sort и bounded page size; экспорт — отдельная асинхронная операция.

Команды: `Idempotency-Key`, `expected_state_version`, `reason` для чувствительных действий, server-derived actor. Повтор того же ключа с тем же payload возвращает ту же operation; другой payload с тем же ключом — `409 IDEMPOTENCY_CONFLICT`. Ключ включает actor/session boundary и командный target; dedup внешнего действия дополнительно использует domain operation ID.

Response envelope: `data`, `data_status`, `source_time`, `observed_at`, `projection_version`, `request_id`, `capability`, `effective_controls`. Errors: `code`, безопасный `message_key`, `details` разрешённого scope, `retryable`, `operation_id`, `request_id`. Конфликт состояния — 409; запрет роли — 403; истёкшая сессия — 401; rate limit — 429; unavailable source/controls — явный ошибочный ответ без побочного действия. Не раскрывать credentials/provider raw error secrets.

Асинхронная команда возвращает 202 и `operation_id/status_url`. `GET /operations/{id}` поддерживает `accepted`, `queued`, `running`, `succeeded`, `failed`, `blocked`, `unknown`, `cancelled_before_dispatch`. `succeeded` доменной команды не обязательно означает исполнение финансового перевода: конкретный объект и его status возвращаются отдельно. SSE/WebSocket для обновлений — предлагаемый транспорт; polling остаётся доступным. Permission change/revoke проверяется и для открытого stream.

### 3.4 Конкурентность и транзакции

- Optimistic version check на edit/publish/resolve; два Owner не перезаписывают изменения друг друга.
- Для reserve/session creation/payout — DB lock/unique constraints в пределах одной транзакции. Одна активная user demo-session, один payout intent на тот же eligible snapshot.
- Outbox события имеют уникальный `event_id`, sequence в aggregate, `schema_version`; consumers имеют inbox/processed-event uniqueness.
- Provider callback не считается доверенным без проверки подписи/identity и повторного чтения, когда оно требуется contract. События вне порядка не переводят объект назад в противоречивый terminal state.
- Повторяем автоматически только безопасные reads и доказанно идемпотентные действия. После timeout внешней отправки сначала lookup/reconcile, не resend.

### 3.5 Минимальная схема хранения и ограничения

Это предлагаемая схема для миграций, не существующая БД. Payload JSONB допустим для versioned evidence; ключевые связи, деньги и constraint-поля должны быть типизированными колонками, а не неограниченным JSON.

| Таблица/aggregate | Обязательные поля сверх общих | Ограничения |
| --- | --- | --- |
| `staff_accounts/admin_sessions` | identity, status, auth_version; session hash, staff_id, expiry, revoked_at | нет raw session token в audit; uniqueness identity |
| `role_versions/assignments` | role_id/version, grants, staff_id, scope/expiry | published version immutable; server Owner marker отдельно |
| `sessions/settings_versions` | user_id, venue, mode, trader_id, lifecycle, settings_version, timezone | unique active demo per user; settings linked/pinned |
| `operations/attempts` | class, target, intent digest, actor/session ref, control version, state; external refs | unique command/idempotency identity; попытки не удаляются |
| `orders/fills/reserves/lots` | session, venue, source/intent IDs, quantities, outcome/cancel state | unique source fill; reserve release evidence; copied/manual lot distinction |
| `incidents/reconciliation_attempts` | target identity, severity, assignee, reason, evidence refs | resolution не меняет financial/operation records |
| `connection_profiles/capability_evidence` | context IDs, credential_ref, adapter/config versions, operation class, verification | metadata только; scope-aware unique capability identity |
| `health_observations` | connection/component/status/times/error category | append observations; readiness query не подменяет unknown |
| `policy_versions/vip_assignments` | type/version/scope, effective interval, values, publisher, subject, reason | no conflicting effective interval; numeric Owner guard |
| `ledger_transactions/entries` | book, venue, asset, amounts, debit/credit account, source/correction ref | per-asset balancing, unique external-event posting |
| `receipts/allocations/liabilities` | source account/evidence; accrual links; partner/venue, eligibility/version | allocations ≤ confirmed receipt; immutable source obligation identity |
| `payout_intents/liability_reservations` | full snapshot/revision, route/source/destination versions, fee policy, net/gross | liability slice cannot enter two active intents; settlement once |
| `tickets/messages/assignments` | user/session optional, author type, visibility, client_message_id, delivery state | public/internal visibility hard boundary; unique message dedup |
| `content_versions/bundle_manifests` | key/locale/version/state/placeholder schema, author/publisher | published immutable; one atomic manifest per surface/locale |
| `announcements/deliveries/preferences` | purpose, audience/content versions, recipient, channel/read state, consent evidence | dedup campaign-version+recipient+surface; preferences checked at delivery |
| `controls/enforcement_acks/recovery_approvals` | scope/action class/version, reason/incident, component/ack time, actor/checklist digest | monotonic version; distinct recovery identities |
| `audit_events/outbox/consumer_inbox` | actor/action/target/safe diff; aggregate event sequence | append-only audit; unique event/schema ID and processed consumer ID |

PII, staff auth, source evidence и публичные read projections имеют разные data-access paths. Reference to user/session сохраняется даже при редактировании профиля; удаление PII не уничтожает необходимую pseudonymous operation identity. Конкретные privacy deletion/retention правила требуют проверки до production.

### 3.6 Минимальный каталог mutation endpoints

В prefix `/admin/v1`:

| Команды | Permission / результат |
| --- | --- |
| `POST /sessions/{id}/pause`, `/disconnect-demo` | соответствующий session scope; commands через общий domain service |
| `POST /incidents/{id}/assign`, `/comments`, `/resolve` | incident scopes; resolution с evidence, без rewrite outcome |
| `POST /reconciliation-runs` | reconciliation.run; object identity/read-only observation |
| `POST /tickets/{id}/messages`, `/assign`, `/transitions`; `/feedback/{id}/transitions` | support/feedback scopes; public/internal visibility явная |
| `POST /roles`, `/roles/{id}/versions`, `/staff/{id}/assignments` | role.manage + escalation guard; immutable versions |
| `POST /admin-sessions/{id}/revoke` | access.revoke; persistent revocation + audit |
| `POST /connections/{id}/recheck` | health.recheck — отдельный предлагаемый scope; safe probe job |
| `POST /tariff-versions`, `/referral-versions`, `/transfer-fee-policies`, `.../{id}/publish` | численные edits и publication только Owner |
| `POST /pricing/simulations` | pricing.simulate; simulation-only, no ledger posting |
| `POST /users/{id}/vip`, `/partners/{id}/vip`, `.../{id}/end` | только Owner, effective interval/policy version |
| `POST /partners/{id}/payout-previews`, `/payouts`, `/payouts/{id}/confirm` | только Owner; full-balance digest, reservation, async execution |
| `POST /payouts/{id}/cancel-before-dispatch` | только Owner, proven no-send boundary |
| `POST /payouts/{id}/reconcile` | reconciliation.run; не новая отправка и не изменение реквизитов |
| `POST /content/drafts`, `/content/validate`, `/content/publications`, `/content/rollback`; `/locales` | content/locale scopes, no Owner approval |
| `POST /announcements`, `.../{id}/validate`, `/test`, `/publish`, `/pause` | marketing scopes, in-app only V1 |
| `POST /controls/activate`, `.../{id}/recovery-plan`, `/recovery-approvals`, `/restore` | emergency scopes; independent restore checks |
| `POST /audit-exports`, `/finance-exports` | separate export scope; async redacted job |

READ endpoints предоставляют list/detail/versions/history для этих сущностей, plus `/overview`, `/connections/{id}/capabilities`, `/controls/effective`, `/partners/{id}/balance`, `/partners/{id}/payout-options`, `/operations/{id}`. Delete historical audit/posted ledger/paid payouts/published policy/content endpoint отсутствует. Staff-facing raw ledger mutation, mark-paid, trade-for-user, arbitrary signer endpoint отсутствуют.

### 3.7 Доменные события

Минимальные event families: `SessionCommandAccepted/Applied`, `FillObserved/Confirmed`, `ReserveChanged`, `IncidentAssigned/Resolved`, `ReconciliationCompleted`, `AdminSessionRevoked`, `PolicyPublished`, `UserVipChanged`, `ReceiptObserved/Confirmed/Allocated`, `LiabilityEligible/Held`, `PayoutReserved/DispatchStarted/Submitted/OutcomeUnknown/Confirmed`, `CorrectionAppended`, `ContentPublished`, `AnnouncementPublished/Paused`, `DeliveryObserved`, `EmergencyActivated/EnforcementAcknowledged/RecoveryApproved/ControlRestored`.

Envelope: `event_id`, `schema_version`, `aggregate_id/version`, `event_type`, `occurred_at`, `observed_at`, `environment`, `venue?`, `correlation_id`, `causation_id`, `actor_ref`, `payload`, `evidence_refs`. User projection consumes только безопасный subset; internal staff notes/secrets/incident details не уходят в app stream. Replay пересчитывает projections, не выполняет external side effect повторно.

## 4. Аутентификация, роли и разрешения — ADM-14

### 4.1 Staff-модель

Сущности: `StaffAccount`, `RoleDefinition`, `RoleVersion`, `PermissionGrant`, `RoleAssignment`, `AdminSession`, `AccessAudit`. Публичный user account не становится staff автоматически. Сотрудник имеет отдельную identity и status `invited/active/suspended/revoked`; вход требует предложенного MFA/re-auth для чувствительных команд. Выбор MFA и invitation provider — техническая настройка до реализации.

Owner назначен двум личным аккаунтам; shared account/seed недопустим. Owner-привилегии проверяются системным признаком, а не именем кастомной роли. Самостоятельное повышение прав, выдача себе Owner и обход domain guard через custom scope запрещены. В качестве технической защиты предлагается не допускать удаления последнего работоспособного Owner и проверять owner-assignment отдельно от редактора ролей.

Grant: `permission`, `environment`, `venue`, `section`, `data_class`, `expires_at`. Авторизация применяется к списку, detail, nested joins, export и stream; разрешение чтения карточки не открывает все связанные данные. Сотруднику возвращается `allowed_actions`, вычисленный сервером; UI не является security boundary.

### 4.2 Предлагаемый каталог scopes

| Группа | Права | Безусловная граница |
| --- | --- | --- |
| Operations | `operations.view`, `session.pause`, `session.resume_demo`, `session.disconnect_demo`, `incident.view/assign/resolve`, `reconciliation.view/run` | live submit/close за пользователя не делегируется этим набором; resume снимает только разрешённую demo-паузу, не emergency gate |
| User context | `users.view_minimal`, `users.view_extended` | extended отдельно; нет impersonation login |
| Support | `support.view/reply/assign`, `feedback.view/manage` | ticket visibility по policy, без изменения ledger |
| Data | `health.view`, `traders.view`, `ingestion.view` | ручное исправление source metrics не предусмотрено |
| Pricing | `pricing.view/simulate`, подготовка описания | численные параметры, publish, user/partner VIP activation — только Owner |
| Finance | `finance.view_aggregate`, `finance.view_detail`, `finance.export` | create/confirm/cancel payout и изменение реквизитов — только Owner |
| Staff | `staff.view`, `role.manage`, `access.revoke` | scope не даёт self-escalation или Owner-only действий |
| Content | `content.view/edit/publish`, `locale.manage` | текст не изменяет вычисляемый тариф, state или permission |
| Marketing | `marketing.view/edit/segment/test_send/publish/pause/export_aggregate` | нет обязательного Owner approval; customer consent сохраняется |
| Audit | `audit.view/export` | append-only, export не включён в view |
| Emergency | `emergency.view/activate/recover` | restore GLOBAL_STOP/TECH_MODE: Owner + другой человек |

Изменяемые пресеты Operations/Ops Lead/Marketer/Auditor — стартовые наборы, не отдельные системные роли. `role.manage` не означает выдачу прав шире полномочий управляющего; назначение чувствительных grant требует отдельного guard. Конкретный bootstrap этих guard — перед backend.

### 4.3 Session revoke

`POST /staff/{id}/sessions/revoke` и `POST /admin-sessions/{id}/revoke` → revoke marker + session/auth version + audit; API/streams/workers проверяют актуальные права перед execution. Уже отправленное внешнее действие не отменяется отзывом staff session. Отозванная identity не может подтверждать recovery или payout. V1 не ротирует venue API keys через админку.

## 5. Полная карта разделов и контрактов

Для каждого раздела обязательны loading/empty/filter-empty/error/stale/disconnected/permission-denied/auth-expired, видимый environment, scope и last update. UI сначала подтверждает приём команды, затем показывает её доказанный результат. Таблица ниже покрывает все ADM-01–ADM-18.

| Раздел | Read model / entities | Reads и команды | Права / событие / приёмка |
| --- | --- | --- | --- |
| ADM-01 Overview | `OperationsSnapshot`, incidents, health, queue lag | `GET /overview`; drill-down с тем же фильтром | operations.view; counts из той же проекции, unknown не зелёный |
| ADM-02 Users | User, locale, sessions, tickets, UserVipAssignment | `GET /users`, `/users/{id}`; `POST /users/{id}/vip`, end/remove | user-context scopes; VIP только Owner; `UserVipChanged` отражён в effective тарифе user UI |
| ADM-03 Sessions | Session, CopySettingsVersion, RiskDecision, order/lot projections | `GET /sessions/{id}`; pause/resume/disconnect-demo | session scopes; `SessionCommandAccepted/Applied`; одинаковый user/admin status |
| ADM-04 Incidents | Incident, assignment, evidence refs, resolution | list/detail; assign/comment/resolve | incident scopes; resolving ticket/incident не меняет operation outcome |
| ADM-05 Reconciliation | Case, Attempt, evidence, discrepancies | list/detail; `POST /reconciliation-runs` | reconciliation.run; readback только того же operation identity |
| ADM-06 Venues & data | VenueHealth, MarketSnapshot, FeedCheckpoint | health/catalog/data gaps, request readback | health.view; каждый venue/account/environment отдельно |
| ADM-07 Traders & ingestion | TraderIdentity, metrics, RatingSnapshot, ingestion coverage | traders/detail/ingestion-attempts | traders.view; read-only, manual address не требует рейтинга |
| ADM-08 Tariffs & commissions | TariffVersion, ReferralPolicyVersion, SimulatorRun, overrides | list/draft/simulate/publish/schedule/rollback | numbers и publication Owner-only; snapshots/version history |
| ADM-09 Support | Ticket, Message, Assignment, user/session context | tickets/detail; reply/assign/status | support scopes; одна переписка user/admin, send_unknown отдельно |
| ADM-10 Notifications | Notification, DeliveryAttempt, preferences | list/detail/status; controlled readback | `notifications.view` — предлагаемый отдельный scope; нет fake delivered/прочитано |
| ADM-11 Feedback | FeedbackItem, context, classification | list/detail; categorize/assign/status | feedback.manage; ссылка на ticket/incident по необходимости |
| ADM-12 Audit | AuditEvent, export job | list/detail; export | audit.view/export; запрет update/delete API |
| ADM-13 Owner finance | accrual/receipt/ledger/liability/payout/source | journal/balances/partner; prepare/confirm/cancel-before-send | payouts Owner-only; полный eligible snapshot, paid по evidence |
| ADM-14 Staff & access | staff/roles/grants/admin sessions | staff/role CRUD с versions, permission preview, revoke | deny default, no self-escalation, revoke immediate next check |
| ADM-15 Integrations & security | ConnectionProfile, capability, check, credential metadata | read metadata/health/scopes/expiry, recheck | metadata без secrets; rotation/revoke credentials не V1 |
| ADM-16 Content & localization | keys, immutable bundles, locales, publication | edit/validate/preview/publish/rollback | scopes, без owner approval; placeholder validation и version evidence |
| ADM-17 Emergency | controls, enforcement acks, recovery/checklist | preview/activate/recovery/confirm/staged restore | activation scope; independent second-person restore |
| ADM-18 Marketing | AnnouncementVersion, audience, delivery/read | draft/preview/test/publish/schedule/pause | marketing scopes, in-app V1, no obligatory internal approval |

ADM-06 показывает продуктовую диагностику площадок, ADM-15 — контекст интеграций/доступа. Это разные представления одного ConnectionProfile/health store; статус не рассчитывается дважды независимо. ADM-10 — операционные уведомления, ADM-18 — кампании; общая доставка не смешивает их consent и purpose.

## 6. Sessions, orders, risk и пользовательские деньги

### 6.1 Общая модель

Существующие согласованные [правила MVP](MVP_BUSINESS_LOGIC.md) и ADR-0014–0028 остаются источником расчётов copy/risk. Админка наблюдает `Session`, `CopySettingsVersion`, `TraderSignal`, `CopyDecision`, `OrderIntent`, `ExecutionObservation`, `Fill`, `PositionLot`, `Reserve`, `SessionReport`; не меняет их вручную.

Session status и её запреты разделены: пользовательская pause, системная risk-pause, venue restriction и emergency controls — независимые причины. Resume одной причины не обходит другую. Команда остановки/отсоединения хранит desired state и reconciliation progress; request close не равен closed. Для демо admin disconnect вызывает тот же domain workflow, а не удаление позиций.

### 6.2 Контракты, которые admin обязан сохранить

- Одна активная demo-session. Fresh launch создаёт пустую историю; sample active demo — отдельный fixture, без смешения с user session.
- Fixed amount либо процент от подтверждённой суммы конкретной сделки трейдера. Изменение настройки действует на новые сигналы, не переписывает существующие intents/fills.
- Новая BUY проверяется на полную сумму с reserved budget/expenses/day/position limits. Недостаток полного лимита/доказанной глубины — skip whole, не уменьшение до остатка.
- Повтор одного source event не создаёт новую копию; самостоятельная повторная покупка — новый signal. Пропущенный сигнал не догоняется после recovery.
- После подтверждённого partial order fill позиция хранит исполненную часть, remainder/reserve удерживается до результата отмены. Late fill во время cancel уменьшает только ещё возможный остаток.
- Дневной лимит: zone и reset instant из session; unresolved buy reserve переносится через reset. Это не midnight в зоне сервера.
- Обычная user pause запрещает новые BUY/увеличения, но не равна GLOBAL_STOP. Сокращение риска по существующим пользовательским правилам не включается автоматически при глобальной аварии.
- Money availability, position value, realized/unrealized P&L, cash flow — отдельные поля. Неизвестные цены/расходы не подставляются нулями.
- Торговая partial fill допустима; **частичная партнёрская выплата запрещена**. Эти автоматы не используют один status enum.

### 6.3 Не закрывать открытые пользовательские правила случайно

Оставшиеся открытые аспекты BL-05–BL-08 и метрик в MVP_BUSINESS_LOGIC (учёт tracked/manual частей, завершение сессии с позициями, rounding/исполнение и приоритеты ограничений) не объявляются решёнными административной спецификацией. Уже закрытые ADR вопросы BL-01–BL-04 заново не открываются; незавершённые диапазоны/точность sizing отмечаются отдельно. Все связующие DTO должны сохранять unknown/evidence и возможность версии расчёта. До production affected workflow требует отдельного domain contract; админка не вводит новые drawdown thresholds или автопродажи сама.

## 7. Incidents и reconciliation

Incident: `new → triaged → assigned/investigating → resolved → closed`, с возможностью reopen при новом evidence. Это предлагаемый workflow расследования; статус внешней операции хранится отдельно. Severity/priority и причина — versioned dictionary, numeric alert thresholds не зашиваются без calibration.

ReconciliationCase содержит object identity, reason, expected/observed, reservations, attempts, evidence, assignee и decision. Attempt: `queued/running/succeeded/failed/unknown`. Два запуска одной проверки объединяются или сериализуются. API `POST /reconciliation-runs` принимает object ID и допустимый adapter/read scope, не произвольный URL/transaction для подписи.

Новый evidence вызывает обычный domain transition и shared projections. Разрешена добавочная корректировка с причиной и связью с исходной записью; запрещены SQL rewrite past fill/payout, «успех» без evidence и удаление неудобного discrepancy. Export evidence маскирует личные данные/секреты.

## 8. Tariffs, referrals и VIP — ADM-08/02

### 8.1 Сущности и права

`TariffPolicySet`, `TariffVersion`, `ReferralPolicyVersion`, `PartnerTier`, `PartnerVipProfile`, `UserVipProfile`, `UserVipAssignment`, `PolicyPublication`, `SimulatorRun`. Все численные условия вводят Owner вручную; подготовка пояснений и read-only simulation может делегироваться. Публикация/активация/снятие override — только Owner, каждый самостоятельно, без обязательной второй подписи.

Текущая alpha service fee и partner share — 0%. Более поздние paid rates/ceilings из ADR-0005 сохраняются как исторически согласованные версии/границы, не активируются автоматически. Возможность настройки не даёт автоматически поднять действующий ceiling. User VIP отдельно от partner VIP; «VIP» не означает исключение из risk/emergency/venue gates.

### 8.2 Lifecycle и применение

`draft → validated → scheduled/active → superseded/expired`. Validation/simulator/diff обязательны технически; внутренний reviewer/approved шаг не нужен. Atomic publish с version check гарантирует отсутствие перекрытия effective policies для одной комбинации scope/action/liquidity-role. Rollback создаёт новую версию; backdating и молчаливый пересчёт истории запрещены.

Предлагаемый приоритет effective user tariff: platform stage/environment → venue/action/liquidity rule → active user VIP override разрешённых параметров → ceilings/exclusions. Partner reward выбирается отдельно по attribution/referral version/partner tier/VIP. При конфликте двух активных override publish отклоняется, не выбирается случайный последний. Окончательный precedence фиксируется calculation contract до live.

Assignment: profile/custom values, effective start, end или indefinite, reason, actor, version. Expiry/end/removal приводит к обычной применимой версии без переписывания прошлых начислений. У каждого нового расчёта есть effective explanation для user/admin: base rate, override, exclusions, final rate и policy IDs.

Effective intervals — UTC `[from,to)`. Версия расчёта выбирается по подтверждённому экономическому событию/fill time, не по времени доставки API-ответа. Поздний fill до изменения тарифа сохраняет прежнюю применимую версию; если reliable event time неизвестно, начисление остаётся неопределённым до сверки. Receipt arrival не выбирает заново user VIP/rate для старого fill. Calculation hash включает source identity/time, executed amount, action/liquidity evidence, тарифную/referral/VIP/valuation/rounding версии и порядок округления компонентов.

### 8.3 Начисление

`FeeCalculationEvidence`: confirmed fill IDs, liquidity role evidence, action class, notional, currency, rates, policy IDs, rounding profile, fee breakdown. Shadow fee, venue fee, network cost и partner reward — отдельные компоненты. Manual/protective/emergency close и unfilled remainder не создают service fee по действующей политике.

Simulator — без движения денег: прогноз по выбранным inputs, scenarios unknown maker/taker/excluded actions/VIP/tiers, diff с effective policy. `simulated` никогда не попадает в service cash balance или payable. Изменение текста «комиссия» в CMS не меняет расчёт.

## 9. Финансы сервиса — ADM-13

### 9.1 Предлагаемый ledger

Append-only двойная запись для собственных денежных событий сервиса; user paper ledger физически/логически отделён. Entities: `ServiceAccount`, `RevenueAccrual`, `Receipt`, `ReceiptAllocation`, `LedgerTransaction`, `LedgerEntry`, `PartnerLiability`, `LiabilityEvent`, `PayoutIntent`, `PayoutAttempt`, `PayoutEvidence`, `Correction`, `Expense`, `ValuationSnapshot`.

Баланс рассчитывается из entries; не хранится editable «balance» поле как источник истины. Каждая posted transaction сбалансирована по asset/контурy. USD valuation отдельная размерность, а не смешение разных токенов в одной сумме минимальных единиц. Settlement/referral allocation связывает оригинальное начисление, поступление и обязательство; один receipt не расходуется дважды.

### 9.1a Предлагаемая матрица проводок

Это внутренний operational subledger, не обещание готовой бухгалтерской/налоговой отчётности. Accounts: `service_receivable`, `service_cash`, `service_revenue`, `partner_reward_expense`, `partner_payable_pending`, `partner_payable_available`, `partner_payable_reserved`, `transfer_expense`, `adjustment_clearing`. Дебет/кредит рассчитываются внутри одной денежной размерности; преобразование другого актива отражается отдельной settlement/valuation group.

| Подтверждённый факт | Дебет | Кредит | Основание |
| --- | --- | --- | --- |
| Начисление service fee | service_receivable | service_revenue | confirmed executed basis + pinned policy |
| Получение комиссии | service_cash | service_receivable | Receipt/Allocation; не второй revenue |
| Признание partner reward | partner_reward_expense | partner_payable_pending | recognition_basis/referral version + accrual evidence |
| Переход в available | partner_payable_pending | partner_payable_available | eligibility/hold evidence, без нового reward expense |
| Резерв full payout | partner_payable_available | partner_payable_reserved | frozen full intent; no cash transfer yet |
| Полная выплата, service платит fee | partner_payable_reserved + transfer_expense | service_cash | полный net transfer плюс подтверждённый расход сервиса |
| Полная выплата, partner платит fee | partner_payable_reserved | service_cash | gross liability = recipient net + раскрытое удержание; actual source/gas entries через settlement group |
| Доказанная неотправка/release | partner_payable_reserved | partner_payable_available | no-execution evidence; unknown не основание |
| Correction/refund | связанные compensating accounts | связанные compensating accounts | correction_of + evidence; новая запись, не rewrite |

Для комиссии в ином asset settlement group явно связывает USD liability, token transfer и gas expense; нельзя свести их к одной несбалансированной проводке. Несопоставленные receipts находятся в clearing до доказанного allocation, не закрывают произвольный accrual. Ledger constraints: asset-balancing, receipt allocations ≤ receipt, unique external source posting, no duplicate settlement, отсутствие отрицательной availability от конкурирующих резервов. RoundingProfile имеет scale/precision, component rounding mode/order и remainder handling; отсутствие согласованного профиля блокирует live posting.

### 9.1b Финансовые aggregate keys

`RevenueAccrual` уникален по `(environment,venue,account_context,confirmed_fill_id,fee_component)`; policy_version — неизменяемое поле первого начисления, не часть semantic unique key. Изменение факта создаёт linked correction, а не второе начисление. `ReceiptAllocation` имеет FK receipt/accrual, amount/asset/USD valuation и evidence; суммарный allocation проверяется DB transaction. `PartnerLiability` связан с accrual/referral attribution, eligibility policy и журналом; unique source obligation key `(accrual_id,partner_id,reward_component)` исключает повтор при смене referral policy. Policy version хранится pinned, corrections отдельны.

`PayoutIntent` обязательно содержит balance revision, полный набор liability slices, gross USD, net token atomic amount/decimals, route/source/destination versions, fee policy/estimate/cap, preview digest, Owner/session ref и control version. После confirm financial payload immutable. `PayoutAttempt` содержит persisted submission state, lease/fence token, payload digest и все известные external IDs. `PayoutEvidence` — source/destination, token/chain, amount/finality/fee, provider/chain evidence и route legs. Эти поля не скрываются за generic status string.

| Показатель | Значение | Не означает |
| --- | --- | --- |
| estimated | расчёт/ожидание с неполным evidence | полученные средства |
| accrued | подтверждённое право сервиса на доход | cash receipt |
| received | подтверждённое поступление собственных средств | весь accrual автоматически погашен |
| partner pending/held | начисление ещё не прошло доступность | баланс к выплате |
| partner available | подтверждено и прошло текущую eligibility policy | деньги другой площадки доступны этому маршруту |
| partner reserved | вошло в конкретный payout intent | новое доступное обязательство |
| partner paid | полное исполнение intent подтверждено | ручной отметкой закрытый unknown |

Частичное входящее **поступление** может существовать и отображаться отдельно; это не частичная партнёрская выплата. Внутренний перевод между ServiceAccounts не revenue. Возвраты/корректировки — linked entries, не редактирование оригинала. Коррекция не создаёт повторную выплату уже погашенного обязательства.

### 9.2 Источники и eligibility

Revenue и receipts принимаются только из подтверждённого источника с ownership provenance. Builder attribution, публичный referral counter и наш service fee — разные facts. Если источник не подключён, показываются disconnected/empty, а не выдуманная выручка из demo.

Liability eligibility — versioned функция от подтверждённого начисления, основания участия/attribution, условий доступности/hold, corrections/disputes и состояния уже исполненных/зарезервированных выплат. Действующие численные параметры сохраняются из policy до их явного изменения Owner. Конкретная стратегия receipt allocation и окончательные entitlement timestamps уточняются интеграционным контрактом; неподтверждённая сумма никогда не available.

`recognition_basis` (подтверждённое начисление либо подтверждённое получение комиссии как база партнёрского вознаграждения) остаётся требующим определения calculation-policy полем до paid activation. Не добавлять молча условие «сервис уже получил деньги» к ранее согласованному начислению: accrual confirmation и actual receipt — разные факты. Refund после paid или одновременно с reservation вызывает linked correction/incident; автоматический clawback/отрицательный баланс партнёра не считается согласованной бизнес-политикой.

Общий partner USD balance — сумма venue projections, не дополнительная запись обязательства. Cross-venue source transfer/bridge нельзя выполнять автоматически из-за недостатка баланса одной площадки. Расходы/выручка каждой площадки остаются различимыми.

## 10. Полная выплата партнёру — ADM-13

Принят [ADR-0041](decisions/0041_owner_confirmed_automated_partner_payouts.md). UI: партнёр → площадка → доступный маршрут → preview всего available balance → «Выплатить» → «Подтвердить». Нет обязательного внешнего кошелька на каждую выплату и нет произвольного поля уменьшения суммы.

### 10.1 Подготовка и confirmation

`POST /partners/{id}/payout-previews` получает venue/route/recipient-version, вычисляет available snapshot сервером и возвращает full amount, token/chain, fee payer, estimated fee, recipient net, total source debit, controls/version, eligibility IDs, expiry при необходимости quote. Не допускается клиентское amount как авторитетная сумма.

`POST /payouts` создаёт intent из preview; `POST /payouts/{id}/confirm` проверяет Owner/re-auth, expected version, неизменность snapshot/recipient/policy/quote и резервирует полный набор eligible liability slices. Изменился available balance или quote — новый preview и подтверждение, без молчаливой замены суммы. Новые начисления после freeze являются отдельным следующим available balance, не частично выплаченным старым intent.

Confirmation response: `intent_id`, `state`, `operation_id`, `audit_id`, `status_url`, pinned balance/recipient/policy/control revisions. `GET /partners/{id}/balance` возвращает pending/held/available/reserved/paid, revision и exclusions; `GET /partners/{id}/payout-options` — verified/disabled options с reason/evidence time. `GET /payouts/{id}` раскрывает frozen intent/attempts/redacted evidence. `POST /payouts/{id}/reconcile` только читает результат, не повторяет перевод.

Реквизиты — versioned `PartnerPayoutRecipient`: chain/address/token compatibility, verification/allowlist status и actor/reason. Создание/изменение/деактивация через `/partners/{id}/payout-recipients` только Owner; подтверждённый intent остаётся на своей recipient version. API accept новой записи адреса не означает, что площадка уже разрешила его.

`SourceSpendReservation` блокирует доступное расходование сервисного источника по account/chain/asset и резерв fee asset, чтобы два разных партнёра не потратили один баланс. Liability reservation и source-spend reservation атомарны с intent/audit/outbox; external balance имеет freshness gate и recheck перед send. Unknown держит оба резерва. Независимые внешние переводы вне Shadow могут изменить баланс, поэтому preflight остаётся обязательным и не обещает абсолютного контроля кошелька.

### 10.2 Автомат состояний

| Состояние | Переход / резерв / запрет |
| --- | --- |
| `prepared` | preview/intent, внешней отправки нет; сумма ещё не paid |
| `confirmed_reserved` | full snapshot locked; повтор другого Owner возвращает существующий intent/конфликт |
| `dispatching` | durable attempt создан до side effect; executor повторно проверяет controls и capability |
| `submitted` | provider identity известна; наблюдаем до окончательности |
| `confirming` | transaction/user operation найдена, evidence/finality проверяются |
| `paid` | полный рассчитанный перевод доказан; obligation закрыт один раз |
| `blocked` | до confirmation резерв отсутствует; после confirmation и доказанного no-send full резервы сохраняются до явной безопасной release/cancel; автоматической отправки после исчезновения причины нет |
| `failed_confirmed` | доказанный terminal failure/отсутствие исполнения; controlled release + новая попытка с новым preview |
| `unknown` | неизвестно, была ли отправка/исполнение; резерв удерживается, resend запрещён |
| `cancelled_before_dispatch` | отменено до доказанного начала external action; резерв освобождается атомарно |

Partial-paid state отсутствует. Несоответствие пришедшей суммы полной рассчитанной выплате — reconciliation incident; не предлагается «доплатить остаток» кнопкой, пока не выяснен полный результат. Cancel после dispatch нельзя представить как отмену транзакции. Таймаут не равен failed.

После `submission_started` отсутствие доказанной неотправки означает только unknown, не blocked. Stale dispatch lease/restart сначала вызывает lookup прежнего attempt; fencing token не позволяет двум executors отправить его параллельно. При proven non-payment сначала учитываются подтверждённые gas/provider expenses и source cash delta; затем атомарно освобождается полное liability reservation и только неистраченный остаток source reservation. Новый запуск проходит новый preview/confirm Owner; отсутствует unconditional retry endpoint. Отозванные права/сессия инициатора до send блокируют discretionary job; отправленная операция продолжает сверку под системной identity.

### 10.3 Комиссия и settlement

Owner задают `transfer_fee_payer=service|partner`. Preview отдельно показывает gross obligation, expense estimate, recipient net и source debit. При `service` обязательство выплачивается полностью, fee — expense сервиса. При `partner` настроенная комиссия отражается отдельным удержанием, а выплата всё равно погашает весь подтверждённый gross balance.

Gas может оплачиваться другим активом/кошельком; нельзя механически считать debit равным net плюс той же token fee. Списание liability, asset transfer и fee entries связываются одной settlement group. Если фактический fee отличается от estimate, правило максимума/quote validity/отражения разницы определяется до live; нельзя молча уменьшить recipient amount после confirmation или переписать историческую выплату. Кто несёт расходы неудачной попытки (revert/failed bridge leg), должно быть явно определено versioned fee policy до live; отсутствие правила блокирует affected route. Неуспех не означает нулевой gas/provider expense и не делает партнёра частично paid. При неопределённости fee payer policy блокирует activation, а не выбирает default.

### 10.4 Внешние операции

Attempt имеет внутренний id, provider request ID, wallet/account, chain/token, recipient version, signed-payload digest при наличии, nonce/transaction ID/userOperationHash и discovered tx hash. Provider hash может отсутствовать: это не доказанный failure. Executor не получает произвольные реквизиты от browser; только frozen intent и секретный reference к разрешённому сервисному источнику.

Reconciliation проверяет отправителя/получателя/token contract/amount/status/finality/fee и связывает evidence с intent. Receipt success без правильного transfer не равно paid; включение в chain без достаточной окончательности — confirming. Сроки polling/finality и lookup keys задаются adapter profile и интеграционными тестами, без универсального придуманного количества подтверждений.

Bridge route хранит source leg и destination settlement leg с разными operation identities/evidence/finality. Source transaction или поступление на адрес моста не доказывает конечную выплату. Paid — полный рассчитанный destination amount у согласованного beneficiary; source finalized + destination unknown сохраняет reservation/unknown и запрет повторной отправки.

Signing boundary разрешает только source/chain/token/destination-version/amount из frozen intent с control epoch и policy digest. Произвольные calldata/messages через admin API не подписываются. PM Builder header-HMAC authority отдельно от wallet transaction signer; vault/KMS reference сама по себе не доказывает wallet-compatible signing. Настройка signer должна пройти dedicated compatibility/authority test.

## 11. Интеграции, capabilities и health — ADM-06/15

### 11.1 Venue-neutral adapter contract

`describeCapabilities`, `readHealth`, `readMarketSnapshot`, `readTraderHistory`, `readOwnOperation`, `reconcileOperation`; отдельный payout adapter — `previewPayout`, `dispatchPayout`, `lookupPayout`, `readSettlementEvidence`. Funding/user withdrawal не входят в trading execution adapter; сервисные payouts также отдельный authority domain.

Ручной поиск: `readTraderByAddress({venue,address})` и внутренний `GET /traders/by-address?venue=&address=`. Format validation по площадке; состояния `found/not_found/insufficient_data/unavailable`, source coverage и timestamps. Валидный адрес без достаточного рейтинга не превращается в not_found; отсутствие methodology/метрик не запрещает согласованный ручной поиск. Address injection не может изменить provider URL/source wallet.

Capability record: `documented`, `account_granted`, `runtime_verified`, `live_enabled` независимо. Доступное действие = permissions ∩ product policy ∩ environment gate ∩ runtime capability ∩ emergency state. Неподключённый поддерживаемый вариант виден с причиной, но его нельзя отправить. Retry не расширяет permission scope.

Evidence включает checked_at/source_ref, connection_config_version, adapter_version и valid_until/validity_rule. Изменение wallet/profile/scopes/source/adapter аннулирует затронутый runtime_verified до повторной проверки. Documented не является бессрочным green.

### 11.2 Внешние основания и ограничения

- Limitless `POST /portfolio/withdraw` относится к managed server wallet, amount в минимальных единицах, token должен быть recognized collateral, destination ограничен allowlist. Scoped withdrawal token и отдельная Privy-authorized настройка allowlist не заменяются legacy API key. Собственный payout source сервиса требует отдельного подтверждения; child user wallets не источники партнёрских выплат.
- Polymarket Builder Fees поступают в связанный с профилем кошелёк. Перевод требует signer/wallet authorization; Builder/trading credentials сами не дают его. Bridge API создаёт адрес/route, затем нужен отдельный transfer и status readback. Прямой transfer и bridge — разные capability/fee/finality contracts.
- Проверенная на дату документа native Builder Fee policy Polymarket: максимум taker 100 bps, maker 50 bps; изменение раз в 7 дней, вступление через 3 дня, одна pending конфигурация. Внутренняя публикация не означает немедленную внешнюю активацию. Provider-config state (`requested/pending/external_active/mismatch`) хранится отдельно; несовместимое rate/effective time блокируется capability validator. Продуктовая возможность настройки не обещает 1% native maker fee или обход внешних ограничений. Эти изменяемые ограничения перепроверяются при интеграции.
- Конкретные wallets, source assets, сети, quotes, fee collection и payout routes выбираются при интеграции. USDT расчёт 1:1 не доказывает поддержку USDT endpoint площадки.
- Публичные данные, private order feeds и signer/relayer health проверяются отдельно. API HTTP 200 не доказывает ready для торговли/денег.
- Limitless maintenance проверяется как active/scheduled restriction для конкретной operation class; trading cancel-only/post-only не означает автоматически запрет withdrawal. Обработка mode-specific ошибок и повторных reads следует adapter contract, не общей зелёной лампочке.

Официальные основания: [LL withdrawal](https://docs.limitless.exchange/api-reference/portfolio/withdraw), [LL Programmatic API](https://docs.limitless.exchange/developers/programmatic-api), [PM wallets/auth](https://docs.polymarket.com/trading/wallets-auth), [PM builder fees](https://docs.polymarket.com/programs/builders/fees), [PM bridge withdrawal](https://docs.polymarket.com/trading/bridge/withdraw). Перепроверка account-level доступов обязательна перед integration/live.

### 11.3 Health contract

ConnectionProfile: environment/venue/account/profile/signer-context, adapter/config version, scopes, credential metadata refs, responsible staff, public identifiers. HealthCheck: component, status, latency, source/observed times, last success/error, sequence gap, rate-limit observation, threshold profile version.

Проверки: API reachability; authentication; capabilities; public/private feed freshness; websocket reconnect/gaps; RPC/indexer lag; adapter/circuit breaker; queue age; signer/relayer availability; reconciliation oldest unknown; quota/throttling. Каждый компонент поддерживает unknown/not_applicable/disconnected отдельно от healthy.

Нет одного «зелёного» статуса, маскирующего отсутствующую критическую проверку. Ready вычисляется для конкретной операции по её обязательным dependencies. Healthy public catalog не разрешает payout. Freshness/circuit-breaker thresholds калибруются при integration и хранятся версией; unknown threshold не трактуется как бесконечный срок.

V1 показывает metadata и позволяет request recheck. Creation/rotation/revoke venue credentials через админку — следующий этап; `access.revoke` в V1 отзывает только admin session. Secure provisioning выполняется вне content/marketing UI; секреты не попадают в журнал/экспорт.

Expiry/last-used показываются только при наличии фактического provider metadata; отсутствие — `null + not_provided/unknown`, не дата, выдуманная из created_at.

## 12. Аварийное управление — ADM-17

### 12.1 Ортогональные ограничения

`AvailabilityState`: normal/TECH_MODE. `ActionRestriction`: GLOBAL_STOP, risk pause, read-only, venue isolation, DEPOSITS_OFF, WITHDRAWALS_OFF. Последние scoped ограничения и дополнительные варианты уровня — техническая модель; согласованные GLOBAL_STOP/TECH_MODE/funding controls сохраняются. Комбинация вычисляется сервером как пересечение разрешённых действий; локальный normal не снимает глобальный stop.

Scope: project/environment/venue/subsystem; reason/incident/actor/version/effective time. Availability хранится отдельно от trading state. TECH_MODE закрывает user surfaces/API/product jobs, оставляет emergency/monitoring/audit/incidents/reconciliation. GLOBAL_STOP запрещает новые продуктовые и финансовые side effects; не объявляет уже отправленные операции отменёнными и не удаляет evidence.

| Operation class | User pause | GLOBAL_STOP | TECH_MODE | DEPOSITS_OFF / WITHDRAWALS_OFF |
| --- | --- | --- | --- | --- |
| `new_copy_buy` | запрещено | запрещено | запрещено | сами по себе не торговый gate |
| `existing_position_reduce` | допускается по действующей user policy | только отдельный доказанный emergency runbook, иначе запрещено | аналогично | не торговый gate |
| `user_deposit_instructions` | отдельный capability | запрещено | запрещено | DEPOSITS_OFF запрещает |
| `user_withdrawal_submit` | отдельный capability | запрещено | запрещено | WITHDRAWALS_OFF запрещает |
| `service_partner_payout` | user pause не влияет | запрещено до новой отправки | запрещено до новой отправки | user funding switch сам по себе не payout switch |
| `observation/reconciliation/audit` | продолжается | продолжается | продолжается | продолжается |
| `emergency_control/recovery` | отдельно authorized | защищённый control plane доступен | защищённый control plane доступен | доступен |

Отдельный scope-stop сервисных выплат можно добавить как техническое расширение action-class restrictions; имя нового переключателя не считается ранее согласованным. User Withdraw не управляет partner payout.

### 12.2 Enforcement

State сохраняется durable в отдельной управляющей схеме/контуре с независимым endpoint. Команда stop не зависит от venue API. Gate проверяется на HTTP admission, queue admission, worker start и перед каждым внешним действием; schedules/restarts проходят тот же gate. Payout signer authorization также проверяет control version, чтобы executor не обошёл остановку.

Отдельный процесс/схема в общей PostgreSQL независим от frontend, но не автоматически от падения общей БД. При unavailable control store новые side effects fail-closed, console показывает невозможность durable change, не «stop applied». До production failure matrix проверяет общий DB outage, отдельный control store outage, потерю связи с workers и out-of-band инфраструктурную остановку. Конкретная redundancy/topology — deployment gate, а не готовая гарантия этого документа.

Если невозможно получить достаточно актуальный control state, новые side effects запрещены. Read/observation/audit/reconciliation продолжаются по безопасному read path. Control events priority доставляются всем workers, каждый отдаёт ack со state version и last checked time. Пока хотя бы обязательный компонент не подтвердил применение, UI показывает `partially_enforced/unknown`, а не «всё отключено».

Техническая race между проверкой и фактической сетью требует dispatch fence/epoch и serializable boundary внутри executor; уже принятый provider side effect нельзя гарантированно отозвать. Поэтому рубильник обещает запрет новых команд через Shadow с проверяемыми acknowledgements, а не остановку всей blockchain. Доступные bounds propagation/ack timeout — измеряемые SLO, не придуманные обещания «мгновенно».

### 12.3 Activation и recovery

Activation: emergency.activate, re-auth, reason и incident → durable stop/version → urgent notification → enforcement acks. Не нужно ждать второе подтверждение активации.

Recovery GLOBAL_STOP/TECH_MODE: checklist с evidence → Owner подтверждает → другой независимый staff с разрешением recovery подтверждает ту же version/scope/checklist digest → staged restore. Один человек/одна identity не подписывает обе стороны. Изменились controls/incident/checklist — старое confirmation не действует. Auto-expiry/self-enable запрещены.

Этапы восстановления: read-only verification → один проверенный scope/venue → normal. Отложенные BUY не догоняются, unknown/reserves не исчезают. Возможность risk-reducing live actions определяется отдельным доказанным runbook, не универсальным «close all».

### 12.4 Funding controls и user UI

DEPOSITS_OFF блокирует создание инструкций/новые funding requests через Shadow; WITHDRAWALS_OFF — новые requests и неотправленные jobs. UI показывает locale message/reason/status reference, backend повторяет guard. Выданные адреса и прямые действия в кошельке/площадке остаются действующими вне Shadow; фактические переводы отслеживаются даже при stop.

User API возвращает `effective_controls`/allowed_actions. Публичный fallback status bundle готовится заранее и не раскрывает внутренние security details. Emergency console имеет отдельный защищённый адрес и проверяемый out-of-band runbook; конкретный hosting/redundancy выбирается до production.

## 13. Support, feedback, notifications — ADM-09/10/11

Ticket связан с user, optional session/incident и venue; общая переписка на user/admin стороне. Ticket states: `open`, `waiting_support`, `waiting_user`, `resolved`, `closed`. Delivery states сообщения: `draft`, `submitting`, `sent`, `send_unknown`, `failed`; delivery failure не переводит тикет в resolved. `support.reply` использует client message id + idempotency.

`TicketContext` содержит `environment`, `mode`, `venue`, типизированный reference `{kind:session|position|order|activity|account,id}` и safe snapshot версии; общий вопрос имеет context=null. Backend проверяет принадлежность context пользователю и доступ staff к нему. Internal note (`visibility=staff_only`) отдельно от public conversation; user serializer/stream не отдаёт notes, staff evidence, security details или extended PII. Переключение visibility задним числом не публикует private note.

Assignment хранит историю; два оператора отвечают через optimistic conversation version/visible active assignment, без потери сообщения. Reply sender берётся из staff identity. Reopen/close ownership и retention численные сроки фиксируются до backend; не вводить новые вложения/SLA в V1.

Feedback — отдельная сущность формы/категории/контекста; переход в support ticket сохраняет связь, не превращает старое submitted в новое событие отправки. У fresh session нет искусственных unread counts.

Notification фиксирует purpose, domain event ID, template version, recipient/channel и attempt. Операционные/session/security события не смешиваются с маркетинговыми объявлениями. `queued`, `accepted`, `delivered/visible`, `read`, `failed`, `unknown` — разные факты. User unread/read берутся из общей read model; client ACK не доказывает внешнюю email-доставку. Повтор delivery допустим по channel-specific idempotency contract.

## 14. Контент и локализация — ADM-16

### 14.1 Модель

`LocaleDefinition`, `ContentKey`, `ContentDraft`, `ContentVersion`, `LocaleBundle`, `ContentPublication`, `ContentUsageReference`. Keys stable, namespace/surface/state-aware; translations содержат typed placeholders, plural forms и length/markup constraints. Initial locales RU/EN; новые языки не считаются автоматически утверждёнными.

В V1 управляются тексты всех экранов: onboarding, catalog/profile, setup, funds, orders, support, notifications, status/error/empty, finance/emergency explanations. Код хранит contract keys и safe bootstrap fallback, опубликованный bundle — значения. Backend возвращает codes и typed data, а не непереводимый произвольный текст.

### 14.2 Публикация

`draft → validated → scheduled/published → superseded`; optional translation/review рабочие стадии не обязательное Owner approval. Edit/publish scopes раздельны; publisher и author логируются даже для legal/financial/security copy. Validation проверяет обязательные keys, placeholders/types, допустимые ссылки/markup, отсутствие script/HTML injection, plural/currency formatting и component constraints. Текст не изменяет действие кнопки, policy, числовой тариф или state enum.

Locale publish атомарно переключает manifest version. Active screens получают consistent bundle; новая версия не смешивается строками с cache прошлой. Rollback — новая publication на основе прошлых значений. Notification/report/confirmation evidence сохраняет использованную content version, чтобы восстановить показанное пользователю.

Missing key — явный fallback по registry с telemetry; отсутствующий критический key блокирует publication. Format numbers/dates locale-aware; сумма отдельно от строки. Disabled locale сохраняет historical bundles и безопасно переключает новые показы на объявленный fallback.

### 14.3 Лендинг позже

Заложить отдельные `LandingPageVersion/Block/SEO` и references к ContentKey, но V1 не включает page builder/media library/A-B engine. Будущий builder использует разрешённые блоки, preview/publish/rollback; arbitrary JS/HTML не допускается как обычный контент. Работа landing не меняет auth, тариф или venue gate.

## 15. Marketing — ADM-18

V1 — in-app announcements с локализацией, audience definition и delivery/read evidence. Модель: `AnnouncementDraft`, `AnnouncementVersion`, `AudienceDefinitionVersion`, `AudienceSnapshot`, `Delivery`, `CommunicationPreference`, `Suppression`.

Сотрудник с scopes создаёт, тестирует, планирует, публикует и останавливает самостоятельно. Нет обязательных reviewer/Owner-approved states. Purpose/security/operational/marketing различаются; customer consent/preferences и suppression проверяются независимо от внутренних согласований. Если purpose consent-rule не определён, targeted marketing не отправляется по предположению «не отписался».

Audience preview — агрегаты и причины исключения, без контактов/балансов/PnL/текстов тикетов. Approved class/channel restrictions, frequency policy и data-access scopes проверяются перед enqueue и перед delivery. Snapshot фиксирует content/policy versions; поздняя отписка/suppression проверяется снова.

Lifecycle `draft → validated → scheduled/publishing → active → paused/ended/archived`; scheduler проверяет runtime permissions/control state. Pause прекращает новые показы/постановки, не удаляет уже увиденную историю. Delivery V1: eligible/enqueued/available_on_surface/display_ack/read/failed/suppressed/unknown; «available» не «read». Количество пользователей и просмотров вычисляется по уникальным IDs, а не по повторным загрузкам.

Массовые email/Telegram/push, provider integration, external cost accounting и bulk exports — позже. Уже согласованный transactional/security канал не становится marketing channel без отдельного binding/consent.

## 16. Audit, эксплуатация и безопасность

### 16.1 Audit

`AuditEvent`: actor/service identity, time, action, target, scope, reason, before/after или безопасный diff, policy/content/control versions, command/result references, correlation, evidence refs. Audit append-only на уровне application roles; DB maintenance access отдельно журналируется. Секретные значения не записываются даже в before/after. Событие принятия команды, внешней отправки и reconciliation — разные записи.

Audit и critical command persistence атомарны; если audit/outbox transaction не сохранилась, side effect не выполняется. Export имеет отдельный permission, purpose, job, expiring access и redaction; view scope не даёт экспорт. Retention и обязательные legal сроки — настройка до production, не случайная константа.

### 16.2 Observability

Metrics: API/error latency по route/venue/env; auth denials; projection/event lag; outbox oldest age; feed gaps/freshness; adapter quotas/circuit state; unknown operations age; reserve/liability mismatches; fee-policy propagation; payout source balance availability; audit-write failure; control version/acks; content bundle propagation; announcement and support delivery failures.

Logs structured и redacted; trace/correlation переходит API→outbox→worker→adapter→evidence. Метрики не используют user/address как unbounded labels. Alert thresholds и SLO — profile version после измерений; не считать отсутствующую telemetry нулевыми ошибками. Alerts создают deduplicated incident с runbook, affected scope и owner.

### 16.3 Безопасность и восстановление

Разделить admin/user origins и auth audience, защищённые cookies/CSRF/origin validation; RBAC на backend, parameterized DB access, schema validation, no arbitrary query/provider URL from UI. Least-privilege executor credentials; secret references из vault/managed signer; не хранить ключи в repo, экспортируемом config или браузере.

Backups БД/evidence/config и restore drills включают outbox/inbox/idempotency state, policy history и payout attempts. После восстановления внешние side effects остаются выключенными до read-only reconciliation: старый queued job не отправляется снова только потому, что появился в backup. Конкретные RPO/RTO и retention budgets выбираются до production.

Миграции additive/versioned с rollback-compatible reader, публикации не теряют historical IDs. Deployment gate: compatible schema/event versions, release manifest, controls enabled, source ownership evidence, current credentials metadata. Demo/live имеют независимые конфигурации, queue namespaces, data access и signer references; fixture marker виден в UI.

## 17. Связь с пользовательским интерфейсом

Полная evidence-матрица и свежая read-only проверка — [116](116_admin_user_interface_consistency_2026-10-09.md). Ниже обязательные общие контракты; изменение Figma этим документом не выполняется.

| Пользовательская область | Админка | Общая модель / проверка |
| --- | --- | --- |
| Fresh start и active demo | ADM-02/03 | новая сессия пустая, fixture history не копируется пользователю |
| Каталог, профиль, ручной адрес | ADM-06/07 | venue identity, metrics period, unknown и rating methodology version |
| Настройка/проверка/запуск | ADM-03/08/17 | copy settings, effective policy, control scope и launch validation |
| Главная, money cards, activity | ADM-01/03/05 | same projections; available/reserved/executed/PnL различаются |
| Orders/positions/cancel/manual mode | ADM-03/04/05 | partial fills/cancel race, lot ownership, late evidence и reserve |
| Polymarket/Limitless funds | ADM-06/15/17 | venue-specific capabilities; demo disconnected; прямой wallet action вне контроля |
| Support/общий вопрос | ADM-09/11 | тот же ticket/message IDs и delivery lifecycle, session optional |
| Notifications/preferences | ADM-10/18 | purpose/content/read evidence; fresh unread без sample count |
| RU/EN все экраны | ADM-16 | consistent bundle/state keys/typed amounts; rollback without policy change |
| VIP/effective fees | ADM-02/08 | опубликованная effective version и breakdown, zero alpha preserved |
| Emergency/maintenance | ADM-17 | user allowed_actions из того же effective state и status bundle |
| Referral preview | ADM-08/13 | demo/simulation отдельно от accrued/available; agent payout admin-only |

Целевые новые состояния (maintenance, VIP effective explanation, campaign display/read, live payout) нельзя считать уже реализованными в четырёх пользовательских прототипах. Для них требуется отдельная дизайн-итерация; никаких скрытых partner cabinets или требований пройти demo для live не добавлять.

## 18. Проверяемая приёмка и план реализации

### 18.1 Тестовые сценарии до готовности

| Область | Обязательные проверки |
| --- | --- |
| RBAC | deny default, direct URL/API обход, nested-data redaction, expiry/revoke stream, no self-escalation, custom «Owner» не Owner |
| Policy | two Owners concurrent publish, future version, simulator isolation, alpha=0, VIP expiry, excluded actions=0, replay historical fee |
| Ledger | accrual≠receipt, partial inbound only, internal transfer≠revenue, correction linked, per-asset balancing, allocation cap, USD aggregate no double count, USDT1:1 |
| Payout | full eligible balance, pending excluded, two Owners/click dedup, two partners same source reserve, payer modes, funds insufficient, stale preview, unknown at each dispatch boundary, missing hash, bridge destination unknown, restore backup no resend |
| Orders/session | fresh launch empty, repeated source dedup, skip full buy, partial fill + cancel late fill, daily reset reserved carry, pause vs GLOBAL_STOP |
| Emergency | direct API/queue/restart bypass, control unavailable fail-closed, venue isolation, ack partial, external already submitted not cancelled, recovery same identity rejected |
| Content | placeholders/types, unsafe markup, RU/EN coverage, locale fallback, concurrent edits, atomic bundle, historical version/rollback |
| Marketing | permissions without Owner approval, consent/suppression recheck, repeated delivery ACK not extra read, pause scheduled, expired message |
| Support | one conversation both UIs, double-send idempotent, send_unknown not resolved, typed context ownership/general question null, no internal-note/evidence leak |
| Health | HTTP200 but stale/auth missing, capability version invalidation, operation-specific maintenance, unknown telemetry/metadata, feed gaps, secrets redaction |

Дополнительно: тот же fee event с другой policy version не начисляет второй accrual/liability; failed transfer с gas expense сохраняет расход и освобождает только неистраченный source reserve; late fill с тарифом до изменения; VIP expiry до receipt; fee payer изменён между preview/confirm; data/control store outage не даёт ложного stop success; constrained signer отвергает чужой адрес/calldata; stale worker lease сначала lookup, не второй send.

### 18.2 Последовательность вертикальных срезов

1. Contracts/identity/RBAC/audit/outbox и paper read models. Получить безопасные login/denied/revoke и общую user/admin session detail.
2. Operations/users/sessions/incidents/reconciliation/venue health; shared status/reserve evidence. Без live mutations.
3. Emergency controls с API/queue/worker enforcement и независимым recovery; проверка user allowed_actions.
4. Support/feedback/notification read/delivery; общая переписка и unknown handling.
5. Content/localization/version publish плюс in-app announcements; проверка RU/EN пользовательских экранов.
6. Pricing/referral/VIP Owner-configurable registry, simulator и effective explanations, alpha zero.
7. Finance ledger/receipts/liabilities/payout forms с disconnected и тестовым executor; без реального движения.
8. Два integration spikes с проверенными source accounts, permissions, routes, signer, finality, fee/rounding contracts; separate venue gates.
9. Отдельное решение о live, ограниченное включение, fault/recovery/restore drills и эксплуатационная приёмка.

Реализация, Figma-правки и реальные операции требуют следующего поручения. В рамках этого документа подготовлены контракт и сверка, а не работающая админка.

### 18.3 Что остаётся проверить до соответствующего этапа

- До backend: конкретный auth/hosting/DB stack, каталог route permissions, ticket close/reopen policy, event/schema versioning и privacy/retention settings.
- До activation paid/payout: sources/fee collection/receipt allocation, все числа Owner policy, precision/rounding/other asset conversion/fee variance, реальный signer/allowlist и finality/lookup contract.
- До production: измеренные health/control SLO, alerts, load/restore/recovery и свежая UI acceptance.
- До расширений: landing builder, bulk external marketing, credential rotation, attachments/SLA — отдельные поздние модули.

Эти технические проверки не возвращают согласованные продуктовые вопросы на повторное согласование и не блокируют документирование/дизайн. До доказанного gate соответствующая операция остаётся отключённой с честной причиной.

## 19. Основные источники

[План 114](114_admin_console_audit_and_plan_2026-10-06.md), [правила MVP](MVP_BUSINESS_LOGIC.md), [срез интерфейса 109](109_latest_design_review_2026-10-06.md), [исправления 113](113_button_copy_and_reaction_fixes_2026-10-06.md), [каталог ADR](decisions/README.md), в особенности [0029](decisions/0029_configurable_admin_roles_and_unified_operations.md), [0030](decisions/0030_shadow_funding_interface_emergency_controls.md), [0031](decisions/0031_admin_permissions_and_autonomous_publishing.md), [0032](decisions/0032_admin_connection_health_and_session_revocation.md), [0033](decisions/0033_in_app_marketing_first_external_campaigns_later.md), [0034](decisions/0034_managed_content_and_localization_foundation.md), [0035](decisions/0035_two_owners_and_owner_only_pricing_publication.md), [0036](decisions/0036_support_queue_and_conversation_first_release.md), [0037](decisions/0037_partner_payouts_owner_only.md), [0038](decisions/0038_owner_configurable_referral_and_tariff_parameters.md), [0039](decisions/0039_owner_assignable_user_vip.md), [0040](decisions/0040_platform_usd_accounting_and_venue_payout_options.md), [0041](decisions/0041_owner_confirmed_automated_partner_payouts.md).
