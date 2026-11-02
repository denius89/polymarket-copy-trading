# Документальные примеры выдачи API из согласованных данных БД

02.11.2026 · Блок 3 после физического отражения API-карты. Baseline main `679d8e1b06b09a936f6f770a1b6757d363f4181c` (PR №186). **AP01–AP16 — ожидаемые ответы и дельты, статус каждого «не выполнялось».** Это документ, не запущенные запросы, seed, исполняемые тесты, SQL или миграции. C04/карта ошибок/числа/строгий C06 не меняются.

## 1. Источники, обозначения и полнота примера

Основы: [API-карта](database-api-field-map.md), [принятые формы API](backend-api-forms-addendum.md), [синтетические S/N/K/C04-E/D/J](database-synthetic-examples.md), [BASE/PUB/NEG/BAD/READ-FAULT](database-isolated-test-states.md). Связи: [R001–R071](database-constraint-register.md), [A01–A112](database-integrity-matrix.md), [F01–F24](database-fault-reconciliation.md), [E01–E17](database-evidence-plan.md). AP — номера примеров этого документа, не новый реестр API/приёмки и не замена R/A/F/E.

Таблицы ниже задают закрытые объекты: перечислены все поля, неупомянутых нет; вложенный объект раскрывается указанной таблицей. Money(a,b) означает объект ровно n="a", d="b"; это сокращение документа, не функция/строка API. Проценты, версии, счётчики в кавычках — строки; true/false/null — JSON-значения; 30 для signalMaxAgeSeconds — JSON integer. «Ключ отсутствует» не означает null. Эти примеры не являются готовыми HTTP-body: символы IDs требуется заменить реальными синтетическими UUID v4 в будущей изолированной подготовке.

| Символ / контекст | Привязка будущего исходного набора |
| --- | --- |
| U, D, O, REV, CK, CR, SS, ST, SN1 | Для каждого независимого S-сценария собственные user/draft/user ownership/review/clientCommandId/C06 receipt/session/settings/snapshot1; не один пользователь для всех строк |
| V, SRC, TRADER, TR | V-PM/SRC-PM/T-PM/TR-PM-1 либо отдельные Limitless IDs по S-набору. Имя TR — «Синтетический трейдер Polymarket 01» либо «Синтетический трейдер Limitless 01» |
| POLICY, PC, gCatalog, gTrader, gPaper | Действительно закреплённые опубликованные policy/control и положительные версии guards набора; версии не назначаются произвольно «1» после публикации |
| TZDB | Версия базы зон, закреплённая для будущего набора и сохранённая в session. Не вымышленное значение и не утверждение о проверенной библиотеке |
| RQ1, RQ2 и далее | Разные server X-Request-Id по HTTP-передачам; не clientCommandId/receiptId. Не сохраняются в immutable ответах; audit использует request_id своей операции |
| H | Профиль времени S §4.3: draft 2026-11-02T12:00:00.000Z, review checked/created 12:01:00.000Z, expiry 12:11:00.000Z; start 12:02:00.000Z; snapshot created 12:02:00.001Z; read 12:03:00.000Z. Для этой документальной конкретизации session/settings/receipt созданы в 12:02:00.001Z, session.updatedAt тот же. Зона Etc/UTC, deadline 2026-11-16T12:02:00.000Z |
| P | Только AP10: отдельный исходный профиль BASE/PUB, T0=2026-10-30T10:00:00.000Z, а не продолжение H. Начальные моменты/PUB2/PUB3 ровно как в изолированных состояниях §4.3 |

Документальная фиксация моментов H описывает возможный набор контролируемых часов; это не требование всем реализациям иметь одинаковые createdAt или измерение скорости commit. CR.createdAt не называется временем commit. Идентичность/grants/полный вход здесь предпосылки, не созданные аккаунты. Ни один символ не содержит credentials/личный email; владелец 1 и владелец 2 — разные равноправные staff principals.

Все ответы имеют Cache-Control: no-store и новый X-Request-Id. По умолчанию X-Correlation-Id отсутствует. В объектах, где безопасная цель в варианте не установлена, N0 означает ровно nextAction=null и nextActionParams={}; не самостоятельное поле N0. Если пример задаёт конкретный переход, он явно заменяет оба поля по T07: известные неверные настройки → continue_setup, конфликт версии → recover_setup, требуемый вход → authenticate, подтверждённая временная недоступность → retry_later. N0 не отменяет эту карту при известной безопасной цели. Закрытый API не содержит environment, внутренних hashes или proof. Поля review.ownerUserId/claim.actorUserId/commandRef.actorId выдаются только по собственным принятым контрактам; правило минимального userContext относится к Q06.

## 2. Числовые экземпляры для AP01/AP08/AP09

Используются прежние S-наборы; raw p/d — строки без двух нормализованных знаков, raw F/q неактивного режима null. У каждого варианта собственные IDs и слот; строки не выполняются последовательно на одном user.

