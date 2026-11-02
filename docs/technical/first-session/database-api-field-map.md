# Точная карта остальных API-полей и источников БД

02.11.2026 · **Все три блока DB-API-09 приняты; документальное проектирование стыка завершено.** [Итог §§13–14](database-q06-absence-design.md): отдельное all-право, типизированный audit и согласованное Serializable-наблюдение; при overlap допустим Q06→C06 даже при более позднем commit аудита. Старые статусы «предложено/открыто» ниже — история согласования. Реализация, компоненты/права/доказательства остаются; код, SQL, миграции и испытания не начаты.

02.11.2026 · **Блоки 1–2 DB-API-09 приняты целиком**: отдельное право отсутствия для всех площадок и отдельный audit-kind в существующем журнале. [Решение](database-q06-absence-design.md), реестр v4: target user/наблюдение слота, одно evidence, строгие старые session/snapshot связи сохранены. Блок 3 — согласованность с C06/отзывом/login replacement — ещё открыт; DB-API-09 целиком не закрыт. Только документы, без кода, SQL, миграций и испытаний.

02.11.2026 · Документальные примеры этой карты подготовлены отдельным блоком: [AP01–AP16](database-api-response-examples.md), связи R/A/F/E в §12 примеров. Исходные §§1–15 сохранены; см. дополнение §16. Испытания не выполнялись; DB-API-09/10 и остальные инженерные зависимости не закрыты.

02.11.2026 · Следующий блок выполнен: отображение этой карты перенесено в четыре физические спецификации; см. §15. Исходная карта §§1–14 сохранена. Документальные примеры выдачи ещё следующий отдельный блок; испытаний/кода/SQL/миграций нет.

30.10.2026 · Блок 1 по прямому поручению владельца. Baseline main `06bc3d78d0721fdc4aee22abdc2e7e2cf934d52d` (PR №184). **Только документы: код, SQL, миграции и испытания не выполнялись.** Карта отражает принятые формы DB-API-01–08/11; C04/last_input_receipt_id и [карта ошибок](database-error-field-map.md) не пересогласовываются.

## 1. Область, источники и статус

Источник внешних имён, обязательности и закрытых вариантов — [дополнение API §§1–13](backend-api-forms-addendum.md); граница поручения — [передача DB-API §9](backend-database-change-list.md). Источники колонок: физические блоки [ввод/владение](database-physical-design.md), [каталог/review](database-physical-catalog-review.md), [сессия/учёт](database-physical-session-ledger.md), [команды/доступ](database-physical-operations-access.md). Все таблицы ниже принадлежат `shadow`, все соединения сохраняют environment и предусмотренные составные связи. Отсутствие environment во внешнем объекте не отменяет область данных.

| Передача | Разделы этой карты | Что отражено |
| --- | --- | --- |
| DB-API-01 | 2–3 | Входные поля и их назначение; C05 timezone/version, C06 expectedSlot, claim без обычного ключа |
| DB-API-02 | 4 | Исходный commandRef, receipt, Q05 status и HTTP отдельно от исхода |
| DB-API-03 | 5 | Ранний/технический конверт без сохранённого результата |
| DB-API-04 | 6 | Все поля review, числовые варианты, warnings и expectedSlot |
| DB-API-05 | 7 | Текущий draft и уже принятый исторический источник ошибок Q03 |
| DB-API-06 | 8–10 | Settings, financialSnapshot, summary и историческое имя трейдера |
| DB-API-07 | 11 | Сборка разрешённых групп Q04/Q06, restrictedGroups и граница отсутствия |
| DB-API-08 | 12 | Шесть полей claim, Q01 и граница полного входа |
| DB-API-11 | 13 | Диагностика, current navigation и источники безопасных параметров |

DB-API-09 (Q06 без session: права/audit) и DB-API-10 (каталог/курсор/consistent read) **не закрываются**. Принятая внешняя форма отсутствия Q06 здесь только обозначена. Новых колонок/таблиц, audit-кодов, прав, команд или вариантов C04 не вводится; нельзя распространить это утверждение на будущее решение DB-API-09.

Обозначения в таблицах: **И** — сохранённый неизменяемый факт; **Т** — текущее согласованно прочитанное состояние; **В** — вычисляемая проекция/вывод; **П** — контекст конкретной передачи. Входная строка API не становится доверенным фактом без принятого допуска/валидации. Для текущего чтения источник может быть неизменяемой записью, выбранной текущим указателем; это явно указано.

## 2. Общие преобразования

| Форма API | Источник и точное отображение |
| --- | --- |
| UUID | UUID соответствующей колонки/доверенно установленного контекста. ID в запросе — только locator, не право |
| PositiveVersion | Положительный bigint → каноническая десятичная строка без ведущих нулей; не JSON number, timestamp или recordSchemaVersion |
| Counter | Неотрицательный bigint → такая же строка, ноль `"0"` |
| Money.n / Money.d | Пара целых `*_n`/`*_d` → строки без знака/ведущих нулей, d>0, gcd=1, ноль 0/1, ≤64 цифр на компонент. Не округлять, не пропускать через floating point, не ремонтировать несокращённую/неполную пару на чтении |
| Percent | Сохранённые сотые процентного пункта в integer → строка процентных пунктов ровно с двумя десятичными знаками: 50 → `"0.50"`, 300 → `"3.00"`. Это точное представление, не новый расчёт; raw не преобразуется этим правилом |
| Timestamp | Сохранённый timestamptz → UTC с Z и тремя знаками миллисекунд; не время ответа. Серверное now используется отдельно только для явно текущих проверок |
| Raw | Исходный text или null, ≤64 Unicode code points; пустая строка отлична от null. Нет trim/NFC/перезаписи десятичного разделителя |
| requestSchemaVersion | Входной `v1` для проверки формы; отдельная колонка из него не создаётся, он не подменяет сохранённый формат |
| recordSchemaVersion | Только `record_schema_version` соответствующего receipt/review/settings/snapshot. Draft/claim/summary/Q01 не получают вымышленную версию записи |

