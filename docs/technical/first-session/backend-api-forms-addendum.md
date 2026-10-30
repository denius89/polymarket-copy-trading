# Дополнение бэкенда: принятые формы запросов и ответов API

30.10.2026 · **Принято владельцем последовательно в чате бэкенда; сведено по прямому поручению.** Baseline main f72f1e81c31bae95952cc82ee59650b9f304e98f (после PR №180). Это документальный контракт, не OpenAPI, исполняемые схемы, код, SQL, миграции или результаты DB/API/Auth-испытаний.

Дополняет [T01–T17](backend-contracts.md) и [ADR-0065](../../decisions/0065_first_session_backend_contract.md). Использует принятую [карту ошибок API ↔ БД](database-error-field-map.md), все четыре физических блока и [передачу БД](database-backend-handoff.md). Продуктовые числа, C04/last_input_receipt_id, строгий C06, приоритеты причин и правила повторов сохраняются.

Внешний ответ Q06 при отсутствии текущей сессии принят, но **его права и обязательный аудит ещё не обеспечены согласованным физическим контрактом**. Это открытый стык DB-API-09 (§16), не разрешение пропустить аудит, создать фиктивную session или ослабить прежние связи.

## 1. Типы, обязательность и область

Все объекты ниже закрытые: перечисленные поля обязательны, кроме явно названных необязательных; неизвестные поля запрещены. Отсутствие ключа, null, пустая строка, [] и {} различаются. Разделение строк таблицы запятыми означает отдельные поля, не новый вложенный объект.

| Тип / правило | Точная форма |
| --- | --- |
| UUID | Внутренний UUID v4 строкой; clientCommandId создаётся клиентом до первой передачи намерения |
| PositiveVersion | Положительная целочисленная десятичная строка, без ведущих нулей, в пределах положительного bigint |
| Counter | Неотрицательная целочисленная строка в пределах bigint; ноль только "0" |
| Money | Объект ровно n/d: канонические целочисленные строки без знака/ведущих нулей, кроме нуля; d>0, дробь сокращена, ноль 0/1; до 64 цифр на компонент. Единица первого сценария virtual_USD |
| Percent | Нормализованная строка в процентных пунктах, точка и ровно две цифры после неё, без знака/ведущих нулей целой части, кроме нуля |
| Timestamp | UTC с Z и ровно тремя знаками миллисекунд |
| Raw | Исходная строка до 64 Unicode code points либо null; без trim/NFC/числового переписывания |
| Timezone | Поддерживаемое имя IANA либо явно разрешённый null; без автоматической замены на UTC/зону устройства |
| Запросы C04/C05/C06/claim | Несжатый UTF-8 JSON ≤65 536 исходных байт, глубина ≤8 с корнем 1; без дублей ключей, unknown fields и coercion по T13 |
| Чтения | GET без тела; неизвестные, повторные и отсутствующие обязательные query-параметры — INVALID_REQUEST/400 |

requestSchemaVersion=v1 — версия запроса; recordSchemaVersion=v1 — отдельный формат сохранённого review/settings/snapshot/receipt. Draft/trader/claim не получают вымышленную колонку record_schema_version. API-проекция не обязана выдавать внутренние environment/ключи/доказательства.

Команда выражает намерение; actor, realm, environment, права, пригодность policy и источников устанавливает сервер. Идентификатор в пути/теле/cursor не даёт доступа. Владелец 1 и владелец 2 — отдельные равноправные staff principals.

## 2. Диагностика и навигация

### 2.1. Заголовки

X-Request-Id — новый серверный UUID каждой HTTP-передачи, включая ошибку и 204; не принимается как доверенный ID от клиента, не меняет исторический результат.

Необязательный X-Correlation-Id — UUID v4, ровно 36 ASCII-символов в канонической строчной форме с дефисами. Только заголовок, не body/query. Нет trim, смены регистра, снятия скобок/префикса. Пустое/невалидное значение, несколько заголовков или comma-list — 400 INVALID_REQUEST до предметной операции, с собственным X-Request-Id; исходное невалидное значение не копируется в диагностику целиком.

Валидный correlationId возвращается заголовком; при отсутствии не генерируется и не возвращается. Может объединять связанные передачи, в том числе повторы; изменение correlationId не меняет fingerprint/ключ. При смене аккаунта/realm/environment диагностическая цепочка новая, исходные командные ключи прежние. Нет PII, полномочия, DB-уникальности или новой колонки receipt.

Ответы используют Cache-Control: no-store. Заголовки диагностики не дублируются внутри immutable receipt/review. Поведение gateway/прокси при разрыве без прикладного ответа остаётся компонентным контрактом: клиент не выдумывает полученный JSON.

### 2.2. nextActionParams

nextAction — одно значение принятого реестра либо null. nextActionParams всегда объект; при null строго {}. Необязательное поле отсутствует, не передаётся null. Только указанные ключи своего варианта:

| nextAction | Поля nextActionParams |
| --- | --- |
| authenticate | Пустой объект |
| complete_totp, enroll_totp | Обязательный непрозрачный authContextId; ID сам не proof, точный защищённый H01-протокол отдельно |
| select_trader | Необязательные draftId и venueId, только если известны и разрешены |
| continue_setup, review_setup | Обязательный draftId |
| recover_setup | Необязательный draftId |
| view_session, view_summary | Обязательный sessionId |
| resolve_command | Обязательный commandRef |
| retry_later | Необязательный достоверный серверный retryAt типа Timestamp; неизвестный момент не угадывается |

Resource IDs — UUID. commandRef — закрытый объект ровно actorRealm (user/guest), actorId (исходный постоянный user/guest-context UUID), commandType (C04/C06), clientCommandId (исходный UUID). C06/guest недопустим. Среда определяется сервером. После claim прежний guest commandRef остаётся guest; доступ проверяется по конкретной цепочке, ключ не переносится.