| S | Площадка | mode | rawBudget → budget | rawFixedAmount → fixedAmount | rawCopyPercent → copyPercent | rawMarketLimitPercent → marketLimitPercent | rawDailyBuyLimitPercent → dailyBuyLimitPercent | effectiveMarketLimit / effectiveDailyBuyLimit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | Polymarket | fixed | "200" → Money(200,1) | "20" → Money(20,1) | null → null | "10" → "10.00" | "15" → "15.00" | Money(20,1) / Money(30,1) |
| S02 | Polymarket | percent | "200" → Money(200,1) | null → null | "3" → "3.00" | "10" → "10.00" | "15" → "15.00" | Money(20,1) / Money(30,1) |
| S03 | Limitless | fixed | "200" → Money(200,1) | "20" → Money(20,1) | null → null | "10" → "10.00" | "15" → "15.00" | Money(20,1) / Money(30,1) |
| S04 | Limitless | percent | "200" → Money(200,1) | null → null | "3" → "3.00" | "10" → "10.00" | "15" → "15.00" | Money(20,1) / Money(30,1) |
| S05 | Polymarket | fixed | "300" → Money(300,1) | "20" → Money(20,1) | null → null | "10" → "10.00" | "15" → "15.00" | Money(30,1) / Money(45,1) |
| S06 | Polymarket | percent | "300" → Money(300,1) | null → null | "3" → "3.00" | "10" → "10.00" | "15" → "15.00" | Money(30,1) / Money(45,1) |
| S07 | Limitless | fixed | "300" → Money(300,1) | "20" → Money(20,1) | null → null | "10" → "10.00" | "15" → "15.00" | Money(30,1) / Money(45,1) |
| S08 | Limitless | percent | "300" → Money(300,1) | null → null | "3" → "3.00" | "10" → "10.00" | "15" → "15.00" | Money(30,1) / Money(45,1) |
| S13 | Polymarket | fixed | "110" → Money(110,1) | "7" → Money(7,1) | null → null | "7" → "7.00" | "13" → "13.00" | Money(77,10) / Money(143,10) |
| S14 | Limitless | percent | "110" → Money(110,1) | null → null | "3.5" → "3.50" | "7" → "7.00" | "13" → "13.00" | Money(77,10) / Money(143,10) |

Исходные normalized percent integers: 300/350 для q, 1000/700 для p, 1500/1300 для d. Значения P/D не резервируют деньги; q не умножается на B для фиктивной сделки. В snapshot initialFunding/free/equity=B, reserved/positionCost/positionValue/tradingResult=Money(0,1), все торговые счётчики "0". Набор с B300 не превращается в B200. Это независимые заранее заданные эталоны прежних S, не расчёт проверяемой реализации.

## 3. AP01 — полный положительный review

Предпосылки S01–S08/S13/S14, H: полный действующий user-вход, свой editable draft version="1", trader/controls разрешены, slot отсутствует, зона сохранена Etc/UTC. C05 передаёт requestSchemaVersion="v1", draftId=D, expectedDraftVersion="1", proposedTimezone="Etc/UTC". После подтверждённого сохранения HTTP200, корень ровно review и N0. Отдельное подтверждение C06 этим ответом не выполняется.

| Все поля review | Ожидаемое значение / сохранённый источник |
| --- | --- |
| reviewId, draftId, ownershipId | REV, D, O из setup_reviews |
| recordSchemaVersion, draftVersion | "v1", "1" |
| ownerKind, ownerUserId | "user", U |
| venueId, catalogSourceId, traderId, traderRevisionId | V, SRC, TRADER, TR своего S-набора |
| catalogVersion, traderControlVersion | gCatalog, gTrader как PositiveVersion-строки сохранённого review |
| policyVersionId, paperControlId, paperControlVersion | POLICY, PC, gPaper |
| selectedMode | mode из §2 |
| rawBudget, rawFixedAmount, rawCopyPercent, rawMarketLimitPercent, rawDailyBuyLimitPercent | Пять raw из выбранной строки §2; неактивный null сохраняется |
| proposedTimezone, normalizationValid | "Etc/UTC", true |
| budget, fixedAmount, copyPercent, marketLimitPercent, dailyBuyLimitPercent, effectiveMarketLimit, effectiveDailyBuyLimit | Семь нормализованных полей §2, без пропуска неактивного null |
| expectedSlot | Ровно state="absent", generation отсутствует |
| allowedToStart, requiresAuthentication | true, false |
| primaryReasonCode, reasonDetails, fieldErrors | null, [], [] |
| warnings | Два объекта в порядке: code="SYNTHETIC_DATA", params={}; code="COPYING_NOT_CONNECTED", params={} |
| checkedAt, expiresAt, createdAt | "2026-11-02T12:01:00.000Z", "2026-11-02T12:11:00.000Z", "2026-11-02T12:01:00.000Z" |

Warnings в этих наборах основаны на двух установленных фактах; нельзя заменить их [] ради сокращения ответа. Формат допускает [] при установленном отсутствии применимых предупреждений, но это не состояние S-наборов выше. Источник — сохранённый setup_reviews.warnings, не пересчёт на чтении. Дельта C05: +1 review, +0 обычных CMD/слотов/FIN/start-audit/outbox; raw/version/pointer draft прежние.

Вариант существующего свободного слота: отдельный разрешённый исходный набор с slot.generation="7", current_session_id=null. Review.expectedSlot ровно state="present", generation="7"; C05 не повышает поколение. Это иное исходное состояние, не молчаливая замена absent в уже сохранённом REV. C06 использует ровно показанный вариант.

## 4. AP02–AP03 — отрицательный review и отсутствие review

### AP02. Guest + короткий неверный бюджет

Самостоятельный N20/J02 на выбранной площадке: guest ownership O-G, rawBudget="abc", остальные активные значения S01 (для Limitless — S03), slot не применим. Это не expired user, превращённый в guest. HTTP200, корень review, nextAction="authenticate", nextActionParams={}. Полный объект AP01 с явными заменами ниже; остальные поля/времена/ссылки своего набора прежние:

