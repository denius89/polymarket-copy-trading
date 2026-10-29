# Точная карта ошибок API ↔ БД первого сценария

29.10.2026 · Документальная детализация по прямому поручению владельца после PR №177; baseline main `11333018424fec4fe03d33d1fc45cf7b46217112`. Основания: [T01–T04/T14–T16](backend-contracts.md), [DB-T03 и стык Q03](backend-database-change-list.md), [закрытый реестр](backend-code-registry.md), [ADR-0064 §38](../../decisions/0064_first_session_database_contract.md). Имена контейнеров и параметров ниже фиксируются этим дополнением явно, а не приписываются прежнему решению. Это спецификация, без кода, SQL, миграций и испытаний поведения.

## 1. Граница и версия

Закрывается полевая часть DB-T03: reasonDetails → reason_data, fieldErrors → сохранённые details/review, params и происхождение ошибок Q03. C04 scope, last_input_receipt_id, unchanged, claim, атомарность и строгие C06-связи не пересматриваются. Остаются 34 прикладные таблицы; новых колонок и полной истории raw нет. Владелец 1 и владелец 2 равноправны.

Уточняются проектируемые receipt/v1 и review/v1; версия берётся из record_schema_version родителя, отдельного schemaVersion внутри JSON нет. Это завершение документального v1, а не разрешение считать произвольный прежний JSON совместимым. Если при будущей инвентаризации найдутся реально сохранённые записи иной формы, требуется отдельное решение о совместимости/версии и миграции; молчаливое исправление при чтении запрещено. Исторические ADR не переписываются.

## 2. Физические контейнеры и отображение

Объекты закрытые: перечисленные ключи обязательны в своём варианте, неизвестные ключи запрещены. NULL не заменяет объект/массив. Порядок свойств объекта незначим, порядок элементов массива значим. Пустой массив — установленное отсутствие элементов, не неизвестный результат.

| Сохранённое поле / вариант | Точная форма | Представление API |
| --- | --- | --- |
| command_receipt_details.reason_data, succeeded C04/C06 | Пустой объект `{}` | reasonDetails = `[]`; reasonCode = NULL из core |
| То же, rejected C04/C06 | Объект с единственным ключом `reasons`: непустой массив ReasonDetail | reasonDetails = точная копия reasons; reasonCode = reason_code core |
| command_receipt_details.response_data, succeeded C04 | Объект с единственным ключом `fieldErrors`: массив FieldError, в том числе пустой | fieldErrors = точная копия fieldErrors; остальные исходные result-поля из core |
| То же, rejected C04 или любой C06 | Пустой объект `{}` | Исторического fieldErrors в данном варианте команды нет; поле не выдаётся и не синтезируется из текущей формы |
| setup_reviews.reason_details, любой сохранённый C05 review | Объект ровно с двумя ключами: `reasons` и `fieldErrors`, оба массива | reasonDetails = reasons; fieldErrors = fieldErrors; primaryReasonCode = primary_reason_code колонки |

У review с allowed_to_start=true оба массива пусты, primary_reason_code=NULL. При false reasons непустой, первый code равен primary_reason_code; fieldErrors может быть пустым, например при одном AUTH_REQUIRED. При числовых ошибках NUMERIC_SETTINGS_INVALID входит в reasons в порядке T03; нечисловая причина не подавляет независимо установленные fieldErrors. normalization_valid=false может возникнуть и при невыбранном режиме: это не основание выдумывать ошибку неактивного F/q. Review.warnings остаётся отдельным существующим полем, не смешивается с reasons/fieldErrors.

У rejected receipt reasons[0].code строго равен core reason_code. Даже единственная причина без параметров хранится как один элемент с params={}; пустой reason_data у rejected — неполная запись. У succeeded C04 наличие fieldErrors не создаёт reasonCode и не превращает успех сохранения в отказ. У rejected C06 SETUP_INVALID не вычисляются новые fieldErrors и не копируются автоматически ошибки текущего draft: конкретный review сохраняет свои ошибки отдельно. Это не ослабляет ни одну обязательную связь START.