Все объекты закрытые; поля обязательны в своём варианте, кроме явно необязательных параметров навигации. Отсутствующий ключ, null, [], {} и ноль различаются. Для nullable Money оба компонента либо заполнены, либо NULL; половина пары — повреждение, не null API. Неизвестный формат/код, отсутствующий обязательный источник или установленное противоречие → RECORD_UNAVAILABLE/503 без частичной выдачи/подстановки; временная недоступность → SERVICE_UNAVAILABLE. Наличие v1 само по себе не доказывает совместимость всей записи.

## 3. Запросы: источник намерения и назначение

### 3.1. C04 — ссылка на уже принятую модель

Create POST /api/demo/drafts, update PATCH /api/demo/drafts/:draftId; оба передают полную форму. Ни одна строка ниже не меняет атомарность, повторы или ошибки [C04](database-c04-addendum.md).

| Вход | Назначение в принятой модели |
| --- | --- |
| requestSchemaVersion | Проверка формы §2; не record_schema_version |
| clientCommandId | `command_keys.client_command_id` в доверенной области actor/environment/type; общий scope create/update |
| Маршрут create/update | `command_keys.c04_operation`; body.operation нет |
| :draftId только update | Доказанный target → `command_keys.target_draft_id`; сервер связывает `target_ownership_id` с историческим владением при операции. Create ID назначает сервер |
| expectedDraftVersion только update | `command_keys.expected_draft_version`; сравнение с текущей `setup_drafts.version`, а не запись ожидаемого номера как нового текущего |
| locale, step, entryContext | `setup_drafts.locale`, `step`, `entry_context` |
| venueId, traderId, selectedMode | `setup_drafts.venue_id`, `trader_id`, `selected_mode`; условная принадлежность трейдера своей площадке сохраняется |
| rawBudget, rawFixedAmount, rawCopyPercent | `setup_drafts.raw_budget`, `raw_fixed_amount`, `raw_copy_percent` |
| rawMarketLimitPercent, rawDailyBuyLimitPercent | `setup_drafts.raw_market_limit_percent`, `raw_loss_limit_percent`; последнее — дневной лимит новых покупок |
| proposedTimezone | `setup_drafts.proposed_timezone` |

Все пять raw-ключей обязательны, значения могут быть null; сохраняются оба размера F/q, проверяется действующий режим. Колонки формы меняет только успешный created/updated. Unchanged имеет собственный исход, но не меняет ввод/pointer/TTL; exact replay возвращает прежний исход. Форма/маршрут/target/ожидание входят в принятое каноническое намерение и request_hash; это не разрешение хранить сырой HTTP body. Actor/realm/environment устанавливает сервер. Полная история raw не добавляется.

### 3.2. C05, C06 и claim

| Операция / все поля | Назначение / источник |
| --- | --- |
| C05 requestSchemaVersion | Проверка входной формы v1 |
| C05 draftId | Допустимый `setup_drafts.id`; сохранённый результат ссылается через `setup_reviews.draft_id` |
| C05 expectedDraftVersion | Ожидание против `setup_drafts.version`; `setup_reviews.draft_version` — действительно проверенная версия |
| C05 proposedTimezone | Сравнение с `setup_drafts.proposed_timezone` той же версии; review копирует сохранённое значение. При той же версии и другой зоне INVALID_REQUEST без review; устаревшая версия VERSION_CONFLICT. Зона меняется отдельным C04 |
| C06 requestSchemaVersion, clientCommandId | Входная форма; client ID → `command_keys.client_command_id` типа C06/user |
| C06 reviewId | `setup_reviews.id` конкретного показанного review; при успехе `paper_sessions.started_from_review_id`. Для rejected новый результат-session не создаётся |
| C06 expectedDraftVersion | Сравнение с review.draft_version и актуальным вводом; часть исходного намерения/hash. Не записывать в C04-only `command_keys.expected_draft_version` |
| C06 expectedSlot.state, expectedSlot.generation | Сверка с сохранёнными review.slot_observation/expected_slot_generation и текущим slot. Вход только absent без generation либо present с положительной generation; not_applicable/null/0 запрещены. Ожидания входят в исходное намерение; отдельная новая колонка ключа не вводится |
| Claim :draftId | `setup_drafts.id` после доказанного допуска; `draft_claim_receipts.draft_id` при передаче |
| Claim requestSchemaVersion | Единственное поле body, v1. Получатель/первичный guest proof из защищённого H01-контекста, не body |

C05 не имеет clientCommandId/обычного receipt/Q05. Поля review копируются из проверенных данных/правил, клиент не присылает готовый review. C06 получает настройки и источники из review, не из нового body; replay не заменяет review/slot/version свежими. У claim нет clientCommandId/expectedDraftVersion; собственный dedup и временная блокировка по draft сохранены. Hash не является обратимо сохранённым body; эта карта не добавляет возможность восстановить потерянный C06 payload из hash.

### 3.3. Чтения и locator

GET без тела, query только requestSchemaVersion=v1, кроме явно перечисленных параметров Q05; неизвестные/повторные параметры не принимаются.

| Чтение | Доверенное разрешение цели |
| --- | --- |
| Q01 /api/me | Текущий полный user-вход → `users.id`; не staff principal и не paper session |
| Q03 /api/demo/drafts/:draftId | `setup_drafts.id` + текущее ownership и допустимый user/guest контекст |
| Q04 /api/sessions/current | Полный user → `user_session_slots` по environment/user_id/mode=paper → current_session_id |
| Q04 /api/sessions/:sessionId | `paper_sessions.id` в своей области владельца; не обход через чужой slot |
| Q06 /api/admin/sessions/:sessionId | Staff-вход/назначения → разрешённая `paper_sessions.id`; user_id сессии — цель, не actor |
| Q06 /api/admin/users/:userId/sessions/current | :userId — target user, затем его paper slot; право раскрывать отсутствие и его audit остаются DB-API-09 |
| Q05 /api/commands/:clientCommandId | Query requestSchemaVersion, commandType, actorRealm, actorId; path ID → client_command_id. ActorId выбирает actor_user_id либо actor_guest_context_id по realm. Environment серверный; C06/guest запрещён |

Q05 читает typed key↔receipt↔details в исходной области команды. Locator не даёт доступа. До guest create draftId не нужен; после claim исходный guest commandRef не превращается в user. Допуск идёт по конкретной сохранённой цепочке результата/владения/claim. C05/claim/Auth/logout не включаются в Q05. Никакое чтение не принимает клиентские permissions, environment или snapshotVersion для обхода выбранного состояния.