| Поля | Замена |
| --- | --- |
| reviewId, draftId, ownershipId | Собственные REV-G, D-G, O-G |
| ownerKind, ownerUserId | "guest", null |
| rawBudget, normalizationValid | "abc", false |
| Все семь нормализованных числовых полей | null каждый; нет Money с null n/d и нет частично действующих p/d |
| expectedSlot | Только state="not_applicable", без generation |
| allowedToStart, requiresAuthentication, primaryReasonCode | false, true, "AUTH_REQUIRED" |
| reasonDetails | Два объекта в порядке: code="AUTH_REQUIRED", params={}; code="NUMERIC_SETTINGS_INVALID", params={} |
| fieldErrors | Один объект field="rawBudget", code="INVALID_DECIMAL", params={} |

Warnings остаются двумя применимыми предупреждениями. В БД reason_details — объект reasons/fieldErrors; API выдаёт два массива по прежней карте. +1 review, без обычного CMD/FIN. Дополнительный самостоятельный вариант N11/J04: полный user, percent rawCopyPercent="3,2", другие значения S02/S04; primaryReasonCode="NUMERIC_SETTINGS_INVALID", reasonDetails только этот code/params={}, fieldErrors ровно rawCopyPercent/INVALID_STEP с params step="0.50", origin="1.00", unit="percentage_points"; normalized все null, requiresAuthentication=false, expectedSlot=absent; корневая навигация nextAction="continue_setup", nextActionParams ровно draftId своего набора. Raw не исправляется на "3"/"3.5".

### AP03. C05 не создал подтверждённый review

| Самостоятельный вариант | HTTP / полный корень ответа | Ожидаемые записи |
| --- | --- | --- |
| Та же draft version="1", но прислана другая поддерживаемая зона "Europe/Warsaw" вместо сохранённой Etc/UTC | 400; reasonCode="INVALID_REQUEST", reasonDetails=[один code="INVALID_REQUEST", params={}], N0 | +0 reviews; зона draft не меняется |
| Старый expectedDraftVersion="1" при current="2", зона совпадает с version2 | 409; reasonCode="VERSION_CONFLICT", reasonDetails=[один такой же code, params={}], nextAction="recover_setup", nextActionParams={draftId=D} | +0 reviews; новая версия не проверяется вместо указанной |
| Commit C05 неизвестен | 503; reasonCode="SERVICE_UNAVAILABLE", reasonDetails=[один такой же code, params={}], N0 | Нельзя утверждать +0 reviews: сохранение могло состояться. Нет обычного key/receipt/Q05 |

Во всех трёх ответах ключ review отсутствует, не null/{}. При unknown автоматического повтора нет; отдельный явный C05 может создать новый review, прежний возможный не удаляется. C06 допускается лишь по конкретному полученному и показанному review. Варианты zone/version не назначают новый приоритет нескольких одновременно неизвестных причин.

## 5. AP04–AP05 — неизменяемый receipt против текущего Q03

### AP04. Последовательность C04-E01–E06 без изменения её правил

Самостоятельный user draft S01. Locale="ru", step="configure", entryContext="catalog", зона Etc/UTC; остальные поля формы S01. Для каждой новой операции свой key K1/K2/K3/K5/K6 и receipt C1/C2/C3/C5/C6. Здесь C6 — символ receipt C04, не имя команды C06. Времена исходной последовательности сохранены.

| Передача | HTTP / receipt.result | Current draft после неё |
| --- | --- | --- |
| Create K1 в 12:00 | 201; draftId=D, ownershipId=O, draftVersion="1", changeKind="created", lastSavedAt="2026-11-02T12:00:00.000Z", expiresAt="2026-11-09T12:00:00.000Z" | version1, pointer C1 |
| Update K2 в 12:01, expected="1", F "20"→"20.00" | 200; те же D/O, version="2", changeKind="updated", lastSavedAt="2026-11-02T12:01:00.000Z", expiresAt="2026-11-09T12:01:00.000Z" | version2, pointer C2, raw F="20.00" |
| Новый unchanged K3 в 12:02, expected="2" | 200; D/O, version="2", changeKind="unchanged", времена ввода из C2 | version2, pointer **C2**, не C3 |
| Exact replay K1 после K3 | 201; **исходный** created/version1/времена12:00 | По-прежнему version2/pointer C2; CMD +0 |
| Новый stale K5 при expected="1", raw как у version2 | 409; result=null, reasonCode="VERSION_CONFLICT", reasonDetails=[code="VERSION_CONFLICT", params={}] | version2/pointer C2; fieldErrors у этого receipt отсутствует |
| Update K6 в 12:03, expected="2", B→"abc" | 200; D/O, version="3", changeKind="updated", lastSavedAt="2026-11-02T12:03:00.000Z", expiresAt="2026-11-09T12:03:00.000Z" | version3/pointer C6, raw B="abc", raw F="20.00" |

Для каждого ответа корень ровно commandRef/receipt/nextAction/nextActionParams. Для K5 — recover_setup с params ровно draftId=D; для K6 — continue_setup с params ровно draftId=D; остальные передачи таблицы используют N0, когда подходящий переход не установлен. CommandRef ровно actorRealm="user", actorId=U, commandType="C04", clientCommandId соответствующего K. Полный receipt: receiptId соответствующего C, recordSchemaVersion="v1", commandType="C04", outcome="succeeded" кроме K5 ("rejected"), createdAt исходного C. Для конкретизации createdAt C1/C2/C3/C5/C6 — соответственно 12:00:00.000Z / 12:01:00.000Z / 12:02:00.000Z / 12:02:30.000Z / 12:03:00.000Z 02.11.2026. Replay K1 сохраняет первый момент.