Из API-формы при проектировании записи reasons отображается обратно в указанный объект. В рабочем протоколе клиент не пишет reason_data: причины и ошибки устанавливает сервер. Сохранение receipt, его details и изменения ввода/START остаётся в одной ранее принятой транзакции. C05 сохраняет собственный immutable review и не создаёт обычный CommandReceipt.

## 3. ReasonDetail и его params

ReasonDetail содержит ровно `code` (из существующего реестра в контексте операции) и `params` (объект). Список сохраняется в порядке T03: основная причина первой, остальные только достоверно установленные и допустимые, без повторов code. Не следует исполнять дополнительные проверки после технической ошибки ради заполнения списка.

| Контекст | Допустимые code, в порядке приоритета |
| --- | --- |
| Rejected C04 | DRAFT_USED, DRAFT_EXPIRED, VERSION_CONFLICT |
| Rejected C06 | DRAFT_USED, DRAFT_EXPIRED, VERSION_CONFLICT, SESSION_NOT_SETTLED, CURRENT_SESSION_EXISTS, CAPABILITY_UNAVAILABLE, REVIEW_EXPIRED, REVIEW_STALE, SETUP_INVALID |
| Отрицательный review | AUTH_REQUIRED (только guest), SESSION_NOT_SETTLED, CURRENT_SESSION_EXISTS, CAPABILITY_UNAVAILABLE, VENUE_REQUIRED, TRADER_REQUIRED, SIZING_MODE_REQUIRED, TIMEZONE_REQUIRED, NUMERIC_SETTINGS_INVALID |

Для CAPABILITY_UNAVAILABLE params содержит ровно `capabilityReasonCode`: одно из PAPER_START_DISABLED, CATALOG_SOURCE_DISABLED, TRADER_START_DISABLED. При нескольких установленных запретах выбирается первый по этому порядку; вторых элементов с тем же CAPABILITY_UNAVAILABLE нет. Неизвестный trader не порождает TRADER_START_DISABLED. Для всех остальных code таблицы params строго `{}`. Expected/actual version, raw, тексты, ссылки и sessionId в params не добавляются.

Своя препятствующая session у rejected C06 остаётся в существующей related_session_id core. Ссылка в текущем ответе выдаётся только после актуальной авторизации, не внутри неизменяемых reasons. Для review/других ответов действуют текущие безопасные цели T07; эта карта не вводит исторический sessionId в JSON и не обещает ссылку, если её нельзя безопасно восстановить. Ранние transport/Auth/access/conflict ошибки и unknown не записываются как эти предметные reasons; их полный wire-конверт остаётся отдельным DTO-контрактом.

## 4. FieldError: поля, порядок и params

FieldError содержит ровно `field`, `code`, `params`. field — точное имя числового поля запроса. Массив включает не более одной ошибки на активное поле, максимум четыре: бюджет, выбранный размер, рынок, день. При невыбранном режиме F/q не активируются по умолчанию; максимум три независимых поля. Приоритет внутри поля: REQUIRED → INVALID_DECIMAL → OUT_OF_RANGE → INVALID_STEP → FIXED_LIMIT_EXCEEDED. Длина/тип/неизвестный ключ запроса проверяются до предметного сохранения, а не новыми fieldErrors.code.

| field API | Raw-колонка draft/review | unit параметров | Тип величин в params |
| --- | --- | --- | --- |
| rawBudget | raw_budget | virtual_USD | Money |
| rawFixedAmount | raw_fixed_amount | virtual_USD | Money; только selectedMode=fixed |
| rawCopyPercent | raw_copy_percent | percentage_points | Percent; только selectedMode=percent |
| rawMarketLimitPercent | raw_market_limit_percent | percentage_points | Percent |
| rawDailyBuyLimitPercent | raw_loss_limit_percent | percentage_points | Percent; дневной лимит новых покупок, не stop-loss |