## 4. Исторический результат C04/C06 и Q05

Обозначения: K=`command_keys`, C=`command_receipts`, D=`command_receipt_details`; соединения по environment и принятым типизированным связям. Ни current draft, ни current session не заменяют result_* исходного receipt.

| Поле API | Источник | Вид / правило |
| --- | --- | --- |
| commandRef.actorRealm | K.actor_realm | И; исходная область |
| commandRef.actorId | K.actor_user_id при user, K.actor_guest_context_id при guest | И; не login ID и не текущий получатель claim |
| commandRef.commandType | K.command_type, совпадающий с C.command_type | И; C04/C06 |
| commandRef.clientCommandId | K.client_command_id | И; не C.id |
| receipt.receiptId | C.id | И |
| receipt.recordSchemaVersion | C.record_schema_version | И |
| receipt.commandType, receipt.outcome | C.command_type, C.outcome | И; outcome только succeeded/rejected |
| receipt.createdAt | C.created_at | И; не время чтения и не переименованный commit timestamp |
| receipt.reasonCode | C.reason_code | И; null только succeeded |
| receipt.reasonDetails | D.reason_data.reasons rejected; [] из корректного {} succeeded | И/В; точная [карта ошибок §2](database-error-field-map.md), без нового разбора |
| receipt.fieldErrors | D.response_data.fieldErrors | И; поле только succeeded C04, рядом с result; у rejected C04 и всех C06 отсутствует |
| receipt.result | Активная полная result-группа C | В из И; rejected строго null |
| result.draftId, result.ownershipId | C.result_draft_id, C.result_ownership_id | И; только succeeded C04; ownership историческая |
| result.draftVersion, result.changeKind | C.result_draft_version, C.result_change_kind | И; created/updated/unchanged |
| result.lastSavedAt, result.expiresAt | C.result_last_saved_at, C.result_expires_at | И; не текущие времена draft |
| result.sessionId, result.settingsRevisionId | C.result_session_id, C.result_settings_revision_id | И; только succeeded C06 |
| result.snapshotVersion, result.sessionVersion | C.result_snapshot_version, C.result_session_version | И; стартовые "1", не текущие версии |

Прямой C04/C06: корень ровно commandRef/receipt/nextAction/nextActionParams. Q05: те же поля плюс status. Q05.status=committed для succeeded, rejected для rejected; оба HTTP200. Pending — временное наблюдение HTTP202 с receipt=null при допустимом поиске, не сохраняемый outcome. Если receipt ещё не найден, commandRef — проверенный исходный locator разрешённого поиска; это не утверждение о существующей K. Порча/недоступность/нет допуска не маскируются pending.

Прямой статус: C04 created201, updated/unchanged200; C06 succeeded201; сохранённый rejected — HTTP принятой причины. Exact replay сохраняет этот статус и исходный receipt; Q05 HTTP200 не превращает отказ в успех. nextAction/params формируются сейчас (§13). K/C/D не получают диагностику/навигацию. C.related_session_id — только своя блокирующая session у rejected C06, не result и не immutable reasonDetails; разрешённая ссылка может использоваться текущей навигацией после проверки прав.

## 5. Ранний или технический ответ без сохранённого результата

| Все поля корня | Источник / хранение |
| --- | --- |
| reasonCode | Установленная причина текущей передачи по принятому контексту/реестру; не новый C.reason_code |
| reasonDetails | Ровно один объект code=reasonCode, params={}; внешний конверт, не D.reason_data |
| nextAction, nextActionParams | Текущая безопасная навигация §13 |

Нет receipt/result/fieldErrors/status даже со значением null. Такие ответы не пишутся в обычные receipt/details или review. Уже существующий результат предыдущей передачи не удаляется/не заменяется. C04/C06 unknown →503 SERVICE_UNAVAILABLE и, если безопасно, resolve_command по исходному commandRef; не прямой 202. Claim unknown — собственный recovery, C05 unknown — отдельная явная новая проверка, без Q05. Точные Auth-ответы и приоритет независимых ранних защит ещё требуют H01. CATALOG_CHANGED относится только к Q02/DB-API-10 и не добавляется в сохранённые причины C04/C06/review.

## 6. C05: review

HTTP200: корень ровно review/nextAction/nextActionParams только после подтверждённого сохранения, включая отрицательный review. R=`setup_reviews`; все источники ниже **И**, выбранная историческая ownership сохраняется после claim. Обычная запись с reason не становится HTTP-ошибкой допуска; ошибка/unknown до подтверждения использует §5 без review.

| Поле review | Точная колонка / преобразование |
| --- | --- |
| reviewId, draftId, ownershipId | R.id, R.draft_id, R.ownership_id |
| recordSchemaVersion, draftVersion | R.record_schema_version, R.draft_version |
| ownerKind, ownerUserId | R.owner_kind, R.owner_user_id; null user ID только у guest |
| venueId | R.venue_id; nullable при невыбранной площадке |
| catalogSourceId, traderId, traderRevisionId | R.catalog_source_id, R.trader_id, R.trader_revision_id; полная тройка либо все null |
| catalogVersion, traderControlVersion | R.catalog_version, R.trader_control_version; вместе с тройкой трейдера, иначе null |
| policyVersionId, paperControlId, paperControlVersion | R.policy_version_id, R.paper_control_id, R.paper_control_version; обязательные исходные ID/guard |
| selectedMode | R.selected_mode; fixed/percent/null |
| rawBudget, rawFixedAmount, rawCopyPercent | R.raw_budget, R.raw_fixed_amount, R.raw_copy_percent |
| rawMarketLimitPercent, rawDailyBuyLimitPercent | R.raw_market_limit_percent, R.raw_loss_limit_percent |
| proposedTimezone, normalizationValid | R.proposed_timezone, R.normalization_valid |
| budget.n, budget.d | R.budget_n, R.budget_d |
| fixedAmount.n, fixedAmount.d | R.fixed_amount_n, R.fixed_amount_d |
| copyPercent | R.copy_percent → Percent |
| marketLimitPercent, dailyBuyLimitPercent | R.market_limit_percent, R.loss_limit_percent → Percent |
| effectiveMarketLimit.n, effectiveMarketLimit.d | R.effective_market_limit_n, R.effective_market_limit_d |
| effectiveDailyBuyLimit.n, effectiveDailyBuyLimit.d | R.effective_loss_limit_n, R.effective_loss_limit_d; лимит покупок, не убытка |
| expectedSlot.state | R.slot_observation |
| expectedSlot.generation | R.expected_slot_generation → PositiveVersion; ключ только при present |
| allowedToStart, requiresAuthentication | R.allowed_to_start, R.requires_authentication |
| primaryReasonCode | R.primary_reason_code |
| reasonDetails, fieldErrors | R.reason_details.reasons, R.reason_details.fieldErrors по прежней карте |
| warnings | R.warnings; весь сохранённый массив без вычисления по текущему каталогу |
| checkedAt, expiresAt, createdAt | R.checked_at, R.expires_at, R.created_at; не обновлять при чтении |