У succeeded reasonCode=null, reasonDetails=[], result из таблицы, fieldErrors=[] кроме K6: [field="rawBudget", code="INVALID_DECIMAL", params={}]. У rejected K5 result=null и **нет fieldErrors**. У всех отсутствуют session-result/навигация внутри receipt. Каждый новый допустимый K создаёт ровно key/receipt/details, exact replay +0; FIN/start-audit/outbox от C04 +0. Старый C6 после будущего исправления бюджета сохраняет исходную ошибку.

### AP05. Полный Q03 после K6

Чтение в 2026-11-02T12:03:10.000Z при действующем доступе; HTTP200. Корень ровно draft/fieldErrors/fieldErrorsSource/nextAction/nextActionParams; nextAction="continue_setup", nextActionParams={draftId=D}:

| Все поля draft | Ожидаемое значение |
| --- | --- |
| draftId, currentOwnershipId, draftVersion, ownerKind, state | D, O, "3", "user", "editable" |
| locale, step, entryContext | "ru", "configure", "catalog" |
| venueId, traderId, selectedMode | V-PM, T-PM, "fixed" |
| rawBudget, rawFixedAmount, rawCopyPercent | "abc", "20.00", null |
| rawMarketLimitPercent, rawDailyBuyLimitPercent, proposedTimezone | "10", "15", "Etc/UTC" |
| lastSavedAt, expiresAt | "2026-11-02T12:03:00.000Z", "2026-11-09T12:03:00.000Z" |
| createdAt, updatedAt | "2026-11-02T12:00:00.000Z", "2026-11-02T12:03:00.000Z" |
| usedAt, usedBySessionId | null, null |

FieldErrors ровно один INVALID_DECIMAL для rawBudget с params={}; fieldErrorsSource ровно receiptId=C6 и draftVersion="3". После K3 до K6 источник был C2/version2, не C3; новый C05 его также не заменяет. Самостоятельный J05 (иная допустимая тестовая policy) сохраняет Eα источника и Eβ нового unchanged раздельно; значения новой policy здесь не выдумываются. Все чтения +0 CMD/FIN, TTL прежний; Q03 не содержит budget/allowedToStart. Конкурирующее обновление даёт целиком одну разрешённую версию/source/errors, не смесь; таблица сама не доказывает гонку.

## 6. AP06 — claim и старый guest-результат

Самостоятельная ветка C04-E09/E10/J07: G создал D-G/S01 version1 в 12:00, receipt C-G содержит ownership O-G. Полный user U выполнил claim в 12:01, receipt L. Затем свой user C04 изменил raw F "20"→"20.00" в 12:02, current version2/pointer C-U/ownership O-U. Это не продолжение ошибочного бюджета AP05.

Claim HTTP200, корень claim и N0. Claim ровно: claimReceiptId=L, draftId=D-G, previousOwnershipId=O-G, claimedOwnershipId=O-U, actorUserId=U, completedAt="2026-11-02T12:01:00.000Z". Разрешённый повтор возвращает тот же L/момент; прежний guest proof не нужен получателю по доказанной цепочке. Первый claim: +1 ownership/+1 claim receipt/+1 claim audit, current pointer меняется; повтор +0. Сам claim не меняет input version/TTL/last_input_receipt_id и не создаёт CMD/FIN.

Q05 старого guest key после user-правки: HTTP200, status="committed"; commandRef ровно actorRealm="guest", actorId=G, commandType="C04", clientCommandId=K-G. Receipt C-G: v1/C04/succeeded/createdAt12:00, reasonCode=null, reasonDetails=[], fieldErrors=[], result ровно D-G/O-G/version"1"/created/lastSavedAt12:00/expiry09.11 12:00. N0; не user commandRef и не version2. Q03 отдельно показывает user/O-U/version2 и источник C-U/version2; поля формы/времена берутся из текущей версии, без копирования raw из старого receipt.

Сразу после claim **до** user-правки Q03 показывал user/O-U/version1, но fieldErrorsSource C-G/version1 — это допустимая историческая цепочка. Старый guest не получает переданный draft/результат; чужой user также не получает его. Для доказанного полного чужого user скрытый ресурс →404 RESOURCE_NOT_FOUND в конверте §10, без receipt/признака существования. При недействующем guest-контексте применяется принятый Auth/access ответ; точный H01 не заменяется придуманным proof. Одного UUID G/L/D недостаточно для доступа. После claim нужен новый user C05, старый guest review неизменен.

## 7. AP07–AP08 — отказ и успешный C06

### AP07. Сохранённый отказ остаётся отказом

Самостоятельный J03: новая допущенная C06, достоверно PAPER_START_DISABLED, иных препятствий по приоритету нет. Сохранён C-R/K-R. Прямой ответ HTTP409 (CAPABILITY_UNAVAILABLE); корень commandRef/receipt/N0. CommandRef user/U/C06/K-R. Receipt ровно receiptId=C-R, recordSchemaVersion="v1", commandType="C06", outcome="rejected", createdAt исходной записи (для примера "2026-11-02T12:02:00.001Z"), reasonCode="CAPABILITY_UNAVAILABLE", reasonDetails=[один code="CAPABILITY_UNAVAILABLE", params с единственным capabilityReasonCode="PAPER_START_DISABLED"], result=null. Поле fieldErrors отсутствует.