Money — объект ровно `n`/`d`, обе величины канонические десятичные целочисленные строки без знака/ведущих нулей, кроме нуля; d>0, дробь сокращена, ноль только 0/1. До 64 цифр на компонент. Percent в этих params — строка в процентных пунктах с точкой и ровно двумя цифрами после неё, без знака/ведущих нулей целой части, кроме нуля: например `0.50`, `3.00`, `20.00`. Это формат нормализованных параметров ошибки, не новое ограничение raw: ввод `3,5` остаётся допустимым по T01. Единица percentage_points уже используется policy; нового финансового кода нет.

| code | Ровно эти ключи params | Ограничения |
| --- | --- | --- |
| REQUIRED | `{}` | NULL/пустой raw; одно поле field ошибки достаточно |
| INVALID_DECIMAL | `{}` | Нет raw, regexp или текста исключения |
| OUT_OF_RANGE | `min`, `max`, `unit` | Обе границы типа своего поля, взяты из исходной policy; min≤max |
| INVALID_STEP | `step`, `origin`, `unit` | Положительный шаг и точка отсчёта типа своего поля из исходной policy |
| FIXED_LIMIT_EXCEEDED | `max`, `unit` | Только rawFixedAmount; Money-предел этих корректных B/p/d после принятого округления вниз |

Лишние ключи, отсутствие любого указанного ключа, NULL, JSON number вместо строки/Money, смешанные единицы и половина n/d недопустимы. Для fixed сначала проходят собственные диапазон/шаг F и зависимости B/p/d; невалидная зависимость не даёт фиктивный max.

Для paper-mvp-settings-v1: B min/max=100/1 и 1000/1, step/origin=10/1 и 100/1; F min/max=5/1 и 200/1, step/origin=1/1 и 5/1; q min/max=`1.00`/`20.00`, step/origin=`0.50`/`1.00`; p min/max=`5.00`/`20.00`, step/origin=`1.00`/`5.00`; d min/max=`10.00`/`30.00`, step/origin=`1.00`/`10.00`. Источник — [принятая policy](../../policies/paper-mvp-settings-v1.json); значения не меняются. Новый review использует свою policy, старые params не обновляются по текущей policy.

## 5. Q03: источник ошибок текущего ввода

Q03.fieldErrors — сохранённые ошибки команды, создавшей **текущий ввод**, через setup_drafts.last_input_receipt_id → succeeded C04 → command_receipt_details.response_data.fieldErrors. Это не последний по времени receipt и не последняя проверка C05. Новых колонок не требуется.

Рядом Q03 обязательно выдаёт `fieldErrorsSource`: объект ровно `receiptId` (UUID из last_input_receipt_id) и `draftVersion` (каноническая положительная целочисленная строка из result_draft_version источника). Обе ссылки проверяются в том же согласованном чтении, что текущие значения draft: environment/draft/version должны совпадать, command_type=C04, outcome=succeeded, result_change_kind=created либо updated. Имена полей fieldErrorsSource — текущая API-проекция существующего источника, не новое хранилище или право читать чужой receipt. Доступ после claim определяется принятой исторической цепочкой.

| Ситуация | Q03 / исторический результат |
| --- | --- |
| Created/updated сохранил ввод и ошибки | Q03 показывает этот ввод, его version и ошибки этого receipt |
| Новый unchanged по тем же raw и актуальной версии | Его собственные ошибки принадлежат новому receipt; pointer не меняется. Q03 продолжает показывать источник создавшего ввод receipt |
| Policy изменилась без изменения raw | Q03 не пересчитывает ошибки, не утверждает соответствие текущей policy и не вычисляет флаг такой совместимости; C05 — явная новая проверка |
| Новое unchanged оценено по иной policy | Его fieldErrors могут отличаться от Q03; API различает receiptId/источник. Нельзя переписать pointer, чтобы скрыть различие |
| Последующий C05 сохранил review | Его fieldErrors выдаются с этим review и его policy_version_id; Q03 не подменяет ими ошибки сохранения |
| Старый C04 replay после updated/claim | Старый исход неизменен; Q03 показывает текущий ввод и его собственный источник |
| Источник/detail отсутствует, неверен или неизвестного формата | Целостный Q03 недоступен: существующий RECORD_UNAVAILABLE/503, без выдуманного `[]`, пересчёта или записи ремонта |