normalizationValid=false: все семь нормализованных числовых полей null, не отдельные Money с null-компонентами; allowedToStart=false. При true заполнены budget/marketLimitPercent/dailyBuyLimitPercent/effectiveMarketLimit/effectiveDailyBuyLimit и ровно действующий fixedAmount либо copyPercent; неактивное поле null. Отказ по входу/слоту/допуску может иметь полный валидный числовой набор. Primary/reasons/fieldErrors сохраняют ранее принятую карту, не пересчитываются по новой policy.

ExpectedSlot у guest ровно state=not_applicable; у user absent без generation либо present с положительной generation. Поле generation отсутствует, а не null, в первых двух вариантах. Существующий свободный слот всё равно present. Ошибка чтения слота не даёт absent. Expiry сохранён как checked_at+10 минут; просмотр не продлевает.

Точная уже принятая форма warnings в R.warnings: массив объектов ровно code/params; codes только SYNTHETIC_DATA, COPYING_NOT_CONNECTED, в этом порядке без повторов; params всегда {}; только применимые установленные предупреждения, отсутствие — []. Лимит ≤16 384 байта компактного UTF-8 на **всё поле** по правилам карты ошибок §7. Не null/{} вместо массива, не новый wrapper/schemaVersion; неизвестный code/лишнее поле не игнорируется. Предупреждения не блокируют старт и не включаются в reasons. Это отражение API-решения, а не новое правило предупреждений или созданный codec.

## 7. Q03: текущий draft и прежний источник ошибок

Корень ровно draft/fieldErrors/fieldErrorsSource/nextAction/nextActionParams. D=`setup_drafts`, O=`draft_ownerships`, выбранная через D.current_ownership_id своего draft/environment. Поля draft — **Т**, кроме state (**В**); неизменяемые времена не заменяются текущим временем.

| Поле draft | Источник |
| --- | --- |
| draftId, currentOwnershipId, draftVersion | D.id, D.current_ownership_id, D.version |
| ownerKind | O.owner_kind; текущая, не ownership старого receipt |
| state | used при согласованных D.used_at/used_by_session_id; иначе expired при serverNow≥D.expires_at; иначе editable. Отдельной колонки state нет |
| locale, step, entryContext | D.locale, D.step, D.entry_context |
| venueId, traderId, selectedMode | D.venue_id, D.trader_id, D.selected_mode |
| rawBudget, rawFixedAmount, rawCopyPercent | D.raw_budget, D.raw_fixed_amount, D.raw_copy_percent |
| rawMarketLimitPercent, rawDailyBuyLimitPercent | D.raw_market_limit_percent, D.raw_loss_limit_percent |
| proposedTimezone | D.proposed_timezone |
| lastSavedAt, expiresAt, createdAt, updatedAt | D.last_saved_at, D.expires_at, D.created_at, D.updated_at |
| usedAt, usedBySessionId | D.used_at, D.used_by_session_id; оба null до использования, затем оба заполнены |

Корневые fieldErrors/fieldErrorsSource **не новые определения**: [карта ошибок §5](database-error-field-map.md). D.last_input_receipt_id → succeeded C04 created/updated → details.response_data.fieldErrors. fieldErrorsSource.receiptId — ID источника, draftVersion — его result_draft_version, совпадающая с D.version. Согласованное чтение проверяет environment/draft/version и всю обязательную цепочку. Новый unchanged/C05/claim не заменяет pointer. После claim O может быть user, источник ошибок — guest historical. Нет вывода policy из времени, пересчёта ошибок, allowedToStart или нормализованных настроек в Q03. Editable не означает разрешённый будущий C04; чтение expired/used не продлевает срок и не открывает запись.

## 8. Settings

S=`settings_revisions`; **И**, выбранная по `session_snapshots.settings_revision_id` выдаваемого состояния и принадлежащая той же session/environment, не max(created_at). У Q04 поле session.settings обязательно; у Q06 — только разрешённая группа.

| Все поля settings | Источник |
| --- | --- |
| settingsRevisionId, sessionId | S.id, S.session_id |
| recordSchemaVersion, sequence, previousRevisionId | S.record_schema_version, S.sequence, S.previous_revision_id; null previous только первая sequence="1" |
| budget.n, budget.d | S.budget_n, S.budget_d |
| sizingMode | S.sizing_mode |
| fixedAmount.n, fixedAmount.d | S.fixed_amount_n, S.fixed_amount_d; объект только fixed, иначе fixedAmount=null |
| copyPercent | S.copy_percent → Percent при percent, иначе null |
| marketLimitPercent, dailyBuyLimitPercent | S.market_limit_percent, S.loss_limit_percent → Percent |
| effectiveMarketLimit.n, effectiveMarketLimit.d | S.effective_market_limit_n, S.effective_market_limit_d |
| effectiveDailyBuyLimit.n, effectiveDailyBuyLimit.d | S.effective_loss_limit_n, S.effective_loss_limit_d |
| policyVersionId, calculationVersion | S.policy_version_id, S.calculation_version |
| signalMaxAgeSeconds | S.signal_max_age_seconds; JSON integer 30 по policy, не строка версии |
| commandReceiptId, createdAt | S.command_receipt_id, S.created_at |