Навигация относится к текущему разрешённому контексту, не переписывает receipt/review. Нет секретов, OTP, cookie, настроек или клиентских прав в params. Draft ID требует актуального чтения. В Q06 нельзя механически использовать пользовательский переход; если безопасного административного перехода нет, nextAction=null. Автоматического start нет.

## 3. Точные запросы

### 3.1. C04 — сохранение

Create: POST /api/demo/drafts. Update: PATCH /api/demo/drafts/:draftId (UUID только в пути). Несмотря на PATCH, передаётся **полная форма**, не набор частичных изменений.

| Обязательное поле обоих вариантов | Тип |
| --- | --- |
| requestSchemaVersion | v1 |
| clientCommandId | UUID |
| locale | ru/en |
| step | select_trader/configure/review |
| entryContext | catalog/trader_details/session_summary либо null |
| venueId, traderId | UUID либо null; trader требует свою venue |
| selectedMode | fixed/percent либо null |
| rawBudget, rawFixedAmount, rawCopyPercent, rawMarketLimitPercent, rawDailyBuyLimitPercent | Raw, все пять ключей присутствуют |
| proposedTimezone | Timezone |

Update дополнительно требует expectedDraftVersion типа PositiveVersion. Create этого поля не принимает, draftId назначает сервер. Операция create/update определяется маршрутом и входит в fingerprint; body.operation отсутствует. Нет userId/guest proof/environment/готовых settings/permissions в body. Step/entryContext не свидетельствуют о проверке.

Оба raw размера сохраняются, но проверяется только выбранный активный режим. Точный replay сохраняет маршрут/ключ/полный payload; create replay не превращается в update. Следующая правка после подтверждённого результата — новое намерение с новым ключом и актуальной версией; unknown сначала разрешается по исходному ключу.

### 3.2. C05 — проверка

POST /api/demo/validate. Body ровно: requestSchemaVersion=v1, draftId UUID, expectedDraftVersion PositiveVersion, proposedTimezone Timezone. Все четыре поля обязательны.

proposedTimezone совпадает с сохранённой зоной указанной версии draft; изменение сначала сохраняется C04. При той же версии и другой зоне — INVALID_REQUEST, review не создаётся. Устаревшая версия — VERSION_CONFLICT, без проверки другой текущей версии. null зоны может дать отрицательный review с TIMEZONE_REQUIRED по принятому приоритету. Нет clientCommandId, повторных настроек/slot/policy/owner в body. C05 не сохраняет изменения формы и не восстанавливается через Q05.

### 3.3. C06 — запуск

POST /api/sessions. Body ровно пять обязательных полей: requestSchemaVersion=v1, clientCommandId UUID, reviewId UUID конкретного полученного и показанного review, expectedDraftVersion PositiveVersion, expectedSlot.

expectedSlot — закрытый вариант: state=absent без generation либо state=present с обязательной generation PositiveVersion. generation=null/0 не кодирует отсутствие; not_applicable в C06 запрещён. Ожидания берутся из показанного review и не обновляются автоматически на повторе. Нет settings/budget/trader/balances/userId/permissions в body; проверенные параметры читает сервер из review. clientCommandId только в body, дополнительного idempotency-заголовка нет. При unknown все пять полей прежние; новый review не подставляется под старый ключ.

### 3.4. Claim

POST /api/demo/drafts/:draftId/claim. UUID только в пути; body ровно requestSchemaVersion=v1. Нет clientCommandId, expectedDraftVersion, owner/user ID, настроек, reviewId или guest-секрета в body. Полный user-вход и первичный guest proof — через защищённый H01-контекст. Dedup уже задаёт собственный claim receipt/уникальность draft; точный Auth transport/recovery не закрывается этой формой.

### 3.5. Q05 — исходный результат

GET /api/commands/:clientCommandId. Путь содержит исходный UUID намерения, не receiptId. Обязательные query: requestSchemaVersion=v1, commandType=C04/C06, actorRealm=user/guest, actorId=UUID исходного постоянного актора. C06/guest — INVALID_REQUEST.

Нет тела, environment, дубля path ID в query или иных параметров. Locator не заменяет актуальную авторизацию. Потерянный guest create восстанавливается без draftId через исходный доказанный контекст; после claim — только через подтверждённую цепочку конкретного результата. Pending допустим лишь в разрешённой области поиска; отсутствие доступа/сбой не pending. C05/Auth/claim исключены из Q05.

### 3.6. Q01, Q03, Q04 и Q06

| Чтение | Маршрут |
| --- | --- |
| Q01 | GET /api/me |
| Q03 | GET /api/demo/drafts/:draftId |
| Q04 current | GET /api/sessions/current |
| Q04 by ID | GET /api/sessions/:sessionId |
| Q06 by ID | GET /api/admin/sessions/:sessionId |
| Q06 current | GET /api/admin/users/:userId/sessions/current |

Path IDs — UUID. Query у каждого ровно requestSchemaVersion=v1; тела нет. Не принимаются expectedDraftVersion/snapshotVersion, staffId/assignmentId/role/environment, projections, фильтры/история/экспорт или дубли path ID. Q01/Q04 требуют полный пользовательский вход, Q03 — допустимое текущее владение, Q06 — отдельный полный staff-вход и действующие назначения. userId пути Q06 — цель просмотра, не actor.

Current выбирается по указателю пользователя, не по последней дате произвольной сессии. Q03 может показать свой expired/used draft, не продлевая TTL и не открывая запись. Отсутствующий/скрытый конкретный ресурс — одинаковый 404. Для Q06 current без session действует открытый стык §16.

## 4. Q05, receipt и прямые ответы C04/C06

### 4.1. Ответ Q05

