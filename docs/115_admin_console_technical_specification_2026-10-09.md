# Shadow: техническая спецификация админки

21.10.2026 — [RU/EN для остальных ролей](design/admin/role-locale-state-2026-10-21/README.md): переключение языка добавлено в шесть существующих ролевых профилей. Рабочее назначение и точный экран возврата сохраняются отдельно для каждого контекста; два назначения Норы не смешиваются. Прямой вход в профиль не подставляет чужую рабочую область. Карта 0.32: 878 основных пар /894 корня на язык, включая шесть новых служебных списков языков на локаль. Набор компонентов 0.4.21 сохранён. Только дизайн; работающая авторизация и все сочетания реального сервиса не проверены.

21.10.2026 — [Сохранение состояния RU/EN](design/admin/locale-state-2026-10-21/README.md): языки используют общую страницу прототипа, прежние идентификаторы экранов и ссылки сохранены. Исправлены перезапуск при выборе языка и старые внутренние ссылки, включая варианты раскрытого меню. Сохраняются подготовленные значения профиля, сессий, списков и обращений; черновик фильтра отделён от применённого отбора. Карта 0.31: 878 пар /888 корней на язык, без новых экранов. Это дизайн и выбранные проверки; перезагрузка и новые прямые ссылки начинают самостоятельный учебный сеанс, реальный сервис не проверялся.
21.10.2026 — [Общий проход оставшихся цепочек](design/admin/general-pass-2026-10-21/CONTROL_PLAN.md): десять дополнительных маршрутов RU/EN. Исправлены сохранение email и завершённых сеансов, статуса и связи отзыва, возврат в исходную выборку журнала. Карта 0.30: 878 пар / 888 корней на язык, без новых экранов; UI kit 0.4.21 сохранён. Контрольный план уточняет полномочия и приоритет решений. Это дизайн и выбранные ручные проверки; полная приёмка всех сочетаний и реального сервиса остаётся открытой.

20.10.2026 — [Фильтры, списки и инциденты](design/admin/lists-incidents-2026-10-20/contract.md): 26 новых пар RU/EN, карта 0.29 (878 основных пар, 888 корней на язык). Черновик и применённый отбор разделены; отмена сохраняет исходный снимок, ошибки обновления — выборку и страницу. Обращения открывают соответствующего клиента; закрытие инцидента требует подтверждающих данных и проверки версии. Набор компонентов 0.4.21 сохранён. Это дизайн и проверка подготовленных маршрутов; общая приёмка, реальные операции и разработка не завершены.

20.10.2026: [Продолжение по отчёту](design/admin/report-gaps-2026-10-20/README.md): диагностика двух площадок, принятые состояния сессии, поиск и связанные записи, типизированная поддержка, возобновление инцидента и приглашение без автоматических прав. Карта 0.28: 852 пары /857 корней на язык, UI kit 0.4.21 сохранён. Полная приёмка всех сочетаний и реальные интеграции не заявлены.

Уточнение 20.10.2026: [ручной проход и контракт сохранения контекста](design/admin/manual-prototype-pass-2026-10-20/contract.md). Подтверждённое исполнение не исчезает при повторном чтении; отправленный ответ сохраняется при добавлении внутренней заметки; одна выплата имеет один текущий результат. Площадка, действующие реквизиты и версия доступа остаются однозначными. Настоящие операции и проверки ключей не выполнялись. Карта 0.27, 825 пар.

Уточнение 20.10.2026, продолжение L01/L02: [EN и завершение сценариев ролей/ключей](design/admin/roles-keys-completion-2026-10-20/README.md). В проверенных 80 ролевых контекстах каждого языка рабочие переходы не переключают сотрудника; шесть личных профилей используют возврат к предыдущему экрану. Служебный показ другого участника явно отделён от рабочих действий. Минимальное меню второго владельца — ограничение учебного маршрута, а не его полномочий: оба владельца равноправны. Замена и восстановление требуют двух отдельных проверок разных физических ключей; ошибка, отмена, повтор ключа или истечение не дают успех. Восстановление не открывает рабочую область, не возвращает отозванные сеансы и денежные подтверждения; после него нужен новый вход. Это дизайн по ADR-0046, не серверная проверка. Карта 0.26, 819 пар, UI kit 0.4.21 без изменений.

Уточнение 20.10.2026: для переходов между рабочими экранами и личным профилем сохраняются сотрудник и его текущие полномочия. Открытие профиля не переключает владельца и не повышает права. Перед изменениями защиты владелец подтверждает личность физическим ключом в защищённом окне браузера; поле ручного ввода кода не заменяет эту проверку. Основной и запасной ключи проверяются отдельно. [Первый срез исправлений и незавершённые проверки RU/EN](design/admin/roles-account-clarity-2026-10-20/README.md). Условия уже приняты в ADR-0046; серверная реализация не начата.

Уточнение 19.10.2026: [ADR-0059](decisions/0059_clob_market_profiles_freshness_price_and_fees.md)/[136](136_venue_market_profiles_and_quote_gates_2026-10-19.md): принят контракт CLOB-профилей обеих площадок — возраст книги ≤2 с, получение snapshot ≤1 с, clock uncertainty ≤250 мс, предел цены 2% от текущего best соответствующей стороны. Минимумы/precision/fees — по точному market/order-shape профилю; AMM пока неподдерживаемый. Обязательная проверка потока/часов и расходов ещё не пройдена: runtime выключен, неизвестное блокирует конкретный профиль.

Уточнение 19.10.2026: [ADR-0058](decisions/0058_paper_mvp_numeric_settings_policy.md) принимает [числовую политику 130](130_paper_copy_settings_numeric_policy_proposal_2026-10-18.md): B=$100–$1 000/шаг $10; новый F от $5/шаг $1 до целого доллара min(P,D); q=1–20%/шаг 0,5 п.п.; p=5–20% и d=10–30%/шаг 1 п.п.; сигнал 30 с без редактирования. $5 — минимум только фиксированного поля, не процентного BUY. Неизменённый активный F при снижении B/p/d сохраняется с предупреждением по ADR-0056. Профили рынка/расходов и runtime отдельно; Figma не менялась.

Уточнение 19.10.2026: [ADR-0057](decisions/0057_effective_limits_and_rejection_reason_priority.md)/[контракт 135](135_effective_limits_and_rejection_reasons_2026-10-19.md) закрывают способ совмещения лимитов и главной причины BL-08. Все применимые правила обязательны; min максимумов допустим только одной квоте, разные области имеют собственные остатки. Причины упорядочены от режима/сверки и данных до денег/экспозиции/дня, остальные доказанные препятствия сохраняются в деталях. Неизвестное/непроверенное отдельно от нарушенного. Числовые thresholds и runtime этим не принимаются.

Уточнение 19.10.2026: [ADR-0056](decisions/0056_active_session_budget_flows_and_settings_revisions.md) и [контракт 134](134_active_session_budget_and_settings_versions_2026-10-19.md) принимают версии активной конфигурации и ΔB как отдельный виртуальный flow. Старые обязательства всех версий учитываются текущими лимитами; снижение ниже занятого допускается с предупреждением без ликвидации. sizingRevision сохраняет размер полученного сигнала, admissionRevision проверяет текущие ограничения перед резервом. Принято для paper MVP, без изменения Figma/приложения.

Уточнение 19.10.2026: принят [ADR-0055](decisions/0055_exact_rational_position_attribution.md); [контракт 133](133_exact_position_arithmetic_contract_2026-10-19.md) — нормативная арифметика частей. Внутренняя атрибуция количества/стоимости/расходов — точные рациональные n/d, общие внешние заявки сохраняют шаг инструмента. Раскладка SELL фиксируется; стоимость списывается пропорционально без округления частей; хвост r переносится по r+f*(q−r), подтверждённые продажи его уменьшают. Это контракт, не подтверждение реализации БД/API или изменения Figma.

Уточнение 19.10.2026: [ADR-0052](decisions/0052_late_fills_follow_ownership_and_exit_target.md) задаёт управление поздним fill и сокращение поздней части; [ADR-0053](decisions/0053_serialize_sells_and_preserve_exit_targets.md) — одну незавершённую SELL на исход и сохраняемую цель выхода; [ADR-0054](decisions/0054_round_down_without_limit_bypass_and_keep_dust.md) — округление количества вниз без обхода полной проверки BUY и явный малый остаток, блокирующий финал. Это принятые владельцем правила paper MVP. Техническая арифметика распределения, параметры рынков и runtime требуют отдельных проверок; макеты не менялись.

Уточнение 19.10.2026: [ADR-0049](decisions/0049_position_parts_cost_and_manual_sales.md) принимает раздельный учёт частей, сохранение стоимости/лимита при detach и пропорциональное распределение ручной продажи выбранной группы. [ADR-0050](decisions/0050_shadow_assessment_boundary_and_exit_only_tail.md) закрывает период оценки на 14-й день: BUY запрещены, их остатки отменяются с подтверждением, выходы существующей копируемой части продолжаются до явного отключения. [ADR-0051](decisions/0051_strict_session_completion_and_paper_reset.md) разрешает новую сессию/reset только после закрытия всех частей и сверки всех операций; история сохраняется. Это принятые правила, не подтверждение реализации или обновления Figma.

Актуальное уточнение 14.10.2026: в Paper Alpha комиссия сервиса 0%; 1% — только пример будущей платной версии, которая пока не активна. Технический режим полностью отключает пользовательскую часть и продуктовые фоновые задачи по [ADR-0045](decisions/0045_technical_mode_full_user_shutdown.md). [Актуальные макеты, правила и границы проверки](design/admin/SYNC_2026-10-14.md). Эти уточнения имеют приоритет над прежними общими формулировками ниже.

Срез: **9 октября 2026**. Версия документа: **1.0 для проектирования и реализации после отдельного GO**.

Уточнение **12.10.2026**: приняты [ADR-0043](decisions/0043_admin_money_security_and_incident_recovery.md) и [правки 119](119_admin_security_review_changes_2026-10-12.md). Новые реквизиты и превышение защитных порогов требуют другого Owner; обычные выплаты остаются самостоятельными. Денежное recovery после аварийной блокировки требует независимого подтверждения. Это требования к реализации, не выполненные live-проверки.

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