Чтение не копирует заново параметры текущей policy/review. Нет raw/errors/allowedToStart/actorUserId/environment. Первая revision копирует проверенные значения review при START; карта не разрешает редактирование активных настроек. Обязательный источник не заменяется default B=200 или policy-константой.

## 9. FinancialSnapshot

N=`session_snapshots`; **И**, выбранный через `paper_sessions.current_snapshot_version` своей session/environment. Все ключи обязательны, null нет; current выбор **Т**, сохранённые величины не пересчитываются.

| Все поля financialSnapshot | Источник |
| --- | --- |
| snapshotId, sessionId, settingsRevisionId | N.id, N.session_id, N.settings_revision_id |
| recordSchemaVersion, snapshotVersion | N.record_schema_version, N.version |
| sessionVersion, ledgerSequence | N.session_version, N.ledger_sequence |
| projectionCalculationVersion | N.projection_calculation_version |
| lifecycle, controlState, contentState | N.lifecycle, N.control_state, N.content_state |
| dataOrigin, coverageState, unit | N.data_origin, N.coverage_state, N.unit |
| initialFunding.n, initialFunding.d | N.initial_funding_n, N.initial_funding_d |
| free.n, free.d | N.free_n, N.free_d |
| reserved.n, reserved.d | N.reserved_n, N.reserved_d |
| positionCost.n, positionCost.d | N.position_cost_n, N.position_cost_d |
| positionValue.n, positionValue.d | N.position_value_n, N.position_value_d |
| equity.n, equity.d | N.equity_n, N.equity_d |
| tradingResult.n, tradingResult.d | N.trading_result_n, N.trading_result_d |
| tradeCount, positionCount, orderCount | N.trade_count, N.position_count, N.order_count → Counter |
| asOf, createdAt | N.as_of, N.created_at |

В первом EMPTY initialFunding/free/equity=B; остальные денежные поля 0/1, счётчики "0", состояния active/copying_not_connected/EMPTY/synthetic/no_trade_data/virtual_USD. Это требования к сохранённым данным, **не значения для подстановки при отсутствии строки**. InitialFunding поясняет источник, не повторное зачисление. Чтение не пересчитывает ledger, не повышает version/asOf и не освобождает слот. Будущий signed tradingResult не расширяет первый срез. Проверка допустимого формата не доказывает отсутствие всякой правдоподобной порчи; границы I15/M03 и независимой сверки сохраняются.

## 10. Summary

P=`paper_sessions`, N — выбранный текущий snapshot из §9, TR=`trader_revisions` по **P.trader_revision_id** со всеми scope-связями. Summary — проекция **Т** согласованного состояния и **И** источников запуска, без собственного recordSchemaVersion.

| Все поля summary | Источник |
| --- | --- |
| sessionId, mode | P.id, P.mode |
| venueId, catalogSourceId, traderId, traderRevisionId | P.venue_id, P.catalog_source_id, P.trader_id, P.trader_revision_id |
| traderDisplayName | TR.displayed_name именно сохранённой revision; не traders.current_revision_id и не текущая карточка |
| dataOrigin | P.data_origin, согласованное с N.data_origin и источником |
| lifecycle, controlState | P.lifecycle, P.control_state, совпадающие с N.lifecycle/N.control_state |
| contentState, coverageState | N.content_state, N.coverage_state; в P этих колонок нет |
| sessionVersion | P.version, равная N.session_version для текущего снимка |
| snapshotVersion, settingsRevisionId, asOf | N.version, N.settings_revision_id, N.as_of |
| startedAt, evaluationDeadlineAt | P.started_at, P.evaluation_deadline_at |
| ianaTimezone | P.iana_timezone |
| deadlineCalculationVersion, timezoneDatabaseVersion | P.deadline_calculation_version, P.timezone_database_version |
| createdAt, updatedAt | P.created_at, P.updated_at |

Null нет. N.settings_revision_id совпадает с P.current_settings_revision_id; версии/общие состояния summary и разрешённого financialSnapshot совпадают. Для summary нужны её источники, даже если финансовая группа закрыта; внутреннее чтение для проверки не разрешает выдать закрытые поля. Историческая revision трейдера обязательна; при её повреждении не брать новое displayName. Срок уже сохранён по правилу 14 календарных дней/закреплённой зоны/tzdb; чтение, поездка или новая tzdb не пересчитывают срок и не завершают session.

## 11. Оболочки Q04/Q06 и доступные группы

| Поле / вариант | Источник и граница |
| --- | --- |
| Q04.session | Вся тройка summary/settings/financialSnapshot §§8–10 одного состояния; нет частичного успеха |
| Q06.session.summary | Обязательная полная summary после разрешения session.summary; без неё весь ответ запрещён |
| Q06.session.settings | Полная settings при разрешении session.settings; иначе ключ отсутствует |
| Q06.session.financialSnapshot | Полный snapshot при разрешении session.financial_snapshot; иначе ключ отсутствует |
| Q06.session.userContext.userId | P.user_id при разрешении user.minimal_context; весь userContext отсутствует при запрете. Не actor staff ID, не email/роль |
| Q06.restrictedGroups | **В/П** из текущего разрешения четырёх групп; только закрытые необязательные группы, в порядке session.settings, session.financial_snapshot, user.minimal_context, без повторов |
| nextAction, nextActionParams | **П** по §13; у административного ответа нет автоматического пользовательского перехода |

Корень Q04 ровно session/nextAction/nextActionParams; Q06 дополнительно restrictedGroups. Права вычисляются по действующим полным grants/назначениям/login/principal/среде/paper/venue/срокам, а не по роли в UI, старому audit или наличию строки. Владелец 1 и владелец 2 равноправны. Разрешённая группа полна и не перечислена в restrictedGroups; закрытая отсутствует и перечислена. Ошибка чтения/audit не «закрытая группа»; обнаруженная порча обязательного источника закрывает всё чтение.

Для существующей session Q06 сохраняет до выдачи `audit_events` со своим request_id/session_id/snapshot_version и достаточные `audit_authorizations` по фактически выданным группам. Выбор evidence и состав grant уже определены физическим блоком 4 §4; в API они не выгружаются. RestrictedGroups не сохраняется в snapshot/receipt; audit evidence не заменяет текущий допуск. Новая HTTP-передача — новый audit, внутренние попытки одной передачи не меняют requestId. Потеря ответа не отменяет audit, аудит не доказывает доставку.