Корень: commandRef (§2), status, receipt, nextAction, nextActionParams; все обязательны.

| HTTP | status | receipt |
| --- | --- | --- |
| 200 | committed | Полный сохранённый succeeded |
| 200 | rejected | Полный сохранённый rejected |
| 202 | pending | Строго null |

Pending — окончательный исход пока не установлен, не утверждение об исполнении/отмене. Недоступное хранилище/повреждённые обязательные details/неподдерживаемый результат — 503, не pending. Старый результат и текущая навигация разделены. Правила бюджета/опроса T06 сохраняются.

### 4.2. Общая часть receipt

| Обязательное поле | Тип / правило |
| --- | --- |
| receiptId | UUID исходной записи |
| recordSchemaVersion | v1 |
| commandType | C04/C06, совпадает с commandRef |
| outcome | succeeded/rejected |
| createdAt | Исходный Timestamp создания receipt, не время чтения и не переименованный commit timestamp |
| reasonCode | null у succeeded; код реестра у rejected |
| reasonDetails | [] у succeeded; непустой массив ReasonDetail у rejected, первый code равен reasonCode |
| result | Закрытый объект соответствующего успеха либо null у rejected |

ReasonDetail и FieldError — строго [карта ошибок](database-error-field-map.md), включая закрытые params/порядок/единицы/лимиты. Succeeded C04 дополнительно имеет обязательный fieldErrors **на уровне receipt рядом с result**; [] допустим. Rejected C04 и любые C06 поля fieldErrors не имеют.

| Вариант result | Ровно эти обязательные поля |
| --- | --- |
| C04 succeeded | draftId UUID, ownershipId UUID исторического владения, draftVersion PositiveVersion, changeKind created/updated/unchanged, lastSavedAt Timestamp, expiresAt Timestamp |
| C06 succeeded | sessionId UUID, settingsRevisionId UUID, snapshotVersion PositiveVersion, sessionVersion PositiveVersion; исходный старт обе версии "1" |
| C04/C06 rejected | null; успешные result-поля отсутствуют |

У C04 нет session-result и наоборот. Своя блокирующая session rejected C06 не является result и не помещается в immutable reasons; разрешённая текущая ссылка — через навигацию. Нет environment/commandKeyId/hash/секретов/requestId/correlationId/прав внутри API receipt.

Прямое отображение: receiptId ← command_receipts.id; createdAt ← его created_at; recordSchemaVersion ← record_schema_version; result ← активная группа result_* core. reasonDetails ← details.reason_data.reasons у rejected либо [] из корректного {} у succeeded; fieldErrors ← details.response_data.fieldErrors только succeeded C04. Пропущенный обязательный источник не заменяется пустым значением.

### 4.3. Прямые ответы C04/C06

Корень ровно commandRef, receipt, nextAction, nextActionParams; receipt всегда объект. Исторический receipt совпадает с полученным через Q05; status-наблюдение в прямом ответе отсутствует. Result-поля не дублируются в корне.

C04 created201, updated/unchanged200; C06 succeeded201; сохранённый отказ — согласованный HTTP его причины. Exact replay возвращает исходный receipt и исходный статус, в том числе201. Q05 читает тот же rejected с200. Current requestId/навигация могут отличаться; байтового равенства всех ответов не обещается.

Ранний/технический отказ использует §5 без receipt. Неизвестный commit прямого C04/C06 — технический503, не успешный202 pending; затем Q05 по исходному ключу. COMMAND_OUTCOME_UNRESOLVED остаётся кодом наблюдения202 в реестре, не дополнительным полем закрытого ответа Q05 и не кодом прямого503.

## 5. Ошибка без сохранённого предметного результата

Корень ровно четыре обязательных поля:

| Поле | Форма |
| --- | --- |
| reasonCode | Один существующий код нужного контекста/HTTP; также принятый CATALOG_CHANGED для списка Q02 |
| reasonDetails | Ровно один элемент code/params; code=reasonCode, params={} |
| nextAction | Одно безопасное действие либо null |
| nextActionParams | Форма §2, при null — {} |

Нет receipt даже со значением null, result, fieldErrors, status, сырого ввода, текстов библиотек или внутренних причин. Это форма ранней/технической ошибки, не замена сохранённого rejected и не отрицательный review. Применяется к оговорённым C04/C05/C06/claim и Q01–Q06; точные защищённые Auth-ответы C01–C03/C07 ещё требуют H01.

| Ситуация | HTTP / код / действие |
| --- | --- |
| Структура/размер/media | 400 INVALID_REQUEST / 413 REQUEST_TOO_LARGE / 415 UNSUPPORTED_MEDIA_TYPE |
| Вход | 401 AUTH_REQUIRED/AUTH_EXPIRED/AUTH_REVOKED, authenticate если безопасно |
| Доступ/скрытый ресурс | 403 ACCESS_DENIED / 404 RESOURCE_NOT_FOUND без закрытых сведений |
| Другой payload старого key | 409 KEY_REUSE_CONFLICT, исходный receipt неизменен; новый ключ не автоматически |
| Частота | 429 RATE_LIMITED, retry_later; retryAt если безопасный момент установлен |
| C04/C06 unknown | 503 SERVICE_UNAVAILABLE; resolve_command с исходным доказанным доступным commandRef |
| Повреждённое/несовместимое обязательное данное | 503 RECORD_UNAVAILABLE, без частичной выдачи или pending |
| Изменение каталога между страницами | 409 CATALOG_CHANGED; §14 |

Если безопасное действие/область не установлены, nextAction=null. Ранний отказ текущей передачи не доказывает, что предыдущая передача того же намерения не выполнилась. Ни503, ни retry_later не разрешают автоматически новый ключ/новое исполнение. Разрыв без ответа не выдуманный JSON; остаётся локальная неопределённость и принятый recovery.