Рыночное отклонение USDT контролируется отдельно (§11.5): внутренний фиксированный 1:1 не является обещанием рыночной цены. Guard может остановить затронутый денежный маршрут, но не меняет прошлые оценки/обязательства.

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
| `recipient_change_proposals/recipient_activations/payout_security_policy_versions/payout_additional_approvals` | exact digest, author/independent Owner, state/version/effective time | no self-approval, invalidate on security/version change |
| `funding_operations/funding_observations` | user/venue/route/external event IDs, authorization refs, evidence/state | no double availability, unknown no resend |
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
| `POST /staff/{id}/compromise`, `/connections/{id}/isolate` | scoped security права, durable isolation/revoke и incident (§4.4/11.4) |
| `POST /recipient-proposals/{id}/approve`, `/payout-security-policies/{id}/activate`, `/payouts/{id}/additional-approval` | другой Owner, exact version/digest; guards §10.5/10.6 |
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

Сущности: `StaffAccount`, `RoleDefinition`, `RoleVersion`, `PermissionGrant`, `RoleAssignment`, `AdminSession`, `AccessAudit`. Публичный user account не становится staff автоматически. Сотрудник имеет отдельную identity и status `invited/active/suspended/revoked`; для владельцев обязательны основной и запасной проверенные физические ключи; для остальных сотрудников — защищённый вход по устройству или ключу согласно полномочиям. Перед чувствительными командами выполняется новая проверка личности. Поставщик входа и приглашений выбирается при реализации; правило защиты определено в ADR-0046.

Owner назначен двум личным аккаунтам; shared account/seed недопустим. Owner-привилегии проверяются системным признаком, а не именем кастомной роли. Самостоятельное повышение прав, выдача себе Owner и обход domain guard через custom scope запрещены. В качестве технической защиты предлагается не допускать удаления последнего работоспособного Owner и проверять owner-assignment отдельно от редактора ролей.

Grant: `permission`, `environment`, `venue`, `section`, `data_class`, `expires_at`. Авторизация применяется к списку, detail, nested joins, export и stream; разрешение чтения карточки не открывает все связанные данные. Сотруднику возвращается `allowed_actions`, вычисленный сервером; UI не является security boundary.

### 4.2 Предлагаемый каталог scopes

| Группа | Права | Безусловная граница |
| --- | --- | --- |
| Operations | `operations.view`, `session.pause`, `session.resume_demo`, `session.disconnect_demo`, `incident.view/assign/resolve`, `reconciliation.view/run` | live submit/close за пользователя не делегируется этим набором; resume снимает только разрешённую demo-паузу, не emergency gate |
| User context | `users.view_minimal`, `users.view_extended` | extended отдельно; нет impersonation login |
| Support | `support.view/reply/assign`, `feedback.view/manage` | ticket visibility по policy, без изменения ledger |
| Data | `health.view`, `traders.view`, `ingestion.view`; новые edit/publish/simulate scopes — предложение ADR-0044 | source metrics read-only; настройка версий сборщиков/валидации/рейтинга добавлена в дизайн; права публикации ещё на вычитке |
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

### 4.4 Компрометация сотрудника

`POST /staff/{id}/compromise`: отдельное `security.staff_compromise` в разрешённом staff scope, re-auth, reason/incident, expected auth version. В durable transaction: suspended/compromised status, auth version increment, revoke всех сеансов и неиспользованных recipient/payout/security-policy/recovery approvals этой identity, audit/outbox. Новые HTTP/stream/execution проверки отклоняют identity; jobs от неё до отправки блокируются. После начала отправки — observation/reconciliation, не фиктивная отмена.

Владелец/уполномоченный security-сотрудник может изолировать аккаунт, но это право не назначает Owner и не даёт отправлять выплаты. Отдельно создать incident, уведомить обоих Owner и сохранить ссылки на последние действия. Notification failure фиксируется/повторяется как доставка, не задерживает блокировку. UI показывает фактическое применение по компонентам; возможная race с внешней отправкой обрабатывается как §10.2/12.2. Восстановление account не возвращает старые сеансы/approval; новый доверенный вход и security-runbook обязательны.

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
| ADM-07 Data & rating | TraderIdentity, source observations, coverage, collector/validator/rating policy versions, RatingSnapshot | reads плюс проектируемые draft/validate/impact/apply/restore commands | raw facts read-only; manual address не требует рейтинга; настройки расширены ADR-0044, новые права — предложения |
| ADM-08 Tariffs & commissions | TariffVersion, ReferralPolicyVersion, SimulatorRun, overrides | list/draft/simulate/publish/schedule/rollback | numbers и publication Owner-only; snapshots/version history |
| ADM-09 Support | Ticket, Message, Assignment, user/session context | tickets/detail; reply/assign/status | support scopes; одна переписка user/admin, send_unknown отдельно |
| ADM-10 Notifications | Notification, DeliveryAttempt, preferences | list/detail/status; controlled readback | `notifications.view` — предлагаемый отдельный scope; нет fake delivered/прочитано |
| ADM-11 Feedback | FeedbackItem, context, classification | list/detail; categorize/assign/status | feedback.manage; ссылка на ticket/incident по необходимости |
| ADM-12 Audit | AuditEvent, export job | list/detail; export | audit.view/export; запрет update/delete API |
| ADM-13 Owner finance | accrual/receipt/ledger/liability/payout/source; recipient/security-policy/approval | prepare/confirm; другой владелец подтверждает реквизиты (затем 24 часа), защитные правила и пороговую выплату | Owner-only; полная сумма, exact independent approval по условиям, paid по evidence |
| ADM-14 Staff & access | staff/roles/grants/admin sessions/compromise | staff/role CRUD, permission preview, revoke/compromise | deny default, no self-escalation, invalidate unused approvals |
| ADM-15 Integrations & security | ConnectionProfile, capability, check, credential metadata/isolation | read/recheck; emergency isolate; provider revoke evidence отдельно | no secrets; local isolation V1, полный rotation UI позже (§11.4) |
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
- Fixed amount либо процент от подтверждённой суммы конкретной сделки трейдера. sizingRevision фиксирует размер нового сигнала, admissionRevision применяет текущие ограничения перед резервом; существующие допущенные intents/fills не переписываются (ADR-0056/134).
- Новая BUY проверяется на полную сумму с reserved budget/expenses/day/position limits. Недостаток полного лимита/доказанной глубины — skip whole, не уменьшение до остатка.
- Повтор одного source event не создаёт новую копию; самостоятельная повторная покупка — новый signal. Пропущенный сигнал не догоняется после recovery.
- После подтверждённого partial order fill позиция хранит исполненную часть, remainder/reserve удерживается до результата отмены. Late fill во время cancel уменьшает только ещё возможный остаток.
- Дневной лимит: zone и reset instant из session; unresolved buy reserve переносится через reset. Это не midnight в зоне сервера.
- Обычная user pause запрещает новые BUY/увеличения, но не равна GLOBAL_STOP. Сокращение риска по существующим пользовательским правилам не включается автоматически при глобальной аварии.
- Money availability, position value, realized/unrealized P&L, cash flow — отдельные поля. Неизвестные цены/расходы не подставляются нулями.
- Торговая partial fill допустима; **частичная партнёрская выплата запрещена**. Эти автоматы не используют один status enum.

### 6.3 Пополнение и пользовательский вывод: отдельные lifecycle

Это отдельный от ServicePayout контур по user/venue/account/environment и подтверждённому funding route. В demo показан как неподключённый, реальных запросов/зачислений нет. При live Shadow инициирует только поддержанные действия и читает подтверждённые внешние факты; универсальная custody-модель не предполагается.

`UserFundingOperation`: operation id, direction, user/account/venue, route/asset/network, requested amount при наличии, provider/transaction refs, admission control version, initiator authorization, observations/evidence, state/version, safe reason, correlation. Факт внешнего события уникален по venue/network/provider identity и event/log index; дубли/reorg не дают двойного доступного баланса. Public projection содержит безопасные суммы/состояния, staff-only evidence отдельно.

| Контур | Состояния и переходы |
| --- | --- |
| Пополнение | instructions_requested → instructions_ready (или blocked/failed_confirmed) → transfer_observed → confirming → credited_external/available_confirmed либо pending_verification/unknown; при доказанном несоответствии — incident |
| Вывод | requested → validating → authorization_required/authorized → reserved_external_or_internal (только при доказанной reservation capability) → dispatching → submitted → confirming → completed_confirmed; до send blocked/cancelled_before_dispatch; terminal failure только по evidence; неизвестная отправка/итог → unknown |

Адрес/инструкция не равны поступлению, submitted не равен успешному выводу. Баланс/резерв принадлежат своему фактическому контурy: если reserve у провайдера, UI читает его evidence; внутренний контроль intent не обещает блокировать самостоятельные внешние расходы пользователя. До integration выбираются route-specific verification, authorization, fees и finality; неподдержанная reservation не выдумывается.

На неизвестном исходе нет автоматической повторной отправки/освобождения подтверждённого резерва. Backend/worker проверяют controls до каждого нового side effect и допускают readback уже отправленного. Клиентское подтверждение связано с точным intent/recipient/route/amount; незапущенная заявка после emergency требует нового preflight и подтверждения пользователя, а не сотрудника вместо него.

При DEPOSITS_OFF новые инструкции/requests запрещены. Входящий перевод на старый адрес всё равно наблюдается/сверяется: уже доступный подтверждённый внешний актив показывается как доступный, отсутствие достаточных evidence — как ожидание проверки. Shadow не удерживает актив в самостоятельном кошельке и не скрывает известный факт. UI различает unavailable amount и confirmed amount; админ видит причину/связанный incident. Произвольное зачисление/возврат сотрудником не добавляется.

READ `/user-funding-operations`, detail/observations, prepare/confirm/cancel-before-send и reconcile команды уточняются адаптером до live; серверный контракт включает idempotency, state version, no-resend и permission checks. Таблицы funding_operations/funding_observations/authorization refs и события FundingInstructionsPrepared, FundingTransferObserved, FundingAvailabilityConfirmed, UserWithdrawalSubmitted/Confirmed/Unknown относятся к этому отдельному контурy, не к service ledger.