Current Q04: достоверно нет строки своего paper slot либо его current_session_id=NULL → session=null, после полного доступа/чтения. Заполненный pointer на отсутствующую/чужую/повреждённую session — ошибка, не отсутствие. Старую session вместо current не выбирать. By-ID missing/hidden → одинаковый404, не200/null. Нет искусственного snapshot или записи слота при чтении.

Current Q06 без session: внешний 200/session=null/restrictedGroups=[] принят, но **право раскрытия target user и физическая форма обязательного audit открыты в DB-API-09**. [] здесь не означает всех прав. Эта карта не выбирает новое событие, nullable-ссылки или фиктивный snapshot. По старому audit-контракту эту ветку нельзя объявить реализуемой без дополнения.

## 12. Claim и Q01

Claim HTTP200: корень claim/nextAction/nextActionParams. L=`draft_claim_receipts`; шесть полей — **И**, при разрешённом повторе из той же записи, не текущая реконструкция.

| Все поля claim | Источник |
| --- | --- |
| claimReceiptId | L.id |
| draftId | L.draft_id |
| previousOwnershipId | L.previous_ownership_id |
| claimedOwnershipId | L.claimed_ownership_id |
| actorUserId | L.actor_user_id |
| completedAt | L.completed_at |

Обе ownership принадлежат одному draft и различаются; получатель доверенно установлен, не передан body. Нет новой ownership/времени на replay, raw/version/fieldErrors в claim нет. Успех после целой атомарной передачи; error без claim, unknown не успех/Q05. После передачи Q03 показывает текущий ввод, затем требуется новый user C05; гостевой review не переписывается. UUID результата не заменяют proof, защищённый recovery H01 остаётся зависимостью.

| Все поля Q01 | Источник / вид |
| --- | --- |
| authenticated | **В/П** true только после доказанного полного действующего user-входа; не колонка users/auth_sessions и не признак наличия paper session |
| user.userId | **Т** `users.id`, связанный с подтверждённым user login/identity своей среды |
| user.locale | **Т** `users.locale`, не язык браузера или draft |
| nextAction, nextActionParams | **П** текущая безопасная навигация |

Корень ровно authenticated/user/nextAction/nextActionParams; user ровно userId/locale. auth_sessions.user_id/realm/identity/assurance/срок/отзыв и текущий статус пользователя участвуют в проверке вместе с доверенным Auth-adapter, но не выдаются как новые поля. Pending MFA не полный вход; нет/expired/revoked —401, техническая недоступность не доказанный logout. Нет user=null при200, staff-ролей, баланса, cookies/tokens. Q01 не создаёт draft/session/command receipt; по принятому Auth-дополнению §7 первый успешный Q01 надёжно закрывает cookie-recovery-window в Auth. Этот служебный эффект не foreground и не продлевает вход; механизм фиксации ещё BA-G06. Auth/logout не получают обычный CommandReceipt из-за этой карты.

## 13. Текущая диагностика и навигация

### 13.1. Заголовки

| Поле | Источник и сохранение |
| --- | --- |
| X-Request-Id | **П** новый серверный UUID каждой HTTP-передачи, включая ошибку/204. Не доверять клиентскому значению; не поле immutable receipt/review. Где принят audit, сохраняется как `audit_events.request_id` конкретного события; это не новый command key |
| X-Correlation-Id | **П** необязательный валидный входной UUID v4: 36 ASCII, lowercase с дефисами, без trim/смены регистра/списков. Валидный возвращается заголовком; отсутствующий не создаётся. Неверный →400 INVALID_REQUEST до предметной операции, без копирования исходного невалидного значения. Нет новой DB-колонки/unique/fingerprint |
| Cache-Control | **П** no-store; не сохранённое поле предметного результата |

RequestId и correlationId не дублируются внутри receipt/review. Разрыв без ответа не даёт вымышленного прикладного JSON. Смена аккаунта/realm/environment начинает новую диагностическую цепочку, но не переносит исходные командные ключи.

### 13.2. nextActionParams

nextAction — разрешённое значение реестра либо null; nextActionParams всегда закрытый объект. Все поля ниже **П**: ссылки из существующих данных допускаются лишь после актуальной проверки, snapshot/receipt/review их не хранят. Отдельная таблица навигации не вводится.

| nextAction | Ровно допустимые параметры / источник |
| --- | --- |
| null | {} |
| authenticate | {} |
| complete_totp, enroll_totp | Обязательный authContextId из защищённого H01-контекста; не login/user/claim ID и не proof; точный механизм отдельно |
| select_trader | Необязательные draftId и venueId только при известных допустимых целях; draft/venues своей среды, не произвольный последний draft |
| continue_setup, review_setup | Обязательный draftId допустимого текущего `setup_drafts.id`; старый receipt сам по себе не разрешает этот переход |
| recover_setup | Необязательный draftId только если известен и доступен |
| view_session, view_summary | Обязательный sessionId разрешённой `paper_sessions.id`; источник может быть result_session_id, current pointer или допустимая related_session_id, но право проверяется сейчас |
| resolve_command | Обязательный commandRef по §4 либо проверенный исходный locator §3.3 при unknown; C04/C06 только, без переноса guest scope |
| retry_later | Необязательный retryAt — достоверный серверный момент допустимого повтора типа Timestamp; если неизвестен, ключ отсутствует. Не угадывать из created_at/TTL/таймаута |

Необязательный параметр отсутствует, а не null. Не включать секреты, OTP, raw/settings, environment или права. Если безопасная цель не установлена — null/{}. Для Q06 использовать только допустимую административную навигацию; если её нет, null. Исторический related/result ID может существовать без текущего права на переход. Retry_later/resolve_command не разрешают новый ключ или автоматический start. Эта карта указывает источники параметров, не придумывает новую таблицу выбора действий по состояниям поверх T07/H01.

## 14. Граница завершения и следующие документальные шаги