У C05 unknown нет resolve_command/Q05: явная новая проверка разрешена по T05. У claim свой протокол восстановления, не Q05 (§12). Приоритет нескольких независимых ранних transport/Auth-защит остаётся отдельной незавершённой спецификацией; этот конверт его не назначает.

## 6. C05: ответ и полный review

HTTP200 только для подтверждённого сохранённого review, в том числе отрицательного. Корень ровно review (объект), nextAction, nextActionParams. Ошибка допуска/исполнения/unknown — §5 без поля review; review=null/пустой объект не подставляются.

| Обязательные поля review | Тип / допустимый null |
| --- | --- |
| reviewId, draftId, ownershipId | UUID; историческая ownership при проверке |
| recordSchemaVersion | v1 |
| draftVersion | PositiveVersion |
| ownerKind | guest/user |
| ownerUserId | UUID у user, null у guest |
| venueId | UUID либо null при невыбранной площадке |
| catalogSourceId, traderId, traderRevisionId | Все три UUID одной revision/source/venue либо все null |
| catalogVersion, traderControlVersion | PositiveVersion вместе с группой трейдера, иначе оба null |
| policyVersionId, paperControlId | Обязательные UUID |
| paperControlVersion | PositiveVersion |
| selectedMode | fixed/percent/null |
| rawBudget, rawFixedAmount, rawCopyPercent, rawMarketLimitPercent, rawDailyBuyLimitPercent | Пять Raw |
| proposedTimezone | Timezone |
| normalizationValid | Boolean |
| budget, fixedAmount, effectiveMarketLimit, effectiveDailyBuyLimit | Money либо null по варианту нормализации |
| copyPercent, marketLimitPercent, dailyBuyLimitPercent | Percent либо null по варианту нормализации |
| expectedSlot | Закрытый объект наблюдения ниже |
| allowedToStart, requiresAuthentication | Boolean |
| primaryReasonCode | null при allowedToStart=true, иначе обязательный код |
| reasonDetails, fieldErrors | Оба массива по карте ошибок |
| warnings | Массив закрытых объектов ровно code/params |
| checkedAt, expiresAt, createdAt | Timestamp; expiry=checkedAt+10 минут |

normalizationValid=false → все семь нормализованных числовых полей null, allowedToStart=false. При true заполнены B/p/d/P/D и ровно действующий F либо q: fixedAmount при fixed, copyPercent при percent; неактивный нормализованный размер null. При mode=null полного числового набора нет. Валидные числа могут сопровождать отказ из-за входа/слота/допуска.

expectedSlot: guest — только state=not_applicable; user — state=absent без generation либо state=present с generation PositiveVersion. Неизвестное чтение слота не absent. Это отображение slot_observation/expected_slot_generation; существующий свободный слот всё равно present. В C06 передаётся user-вариант конкретного показанного review без автоматического обновления.

Guest всегда requiresAuthentication=true/allowedToStart=false; допустимый полный user — requiresAuthentication=false. Истёкший вход не превращается в гостя. При allowedToStart=true reasonDetails/fieldErrors пусты, primaryReasonCode=null. При false reasonDetails непустой с основной причиной первой; fieldErrors может быть пустым.

Warnings: только SYNTHETIC_DATA, COPYING_NOT_CONNECTED; params строго {}; без повторов, в указанном порядке, только применимые установленные предупреждения; отсутствие — []. Они не блокируют старт. Это принятая точная API-форма; отразить закрытую форму существующего warnings JSON и проверки в документах БД, без новой колонки.

reviewId ← setup_reviews.id, прочие обычные поля snake_case→camelCase. raw_loss_limit_percent→rawDailyBuyLimitPercent, loss_limit_percent→dailyBuyLimitPercent, effective_loss_limit_n/d→effectiveDailyBuyLimit; это лимит новых покупок, не stop-loss. reasonDetails/fieldErrors ← reason_details.reasons/fieldErrors. Environment внутренний. Не добавлять текущие navigation/diagnostics, не менять raw/guards/сроки при чтении. Missing/malformed обязательное — RECORD_UNAVAILABLE/503. Новый user C05 обязателен после claim; разрешённый review не запускает сессию.

## 7. Q03: текущий черновик

HTTP200: корень ровно draft, fieldErrors, fieldErrorsSource, nextAction, nextActionParams.

| Обязательные поля draft | Тип / правило |
| --- | --- |
| draftId, currentOwnershipId | UUID |
| draftVersion | PositiveVersion |
| ownerKind | guest/user текущей ownership |
| state | editable/expired/used |
| locale | ru/en |
| step | select_trader/configure/review |
| entryContext | catalog/trader_details/session_summary/null |
| venueId, traderId | UUID/null; trader требует свою venue |
| selectedMode | fixed/percent/null |
| rawBudget, rawFixedAmount, rawCopyPercent, rawMarketLimitPercent, rawDailyBuyLimitPercent | Пять Raw |
| proposedTimezone | Timezone |
| lastSavedAt, expiresAt, createdAt, updatedAt | Timestamp |
| usedAt, usedBySessionId | Оба null до использования, после — Timestamp/UUID одной созданной session |

draftId ← id; draftVersion ← version; currentOwnershipId и ownerKind — текущая ownership; остальные обычные поля snake_case→camelCase с rawDailyBuyLimitPercent исключением. Used приоритетнее expiry; иначе при serverNow≥expiresAt expired, затем editable. Editable не гарантирует успех будущего C04.

fieldErrors — исходные ошибки succeeded created/updated C04 через last_input_receipt_id. fieldErrorsSource ровно receiptId UUID и draftVersion PositiveVersion; версия совпадает с draft.draftVersion в согласованном чтении. Новый unchanged/C05/claim не меняет источник, новая policy не пересчитывает ошибки. После claim текущая ownership может быть user, источник — исторический guest receipt.