### 6.4 Не закрывать открытые пользовательские правила случайно

Выбор правил частей/завершения, late/очереди/округления, точной арифметики, версий бюджета и совмещения/причин принят в ADR-0049–0057. Остаются физический ledger/CAS, время/календарная граница, профили рынка/расходов (поля формы приняты ADR-0058), partial SELL/cadence, методика метрик и реализация; административная спецификация не объявляет их готовыми. DTO сохраняют unknown/evidence/версии; user и admin используют единый вердикт с разрешёнными деталями по ADR-0057/135. Нет новых drawdown thresholds или автопродаж.

## 7. Incidents и reconciliation

Incident: `new → triaged → assigned/investigating → resolved → closed`, с возможностью reopen при новом evidence. Это предлагаемый workflow расследования; статус внешней операции хранится отдельно. Severity/priority и причина — versioned dictionary, numeric alert thresholds не зашиваются без calibration.

ReconciliationCase содержит object identity, reason, expected/observed, reservations, attempts, evidence, assignee и decision. Attempt: `queued/running/succeeded/failed/unknown`. Два запуска одной проверки объединяются или сериализуются. API `POST /reconciliation-runs` принимает object ID и допустимый adapter/read scope, не произвольный URL/transaction для подписи.

Новый evidence вызывает обычный domain transition и shared projections. Разрешена добавочная корректировка с причиной и связью с исходной записью; запрещены SQL rewrite past fill/payout, «успех» без evidence и удаление неудобного discrepancy. Export evidence маскирует личные данные/секреты.

## 8. Tariffs, referrals и VIP — ADM-08/02

### 8.1 Сущности и права

`TariffPolicySet`, `TariffVersion`, `ReferralPolicyVersion`, `PartnerTier`, `PartnerVipProfile`, `UserVipProfile`, `UserVipAssignment`, `PolicyPublication`, `SimulatorRun`. Численные условия вводят владельцы вручную; подготовку пояснений и просмотр расчёта можно делегировать. Обычные тарифы и назначение, изменение или прекращение пользовательского VIP публикует один владелец. Денежное реферальное правило и партнёрский VIP, меняющий денежные условия, требуют согласий двух разных владельцев по ADR-0047 §2. Автор не даёт второе согласие своей версии.

Текущая alpha service fee и partner share — 0%. Более поздние paid rates/ceilings из ADR-0005 сохраняются как исторически согласованные версии/границы, не активируются автоматически. Возможность настройки не даёт автоматически поднять действующий ceiling. User VIP отдельно от partner VIP; «VIP» не означает исключение из risk/emergency/venue gates.

### 8.2 Lifecycle и применение

`draft → validated → scheduled/active → superseded/expired`. Проверка значений, симуляция и сравнение версий обязательны. Для обычного тарифа и пользовательского VIP второй согласующий не нужен; для денежных партнёрских правил действует независимая проверка второго владельца по ADR-0047. Atomic publish с version check гарантирует отсутствие перекрытия effective policies для одной комбинации scope/action/liquidity-role. Rollback создаёт новую версию; backdating и молчаливый пересчёт истории запрещены.

Предлагаемый приоритет effective user tariff: platform stage/environment → venue/action/liquidity rule → active user VIP override разрешённых параметров → ceilings/exclusions. Partner reward выбирается отдельно по attribution/referral version/partner tier/VIP. При конфликте двух активных override publish отклоняется, не выбирается случайный последний. Окончательный precedence фиксируется calculation contract до live.

Assignment: profile/custom values, effective start, end или indefinite, reason, actor, version. Expiry/end/removal приводит к обычной применимой версии без переписывания прошлых начислений. У каждого нового расчёта есть effective explanation для user/admin: base rate, override, exclusions, final rate и policy IDs.

Effective intervals — UTC `[from,to)`. Версия расчёта выбирается по подтверждённому экономическому событию/fill time, не по времени доставки API-ответа. Поздний fill до изменения тарифа сохраняет прежнюю применимую версию; если reliable event time неизвестно, начисление остаётся неопределённым до сверки. Receipt arrival не выбирает заново user VIP/rate для старого fill. Calculation hash включает source identity/time, executed amount, action/liquidity evidence, тарифную/referral/VIP/valuation/rounding версии и порядок округления компонентов.

### 8.3 Начисление

`FeeCalculationEvidence`: confirmed fill IDs, liquidity role evidence, action class, notional, currency, rates, policy IDs, rounding profile, fee breakdown. Shadow fee, venue fee, network cost и partner reward — отдельные компоненты. Manual/protective/emergency close и unfilled remainder не создают service fee по действующей политике.

Simulator — без движения денег: прогноз по выбранным inputs, scenarios unknown maker/taker/excluded actions/VIP/tiers, diff с effective policy. `simulated` никогда не попадает в service cash balance или payable. Изменение текста «комиссия» в CMS не меняет расчёт.

## 8.4 Дизайн партнёрских правил, тарифов и VIP · 16.10.2026

Действующий срез: [пакет макетов](design/admin/partner-rules-tariffs-vip-2026-10-16/README.md), карта 0.17. 32 новых состояния RU и EN, три обновлённых экрана проверки и семь входных экранов на язык. Числа и подтверждения учебные, Paper Alpha сохраняет комиссию 0%.

Денежное партнёрское правило: параметры → сравнение и расчёт → первое согласие владельца A → ожидание → независимая проверка B → второе согласие → начало в установленный срок. Согласия связаны с одной точной версией, областью, базой признания, лестницей, округлением, временем, плательщиком комиссии и причиной. Один автор не может дать два согласия. Смена версии, утрата прав или истечение срока запрещают завершение; отказ и причина сохраняются. После завершения двух согласий отложенное начало не требует повторной подписи лишь из-за наступления установленного времени, но изменение согласованных условий требует нового цикла. Партнёрское индивидуальное денежное исключение проходит тот же контроль двух владельцев; оно не является пользовательским VIP.

Накопительная лестница действует за всё время. До платного включения владельцы выбирают метрику (подтверждённые клиенты или оборот), точные пороги, доли, область, периоды и профиль округления. Показанные 0/10/50 клиентов и 25/30/35% — только пример настройки. Доля считается от комиссии Shadow, не от оборота или прибыли. Пример подтверждённого начисления как базы признания и DEMO-RND-01 не закрывает открытый вопрос recognition_basis и окончательный расчётный контракт: выбор между начислением и фактическим получением средств ещё согласуется до платного запуска. Настройка не снимает действующие ограничения.

Обычный тариф публикует один владелец: проверка → запланированная версия → начало → окончание/замещение. Откат создаёт новую версию с причиной, временем и автором. Перед публикацией и откатом проверяется актуальная версия; конфликт возвращает к проверке, без перезаписи конкурирующей публикации. Исторические комиссии и подтверждённые обязательства не пересчитываются.

Внутренняя публикация и применение площадками — отдельные состояния. На одной странице видны собственная версия, Polymarket и Limitless, время наблюдения и подтверждающие данные каждой площадки. Показаны ожидание, подтверждение, доказанный отказ, неизвестный результат и неподдержанный маршрут. Неизвестность не считается успехом или нулевой ставкой; затронутый платный маршрут закрыт до проверки. Нельзя повторять неизвестный запрос автоматически. Неподдержанный механизм не заменяется скрытым списанием. Все подтверждения в макете синтетические; возможности и маршруты реальных API остаются предметом интеграции (Z06). Подтверждение применения не означает фактическое получение дохода.

Пользовательский VIP: один владелец назначает условия и срок [начало, окончание) в UTC, указывает причину; показаны проверка, ожидание начала, действие, окончание и досрочное прекращение новой версией. После окончания применяется текущий допустимый базовый тариф; прошлое сохраняется. В Alpha действующая комиссия 0% независимо от учебного примера будущих 0,5% вместо 1%. Два владельца не требуются для обычного пользовательского VIP.

Физические ключи, проверка прав, точной версии и срока согласия проверяются сервером при реализации. Прототип показывает подготовленные состояния, не выполняет подтверждения, начисления или переводы. Отдельные кнопки «пример» показывают альтернативный исход, а не выполняют случайную операцию.

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

Реквизиты — versioned `PartnerPayoutRecipient`: chain/address/token compatibility, verification/allowlist status и actor/reason. Создание/изменение/деактивация через `/partners/{id}/payout-recipients` только Owner; подтверждённый intent остаётся на своей recipient version. API accept новой записи адреса не означает, что площадка уже разрешила его. По ADR-0043 новый/изменённый recipient сначала pending_second_owner, другой владелец подтверждает точную версию, затем обязательны 24 часа и повторная проверка перед активацией (§10.5); неактивные или непроверенные реквизиты блокируют выплату.

`SourceSpendReservation` блокирует доступное расходование сервисного источника по account/chain/asset и резерв fee asset, чтобы два разных партнёра не потратили один баланс. Liability reservation и source-spend reservation атомарны с intent/audit/outbox; external balance имеет freshness gate и recheck перед send. Unknown держит оба резерва. Независимые внешние переводы вне Shadow могут изменить баланс, поэтому preflight остаётся обязательным и не обещает абсолютного контроля кошелька.

Дополнительно confirmation проверяет активную recipient version и текущую security-policy. Если полный frozen payout превышает порог, intent остаётся awaiting_second_owner, без внешней отправки, до отдельного подтверждения другого Owner (§10.6). Это исключение, не требование второго подтверждения обычной выплаты. Резервирование при втором подтверждении атомарно с повторной проверкой полного snapshot; changed snapshot требует нового preview/approval. Source spend сохраняет защиту от двух параллельных партнёров.

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

### 10.5 Защищённые реквизиты

Действует ADR-0047. Предложение реквизитов (RecipientChangeProposal) хранит партнёра, площадку, сеть, актив/контракт, полный адрес, точную версию и контрольную сумму, автора, причину и подтверждающие данные проверки подключения. Состояния: pending_second_owner → awaiting_delay → active; отдельные исходы rejected / cancelled / invalidated / deactivated.