UI объясняет смысл «ошибки при сохранении этого ввода; для проверки по действующим правилам нужна новая проверка». Пустой fieldErrors говорит только об отсутствии числовых ошибок в исходном сохранении. Q03 не предоставляет разрешение запуска. В C04 нет сохранённого policy_version_id для этих ошибок: Q03 не приписывает им текущую policy и не извлекает её из времени. Для проверяемой версии policy используется конкретный C05 review. Полная история raw/новая policy-колонка C04 не добавляются.

## 6. Неизменяемый факт и текущая выдача

Receipt/details и review, включая порядок reasons/fieldErrors и точные params, неизменяемы. Replay C04/C06 и Q05 читают исходные значения, без повторной проверки по новой policy; отсутствие старых details не заменяется восстановлением из текущего draft. Формат времени/чисел не меняется из-за locale, RU/EN текст строится UI.

RequestId/X-Request-Id относится к текущей HTTP-передаче; nextAction и разрешённые ссылки — к текущему доступу; restrictedGroups — к текущей проекции Q06. Они не входят в reason_data/response_data/review.reason_details. Корректно сохранённый отказ читается Q05 с HTTP 200; reasonCode остаётся отказом исходной команды. Pending/503 не превращаются в сохранённый rejected. Auth/claim/logout используют ранее принятые защищённые контексты и не получают новые обычные receipts из-за этой карты.

Q06 не получает дополнительную группу ошибок и не декодируется как полный сохранённый snapshot. Закрытая группа отсутствует с restrictedGroups; доступная пустая группа отличается от повреждённой. Текущая авторизация, согласованное состояние и обязательный audit до выдачи сохраняются. Новые URL/секреты/разрешения внутри params запрещены.

## 7. Полнота, пределы и ошибки формата

Каждое ограниченное JSON-поле имеет собственный предел 16 384 байта компактного UTF-8: отдельно reason_data, response_data, setup_reviews.reason_details и warnings. Обёртка и оба массива review входят в один предел reason_details; не по 16 КиБ на каждый массив. Представление для измерения без незначимых пробелов, с минимальным экранированием JSON и неэкранированными допустимыми Unicode-символами; фиксированные keys/codes/params этой карты ASCII. Это не fingerprint команды и не разрешение менять raw.

Проверяются схема, типы, количество/порядок, уникальность field/code, допустимость кода по операции, согласие основной причины с core и допустимые units. Нельзя обрезать массив, убрать params или вторую причину ради лимита. Превышение при подготовке результата — техническая ошибка до commit: полный откат предметной транзакции, не durable business rejection. Unknown commit сохраняет прежний протокол выяснения. При чтении malformed/oversized/неподдерживаемой записи — RECORD_UNAVAILABLE/503 без partial success, нового ключа или ремонта; временная инфраструктурная недоступность — SERVICE_UNAVAILABLE. Если malformed уже найден в Q06-пути, audit не превращает его в разрешённый нулевой снимок.

Строгие дубли имён проверяются до преобразования в jsonb; сравнение ключей учитывает эквивалентные escapes. Неизвестные вложенные поля не игнорируются. На полном format scan проверяется вся запись родительского v1 вместе с details, а не только record_schema_version. Защищённый отчёт/место доказательств остаются M05; здесь нет исполняемого валидатора.

## 8. Оставшиеся зависимости

Поля этой карты и Q03 provenance определены документально. M01 ещё не равен готовой интеграции: остаются полные DTO остальных запросов/ответов, Q05 locator, expected slot, Q06-группы и безопасные цели навигации, защищённый Auth/claim/logout протокол, codecs/публикация policy и совместимость компонентов. M02–M03 требуют изолированных тестовых механизмов; M05 — конкретного хранилища/формата/прав evidence. Реализация и испытания требуют отдельного поручения.

Связанные ожидаемые проверки: [карта целостности](database-integrity-matrix.md), [подкейсы J01–J10](database-synthetic-examples.md), [сбои и сверка](database-fault-reconciliation.md). A01–A112 не объявляются пройденными. Проверки ссылок/документов не являются DB/API/Auth/concurrency/restore испытаниями.