updatedAt служебной записи не заменяет draftVersion для C04 или lastSavedAt/expiresAt для TTL. Raw и неактивный размер возвращаются точно. Нет нормализованных settings/allowedToStart. Expired/used свой draft читается при текущем доступе, без продления/разрешения записи. Missing/hidden404; повреждённая обязательная цепочка503, не draft=null или выдуманные [].

## 8. Settings для Q04 и разрешённого Q06

| Обязательное поле | Тип |
| --- | --- |
| settingsRevisionId, sessionId | UUID |
| recordSchemaVersion | v1 |
| sequence | PositiveVersion, первая "1" |
| previousRevisionId | UUID предыдущей своей revision; null только первая |
| budget | Положительный Money |
| sizingMode | fixed/percent |
| fixedAmount | Money только fixed, иначе null |
| copyPercent | Percent только percent, иначе null |
| marketLimitPercent, dailyBuyLimitPercent | Percent |
| effectiveMarketLimit, effectiveDailyBuyLimit | Положительные Money |
| policyVersionId | UUID |
| calculationVersion | paper-settings-calculation-v1 первого сценария |
| signalMaxAgeSeconds | Целое JSON-число, 30 по policy; не пользовательский параметр |
| commandReceiptId | UUID создавшего результата |
| createdAt | Timestamp |

settingsRevisionId ← settings_revisions.id; monetary pairs и dailyBuyLimit отображаются как в §6. Настройки выбираются по settingsRevisionId выдаваемого snapshot, а не max(createdAt); принадлежат той же session. Первая revision точно копирует валидные параметры review, будущая policy историю не меняет. Raw/errors/allowedToStart отсутствуют; actorUserId/environment не выдаются в этой проекции. Владельца Q06 раскрывает только user.minimal_context.

Нет новой команды редактирования активных настроек. При Q06-denied вся группа отсутствует с restrictedGroups; при missing/malformed разрешённой обязательной группы —503 всего чтения.

## 9. FinancialSnapshot для Q04 и разрешённого Q06

| Обязательные поля | Тип / первое пустое состояние |
| --- | --- |
| snapshotId, sessionId, settingsRevisionId | UUID |
| recordSchemaVersion | v1 |
| snapshotVersion, sessionVersion, ledgerSequence | PositiveVersion |
| projectionCalculationVersion | paper-empty-snapshot-v1 |
| lifecycle, controlState, contentState | active / copying_not_connected / EMPTY |
| dataOrigin, coverageState, unit | synthetic / no_trade_data / virtual_USD |
| initialFunding, free, equity | Money, исходно B |
| reserved, positionCost, positionValue, tradingResult | Money, исходно 0/1 |
| tradeCount, positionCount, orderCount | Counter, исходно "0" |
| asOf, createdAt | Timestamp времени данных/создания соответственно |

snapshotId ← session_snapshots.id, snapshotVersion ← version, прочие обычные поля/пары из snapshot. Внутренняя environment не выдаётся. Все ключи обязательны, null не допускается. Состояния/нули/версии читаются из сохранённых данных, не подставляются по предположению «это первый запуск». Future signed tradingResult не расширяет пустой первый сценарий.

Читается current_snapshot_version своей session; settings по его ссылке. initialFunding поясняет источник, не второе зачисление. Чтение не пересчитывает ledger/суммы и не повышает version/asOf. Обычный decoder не объявляется независимой проверкой любой правдоподобной порчи: границы сверки сохраняются по I15/M03.

Нет session → нет искусственного financialSnapshot. Q06-denied → объект отсутствует и код группы в restrictedGroups. Missing/malformed/проверенное противоречие обязательных данных →503 всего чтения, без EMPTY/ремонта/funding. Частичный Q06 — разрешённая проекция; recordSchemaVersion источника не подтверждает выдачу всех других групп или полной строки БД.

## 10. Summary для Q04 и обязательного Q06

| Обязательные поля | Тип / источник |
| --- | --- |
| sessionId | UUID paper_sessions.id |
| mode | paper |
| venueId, catalogSourceId, traderId, traderRevisionId | UUID сохранённого выбора session |
| traderDisplayName | Строка displayed_name именно сохранённой trader revision |
| dataOrigin | synthetic первого сценария |
| lifecycle, controlState, contentState, coverageState | active/copying_not_connected/EMPTY/no_trade_data первого состояния, из согласованных session/snapshot |
| sessionVersion, snapshotVersion | PositiveVersion выбранного состояния |
| settingsRevisionId | UUID настроек выбранного snapshot |
| asOf | Timestamp данных snapshot |
| startedAt, evaluationDeadlineAt | Сохранённые Timestamp |
| ianaTimezone | Закреплённая IANA-зона |
| deadlineCalculationVersion | paper-evaluation-deadline-v1 |
| timezoneDatabaseVersion | Фактическая сохранённая версия tzdb |
| createdAt, updatedAt | Timestamp записи session, не время ответа |

Null не допускается. Общие поля summary/financialSnapshot совпадают. Новая карточка каталога не заменяет историческое имя. Срок —14 календарных дней в закреплённой зоне с прежними gap/overlap-правилами; поездка/новая tzdb/чтение не пересчитывают срок. Наступление границы не команда завершения.

Нет бюджета/сумм/счётчиков/ID пользователя в summary; она не обходит ограничения групп. Без разрешённой summary Q06 недоступен целиком. Отсутствующая ревизия/повреждение/несогласованность обязательных источников →503, без fallback на текущий каталог. Навигация вне summary.

## 11. Сборка Q04 и Q06; отсутствие сессии