Один владелец создаёт предложение. Другой действующий владелец с повторной проверкой физическим ключом подтверждает точную версию: author != reviewer. Подтверждение записывает approved_by / approved_at и activation_not_before = approved_at + 24 часа. Оно переводит предложение в awaiting_delay, а не active. Обязательные поля ожидания: часовой пояс, плановое время активации, оставшееся время и право любого владельца отменить изменение. Сокращения задержки, исключения для Paper Alpha и отключения таймера нет.

API разделяет второе подтверждение и активацию: POST /recipient-proposals/{id}/approve — другой владелец, expected version и точная контрольная сумма; POST /recipient-proposals/{id}/cancel — любой владелец; guarded activation после activation_not_before выполняется только при повторной проверке версии, адреса, проверки подключения и действующих ограничений. Прежний endpoint /activate не должен одновременно подтверждать и немедленно включать новый адрес. Фоновая активация, если выбрана при реализации, не обходит технический режим: остановленное продуктовое задание ждёт разрешённого восстановления.

Старая версия и история сохраняются. Подготовленная выплата привязана к своей версии адреса и не перенаправляется на новую автоматически. Изменение предложения, утрата прав, компрометация или несовместимые ограничения аннулируют согласия; новое изменение требует новых двух владельцев и новых 24 часов. После активации обычную полную выплату может подтвердить один владелец, если дополнительные пороги не требуют второго; третье подтверждение только из-за смены адреса не вводится. Физический ключ не заменяет второго человека. Оба владельца получают уведомления о предложении, подтверждении, отмене и активации; журнал сохраняет безопасные изменения. Задержка относится к реквизитам партнёра, а не автоматически к регистрации собственного источника.

### 10.6 Защитные пороги выплат

`PayoutSecurityPolicyVersion` отделена от TariffVersion: single-payout, daily-total, partner-total, source-total, new-recipient threshold; aggregation window/timezone, fee inclusion, native/USD valuation basis, effective time, version и approval digest. Owner задаёт числа вручную; создать/изменить/отключить policy может предложить один Owner, активирует другой. Права кастомной роли этого не обходят; изменение тарифов/обычных VIP не получает новый approval.

Срабатывание порога дополнительного подтверждения полной доступной суммы → awaiting_second_owner; второй Owner подтверждает конкретные partner/venue/source/recipient/asset/amount/fee/quote/policy/control versions. Один Owner не может подтвердить за две стороны. Разрешение одноразовое для этого intent; изменение параметров, compromise, отзыв прав или новый аварийный control epoch требует нового preview/approval. Это дополнительная проверка, а не поле уменьшения суммы: долг не режется и не дробится ради лимита.

Жёсткие максимумы запрещают отправку и не снимаются вторым подтверждением. Целевой остаток даёт предупреждение; операционный резерв вычитается отдельно и один раз. Суммарные пороги считают подтверждённые отправки плюс активные резервы и операции с неизвестным результатом, чтобы параллельные intents не обходили дневной/источниковый порог. Второе подтверждение не отменяет недостаток средств, stop, неверный recipient или неизвестный предыдущий результат. Конкретные числа, окна и expense accounting настраиваются/валидируются до live; отсутствующая обязательная security policy блокирует live отправку. UI показывает сработавшее правило и требуемое подтверждение без выдуманных чисел.

Хранение: recipient_change_proposals/recipient_activations, payout_security_policy_versions, payout_additional_approvals; уникальные operation/version/digest и разные identity. Mutation API: propose/approve/cancel recipient; guarded activation после обязательных 24 часов, propose/activate security policy, approve full payout; события RecipientProposed/ApprovedAwaitingDelay/Cancelled/Activated, PayoutSecurityPolicyProposed/Activated, PayoutAdditionalApprovalRequired/Recorded/Invalidated. Все проверки повторяются на executor и constrained signer; UI-кнопки не являются защитой.

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

V1 показывает metadata и позволяет request recheck. Полное creation/rotation/provider revoke venue credentials через админку — следующий этап; `access.revoke` в V1 отзывает только admin session. Secure provisioning выполняется вне content/marketing UI; секреты не попадают в журнал/экспорт.

Expiry/last-used показываются только при наличии фактического provider metadata; отсутствие — `null + not_provided/unknown`, не дата, выдуманная из created_at.

### 11.4 Изоляция подключения и украденного credential

V1 `POST /connections/{id}/isolate` (`security.connection_isolate` в разрешённой области) запрещает использование secret reference/signing profile внутри Shadow, увеличивает control version и останавливает неотправленные jobs. Evidence/observations незавершённых операций продолжаются безопасным независимым read path; если read credential тоже скомпрометирован, использовать иной проверенный источник или показывать unknown.

Local state isolated не равно provider credential revoked. Внешний отзыв выполняется только через доказанный API/capability либо защищённый провайдерский runbook; отдельно хранить requested/confirmed/failed/unknown и evidence. Нельзя считать украденный ключ обезвреженным локальным stop. Полный интерфейс создания/ротации credentials остаётся следующим этапом, но emergency isolation и план внешнего отзыва требуются до live. Возврат — проверка credential/source/signer, незавершённых операций и независимое monetary recovery §12.3.

### 11.5 Рыночное отклонение USDT

Исследование источников и подробный контракт — [120](120_usdt_usd_sources_and_admin_alerts_2026-10-12.md): рекомендуемый Kraken USDT/USD (оперативная котировка) и CoinGecko tether/USD (периодическая агрегированная сверка). API read-only проверен для Kraken REST; WS/CoinGecko authenticated spike ещё не выполнены. Owner настраивает warning threshold, confirmation window, freshness/spread, recovery hysteresis, recipients/reminders; по подтверждённому warning — admin incident/notification. Warning не включает monetary stop автоматически; отдельный critical/quality gate остаётся по ADR-0043. Администраторское notification center + проверенные security Telegram/email каналы отделены от клиентского маркетинга. Числа не зашиты, квота и timestamps источников учитываются.

MarketDeviationObservation хранит источник, цену/время/актив, freshness/verification, configured threshold и policy version. Внутренний 1 USDT = $1 сохранён (§3.2); внешняя котировка используется только для отдельного alert/route gate, не для пересчёта старых обязательств. Проверенное отклонение блокирует новые затронутые денежные side effects и создаёт incident; неизвестная обязательная проверка также не является healthy.

До live выбрать источники, порог, stale handling и recovery evidence; отсутствующие значения не заменять фиктивными defaults. Граница затронутых маршрутов явно задаётся, не автоматически вся торговля/все активы. Shadow не получает новую функцию самостоятельного обмена. Уже отправленное наблюдается, снятие аварийного денежного gate проходит §12.3.

## 12. Аварийное управление — ADM-17

### 12.1 Ортогональные ограничения

`AvailabilityState`: normal/TECH_MODE. `ActionRestriction`: GLOBAL_STOP, risk pause, read-only, venue isolation, DEPOSITS_OFF, WITHDRAWALS_OFF, PARTNER_PAYOUTS_OFF. Последние scoped ограничения и дополнительные варианты уровня — техническая модель; согласованные GLOBAL_STOP/TECH_MODE/funding controls сохраняются. Комбинация вычисляется сервером как пересечение разрешённых действий; локальный normal не снимает глобальный stop.

Scope: project/environment/venue/subsystem, staff/user identity, connection, service source/wallet, signer, network, asset/token contract, route + action class; reason/incident/actor/version/effective time. Availability хранится отдельно от trading state. Технический режим полностью закрывает приложение и публичный API для пользователей, блокирует новые торговые и денежные действия через Shadow и останавливает все продуктовые фоновые задачи в выбранной среде. Работают только аварийная админка, мониторинг, журнал аудита, инциденты, безопасная сверка и восстановление. Сверка ничего не отправляет; уже отправленные операции могут завершиться. Прямые действия вне Shadow не блокируются. GLOBAL_STOP запрещает новые продуктовые и финансовые side effects; не объявляет уже отправленные операции отменёнными и не удаляет evidence.

| Operation class | User pause | GLOBAL_STOP | TECH_MODE | DEPOSITS_OFF / WITHDRAWALS_OFF |
| --- | --- | --- | --- | --- |
| `new_copy_buy` | запрещено | запрещено | запрещено | сами по себе не торговый gate |
| `existing_position_reduce` | допускается по действующей user policy | только отдельный доказанный emergency runbook, иначе запрещено | аналогично | не торговый gate |
| `user_deposit_instructions` | отдельный capability | запрещено | запрещено | DEPOSITS_OFF запрещает |
| `user_withdrawal_submit` | отдельный capability | запрещено | запрещено | WITHDRAWALS_OFF запрещает |
| `service_partner_payout` | user pause не влияет | запрещено до новой отправки | запрещено до новой отправки | user funding switch сам по себе не payout switch |
| `observation/reconciliation/audit` | продолжается | продолжается | продолжается | продолжается |
| `emergency_control/recovery` | отдельно authorized | защищённый control plane доступен | защищённый control plane доступен | доступен |

По ADR-0043 PARTNER_PAYOUTS_OFF — согласованный самостоятельный запрет service_partner_payout до новой отправки. Чтение/сверка/учёт сохраняются; пользовательский WITHDRAWALS_OFF не заменяет этот переключатель. У target restriction отображается точный запрещённый набор действий, а не обещание глобально остановить чужой кошелёк.

### 12.2 Enforcement

State сохраняется durable в отдельной управляющей схеме/контуре с независимым endpoint. Команда stop не зависит от venue API. Gate проверяется на HTTP admission, queue admission, worker start и перед каждым внешним действием; schedules/restarts проходят тот же gate. Payout signer authorization также проверяет control version, чтобы executor не обошёл остановку.

Отдельный процесс/схема в общей PostgreSQL независим от frontend, но не автоматически от падения общей БД. При unavailable control store новые side effects fail-closed, console показывает невозможность durable change, не «stop applied». До production failure matrix проверяет общий DB outage, отдельный control store outage, потерю связи с workers и out-of-band инфраструктурную остановку. Конкретная redundancy/topology — deployment gate, а не готовая гарантия этого документа.