После снятия запрета Q05 HTTP200/status="rejected" возвращает тот же commandRef/receipt; это не success и не новая проверка. Exact replay сохраняет прежний HTTP409 и receipt. В БД reasons лежат в reason_data.reasons, response_data={}; новый CMD только у исходного принятого отказа, чтения/replay +0. Нет новых session/settings/funding/journal/snapshot/start-audit/outbox. Допустимая судьба впервые зарезервированного слота определяется исходной TX06-точкой, не выводится из HTTP; если резервирование достигнуто, сохраняется свободный generation1 вместе с отказом. Новая команда после разрешённого нового намерения не подменяет старый исход.

### AP08. Полный START и повтор

Отдельный AP01/S-case, H, явный C06 с requestSchemaVersion="v1", clientCommandId=CK, reviewId=REV, expectedDraftVersion="1", expectedSlot ровно state="absent". Только после подтверждённого полного START прямой HTTP201: commandRef user/U/C06/CK; receipt ровно receiptId=CR, recordSchemaVersion="v1", commandType="C06", outcome="succeeded", createdAt="2026-11-02T12:02:00.001Z", reasonCode=null, reasonDetails=[], result={sessionId=SS, settingsRevisionId=ST, snapshotVersion="1", sessionVersion="1"}. FieldErrors отсутствует. Корневая навигация при разрешённой своей session: nextAction="view_session", nextActionParams ровно sessionId=SS.

Exact replay —201 с тем же историческим receipt, Q05 —200/status="committed" с ним же; requestId новый. Навигация всегда требует текущего доступа. Исходный START — полный набор S §4.2 с одним funding B/1, журналом и двумя entries +B/−B, снимком1, audit/outbox и used draft. Replay/Q05 не добавляют ни денег, ни start audit/outbox, ни settings/snapshot. При утрате доступа старый факт остаётся, но выдача закрывается. Полнота не доказывается одним receipt или счётом строк.

## 8. AP09 — полный Q04 одного пустого состояния

Каждый S-case §2 после AP08/H; read в 12:03. HTTP200, корень session и N0; session ровно summary/settings/financialSnapshot. Три объекта ниже полностью задают ответ, параметры из §1–2, без скрытых полей.

| Все поля settings | Значение |
| --- | --- |
| settingsRevisionId, sessionId, recordSchemaVersion | ST, SS, "v1" |
| sequence, previousRevisionId | "1", null |
| budget, sizingMode, fixedAmount, copyPercent, marketLimitPercent, dailyBuyLimitPercent, effectiveMarketLimit, effectiveDailyBuyLimit | Значения §2; sizingMode=mode |
| policyVersionId, calculationVersion | POLICY, "paper-settings-calculation-v1" |
| signalMaxAgeSeconds, commandReceiptId, createdAt | 30, CR, "2026-11-02T12:02:00.001Z" |

| Все поля financialSnapshot | Значение |
| --- | --- |
| snapshotId, sessionId, settingsRevisionId, recordSchemaVersion | SN1, SS, ST, "v1" |
| snapshotVersion, sessionVersion, ledgerSequence | "1", "1", "1" |
| projectionCalculationVersion | "paper-empty-snapshot-v1" |
| lifecycle, controlState, contentState | "active", "copying_not_connected", "EMPTY" |
| dataOrigin, coverageState, unit | "synthetic", "no_trade_data", "virtual_USD" |
| initialFunding, free, equity | Money(B,1) каждый: 200/300/110 по §2 |
| reserved, positionCost, positionValue, tradingResult | Money(0,1) каждый |
| tradeCount, positionCount, orderCount | "0" каждый |
| asOf, createdAt | "2026-11-02T12:02:00.000Z", "2026-11-02T12:02:00.001Z" |

| Все поля summary | Значение |
| --- | --- |
| sessionId, mode | SS, "paper" |
| venueId, catalogSourceId, traderId, traderRevisionId | V, SRC, TRADER, TR |
| traderDisplayName | Сохранённое имя TR из §1, не новая current revision каталога |
| dataOrigin | "synthetic" |
| lifecycle, controlState, contentState, coverageState | "active", "copying_not_connected", "EMPTY", "no_trade_data" |
| sessionVersion, snapshotVersion, settingsRevisionId | "1", "1", ST |
| asOf, startedAt | "2026-11-02T12:02:00.000Z" каждый |
| evaluationDeadlineAt, ianaTimezone | "2026-11-16T12:02:00.000Z", "Etc/UTC" |
| deadlineCalculationVersion, timezoneDatabaseVersion | "paper-evaluation-deadline-v1", TZDB из сохранённого источника |
| createdAt, updatedAt | "2026-11-02T12:02:00.001Z" каждый |

S14 особенно: copyPercent="3.50", effectiveMarketLimit=Money(77,10), effectiveDailyBuyLimit=Money(143,10), free/equity=Money(110,1), а не 88/1, не 7.7 JSON number и не виртуальная сделка. S13 fixedAmount=Money(7,1), copyPercent=null при тех же P/D. Settings выбираются по snapshot.settingsRevisionId, snapshot по current pointer. Q04 ничего не сохраняет/не пересчитывает/не исправляет. Не выдаются actorUserId настроек, userContext, raw, policy из текущего control или score. При последующей публикации другой карточки имя TR остаётся историческим; повреждение TR не разрешает fallback на новое имя.

## 9. AP10–AP12 — текущий снимок и административные группы

### AP10. BASE-V3 против исходного receipt