| Ответ | Ровно эти обязательные поля корня |
| --- | --- |
| Q04 HTTP200 | session, nextAction, nextActionParams |
| Q06 HTTP200 | session, restrictedGroups, nextAction, nextActionParams |

Q04 session-объект ровно summary/settings/financialSnapshot (§§8–10), все три обязательны; частичного успеха нет.

Q06 session-объект: summary обязательна; settings, financialSnapshot, userContext присутствуют только по разрешению соответствующих session.settings/session.financial_snapshot/user.minimal_context. userContext — закрытый объект ровно userId UUID владельца. Других персональных данных/ролей нет.

restrictedGroups — массив только session.settings, session.financial_snapshot, user.minimal_context, без повторов, в этом порядке. Закрытая группа отсутствует и обязательно перечислена; разрешённая целая группа присутствует и не перечислена. session.summary не элемент массива: без неё весь ответ запрещён. Ошибка чтения/audit не restricted.

### Текущее отсутствие

После полного входа, доступа и достоверного чтения: current route возвращает200/session=null. Это отсутствие текущей session, не всей истории; слот/session не создаются, старая session не выбирается вместо текущей. Отсутствие не разрешает C06 без его проверок. Нельзя выбрать произвольный draft для nextAction; если безопасной цели нет —null/{}.

Q06 current при отсутствии имеет restrictedGroups=[]: карточки нет, это не сертификат всех прав и не разрешение будущей выдачи. Нельзя раскрывать user existence/отсутствие без допуска. Обязательный audit до такого успеха — принятое требование, **физическая форма и основание права открыты (§16)**.

Missing/hidden конкретный sessionId →404, не200/null. Недействующий вход→401, недоступное чтение→503 SERVICE_UNAVAILABLE; pointer на отсутствующую session или повреждённые обязательные данные→503 RECORD_UNAVAILABLE. Ни одна ошибка не доказанное отсутствие.

Все группы одного ответа согласованы. Отдельные последовательные Q04/Q06 могут законно увидеть разные версии после разрешённого изменения. Каждая успешная Q06-передача имеет собственный audit; потеря ответа не отменяет его. Нельзя заново объявить read-only диагностику полноценным Q06 без записи audit.

## 12. Claim: ответ

HTTP200: корень ровно claim, nextAction, nextActionParams. claim — объект с шестью обязательными непустыми полями:

| Поле | Тип / источник draft_claim_receipts |
| --- | --- |
| claimReceiptId | UUID id |
| draftId | UUID draft_id |
| previousOwnershipId | UUID previous_ownership_id |
| claimedOwnershipId | UUID claimed_ownership_id |
| actorUserId | UUID actor_user_id, доверенно установленный получатель |
| completedAt | Timestamp completed_at |

Ownership IDs различаются и принадлежат одному draft. Первый успех/разрешённый повтор возвращают один исходный claim, без новой ownership/времени. Повтор получателю по доказанной цепочке не требует прежнего guest proof. Успех только после подтверждённой атомарной передачи; старый guest доступ закрыт только для переданного draft/результатов, не всех независимых drafts.

Нет raw/version/fieldErrors в claim. После успеха — Q03 актуального ввода без потери локальных несохранённых правок, затем новый пользовательский C05; гостевой review исторический. Error — §5 без claim; чужой user не получает сведения. Unknown→503 SERVICE_UNAVAILABLE, не успех/resolve_command/Q05. Точный защищённый H01-recovery остаётся открытым; эти UUID не proof. Current requestId/navigation отделены.

## 13. Q01: полный пользовательский вход

HTTP200: корень ровно authenticated=true, user, nextAction, nextActionParams. user — объект ровно userId UUID постоянного пользователя и locale ru/en из его профиля.

OTP/TOTP/recovery промежуточного этапа не даёт этот полный ответ. Нет/expired/revoked login→согласованный401, не200/user=null. Недоступность проверки→техническая ошибка, не доказанный logout. Не добавляются paper session/баланс/staff-роли/cookies/tokens; Q04 читает session отдельно. Locale не меняется по браузеру или отдельному draft.

Q01 не создаёт аккаунт/draft/session. Автоопрос не продлевает вход; запоздалый ответ после logout не возвращает авторизованный UI. Полнота входа проверяется сервером; успешный конверт не заменяет H01.

## 14. Q02: карточка и список трейдеров

### 14.1. Запрос карточки

GET /api/traders/:venueCode/:traderId. venueCode строго polymarket/limitless, traderId внутренний UUID; query ровно requestSchemaVersion=v1. Без тела, неизвестных/повторных параметров и дубля path IDs.

Guest/user читают разрешённый каталог; среда/источники серверные. Один внешний адрес разных venue/source не объединяет записи. Неверные формат/venue enum→400 INVALID_REQUEST; отсутствующий/скрытый/не принадлежащий указанной venue трейдер→одинаковый404 RESOURCE_NOT_FOUND. Missing/malformed обязательная текущая revision→503 RECORD_UNAVAILABLE; временный сбой→503 SERVICE_UNAVAILABLE. Известный start-disabled при разрешённом чтении→200 с явной доступностью.

### 14.2. Ответ карточки и общий Trader

HTTP200: корень ровно trader, nextAction, nextActionParams.

| Обязательные поля trader | Тип / источник |
| --- | --- |
| traderId, venueId, catalogSourceId | UUID постоянной идентичности |
| venueCode | polymarket/limitless, совпадает с запросом |
| externalTraderId | Непустая строка своего источника |
| displayName | displayed_name выбранной revision |
| traderRevisionId | UUID current revision |
| traderRevision | PositiveVersion revision |
| dataOrigin | synthetic первого стенда |
| sourceRef | Безопасная сохранённая ссылка/идентификатор из revision |
| observedAt, revisionCreatedAt | Timestamp наблюдения/подготовки и сохранения revision |
| catalogVersionAtCreation | PositiveVersion каталога при создании revision |
| catalogVersion, traderControlVersion, paperControlVersion | PositiveVersion текущих прочитанных guards |
| startAvailability | Закрытый объект available Boolean и capabilityReasonCode |