Если невозможно получить достаточно актуальный control state, новые side effects запрещены. Read/observation/audit/reconciliation продолжаются по безопасному read path. Control events priority доставляются всем workers, каждый отдаёт ack со state version и last checked time. Пока хотя бы обязательный компонент не подтвердил применение, UI показывает `partially_enforced/unknown`, а не «всё отключено».

Техническая race между проверкой и фактической сетью требует dispatch fence/epoch и serializable boundary внутри executor; уже принятый provider side effect нельзя гарантированно отозвать. Поэтому рубильник обещает запрет новых команд через Shadow с проверяемыми acknowledgements, а не остановку всей blockchain. Доступные bounds propagation/ack timeout — измеряемые SLO, не придуманные обещания «мгновенно».

### 12.3 Activation и recovery

Activation: emergency.activate, re-auth, reason и incident → durable stop/version → urgent notification → enforcement acks. Не нужно ждать второе подтверждение активации.

Recovery GLOBAL_STOP/TECH_MODE: checklist с evidence → Owner подтверждает → другой независимый staff с разрешением recovery подтверждает ту же version/scope/checklist digest → staged restore. Один человек/одна identity не подписывает обе стороны. Изменились controls/incident/checklist — старое confirmation не действует. Auto-expiry/self-enable запрещены.

Этапы восстановления: read-only verification → один проверенный scope/venue → normal. Отложенные BUY не догоняются, unknown/reserves не исчезают. Возможность risk-reducing live actions определяется отдельным доказанным runbook, не универсальным «close all».

Восстановление денежных возможностей после security/emergency-блокировки (funding/payout/connection/source/signer/network/asset/route) также требует Owner + другого действующего staff с `emergency.recovery_approve` в scope. Activation выполняет один обладатель emergency.activate/соответствующего security-isolate scope. Восстановление неденежного точечного ограничения — назначенное recovery право и checklist; GLOBAL_STOP/TECH_MODE всегда требуют независимого подтверждения. Плановые health/capability recheck не подменяют снятие аварийного stop; права самостоятельной пользовательской pause/resume сохраняются.

Recovery approval одноразово для exact control/checklist digest. Снятие ограничения не переавторизует старый денежный intent: неотправленные заявки требуют fresh preflight/preview и повторного подтверждения Owner для service payout или пользователя для user withdrawal, если поддержан такой маршрут. Дополнительные Owner approvals реквизитов/порогов проверяются повторно. Submitted/unknown сначала reconcile без повторной отправки. Не смешивать recovery authorization с payout authorization.

Ограниченный восстановительный денежный маршрут отличается от общего снятия ограничения. По ADR-0047 §7 его отдельно разрешают два владельца, затем два владельца отдельно подтверждают точный перевод. Общее подтверждение владельцем и сотрудником не заменяет эти согласия.

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

Защита от прямого DB access: отдельная audit replica/archive с независимыми credentials и retention; цепочка/контрольные точки целостности, внешний trusted checkpoint, сверка sequence/полноты и обнаружение truncation. Hash chain в той же базе без независимой опоры недостаточен. Queue/local append остаются атомарны; replica lag/недоступность и tamper создают alerts/incidents, а допустимое отставание/guard чувствительных денежных команд определяются до production. Stop не ждёт удалённую доставку audit: durable local emergency record + приоритетная репликация. Конкретный vendor/WORM/retention не считается выбранным; тест DB edit/delete и archive failure обязателен.

### 16.2 Observability

Metrics: API/error latency по route/venue/env; auth denials; projection/event lag; outbox oldest age; feed gaps/freshness; adapter quotas/circuit state; unknown operations age; reserve/liability mismatches; fee-policy propagation; payout source balance availability; audit-write failure; control version/acks; content bundle propagation; announcement and support delivery failures.

Logs structured и redacted; trace/correlation переходит API→outbox→worker→adapter→evidence. Метрики не используют user/address как unbounded labels. Alert thresholds и SLO — profile version после измерений; не считать отсутствующую telemetry нулевыми ошибками. Alerts создают deduplicated incident с runbook, affected scope и owner.

### 16.3 Безопасность и восстановление

Разделить admin/user origins и auth audience, защищённые cookies/CSRF/origin validation; RBAC на backend, parameterized DB access, schema validation, no arbitrary query/provider URL from UI. Least-privilege executor credentials; secret references из vault/managed signer; не хранить ключи в repo, экспортируемом config или браузере.

Backups БД/evidence/config и restore drills включают outbox/inbox/idempotency state, policy history и payout attempts. После восстановления внешние side effects остаются выключенными до read-only reconciliation: старый queued job не отправляется снова только потому, что появился в backup. Конкретные RPO/RTO и retention budgets выбираются до production.

Миграции additive/versioned с rollback-compatible reader, публикации не теряют historical IDs. Deployment gate: compatible schema/event versions, release manifest, controls enabled, source ownership evidence, current credentials metadata. Demo/live имеют независимые конфигурации, queue namespaces, data access и signer references; fixture marker виден в UI.

Compromise/recovery runbooks включают сотрудника/Owner, внешний credential и сервисный источник; изоляция Shadow не доказывает остановку внешнего злоумышленника. Потеря обоих Owner: отдельный защищённый out-of-band identity recovery с независимой проверкой, audit/evidence и тестом. Нет общего master key, staff self-promotion или универсального обхода Owner. Custodians/provider/proof procedure выбираются до production; пока личности и доступ не восстановлены, новые денежные side effects закрыты.

Control state/version защищены от прямого неаудированного изменения БД: executor проверяет authoritative epoch/целостность, mismatch fail-closed и incident. Слепое чтение изменённой строки как разрешения запрещено; trust anchor/topology проверяются до production.

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

Дополнительная аварийная матрица ADR-0043: украден один Owner → revoke account/sessions/unused approvals; потеря обоих Owner → проверенный identity recovery без обхода; один Owner меняет recipient и сразу платит → blocked; один Owner повышает/отключает threshold → pending второго Owner; параллельные выплаты не обходят total threshold; security key одной identity не играет роль второго человека; локально изолированный украденный credential не маркируется provider revoked; DEPOSITS_OFF + фактическое поступление → observed/verified без двойного зачисления; stop на границе send → no-send или submitted/unknown + сверка; old backup/outbox → no duplicate send; недошедший ack → partially_enforced; прямые DB control/audit edits → tamper incident/fail-closed; USDT alert не переписывает прошлый 1:1. Это требования тестов, не отчёт об их выполнении.

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

Дополнительные gates ADR-0043 до денежных live операций: активная двусторонне подтверждённая security-policy, защищённые recipient versions, isolation/provider-revoke runbook, monetary recovery и market deviation gate затронутых маршрутов. До production: независимый audit checkpoint/archive, control tamper detection и identity recovery обоих Owner.

## 19. Основные источники

[План 114](114_admin_console_audit_and_plan_2026-10-06.md), [правила MVP](MVP_BUSINESS_LOGIC.md), [срез интерфейса 109](109_latest_design_review_2026-10-06.md), [исправления 113](113_button_copy_and_reaction_fixes_2026-10-06.md), [каталог ADR](decisions/README.md), в особенности [0029](decisions/0029_configurable_admin_roles_and_unified_operations.md), [0030](decisions/0030_shadow_funding_interface_emergency_controls.md), [0031](decisions/0031_admin_permissions_and_autonomous_publishing.md), [0032](decisions/0032_admin_connection_health_and_session_revocation.md), [0033](decisions/0033_in_app_marketing_first_external_campaigns_later.md), [0034](decisions/0034_managed_content_and_localization_foundation.md), [0035](decisions/0035_two_owners_and_owner_only_pricing_publication.md), [0036](decisions/0036_support_queue_and_conversation_first_release.md), [0037](decisions/0037_partner_payouts_owner_only.md), [0038](decisions/0038_owner_configurable_referral_and_tariff_parameters.md), [0039](decisions/0039_owner_assignable_user_vip.md), [0040](decisions/0040_platform_usd_accounting_and_venue_payout_options.md), [0041](decisions/0041_owner_confirmed_automated_partner_payouts.md).

## Личный аккаунт сотрудника · уточнение 12.10.2026

По поручению владельца личный профиль оформлен как в клиентском UI, переключение языка перенесено внутрь него. Self-service каждого активного сотрудника отделён от управления чужим доступом и Owner-only действиями. Дизайн, состояния и auth-provider open questions — [пакет 05](design/admin/package-05/README.md) и [контракт](design/admin/package-05/account-contract.md). 38 новых RU/EN состояний на язык; существующие auth/revoked/expired используются повторно. Это дизайн для вычитки, не реализованный auth/API и не выбранный провайдер.


## Уточнение 13.10.2026 · ADM-07 «Данные и рейтинг»

По поручению владельца прежний observational-only блок расширен настройками сборщиков и версионируемых правил валидатора/рейтинга. Согласованные R-1 веса и eligibility ADR-0011 сохранены; новые демо значения не утверждены. [ADR-0044](decisions/0044_data_ingestion_validator_and_rating_controls.md) и [контракт дизайна](design/admin/package-09/data-rating-contract.md) задают границы, preview, command evidence, proposed rights и открытые API-specific вопросы. Публикация должна переключать клиентский каталог только на готовый подтверждённый единый snapshot, не на смесь частично пересчитанных профилей.


## Уточнения по вычитке 14.10.2026

[ADR-0046](decisions/0046_admin_authentication_and_review_clarity.md) задаёт способы входа, ограниченный доступ по резервному коду и конкретные результаты блокировки. Сохраняется различие обычной выплаты одним владельцем, подтверждения реквизитов/защитных правил другим владельцем и аварийного восстановления владельцем с независимым уполномоченным сотрудником. Это историческое правило ADR-0046 заменено ADR-0047: после второго подтверждения новых/изменённых реквизитов обязательны 24 часа.

### ADM-07: управление сбором данных и методикой