**Согласовано ранее:** внешние формы API, C04/last_input_receipt_id, карта ошибок/Q03, строгая полнота C06, claim и права существующей Q06-session. **Отражено этим блоком:** точное происхождение всех полей DB-API-01–08/11, преобразования, закрытые варианты, неизменяемая история против текущей выдачи. **Проверено испытаниями: ничего.** Само соответствие Markdown-колонкам не доказывает работающие codecs, Auth, атомарность или безопасное чтение.

Следующие блоки по отдельному поручению: точечно перенести эту карту в затронутые физические спецификации и проверки (в том числе точную форму warnings вместо исторического «пустая структура»); затем дополнить документальные примеры выдачи и R/A/F/E-связи. Это не повторный выбор API-форм или ошибок. В этой задаче физические таблицы/условия, исходные матрицы, примеры и сценарии не переписываются и не объявляются испытанными.

Открытые зависимости: DB-API-09/10; H01 protected transport/recovery/независимые ранние guards; совместимые компоненты/кодеки/привилегии и mapping временного guard claim; реальные lifecycle-формы M02, инструменты/права M03, формат/место/права evidence M05, компоненты времени/backup/restore H06. M01 не закрывается целиком; M04 первого стенда по-прежнему без архива/cleanup. При обнаружении реально сохранённых иных форматов нужно отдельное решение совместимости, не ремонт на чтении и не молчаливое объявление v1 совместимым.

Основания будущих проверок остаются в [реестре R001–R071](database-constraint-register.md), [матрице A01–A112](database-integrity-matrix.md), [сбоях F01–F24](database-fault-reconciliation.md) и [плане доказательств E01–E17](database-evidence-plan.md). Они не пройдены этим документом. Ни новые A-критерии, ни код/SQL/миграции/стенд/исполняемые тесты не создавались.

## 15. Отражение в физических спецификациях — блок 2

02.11.2026 · На baseline main 6a4e2fe04f8b4bb11dcbe09812724ffec84cb0c0 (PR №185) карта перенесена в действующие физические документы. Предыдущее указание §14 «следующий блок — физические спецификации» выполнено документально, не реализацией.

| Передача | Место отражения |
| --- | --- |
| DB-API-01/05/08 | [Блок 1 §11](database-physical-design.md): форма ввода, current ownership/источник Q03, Q01; [блок 2 §12](database-physical-catalog-review.md): C05 zone/version; [блок 3 §2/12](database-physical-session-ledger.md): expectedSlot; [блок 4 §12](database-physical-operations-access.md): claim/ключи |
| DB-API-04 | [Блок 2 §8/12](database-physical-catalog-review.md): точная закрытая форма warnings в строке колонки, полнота review/проценты/слот, предел/неизменяемость/повреждение |
| DB-API-06/07 | [Блок 3 §12](database-physical-session-ledger.md): settings/snapshot/summary, историческое имя/версии/числа; [блок 4 §12](database-physical-operations-access.md): целые разрешённые группы и обязательный аудит существующей session |
| DB-API-02/03/11 | [Блок 4 §2/12](database-physical-operations-access.md): точный locator, исходный receipt/HTTP, technical envelope и текущие diagnostics/navigation без новых колонок |

Состав колонок/PK/FK/unique и атомарные наборы не изменены; предупреждения уточняют существующий warnings JSON по принятой форме. Карта ошибок и C04 остаются прежними, raw loss-названия колонок сохраняются. [Реестр §13](database-constraint-register.md) указывает применимые R без новых номеров. DB-API-09/10 и H01/компоненты/codec/привилегии/guard mapping/M02–M03/M05/H06 остаются. Следующий отдельный документальный блок — примеры выдачи с R/A/F/E-связями; ни одно испытание не проведено.

## 16. Документальные примеры выдачи — блок 3

02.11.2026 · [AP01–AP16](database-api-response-examples.md) конкретизируют эту карту на прежних синтетических данных. Полные поля review/Q03/settings/snapshot/summary, варианты receipt/claim/Q01/Q04/Q06 и ошибки связаны с сохранёнными источниками и дельтами. Числа/версии/времена приведены явно; неизвестные реальные UUID/guards/tzdb обозначены как будущие параметры набора, не как выполненная подготовка.

Исторический результат отделён от текущего состояния и навигации; denied/empty/corrupt/unknown не смешиваются. Матрица AP→R/A/F/E находится в §12 примеров. Формы API согласованы ранее, примеры отражены в документах; испытания не выполнялись. DB-API-09/10 не закрываются и не получают вымышленных источников; C04, карта ошибок, строгий C06 и §§1–15 сохранены.

## 17. Право отсутствия Q06 принято отдельно от хранения

02.11.2026 · [DB-API-09 §7](database-q06-absence-design.md): принято отдельное read/ADM-03/user.current_session_absence/paper/all право; one/старые grants не заменяют его. Внешний current-ответ200/session=null/restrictedGroups=[] прежний, новой группы/поля нет; существующая session проходит прежние проверки. Отсутствующий/скрытый target user — одинаковый404. Новые audit-поля/тип/evidence пока предложение §8, не выбранный источник; DB-API-09 остаётся открытым по физической полноте и согласованности.

## 18. Принятое хранение факта отсутствия Q06

02.11.2026 · [DB-API-09 блок 2 §8–9](database-q06-absence-design.md) принят.200/session=null/restrictedGroups=[] остаётся прежним внешним ответом. Источник разрешения — новый целый grant блока 1; доказательство разрешённой подготовки отсутствия — admin_session.current_absence_authorized с target_user_id/slot_observation/observed_slot_generation и одним evidence. Эти колонки внутренние, в API не добавляются. Event не служит источником текущего отсутствия при повторном HTTP: данные и права читаются заново. Поля старого Q06 и его реальные session/snapshot ссылки сохранены. Конкуренция/протокол наблюдения остаются блоком 3; AP16 ещё не испытан.

## 19. Итог DB-API-09: принятый смысл current-ответа

02.11.2026 · [Все три блока приняты](database-q06-absence-design.md).200/session=null/restrictedGroups=[] разрешён только после текущего all-grant допуска и подтверждённого нового audit/evidence одной Serializable-операции. Новой API-группы/asOf/snapshot нет; safe navigation при отсутствии цели null/{}. Unknown/порча/отказ аудита не null200.