Отдельная будущая PUB-копия профиля P/S14, не реальные команды первого сценария. По принятой BASE-V3 сохранены SN1/SN2/SN3, current_snapshot_version="3", session.version="3", settings ST1 и ledgerSequence="1" прежние; деньги и slot generation="1" не изменились. Q04 имеет полную структуру AP09, но свои IDs и следующие времена/версии:

| Источник / поле | Значение P |
| --- | --- |
| financialSnapshot.snapshotId/snapshotVersion/sessionVersion | SN3 / "3" / "3" |
| summary.snapshotVersion/sessionVersion | "3" / "3" |
| snapshot.asOf и summary.asOf/startedAt | "2026-10-30T10:00:02.000Z" |
| snapshot.createdAt и summary.updatedAt | "2026-10-30T10:00:04.000Z" |
| summary.createdAt, settings.createdAt, исходный receipt.createdAt в этой конкретизации | "2026-10-30T10:00:02.000Z" |
| summary.evaluationDeadlineAt | "2026-11-13T10:00:02.000Z" |

Q05/replay исходного C06 по-прежнему содержит result.snapshotVersion="1", sessionVersion="1", settingsRevisionId=ST1 и исходные IDs/createdAt; current SN3 не копируется в receipt. Сам PUB добавил только полные снимки/соответствующее состояние, не новые деньги/CMD/start-audit/outbox; последующие чтения +0. Равенство sessionVersion/snapshotVersion здесь свойство этой fixture, не общий новый инвариант. M03-путь PUB не реализован и не публичный endpoint.

### AP11. Та же сессия у двух владельцев

Отдельный S14/AP09, H; у владельца 1 и владельца 2 отдельные действующие полные staff-входы и достаточные целые grants всех четырёх групп. Для каждого Q06 HTTP200: session ровно три объекта AP09 плюс userContext={userId=U}; restrictedGroups=[]; N0. IDs/версии/суммы/время одинаковы при неизменном исходном состоянии; запросы имеют разные requestId и actor_staff_id.

Каждая подтверждённая выдача сохраняет свой audit session=SS/snapshot_version=1 и достаточное evidence для session.summary/session.settings/session.financial_snapshot/user.minimal_context. В минимальном выбранном достаточном наборе — по одной детерминированно выбранной разрешающей строке на группу; фактические assignment/grant/version привязаны к доверенному набору, не выдуманы из роли owner. В этом полном варианте каждый запрос → +1 audit/+4 evidence; два разных чтения → +2 audit/+8 evidence, FIN/CMD +0. Потеря ответа не удаляет уже сохранённый audit, повтор HTTP требует новый. Никакого старшинства владельцев нет.

### AP12. Закрытые группы — отсутствие ключей

Самостоятельные доверенно подготовленные варианты ограниченного назначения, без новой роли или изменения полномочий владельцев по умолчанию:

| Установленный доступ | Полный session-объект | restrictedGroups | Обязательное evidence |
| --- | --- | --- | --- |
| summary и settings | summary/settings из AP09; **нет** financialSnapshot и userContext | ["session.financial_snapshot", "user.minimal_context"] | Только две выданные группы, каждую разрешает целый grant |
| Только summary | Только summary из AP09 | ["session.settings", "session.financial_snapshot", "user.minimal_context"] | summary |
| Нет обязательной summary при установленном access denial | Нет session/restrictedGroups; HTTP403, конверт ACCESS_DENIED из §10 | Поле отсутствует | Не успешный Q06; фиктивный read_authorized audit не создаётся |

В первых двух строках корень session/restrictedGroups/N0, HTTP200 только после сохранённого audit/evidence. Закрытое financialSnapshot не null, не {}, не zero/EMPTY. Источники summary всё равно полны; отсутствие закрытой группы не скрывает уже обнаруженное противоречие обязательного источника. Нельзя склеить часть scope из разных grants или считать [] доказательством полноты прав. Для скрытого ресурса действует одинаковый404; таблица не меняет правила скрытия/приоритет Auth.

## 10. AP13–AP14 — повреждение, audit failure и неизвестность

Единый обозначенный здесь конверт ERR(code) — корень ровно reasonCode=code, reasonDetails=[единственный объект code=code, params={}], nextAction=null, nextActionParams={}. Это запись формы в документе, не строка/функция API. Параметры навигации заменяются только явно оговорённым безопасным вариантом. В ERR нет receipt/review/result/fieldErrors/status/session/restrictedGroups даже со значением null.

### AP13. Раздельные отрицательные состояния

| Предусловие после актуального допуска | Ожидаемый ответ | Запрещённая подстановка / смысл |
| --- | --- | --- |
| Q03: источник last_input_receipt_id или его обязательные details повреждены | 503 ERR(RECORD_UNAVAILABLE) | Не fieldErrors=[], не текущая policy, не последнее review |
| Q05: найденный core без обязательных details/неизвестный format | 503 ERR(RECORD_UNAVAILABLE) | Не pending202 и не повторное исполнение |
| C05 review в контролируемой выдаче: warnings NULL/{}/лишний key/неизвестный code/повтор/обратный порядок | 503 ERR(RECORD_UNAVAILABLE) при уже повреждённом обязательном источнике | Не сортировать/фильтровать/заменять на []; при подготовке новой записи нарушение должно прервать целую транзакцию до commit |
| Разрешённый Q04/Q06: половина Money n/d, отсутствующий current snapshot, чужой settings ID, противоречащие версии либо отсутствующая историческая TR | 503 ERR(RECORD_UNAVAILABLE) | Не смешанный/частичный200, не текущая карточка, не новый funding |
| Временный сбой чтения при неизвестном состоянии хранилища | 503 ERR(SERVICE_UNAVAILABLE), но nextAction="retry_later", nextActionParams={} при установленной временной недоступности | Не «порча доказана», не пустое состояние |
| Q06: сбой записи audit до подтверждённого commit | 503 ERR(SERVICE_UNAVAILABLE), nextAction="retry_later", nextActionParams={} при установленной временной инфраструктурной ошибке | Данные не выдаются. При доказанном rollback новый audit/evidence +0; неизвестность commit не позволяет утверждать +0 |