Прежнее ограничение «только наблюдение» заменено [ADR-0044](decisions/0044_data_ingestion_validator_and_rating_controls.md). Настройки сборщика, правила проверки данных, черновики, симуляция, публикация и восстановление методики входят в область дизайна. Просмотр не даёт изменения, подготовка не даёт публикации. Операционный сотрудник с соответствующим правом готовит и проверяет черновик; в текущих сценариях владелец применяет настройки и публикует либо восстанавливает методику. История, автор, причина, проверяемая версия и журнал обязательны. Восстановление создаёт новую версию; исходные метрики и совершённые сделки вручную не переписываются. Отсутствие рейтинга само по себе не запрещает ввод адреса или действующую сессию. Конкретные интервалы, численные правила и имена разрешений проверяются при интеграции и реализации.

### Резервные коды и блокировка сотрудника

Резервный код даёт только доступ к восстановлению сильной защиты. Состояние такого сеанса запрещает денежные команды, активацию реквизитов и подтверждения восстановления системы. После проверки новых ключей нужен новый вход; ранее отозванные подтверждения остаются отозванными. Блокировка скомпрометированного сотрудника отзывает все его сеансы и неиспользованные подтверждения, запрещает новые действия этой личности и создаёт проверяемый инцидент. Уже отправленные операции и их резервы сверяются, а не отменяются фиктивно.


## Принято 16.10.2026: доходы и партнёрские выплаты

Актуальный контракт: [ADR-0047](decisions/0047_service_treasury_and_recipient_delay.md). Он заменяет прежнее отсутствие задержки адреса и статус модели кошельков как несогласованного предложения.

Согласованная логическая модель · 16 октября 2026

Принято владельцем с уточнениями по полной выплате, однократному резервированию, задержке адреса 24 часа и ограниченному восстановлению. Это решение об учёте, контроле и дизайне, а не разрешение реальных переводов. Paper Alpha: комиссия Shadow 0%, реальные выплаты выключены; 1% — неактивный пример будущей платной версии.

### 1. Деньги, доход и обязательства

Раздельно учитывать: начисленный доход Shadow; фактическое поступление собственных средств; обязательство конкретному партнёру; фактическую выплату. Денежный маршрут и возникновение долга — разные процессы. Перевод между собственными источниками не создаёт доход и не погашает партнёрский долг.

Источник — зарегистрированный собственный кошелёк или счёт Shadow с назначением, площадкой, сетью, точным активом и правилами использования. Внутренний учётный счёт без самостоятельного внешнего кошелька или счёта не считается денежным источником. Доходы и выплаты — отдельные функции; допустимы несколько источников, но в первой версии используется минимально необходимое число реальных кошельков. Пользовательские деньги и ключи не входят в них.

Начисление дохода: рассчитано, подтверждено, скорректировано или отменено. Фактическое поступление отдельно имеет подтверждение сети/площадки и сопоставление с начислением. Сопоставление может быть полным, частичным, отсутствовать или требовать сверки. Частичное сопоставление поступления не является частичной партнёрской выплатой.

Внешнее событие учитывается один раз по площадке, сети, идентификатору операции и позиции внутри неё; при необходимости ключ включает актив и тип события. Повторная обработка не создаёт повторное начисление или поступление. Исправления — отдельные связанные записи, исходная операция не переписывается.

Стартовые средства владельца разрешены из отдельно зарегистрированного собственного источника и учитываются как финансирование, не как доход. Пополнение источника выплат в первой версии запускает владелец через интерфейс; автоматическое пополнение выключено.

### 2. Начисления партнёрам и полная выплата

Обязательство возникает по утверждённой версии партнёрского правила: партнёр, источник дохода, площадка, база расчёта, ставка, срок действия, округление и плательщик комиссии. Денежные партнёрские правила утверждают два разных владельца; изменения действуют на новые начисления и не пересчитывают ранее подтверждённый долг. Это не вводит второе согласование для обычных тарифов, VIP, текстов и маркетинга.

Сумма операции равна всему подтверждённому доступному непогашенному долгу конкретному партнёру по выбранной площадке. Не подтверждённое и уже зарезервированное для существующей операции в новую выплату не входят. Баланс общего источника не является долгом конкретному партнёру. Если денег на всю сумму и комиссию недостаточно, вся выплата ожидает пополнения; произвольная сумма и частичная выплата недоступны.

Общий учёт ведётся в долларах. Для USDT принят внутренний коэффициент 1 USDT = $1; это не обещание внешнего курса и не правило для любых других активов. В интерфейсе сохраняются исходные актив, сеть, сумма и площадка. Комиссия перевода показывается отдельно, её плательщика настраивают владельцы.

### 3. Доступные средства без двойного вычета

Подтверждённый пригодный баланс — фактически подтверждённые собственные средства, разрешённые к использованию на выбранном маршруте. Неподтверждённые, несопоставленные и заблокированные суммы не включаются в него и повторно из него не вычитаются.

Свободно до комиссии = максимум из нуля и разности: подтверждённый пригодный баланс минус уникальные действующие резервы операций и выделений минус отдельный операционный резерв. Один резерв учитывается только один раз, включая долю, выделенную другим партнёрам. Незарезервированные долги показываются отдельно и повторно не вычитаются. Очередность выделения средств фиксируется в журнале; выбор партнёра не позволяет расходовать чужой резерв.

Новая полная выплата допустима, если свободных средств хватает на весь её долг и необходимые расходы перевода. Комиссия учитывается один раз: в резерве операции либо как дополнительный расход при проверке, но не в обоих местах. Повторный просмотр уже созданной операции использует её собственный резерв, а не повторно резервирует сумму.

Учебный пример будущего платного режима: пригодный баланс 200 USDT; резервы других операций 50; операционный резерв 20; свободно до комиссии 130. Долг партнёру 120, комиссия перевода за счёт сервиса 0,50: полная выплата допустима, остаток 9,50. При свободных 100 выплата 120 целиком ожидает пополнения; 100 не отправляются. Эти числа не являются настройками реального сервиса.

### 4. Адреса: проверка и обязательные 24 часа

Новые или изменённые реквизиты партнёра предлагает один владелец, проверяет и подтверждает другой. Подтверждение относится к точной версии партнёра, площадки, сети, актива и полного адреса. После второго подтверждения начинается обязательная задержка 24 часа; до её окончания новый адрес недоступен для выплат. Оба владельца получают уведомление.

Показать время второго подтверждения, плановое время активации и оставшееся ожидание с часовым поясом. Ускорение, отключение задержки и исключение для Paper Alpha отсутствуют. Во время ожидания любой владелец может отменить изменение. Повторное изменение аннулирует подтверждения и запускает процедуру заново. По истечении срока активация допускается только после повторной проверки актуальности версии, адреса и действующих запретов; срок сам по себе не отменяет остановку.

Предыдущие реквизиты сохраняются отдельной версией и не переписываются. Их использование возможно только если они отдельно остаются активными и не заблокированы; ожидание нового адреса не разрешает автоматически переключать выплату на другой адрес. Отмена изменения не активирует ранее отклонённую или заблокированную версию.

### 5. Владельцы, подтверждения и источники

Обычную выплату на активный адрес в пределах защитных порогов подтверждает один владелец с новой проверкой физическим ключом. Превышение порога требует двух разных владельцев для полной суммы. Подготовка и просмотр не дают права отправки.

Добавление, изменение, повторная активация и удаление собственного источника требуют двух разных владельцев. Экстренно отключить скомпрометированный источник может один владелец. Удаление означает архивирование конфигурации; история, долги, незавершённые операции и сверка сохраняются. Задержка 24 часа здесь автоматически не вводится: она относится к реквизитам партнёра.

Подтверждение имеет ограниченный срок и связано с конкретной версией. Изменение суммы, получателя, сети, актива, источника, комиссии, причины или существенных правил отменяет подтверждения. Срок и численные параметры настраивают владельцы; без действующего правила реальная отправка запрещена. Секретные ключи в админке не показываются; физический ключ входа не является ключом кошелька.

Переводы между собственными источниками имеют отдельное денежное разрешение, точные разрешённые направления, сумму, причину и сверку. Произвольный перевод на любой адрес не предоставляется.

### 6. Лимиты, ошибки и сверка

Целевой остаток — ориентир с предупреждением; защитный порог — требование второго владельца; жёсткий максимум — запрет новых управляемых пополнений сверх лимита. Прямое внешнее поступление в блокчейне остановить нельзя: превышение фиксируется, создаётся предупреждение/инцидент и ограничиваются затронутые действия через Shadow.

Дополнительно настраиваются суточный лимит выплат и лимит одному партнёру или адресу. Граница суток, часовой пояс, учёт комиссии и связанные операции сохраняются в версии правил. Связанные операции суммируются; дробление для обхода проверки запрещено. Изменение и отключение лимитов утверждает другой владелец. Превышение жёсткого запрета нельзя снять вторым подтверждением самой выплаты.

При неизвестном результате резерв сохраняется; новая отправка с тем же экономическим назначением запрещена до сверки. Проверяются сеть, площадка/поставщик и известные идентификаторы. Подтверждённое полное исполнение погашает долг; доказанный окончательный отказ освобождает резерв отдельной записью. Сотрудник не может вручную объявить неподтверждённую выплату успешной.

Расхождение ожидаемой и фактической суммы фиксируется отдельно без редактирования исходной операции. Фактический перевод учитывается по подтверждающим данным, создаётся инцидент, остаток обязательства не теряется. Неожиданная неполная внешняя отправка — ошибка исполнения и сверки, а не разрешённая частичная выплата или автоматический повтор.

### 7. Остановки и восстановительное пополнение

Остановка выплат запрещает новые партнёрские выплаты и обычные пополнения их источников через Shadow. Отдельная остановка пополнений может запрещать только пополнения. Глобальный денежный запрет запрещает все новые денежные отправки Shadow. Уже отправленные операции продолжают сверяться; внешние входящие переводы фиксируются без обещания их заблокировать.