Отсутствие относится к согласованному снимку: при перекрывающемся C06 оно может предшествовать START даже с более поздним commit audit. Следующая новая транзакция после завершённого START выбирает session и прежние групповые права. Не возвращать старый audit как current-состояние, не использовать его occurred_at как timestamp commit/гарантию отсутствия до доставки.5s/одна попытка Q06 сохраняются; карта отражена, codecs/поведение не испытаны.

## 20. Q02: принятые источники, видимость и граница страницы

02.11.2026 · [Точная карта 17 полей Trader, DB-API-10 §2](database-q02-catalog-design.md) теперь связана с принятыми блоками1–2 (§§6–8). catalogVersion ← source.version, traderControlVersion ← trader.version, paperControlVersion ← paper_controls.version; displayed_name/source_ref/observed_at принадлежат current revision, historical catalogVersionAtCreation не заменяет текущий guard.

read_visible двух таблиц — внутренние колонки, не новые API-поля; startAvailability по-прежнему ровно available/capabilityReasonCode с прежним приоритетом. Полная карта применяется к trader карточки и каждому items. Query Q02 имеет собственные venueCode/limit/cursor из API §14 и не ограничивается общим правилом query для Q01/Q03–Q06.

Единый снимок/полный fingerprint не заменяет текущий H01. Подлинность/формат cursor — следующий блок, версия области доступа — явная зависимость. HTTP409 чтения не сохраняет бизнес-отказ; unknown503 не разрешает автоматический новый обход. DB-API-10 ещё открыт; испытания не выполнялись.

## 21. Принятый cursor Q02 и источники его полей

02.11.2026 · [Точный блок3 §§9–10/12–13](database-q02-catalog-design.md) принят. Внешний API по-прежнему передаёт одну непрозрачную base64url-строку cursor/nextCursor; восемь plaintext-полей не добавляются в корень API или таблицы БД.

| Внутреннее поле | Принятый источник / проверка |
| --- | --- |
| requestSchemaVersion | v1, фиксированный поддерживаемый профиль |
| environmentBinding | SHA-256/JCS доверенной серверной environment с доменом по Q02 §9.2 |
| readerBinding | SHA-256/JCS защищённых realm/readContextId H01 и environmentBinding; не клиентские полномочия |
| venueId, venueCode | Разрешённая venues.id/code, соответствие запросу |
| limit | Эффективное принятое значение1–50; default20, то же при продолжении |
| lastTraderId | Последний фактически выданный traders.id страницы, не дополнительный элемент проверки продолжения |
| catalogFingerprint | SHA-256/JCS полного Manifest одного снимка, включая scopeRevision, P/S/T/current R; отдельной колонки нет |

Точные bytes/канонизация/AEAD/keys — Q02 §9; номер codec не новый runtime-код реестра. ScopeRevision меняет fingerprint, а не readerBinding. Подлинный cursor не даёт доступа; сохранённый допуск и иное достоверное состояние →409, неподходящий cursor→400, unknown→503, утрата доступа→access/hidden. Исторические причины C04/C06/Q03 и requestId/nextAction не смешиваются с cursor. Испытания/компоненты/H01 ещё не выполнены.

## 22. Уточнён принятый источник readerBinding Q02

02.11.2026 · [Q02 §§14–15](database-q02-catalog-design.md): readContextId — users.id для user и постоянный UUID защищённого Auth guest context для guest, в канонической строчной форме. ReaderBinding вычисляется прежним SHA-256/JCS массивом §9.2 с realm/environment; payload по-прежнему имеет8 полей, внешних параметров/полей API не добавлено.

Login ID и версия разрешений не источник readContextId. Новый полный login того же user сам по себе не сбрасывает cursor; текущий допуск/ключ/Manifest всё равно обязательны. ScopeRevision меняет fingerprint, не readerBinding. Guest bootstrap/proof/источник версии и согласованность — QH02–QH05; не выводятся из draft/receipt ID. C04/error map сохранены, QID01–QID08 не выполнялись.

## 23. Принятый источник scopeRevision из локального scope

02.11.2026 · [Q02 §§16–17](database-q02-catalog-design.md): Manifest.scopeRevision вычисляется как q02-read-scope-v1:<scopeId>:<version> из q02_read_scopes.id/version. Дублируемого столбца нет. Manifest.sources берётся ровно из q02_read_scope_sources выбранной разрешённой области, с FK своей venue/source, до visibility-фильтра.

Восемь полей cursor/17 полей Trader/JCS/SHA-256/AEAD и внешний API не меняются. Scope ID не новый клиентский query/body-параметр. ReaderBinding использует прежний постоянный user/guest ID, не scope version. Смена разрешённой области/состава устанавливается через прежний fingerprint409, access/unknown остаются отдельными. H01 защищённо выбирает readScopeId; этот selector и restore ещё зависимы, QSC не выполнялись.

## 24. Уточнение Auth/claim после PR №199

02.11.2026 · [Auth-контракт §§7–11](backend-auth-contracts-addendum.md), [ответ БД](database-auth-handoff-review.md). Q01 JSON прежний; X-Shadow-Login-Id в успешном ответе берётся из проверенного auth_sessions.id/доверенного Auth-соответствия, не echo клиентского заголовка. Факт закрытия cookie-window — Auth, не users/auth_sessions.last_user_activity_at и не поле неизменяемого CommandReceipt. Его физический источник/атомарность пока не выбраны.

Claim HTTP200 по-прежнему шесть полей из draft_claim_receipts. GET /api/demo/drafts/:draftId/claim может вернуть202/status=unresolved с observedAt и null/{} navigation, без claim: нужен текущий полный user и доказанная серверная область исходного consent; само отсутствие receipt не даёт допуска. Принятый read-only recovery допускает утраченную/истёкшую claim-cookie по серверной связи исходного context/user/environment/draft. Она не даёт права исполнить и не меняет отдельный GET контекста. Источник этой связи/барьер отсутствия in-flight ещё DB-AUTH-06/07, не новая выбранная колонка.

Реестр теперь v5: три новых Auth409 не добавляют Auth-типы в command_receipts/audit_events и не меняют карту ошибок C04/Q03. Auth-контексты/operations/cookie/continuation не переиспользуют обычный Q05. C04/last_input_receipt_id/строгий C06 сохранены; DA01–DA12 не выполнялись.