При available=true capabilityReasonCode=null. При false ровно один код по приоритету PAPER_START_DISABLED → CATALOG_SOURCE_DISABLED → TRADER_START_DISABLED, только применимые достоверные запреты. Available описывает общий/источниковый/трейдерский допуск, не личное разрешение start. У guest здесь нет AUTH_REQUIRED. Полнота входа/настройки/слот/review проверяются C05/C06.

Все ключи обязательны, иных null нет. Identity/current revision/guards/доступность читаются согласованно. SourceRef без секретов и не автоматически разрешённый внешний переход; observedAt fixture не обещает свежесть реального рынка. Score/доходность/прибыль/торговые counts не выдумываются.

C04 сохраняет только свои venueId/traderId из принятой формы, сервер сам устанавливает актуальные версии. Навигация не выбирает произвольный draft. Missing/hidden карточка→404 без trader=null. Source/environment/live-переключатели/role/userId клиент не задаёт.

### 14.3. Запрос списка

GET /api/traders. Query:

| Параметр | Обязательность / форма |
| --- | --- |
| requestSchemaVersion | Обязательный v1 |
| venueCode | Обязательный polymarket/limitless; одна площадка |
| limit | Необязательный; десятичные ASCII-цифры целого1…50, без ведущих нулей/знака/пробелов/дроби; при отсутствии20 |
| cursor | Необязательная непустая непрозрачная base64url-строка без завершающего =, ≤2048 ASCII-символов |

Тела нет. Пустое значение не отсутствие; другие/повторные параметры запрещены. Нет поиска, клиентской сортировки, only-available, offset/pageNumber/environment/sourceEnvironment/ролей/переключения происхождения. Correlation — только заголовок.

Нет cursor→первая страница. Клиент передаёт выданный cursor без разбора/изменения; подлинность и контекст проверяет сервер. При продолжении те же venue и эффективный limit; смена параметров→новый обход без cursor. Непригодный/повреждённый/не соответствующий этим параметрам cursor→400 INVALID_REQUEST.

Сортировка фиксирована traderId по возрастанию, не score/рекомендация. Включены все разрешённые к просмотру карточки, включая startAvailability=false; закрытые отсутствуют. Доступ проверяется заново на странице.

### 14.4. Ответ списка и конец

HTTP200: корень ровно venueCode, items, nextCursor, nextAction, nextActionParams. Items — массив полных trader (§14.2), без оболочки карточки, одна площадка/порядок. Unknown fields запрещены.

| Установленный результат | items | nextCursor |
| --- | --- | --- |
| Есть продолжение | Ровно эффективный limit элементов | Обязательная строка формы §14.3 |
| Последняя страница | 1…limit элементов | null |
| Первая страница пустого разрешённого списка | [] | null |

Конец определяется только nextCursor=null: последняя страница может иметь ровно limit. Указатель выдаётся после подтверждения наличия продолжения. Нет totalCount/totalPages/pageNumber/hasMore. Сбой/порча не пустой список.

### 14.5. Изменение каталога и CATALOG_CHANGED

Cursor связан с площадкой, эффективным limit, последним traderId и проверяемым состоянием разрешённого каталога: набор источников, версии каталогов/current revisions, source/trader/общий paper-допуск, применимая видимость. Пока состояние не меняется, полный последовательный обход не пропускает/не повторяет записи. Повтор того же запроса даёт ту же страницу items; UI не добавляет её второй раз. Текущая диагностика/navigation не обязаны быть побайтно прежними.

Каждая страница читается согласованно. При изменении состояния между страницами — **409 CATALOG_CHANGED**, форма §5: reasonCode=CATALOG_CHANGED, единственный reasonDetails с тем же code и params={}, nextAction=select_trader, nextActionParams ровно venueId проверенной доступной площадки. Полей items/nextCursor нет. Первую страницу не подставлять молча вместо продолжения.

UI прекращает старый обход, показывает «Каталог изменился. Обновите список», по явному действию запрашивает первую страницу без cursor и заменяет список. Старые/новые страницы не смешиваются, запоздалые ответы прежнего обхода игнорируются. Сохранённый выбор/draft не стираются; актуальность проверяют C05/C06.

Ошибка подлинности/структуры/параметров cursor остаётся400; потеря права — согласованный access/hidden ответ; техническая неизвестность —503, не доказанное изменение. Изменение каталога не сохраняется как business rejection C04/C06 и не меняет историю review/receipt.

CATALOG_CHANGED — единственное новое runtime-значение этого дополнения; согласовано владельцем явно. [Реестр](backend-code-registry.md) расширяется изданием first-session-registry-v2 без переименования прежних кодов или четырёх форматов v1. Точный состав подписи/кодирования cursor, доверенные ключи и механизм согласованной проверки набора/guards требуют спецификации и испытаний; исторический каталог/новая таблица этим не объявлены созданными.

Q02 сохраняет5s, без внутренних автоматических повторов, no-store. Все изменения только чтения/проекции; публичный API загрузки fixture не появляется.

## 15. Связь с БД и остаточные работы