Пополнение для восстановления создаётся только после фиксации причины аварии и указывает точный исходный источник, получателя, сеть, актив, сумму и назначение. Пока действует полное техническое отключение или глобальный запрет денежных операций, отправка такого пополнения запрещена: два подтверждения сами по себе не обходят остановку. Сначала два разных владельца отдельно подтверждают и фиксируют в журнале переход к ограниченному восстановлению: разрешают только конкретный маршрут пополнения, сохраняя закрытыми пользовательское приложение, публичный API, торговые действия, обычные выплаты и остальные продуктовые фоновые задания. Затем два разных владельца подтверждают конкретную операцию пополнения; разрешение маршрута не заменяет подтверждение перевода. Повторное полное отключение немедленно запрещает новые отправки. Уже отправленные операции только сверяются; при неизвестном результате повторная отправка запрещена. Такое пополнение учитывается как перевод собственных средств Shadow, не создаёт доход и не снимает остальные аварийные ограничения автоматически.

### 8. Что показываем в админке

Каталог источников: назначение, тип средств, площадка, сеть, точный актив и его контракт, полный адрес, контролирующее лицо, способ подписания без секретов, разрешённые направления, целевой и максимальный остаток, состояние подключения и время последней проверки. Тип средств — доход, финансирование или выплаты; несовместимые остатки не объединяются в пригодную сумму.

Баланс источника: фактический, неподтверждённый, несопоставленный, заблокированный, пригодный, резервы операций, операционный резерв и свободные средства; отдельно обязательства партнёрам, источник данных, число подтверждений и возраст данных. Показатели не являются суммой всех строк: часть из них — вложенные категории или отдельные обязательства.

Карточка выплаты: конкретный партнёр, правило/версия, подтверждённый доступный долг до операции, полная сумма, остаток после подтверждённого исполнения, маршрут, адреса целиком, комиссия и плательщик, создатель и подтверждающие, срок подтверждения, внутренний идентификатор, защита от повтора, внешний идентификатор, фактическая сумма, резерв, результат сверки и следующий разрешённый шаг.

Сверка: ожидаемые/фактические поступления и выплаты, несопоставленные транзакции, неизвестные результаты, расхождения и ручное расследование. Разрешены подтверждающие данные и классификация расхождения; нет кнопки «объявить выплаченным» без подтверждения.

### 9. До включения реальных денег

Комиссия Shadow и реальные партнёрские выплаты включаются отдельными решениями. До этого реальные переводы, новые действующие денежные права и автоматическое пополнение не запускаются; реальные адреса и ключи в демонстрационные макеты не заносятся.

При интеграции отдельно подтверждаются правовое основание, партнёрские правила, возможности площадок, сети, активы и контракты, получение дохода, поставщик подписания, реальные собственные адреса, лимиты, бухгалтерский/налоговый учёт, тестовые переводы, сверка, аварийный порядок и ответственные владельцы. Наличие комиссии площадки не означает доход Shadow. Механизм комиссии приложения Polymarket документирован, но доступность своему профилю, ставки и фактическое поступление проверяются до включения. Для Limitless отдельно подтверждается источник дохода.

Источники решения: замечания коллеги в этом документе и согласование владельца 16 октября 2026. Предыдущая редакция заменена согласованной; конкретная архитектура кошельков и запуск реальных денег не утверждены.


### Дизайн денежных подтверждений и источников · 16.10.2026

[Пакет конкретных полей, примеров, переходов и границ проверки](design/admin/money-confirmations-sources-2026-10-16/README.md). Формы источника содержат назначение, площадку/среду, сеть, актив/контракт, полный собственный адрес, контроль и способ подписи, источник наблюдения, разрешённые направления, ограничения и причину. Сохранение конфигурации не выполняет перевод и не включает реальную подпись. Добавление, изменение и повторная активация — два владельца; экстренное отключение — один.

Денежная проверка показывает значения: партнёр и весь доступный долг, полный адрес отправителя и получателя, площадку/сеть/актив/контракт, получаемую сумму, расходы и плательщика расходов, полное списание, версии реквизитов/правил/ограничений/снимка, срок согласия и подтверждающего. Снимок проверяется повторно непосредственно перед отправкой. Восстановительный перевод сохраняет свой инцидент и ограничение после отправки, в том числе при неизвестном результате; возврат к обычному пополнению из этой ветви отсутствует.

Все числа в новых макетах — вымышленные примеры, не стандартные настройки реального сервиса. Фактические маршруты обеих площадок и способ подписи проверяются при интеграции. Paper Alpha — комиссия сервиса 0%; 1% остаётся неактивным примером будущей платной версии.


### Дизайн денежных исключений · 16.10.2026

[Набор точных отказных состояний и примеров](design/admin/money-exceptions-2026-10-16/README.md) дополняет правила ADR-0047. Повтор того же экономического запроса возвращает существующую операцию и её уникальный резерв. Чужие резервы не расходуются и не снимаются сотрудником. Доказанный окончательный отказ, неизвестность и неожиданно неполное внешнее исполнение имеют разные статусы: реальные расходы сохраняются, история не переписывается, остаток долга не теряется, непроверенная повторная отправка запрещена.

Согласия имеют время, срок и причину аннулирования для каждого владельца; действует самое раннее истечение. Изменение версии, отзыв согласующего или новый запрет блокируют использование старых согласий. Истечение 24 часов не заменяет повторную проверку реквизитов; новый адрес и новая пара согласий запускают новый полный срок.

После остановки отдельно показаны неотправленные задания, требующие нового снимка и согласий, и уже отправленные, допускающие только проверку результата. Архивирование своего источника двумя владельцами запрещает новые операции, сохраняя историю, остаток, долг и незавершённую сверку. Макеты не являются доказательством серверной реализации этих правил.


## Уточнение 16.10.2026 · уведомления и обратная связь

Пакет ADM-10/11: [макеты и передача](design/admin/notifications-feedback-2026-10-16/README.md). Только дизайн; сообщения, изменения прав и внешние запросы не выполняются. RU и EN используют один состав сценариев, текущую сетку и компоненты. В группу «Управление» добавлены два связанных пункта меню.

### Операционные уведомления — ADM-10

Это журнал операционных и защитных событий, а не конструктор рассылок. Список показывает идентификатор и событие, адресата и канал в разрешённой области, время и состояние. Фильтры: событие, канал, доставка, период UTC, площадка или «без площадки», поиск по идентификатору/адресату. Есть применённая выборка, успешный пустой результат, загрузка, ошибка чтения, просмотр и отказ в доступе. Неизвестный счётчик не становится нулём.

Карточка содержит исходное событие, назначение, безопасный текст, конкретного адресата и канал, версию записи, время, попытки и подтверждающие данные. Финансовые адреса, ключи, секреты и запрещённый контекст не копируются в текст уведомления, ссылки или внешние сообщения. Переход к связанной сущности проверяет её собственные права. Уведомление о реквизитах не подтверждает реквизиты и не заменяет согласия владельцев.

Доступность в приложении, доставка и прочтение — отдельные факты с отдельными основаниями и временем. Создание записи не означает доставку; доставка не означает чтение. Отсутствие подтверждения остаётся неизвестностью. Ознакомление отмечается только за текущего адресата; просмотр владельцем A записи B не отмечает ознакомление B. Отметка не снимает ограничений, не закрывает инцидент и не подтверждает денежное действие.

Каждому адресату одного события соответствует собственная запись. Уникальность события, назначения, адресата и канала исключает повторное создание того же сообщения; попытки доставки хранятся отдельно. Различаются доказанный отказ, неизвестный результат и неподключённый канал без выполненной попытки. «Проверить результат» только читает сведения прежней попытки; универсальной кнопки повторной отправки нет. Перепроверка не создаёт новое сообщение. Подключения, получатели и правила меняются в своих разделах по отдельным правам.

Массовые email/Telegram/push остаются отложенным маркетинговым этапом (ADR-0033). Защитные каналы для администраторов этим запретом не откладываются, но в макетах неподключённый канал не выглядит доставленным. При полном техническом отключении продолжаются только разрешённые аварийные уведомления; продуктовые рассылки и задания не продолжают работу под видом мониторинга.

### Обратная связь — ADM-11

Отзыв — самостоятельная сущность со своим исходным текстом, происхождением, временем, языком и переданным контекстом. Оригинал не изменяется при классификации, назначении, завершении, связывании или обнаружении похожей темы. Английский оригинал сохраняется на английском и в русском интерфейсе; перевод не подменяет текст автора.

Список: идентификатор/тема, категория, статус, ответственный, дата и разрешённый контекст; фильтры по категории, статусу, периоду, назначению и поиску. Карточка показывает исходник отдельно от внутренней обработки, переданный экран/сущность, заметки и историю. В первой версии показаны классификация, назначение и статус по праву feedback.manage, без согласования владельца. Просмотр не даёт изменения автоматически; запрет доступа не раскрывает текст, пользователя или связанные записи.

Изменения обработки сохраняют автора, время, версию, прежнее и новое значение. Проверка ожидаемой версии предотвращает перезапись одновременной правки; при конфликте нужно открыть актуальное состояние и повторно проверить собственный черновик. Ошибка поля не меняет сохранённые данные. Внутренняя заметка не отправляется клиенту.

Связь с обращением или инцидентом не заменяет оригинал и не создаёт вторую сущность автоматически. Показан проверяемый пример связи FB-DEMO-01 с существующим TKT-1042: Амина Рахман / USR-1007, Polymarket, S-CP-041. При создании проверяются допустимый тип, совпадение контекста и собственные права на обе записи; повтор не создаёт дублирующую связь. Отзыв, переписка и их статусы существуют отдельно. «Разобрано» означает завершение обработки отзыва, а не исправленную ошибку или закрытое обращение. Клиенту отвечают в поддержке, если требуется ответ.

Без переданного контекста пользователь, площадка и сессия остаются неизвестными; сотрудник не выбирает похожего человека по догадке. Похожие отзывы сохраняют отдельные оригиналы, пользователей и историю; сходство темы не является доказательством общей операции. Полное техническое отключение запрещает обычную продуктовую обработку отзывов и новые изменения; аварийная админка остаётся отдельным контуром.

### Передача и ограничения проверки

Поля, фильтры и исходы представлены подготовленными снимками прототипа. Свободный ввод, сохранение данных между снимками, фактическая доставка, серверные права и конкурентные изменения реализуются позднее. Структурная и выборочная визуальная проверка не заменяют ручной проход всех языков и ролей. Paper Alpha сохраняет комиссию 0%; реальные отправки и сделки не включаются.