NEG — попытка записи при действующих ограничениях; BAD — отдельная повреждённая копия; READ-FAULT — только модель на границе чтения. Они не взаимозаменяемы. Review-ошибка чтения не вводит новый публичный GET review: проверяется допустимая существующая граница выдачи/decoder. Для корректного положительного контроля полный объект AP01/AP09 проходит по своему контракту; реального прогона не было. Не добавлять padding/message ради 16 КиБ закрытого warnings; oversized/малформат не допустимое содержимое. Обнаруженная ошибка не разрешает ремонт/очистку/смену ключа.

### AP14. Unknown отдельно от сохранённого отказа

Самостоятельные C04 или C06 с известным исходным commandRef и доказанным доступом. Прямой unknown: HTTP503, reasonCode="SERVICE_UNAVAILABLE", reasonDetails=[code="SERVICE_UNAVAILABLE", params={}], nextAction="resolve_command", nextActionParams ровно commandRef исходного намерения. Нет receipt/status. При отсутствии безопасного locator — N0, не раскрытие чужой области.

Последующий разрешённый Q05, когда окончательный исход ещё не установлен: HTTP202; commandRef исходный; status="pending"; receipt=null; N0. Это не сохранённая строка pending, не доказательство отсутствия эффекта и не разрешение нового key. Недоступное хранилище →503, а не202. Когда найден полный результат, Q05 возвращает200 и соответствующий исходный receipt (AP07/AP08/AP04); новый requestId не меняет fingerprint. Свежая сверка не идёт по старому Serializable-снимку/отстающей копии.

Если разрешённый claim неизвестен:503 ERR(SERVICE_UNAVAILABLE), без claim/commandRef/Q05; защищённое восстановление H01 своим контекстом. C05 unknown описан AP03. Сам таймаут, закрытое соединение или отсутствие receipt при чтении не доказывают rollback ни одной из этих операций. Одни документальные ответы не доказывают корректность гонок CC01/CC15/CC17 или бюджета.

## 11. AP15–AP16 — профиль, диагностика и достоверное отсутствие

### AP15. Q01 и текущие заголовки

Полный действующий user U с users.locale="ru": HTTP200, корень authenticated=true, user={userId=U, locale="ru"}, N0. Браузер/draft могут иметь иной язык; профиль не меняется от чтения. Нет staff-ролей, баланса, paper session, cookies или токенов. Background Q01 не продлевает вход. Отдельный достоверно истёкший login →401 ERR(AUTH_EXPIRED) с nextAction="authenticate", nextActionParams={}; неполный вход не200/authenticated=true; временно недоступная проверка →503 ERR(SERVICE_UNAVAILABLE) с nextAction="retry_later", nextActionParams={}, не доказанный logout. Auth/logout не создают обычных CommandReceipt/Q05.

Для двух разрешённых чтений одного исторического receipt — разные X-Request-Id RQ1/RQ2. Если клиент дал валидный синтетический X-Correlation-Id `7e56b3a0-1d42-4c19-8a31-2c5e60f094bd`, он отражается заголовком; в receipt/review/params его нет. Без заголовка не генерировать correlation. Невалидный или повторный correlation даёт400 ERR(INVALID_REQUEST) с новым requestId до предметной операции; исходное невалидное значение не копируется целиком. Замена correlation не меняет исходный key/hash и не подтверждает безопасность позднего UI-ответа после logout.

### AP16. Q04 current: пусто, скрыто, повреждено

| Самостоятельный установленный случай | Ответ |
| --- | --- |
| Полный user U; своей текущей session достоверно нет (slot отсутствует либо current_session_id=null) | 200, корень ровно session=null и N0; нет snapshot/settings/restrictedGroups |
| Конкретный by-ID отсутствует или скрыт | 404 ERR(RESOURCE_NOT_FOUND), без session=null |
| Current pointer заполнен, но target отсутствует/чужой/повреждён | 503 ERR(RECORD_UNAVAILABLE), не200/null |
| Проверка наличия не завершилась из-за установленной временной инфраструктурной недоступности | 503 ERR(SERVICE_UNAVAILABLE) с nextAction="retry_later", nextActionParams={}; отсутствие не установлено |

Во всех вариантах чтение не создаёт slot/session/финансы, не выбирает старую историю вместо current и не даёт права обходить C06. **Q06 current без session не получает здесь готового полного примера:** внешний200/null/[] уже принят, но право/audit/evidence DB-API-09 остаются несогласованной физической частью. Не подставлять audit с фиктивным SS/SN1 или ослабленными FK. Q02/DB-API-10 также вне этого пакета; карточка/курсор не выдаются за проверенные.

## 12. Связи AP с R/A/F/E

Каждая строка — только относящиеся утверждения, не полное покрытие или прохождение A. E01 (изоляция/происхождение) — общая предпосылка будущих прогонов; E09/реальные trace нужны для конкуренции, таблицы ответов их не заменяют. Все номера R/A/F/E ссылаются на существующие реестры; новых критериев не введено.