| Область | Что закрыто здесь | Что ещё требуется |
| --- | --- | --- |
| Формы запросов | C04/C05/C06/claim, Q01–Q06, explicit slot/locator/параметры каталога | Исполняемые схемы, parser, canonical fingerprint/recovery и компонентная совместимость |
| Исторические результаты | receipt/review/settings/snapshot API-проекции, warnings, raw/нормализация/NULL | Декодеры/round-trip, совместимость реально найденных форматов; API-проекция не дамп полной строки |
| Q03 | Корень/draft/source errors по принятой карте | Проверка цепочки и гонок; policy из времени не выводится |
| Q04/Q06 | Полные разрешённые группы, собственные/current чтения, отсутствие | Q06 без session — §16; exact permissions/audit и runtime доказательства |
| Q02 | Карточка/пагинация/конец/CATALOG_CHANGED | Доверенный cursor и согласованное наблюдение changes, контроль видимости, проверки страниц |
| H01 | Уточнены обычные Q01 и claim-конверты | C01–C03/C07 защищённые поля/маршруты, guest bootstrap/proof/claim/logout unknown, cookie races/CSRF, foreground и recovery |
| M02–M03 | Учтены опубликованные I01–I22 и R001–R071 | Будущие lifecycle физические формы/источники, изолированные инструменты/права и реальные прогоны |
| M05 / компоненты | Прежние принятые требования сохраняются | Формат/хранилище/права evidence, библиотечная совместимость и доказательства |

Семантика поля fieldErrors.params повторно не выбирается: источником остаётся карта БД. Нормализованные проценты и warnings здесь уточняют API; соответствие JSON/декодеров передаётся чату БД. Runtime-кодеков, тестовых БД, будущих lifecycle-кодов, новых торговых endpoints или разрешения deploy нет. Полный M01 **не закрыт**.

## 16. Открытый стык DB-API-09: Q06 без текущей сессии

**Принято:** полный staff-вход/действующие права до раскрытия; достоверное отсутствие→200/session=null/restrictedGroups=[]; обязательный audit до выдачи; сбой audit закрывает ответ; отсутствующий/скрытый user→одинаковый404; ошибка чтения/повреждённый pointer→503; никаких фиктивных session/slot/snapshot.

**Не согласовано физически:** [audit_events §4](database-physical-operations-access.md) требует session_id и snapshot_version для Q06 вместе с FK. При отсутствии session их нет. Evidence прежней выдачи относится к группам существующей session и полному venue scope; точное право проверить отсутствие у target user ещё не задано.

Нужно отдельное предложение БД/H03:

1. Вид события/вариант результата; проверенный targetUserId, actor/login/requestId/time и достаточные evidence. Какие поля/условия/ссылки необходимы — явно, не неявная правка nullable.
2. Точная комбинация section/action/data scope и учёт venue-ограниченного назначения без session/venue. Отсутствие не расширяет права и не разрешает раскрытие existence.
3. Одна согласованная операция доказательства отсутствия и audit, включая гонки с C06/отзывом/login replacement, повтор HTTP и потерю ответа.
4. Сохранить строгую обязательность старых Q06 session/snapshot ссылок; не записывать фиктивную session/нулевой snapshot и не заменять audit логом.

До решения не утверждать, что новые поля/условия хранения точно не нужны. Здесь опубликовано требование и пробел, **не выбран новый audit-kind или access grant**. Реестр событий и физические таблицы этим дополнением не расширяются. Владелец 1 и владелец 2 равноправны.

I20 проверяет существующую session; PR №179/180 сами этот пробел не закрывают. Будущие отдельные проверки: разрешённое отсутствие, недостаточное/venue-ограниченное право, скрытый user, сбой audit/evidence, повтор, обе очередности гонок start/revoke. Пока это ожидания, не выполненные тесты.

## 17. Документальная сверка

| ID | Проверенный стык / сохранённое ограничение |
| --- | --- |
| AF-K01 | Все формы отличают отсутствующий ключ/null/[]/{}/ноль; типы и проценты согласованы с картой БД |
| AF-K02 | C04 полная форма и create/update; old receipt не current draft; unchanged не двигает last_input_receipt_id |
| AF-K03 | C05 зона совпадает с сохранённой версией; negative200 отделён от ранней ошибки/unknown |
| AF-K04 | Review guest slot not_applicable не допустим в C06; present свободного слота не absent |
| AF-K05 | Q05 original guest scope после claim; locator не proof и не новая область ключа |
| AF-K06 | Прямой receipt и Q05 исторически одинаковы; HTTP/навигация/requestId текущие и отдельно |
| AF-K07 | Нет fieldErrors у rejected C04/всех C06; reasonDetails отображается через принятые контейнеры |
| AF-K08 | Q03 owner текущий, источник может быть guest historical; версию не заменяет updatedAt |
| AF-K09 | Q04/Q06 settings/snapshot/summary одного состояния; не current catalog display name; old receipt не меняется |
| AF-K10 | Q06 restricted groups не NULL/порча/доказательство всех прав; user ID только разрешённая отдельная группа |
| AF-K11 | Claim собственный результат и200; нет CommandReceipt/Q05, нужен новый user review |
| AF-K12 | Q01 полный вход не pending MFA и не paper session; автоопрос не активность |
| AF-K13 | Q02 available не личное право start; source/trader scope не внешний адрес без площадки |
| AF-K14 | Q02 последний полный page допустим; cursor invalid400/change409/technical503/access различаются |
| AF-K15 | CATALOG_CHANGED только список Q02; один новый код, immutable форматы и audit enums прежние |
| AF-K16 | Q06 без session явно открыт: API принят, физический audit/access не определён |
| AF-K17 | M02–M03 документальны; SEM/READ-FAULT не DB/API/Auth, I20 не empty-session audit |
| AF-K18 | Точные H01-протоколы, независимые ранние guards, cursor механизм, декодеры, M05 и испытания остаются |

Сверка выполнена по принятым сообщениям и источникам baseline. Проверки Markdown/ссылок/репозитория не являются испытаниями API/БД/Auth/конкурентности/восстановления. [Передача DB-API](backend-database-change-list.md) отделяет уже принятые формы от требуемого ответа БД.