## Уточнение 18.10.2026 · отдельная проверка двух ключей

Для владельца показываются отдельные результаты основного и другого запасного физического ключа. Один запрос не подтверждает оба. Состояния: не проверен, ожидание браузера, подтверждён, ошибка/отмена, повтор уже проверенного ключа, устаревший результат. При ошибке или отмене второго шага первый результат сохраняется только пока действителен для той же учётной записи и той же версии набора ключей. Срок и серверные условия определяются при реализации, новые численные правила не утверждены. Изменение набора, отзыв или истечение действительности аннулирует незавершённую последовательность; чувствительные действия не открываются по старому результату. Только две отдельные действительные проверки разных зарегистрированных ключей завершают настройку. Проверка входа не является денежным согласием.

[Макеты, состояния и границы проверки](design/admin/two-keys-documentation-2026-10-18/README.md). Сценарные переключатели прототипа вынесены из рабочих действий и не реализуются как продуктовые кнопки.


## Уточнение 18.10.2026 · частичное исполнение и денежная сверка

[Контракт и независимые учебные снимки](design/admin/order-money-reconciliation-2026-10-18/contract.md) дополняют разделы 6–7. Запрос отмены и её принятие отделены от окончательно сверённого неисполненного остатка. Поздно полученное исполнение, произошедшее до отмены, сохраняется; повтор наблюдения не добавляет его снова. Неизвестный исход и ошибка чтения не освобождают резерв. Снимок после позднего исполнения не откатывается к ранней версии при повторной проверке. Новых прав вручную торговать или отменять заявки за клиента нет.

Денежная сверка типизирована: полная выплата партнёру, поступление своих средств, клиентское пополнение и исходный клиентский вывод. Для каждого — исходная идентичность, выполняемая проверка, достаточное подтверждение, ошибка чтения и недостаток/конфликт данных. Повторяется только чтение, не отправка. Подтверждённое получение не равно подтверждённой доступности клиентского остатка. Удержание завершённого вывода расходуется, а не возвращается в доступные средства. Собственное пополнение не считается доходом или новым партнёрским начислением. Автоматического снятия ограничений/закрытия инцидента нет.

Все сети, активы, контракты, подтверждения и суммы этих маршрутов — изолированные примеры; поддержка площадок проверяется при интеграции. Комиссия Paper Alpha 0%; частичных партнёрских выплат нет. Служебные исходы прототипа отделены от рабочих действий. Реальные переводы и работающая авторизация не запускались.


## Уточнение 18.10.2026 · рабочее место торговой сессии

[Согласованный учебный снимок, сущности и права](design/admin/session-workspace-2026-10-18/contract.md): позиции, заявки, исходные действия трейдера и решения по сигналам разделены вкладками и связаны точными ID. Решение хранит свои настройки/суммы/время; допуск не равен полному исполнению. Пропуски не создают резерв/заявку и не догоняются, нехватка полной суммы не уменьшает покупку. Ручные и сохранённые после отключения активы не продаются вслед за трейдером.

При отсутствии текущей цены нет рыночной стоимости и прибыли. Загрузка, пустая подтверждённая выборка и устаревший снимок при ошибке чтения различаются. Альтернативный неподключённый профиль Limitless не обещает поддержанные поля API или вторую активную demo-session. Владелец с разрешённым чтением видит учебные суммы; новые права сотрудникам не вводятся. Paper Alpha: комиссия 0%. Рабочие переходы и сценарии прототипа разделены. 17 состояний на язык, UI kit 0.4.21 без расширения. G04/G05/G06 и полный X01/X04 остаются открыты.


## Уточнение 18.10.2026 · права сотрудников и критические действия

[Полная матрица и границы доступа](design/admin/staff-access-2026-10-18/contract.md): 18 разделов, 7 типов действий, площадка, среда, данные и срок. Сохранение черновика и выдача действующих полномочий разделены. Итог показывает все действующие назначения; пример содержит одно назначение, не новые пресеты по умолчанию. Самоэскалация и выдача владельческих прав кастомной ролью запрещены. Ограничения применяются к списку, карточке, вложенным данным, суммам, счётчикам, обновлениям и экспорту. Ошибка или запрет не превращаются в нулевые суммы.

Отзыв права экспорта блокирует выдачу уже готового файла, но не отменяет разрешённое чтение. Блокировка аккаунта, отзыв назначения и окончание срока — отдельные состояния; открытая вкладка не сохраняет права. Отправленное внешнее действие не объявляется отменённым.

Обычный тариф, пользовательский VIP и обычная полная выплата — владелец; второе независимое согласие действует только по ADR-0046/0047. Новые реквизиты после второго владельца ждут 24 часа. Полный технический режим и жёсткий денежный запрет не обходятся двумя согласиями. Общая аварийная разблокировка и денежный маршрут восстановления различаются. Тексты и маркетинг публикуются по выданным правам без нового согласования владельцем. Новая проверка личности не выдаёт недостающие полномочия.

29 состояний на язык, карта 0.22 — 647 корней /642 основных состояния; набор компонентов 0.4.21 без новых семейств. Покрытие дизайном, не реализация серверных проверок. Полные X01/X04 и приглашение B04 остаются открыты. Paper Alpha — комиссия Shadow 0%, реальные действия выключены; 1% только неактивный будущий пример.


## Уточнение 18.10.2026 · каталог рынков и настройки

[Контракт и границы](design/admin/market-source-settings-2026-10-18/contract.md): рынки и источники рыночных данных отдельно от денежных источников; состояние рынка, подключения, свежесть и полнота независимы. Неизвестная цена не равна нулю; восстановленный ответ не закрывает исторический пропуск. Поиск, сохранённая выборка, карточки и качество связаны.

Сборщик: отдельные поля, права, проверка и конфликт версии, подтверждённый отказ; неизвестный исход читается по той же команде. Числа P-1/P-2 учебные, API-возможности не утверждаются. Языки: обязательные тексты и проверка носителем, включение/отключение новой версией по праву публикации без дублирующего владельца, защита английского резервного языка. BN — учебный будущий кандидат, не расширение запуска RU/EN.

Область ограничения: семь типов и точные объекты, совместимость площадки/среды/связей, последствия, конфликт и запрет. Это не универсальный обход полного отключения и не новые права; E04 и T05 остаются частичными до полного прохода.

42 новых состояния на язык, карта 0.23 — 689 корней /684 основных состояния; UI kit 0.4.21 без расширения. D02/D03/L03 покрыты дизайном. Paper Alpha — комиссия Shadow 0%, реальные действия выключены; полные X01/X04 открыты.


## Уточнение 19.10.2026 · команды данных и области ограничений

[Контракт](design/admin/commands-scoped-controls-2026-10-19/contract.md): девять команд, раздельные права, версии/снимки, защита от повторного намерения, принятие/выполнение/полный результат, отказ и неизвестность. Настройка методики не переключает каталог до отдельного полного пригодного расчёта; непригодный старый снимок не сохраняет видимый балл. Обычная пауза сборщика не требует ответа внешнего API и не снимает аварийный запрет.

Все семь типов области с двумя подтипами источника имеют точное подтверждение и восемь семейств применения/независимого восстановления. Остановка собственного денежного источника — один владелец, повторная активация — два разных владельца. Для остальных аварийных восстановлений — владелец и независимый уполномоченный сотрудник; владелец B в примере не делает двух владельцев обязательными всегда. Подготовка не создаёт согласие; REC и RST — разные запросы. При неизвестном эффекте или неполном подтверждении запрет сохраняется; повтор запрещён. Глобальные запреты не обходятся. Восстановление маршрута не разрешает перевод; для восстановительного пополнения действуют отдельные два владельца для маршрута и операции.

87 новых и 8 обновлённых состояний на язык; карта 0.24 — 776 корней /771 основное состояние; UI kit 0.4.21 без новых компонентов. T05/E04 покрыты дизайном, не серверной реализацией или полной приёмкой. Полные X01/X04 открыты; Paper Alpha — комиссия Shadow 0%, реальные действия выключены.

## Уточнение 19.10.2026 — роли и сквозные состояния

19.10.2026: [проход ролей и сквозных сценариев](design/admin/role-scenario-pass-2026-10-19/README.md). Исправлены ролевые меню и вложенные переходы, независимые подтверждения восстановления, отдельная выплата PAY-023 по новому адресу REC v2, ответы ограниченной поддержки и клиентские проекции ограничений. Карта 0.25: 807 корней / 802 основные пары на язык; UI kit 0.4.21 сохранён. Прототипы и документы не подтверждают серверную авторизацию или реальные операции.

Рабочая кнопка не меняет действующего сотрудника. Первое подтверждение ведёт в ожидание; независимый участник открывает свой контекст отдельно. Служебные переключатели учебного прототипа подписаны и отделены от продуктовых действий. Реквизиты REC v2 после двух владельцев и 24 часов требуют нового расчёта PRV-022 и операции PAY-023; разрешение PAY-021 на старый адрес не переносится.

При полном отключении сначала два разных владельца разрешают конкретный маршрут восстановительного пополнения, затем два разных владельца отдельно подтверждают сам перевод. Разрешение маршрута не снимает технический режим и не разрешает обычные выплаты. Сверка только читает итог. Неизвестный итог сохраняет резерв и запрещает повтор.

Меню, вложенные карточки, собственный профиль и возвраты сохраняют роль и область. Настраиваемая роль не превращается во владельца; просмотр не разрешает изменения и экспорт. Публикации текстов и внутренних объявлений выполняет сотрудник с нужным правом без постоянного согласования владельца, с журналом.

## Уточнение навигации финансов · 20.10.2026

[Разбор финансового интерфейса](design/admin/finance-clarity-2026-10-20/README.md) отделяет обычные задачи выплат от дополнительных настроек. Это изменение представления и прототипных маршрутов; разрешения и денежные правила ADR-0043/0047 остаются прежними. Настоящие пороги по-прежнему задаются владельцами, а не берутся из учебного примера. Показ P-14 начинается с полной выплаты 120 USDT при учебном пороге 100 USDT; дополнительная пустая форма не считается действующим правилом и не активируется.