| Пример / исходный набор | R | A | F | E |
| --- | --- | --- | --- | --- |
| AP01 · S01–S08/S13/S14 | R003, R008, R024, R025, R026, R027 | A03, A07, A08, A28, A32, A40, A49, A60 | F07, F10, F22 | E03, E05, E12 |
| AP02 · N20/N11/J02/J04 | R003, R004, R025, R026, R043 | A02, A07, A08, A28, A40 | F07, F22 | E03, E05, E07, E12 |
| AP03 · D05/C05 | R024, R027, R045, R061, R062 | A15, A18, A28, A44, A100 | F07, F09 | E05, E08, E11, E12 |
| AP04 · C04-E01–E06 | R017, R018, R019, R038, R039, R040, R041, R042, R043 | A27, A28, A54, A55, A56, A57, A98, A100 | F05, F10, F17 | E04, E08, E12 |
| AP05 · C04-E06/J05/J06 | R015, R016, R019, R043, R063 | A28, A54, A55, A56, A58, A100, A110 | F05, F07, F17 | E04, E08, E09, E10 |
| AP06 · K01/C04-E09–E12/J07 | R012, R013, R014, R019, R044, R046, R069, R070 | A02, A23, A26, A35, A54, A55, A106, A107 | F06, F17 | E04, E07, E08 |
| AP07 · J03/D07/D08 | R038, R041, R042, R043, R045, R071 | A16, A29, A46, A55, A98, A106 | F03, F08, F17 | E05, E08, E12 |
| AP08 · S/START/D08 | R028, R030, R031, R032, R033, R034, R037, R041, R042, R046, R049 | A03, A04, A11, A13, A29, A60, A100, A103 | F01, F02, F03, F10 | E02, E06, E08 |
| AP09 · S/K06 | R003, R021, R031, R034, R035, R036, R063, R071 | A03, A04, A05, A07, A31, A32, A33, A39, A43, A52 | F11, F22, F23 | E03, E06, E10, E11, E12 |
| AP10 · BASE-V3/PUB | R007, R031, R034, R035, R042, R063 | A05, A29, A33, A45, A52, A53 | F03, F11, F17 | E06, E08, E10 |
| AP11 · K06/I20 | R046, R047, R048, R055, R069, R071 | A05, A23, A24, A37, A52, A104 | F12, F13 | E07, E10 |
| AP12 · J10/I20 | R047, R048, R055, R063, R069, R071 | A05, A23, A24, A30, A52, A53, A104 | F11, F12, F13 | E07, E10, E12 |
| AP13 · J09/I15–I17/I20 | R008, R019, R026, R034, R035, R043, R048, R063, R064 | A40, A49, A53, A80, A81, A95, A99, A100, A110 | F10, F11, F12, F17, F20, F21, F22 | E02, E05, E10, E12, E14 |
| AP14 · J08/D04/D05 | R014, R027, R044, R045, R062, R063 | A18, A29, A48, A69, A100, A105, A106, A107 | F02, F03, F06, F07, F09, F17 | E07, E08, E09, E11 |
| AP15 · D08/D10/T07/T15 | R011, R058, R059, R061, R069, R070, R071 | A06, A23, A25, A29, A44, A70 | F06, F08, F13, F21 | E07, E08, E11, E12, E16 |
| AP16 · current/by-ID/READ-FAULT | R028, R035, R048, R063, R069 | A05, A17, A18, A23, A52, A53, A110 | F11, F12, F13 | E07, E10, E12 |

## 13. Итог и остающиеся зависимости

Отражены документальные ответы для обеих площадок/режимов/бюджетов, исторического и текущего состояния, claim, закрытых групп, повреждений и unknown. При будущем прогоне наблюдать не только HTTP/поля, но и нужные сохранённые IDs/версии/ссылки/дельты и отсутствие запрещённого эффекта по E-плану. Положительный пример JSON/таблицы не подтверждает constraints, безопасный Auth, реальные гонки, аудит или UI.

Исходные S/N/K/C04-E/D/J, A01–A112/R001–R071/F01–F24/E01–E17, карта ошибок, C04/last_input_receipt_id, строгий C06 и история ADR сохранены. Ни одна семантическая fixture не расширяет lifecycle первого сценария; новые DB-API-09/10 решения не выбраны.

Остаются H01 protected context/recovery/ранние guards; компоненты/codecs/привилегии/claim mapping; физические future lifecycle M02, средства и права M03, машинный формат/место/права M05, компоненты времени/backup/restore H06. Отражение форм и примеры не закрывают M01 как готовую интеграцию. Следующее поручение стоит выбирать по конкретным оставшимся стыкам или новой передаче бэкенда; этот документ не запускает реализацию/испытания автоматически.

## 14. Уточнение AP16 после принятия блоков 1–2 DB-API-09

02.11.2026 · [DB-API-09 §§7–9](database-q06-absence-design.md) приняты владельцем и отражены документально. Право и физический audit отсутствия теперь приняты: отдельное all-право, новый event_kind/target/наблюдение слота и одно evidence. Внешний Q06 current200/session=null/restrictedGroups=[] прежний; при отсутствии безопасной навигации null/{}. Старый факт audit не заменяет новое чтение при повторе. Блок 3 согласованности ещё открыт, поэтому AP16 не объявляется полностью готовым/испытанным протоколом.

Все новые варианты NA01–NA16 и связанные предметные испытания — **«не выполнялось»**. Код, SQL, миграции, загрузка данных и испытания не начаты.
