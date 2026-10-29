# Команды и форматы первого сценария — H02

29.10.2026 · Принятая часть [пакета H01–H06](backend-design.md). Это документальный контракт и отображение принятой схемы, не OpenAPI/JSON Schema, исполняемые декодеры или SQL. Дополнение C04 должно быть явно перенесено в физическую спецификацию через [передачу БД](backend-database-change-list.md).

## 1. Запрос выражает намерение

Actor/realm/environment устанавливает сервер. UserId/роль, баланс, готовые effective settings или разрешение запуска из браузера не являются доверенными. clientCommandId — UUID v4 клиента до отправки C04/C06, один ключ на одно намерение. requestSchemaVersion обозначает формат запроса; correlationId — отдельная диагностика.

| Операция | Состав предметного запроса |
| --- | --- |
| C04 create | Полный набор сохраняемых полей формы; сервер назначает draftId, ожидаемой версии нет |
| C04 update | draftId, expectedDraftVersion, полный набор сохраняемых полей формы |
| C05 | draftId, expectedDraftVersion, proposedTimezone |
| C06 | reviewId, expectedDraftVersion, явное ожидаемое состояние слота |

Полный набор формы: locale, step, entryContext, venueId, traderId, selectedMode, rawBudget, rawFixedAmount, rawCopyPercent, rawMarketLimitPercent, rawDailyBuyLimitPercent, proposedTimezone. Незаполненное значение передаётся NULL; отсутствие обязательного ключа не означает скрытый PATCH прежнего поля. Полные запросы/точные поля Auth имеют собственный протокол H01; этот список не превращает одноразовые credentials в C04/C06.

В C06 слот: absent без generation либо present с generation. Нулевое поколение не кодирует отсутствие. not_applicable допустим только в guest review, не в запросе user-запуска. Проверенная конфигурация берётся из immutable review. Вход/review не запускает сессию автоматически.

## 2. Дополнение C04 и durable результат

Расширяются существующие command_keys/command_receipts/command_receipt_details с условными требованиями по типу команды. C06 сохраняет все строгие обязательные связи успешного запуска.

Область ключа: environment + actor realm + постоянный actorId + commandType + clientCommandId. Для user — постоянный userId, без loginId. Для guest — серверный постоянный ID гостевого Auth-контекста, установленного до первого C04; ID без proof не даёт доступа. Создание/изменение draft — варианты намерения C04, а не способ обойти конфликт одного ключа.

| Успешный результат C04 | Смысл |
| --- | --- |
| draftId | Исходный созданный/сохранённый draft |
| ownershipId | Историческое основание владения при выполнении |
| draftVersion | Версия после исходного выполнения |
| changeKind | created / updated / unchanged |
| lastSavedAt, expiresAt | Моменты исходного результата |
| fieldErrors | Сохранённые безопасные ошибки полей |

Обязательные IDs/версия/исход сохраняются отдельными колонками. Полевые ошибки — типизированные details. Не добавляется полная история raw-ввода каждой правки. Новый короткий невалидный числовой ввод может быть успешно сохранён; это не означает валидные effective settings.

| Ситуация | Правило |
| --- | --- |
| Известный ключ | Текущий доступ → проверка исходного fingerprint → прежний receipt; без повторной записи draft |
| Новый ключ | Владение/доступность/used/expiry → expectedVersion до сравнения содержимого |
| Актуальная версия, те же значения | Сохраняется receipt unchanged; draft/version/lastSavedAt/expiry не меняются |
| Устаревшая версия, те же значения | VERSION_CONFLICT |
| Реальное изменение ввода | version+1 и новый TTL в той же транзакции с key/receipt/details |
| После успешного C06 | Новый C04 запрещён; прежний receipt доступен после авторизации, без оживления draft |
| Ошибка транспорта/доступа до допуска к ключу | Нет предметного receipt |
| Окончательный предметный отказ после допуска | Rejected receipt без изменения draft |
| Неизвестный commit | Выяснение результата исходного ключа, не новый ключ |

Пример: сохранение вернуло version5, следующая команда создала version6. Повтор первой возвращает результат version5; Q03 отдельно показывает version6. UI не перезаписывает новую форму старым receipt.

После claim guest proof больше не открывает draft/receipts. Текущий user восстанавливает прежний C04 через подтверждённую цепочку ownership/claim; ключ не переносится в user realm и не исполняется заново. Поиск должен работать также при потере ответа первоначального guest create. Изменение Q05, который в baseline описан только для user, передано БД/общему контракту явно.

Изменение draft и key/receipt/details атомарны. Не появляется durable pending. Точный FK-набор, XOR user/guest, размещение исходного target/ownership для rejected C04 и уникальные индексы ещё должны быть описаны чатом БД; пакет не придумывает готовые колонки.

## 3. Типы, размеры и отображение

| Область | Принятое правило |
| --- | --- |
| Resource ID | Серверный UUID v4; внешние provider/venue IDs сохраняют собственную область и формат |
| Версии/sequence/generation и bigint-счётчики | Целочисленные строки даже для 1; без ведущих нулей, кроме 0 |
| Exact money | Сокращённая пара целочисленных строк n/d; d>0, ноль 0/1, до 64 цифр без знака на компонент |
| Знак | Начальные суммы положительны/неотрицательны по полю; противоположная ledger entry signed. Это не разрешение отрицательного бюджета |
| Нормализованные проценты | API decimal-строка в процентных пунктах; DB integer в сотых п.п.: 300 ↔ 3.00% |
| Raw строки | NULL, пустая строка, 20 и 20.00 различаются; без trim, NFC или числового переписывания; до 64 Unicode code points |
| Время | UTC с Z, ровно три знака миллисекунд; now ≥ expiresAt означает истечение |
| C04/C06 body | Несжатый UTF-8 JSON до 65 536 исходных байт до разбора, включая пробелы; вложенность 8 с корнем 1 |
| JSON-поля дополнительных данных | До 16 384 байт собственного компактного UTF-8 представления каждого ограниченного поля |
| Структурная однозначность | Дубли имён, включая эквивалентные escapes, запрещены; неизвестные поля C06 запрещены |
| Ошибки кодировки | Неисправимые/непредставимые строки отклоняются, не исправляются молча |

Полные сохранённые записи выводятся из колонок принятых четырёх физических блоков. Обычное имя snake_case → camelCase; record_schema_version → recordSchemaVersion=v1. Пара *_n/*_d отображается одним объектом n/d, необязательная пара — целиком NULL, полупары запрещены. Для процентов используется указанная единица, а не необработанное integer-значение БД.

Явные смысловые исключения: raw_loss_limit_percent → rawDailyBuyLimitPercent; loss_limit_percent → dailyBuyLimitPercent; effective_loss_limit_n/d → effectiveDailyBuyLimit. Это дневной лимит новых покупок, не stop-loss. Существующие raw_market_limit_percent/market_limit_percent сохраняют значение p по policy, не получают нового финансового смысла от имени. Необязательная причина/ссылка и пустые массив/объект сохраняют разные смыслы.

## 4. Четыре независимых формата

Форматы — полные сохранённые факты. API выдаёт разрешённое представление. Частичный административный ответ не декодируется как полный snapshot/v1.

### Review v1

Полевая основа — [setup_reviews](database-physical-catalog-review.md#8-shadowsetup_reviews--неизменяемый-результат-проверки): ID/среда/формат, draft/version/ownership/owner, venue и согласованная группа catalog/source/trader/revision/guards, обязательные policy/control refs/версии, selectedMode, пять raw-полей, proposedTimezone, normalizationValid, нормализованные настройки, наблюдение слота, allowedToStart/requiresAuthentication, primaryReasonCode/reasonDetails/warnings и checkedAt/expiresAt/createdAt.

При normalizationValid=false весь нормализованный набор NULL, а не частично действующие параметры. При true — B, p/d, P/D и только выбранный F либо q. Для выбранного известного trader заполнена вся согласованная группа; неполная тройка запрещена. Guest всегда requiresAuthentication=true, allowedToStart=false, slot not_applicable. User absent отличается от present с generation, даже если current pointer пуст. Политика/controls должны быть достоверно прочитаны: техническая недоступность не изображается предметным review.

Review живёт 10 минут, содержит собственную копию, ссылается на историческое ownership. allowedToStart — результат на момент проверки, а не право обойти C06.

### Settings v1

Полевая основа — [settings_revisions](database-physical-session-ledger.md): ID/среда/формат, session, sequence/previousRevision, B, sizingMode и выбранный F/q, p/d и точные P/D, policy/calculation refs, signalMaxAgeSeconds, commandReceipt, actorUser и createdAt.

Начальная sequence=1, previous=NULL; точная копия выбранных валидных параметров review. Неактивный raw-ввод остаётся в draft/review. Signal age=30 секунд из policy, не пользовательская настройка. Будущая политика не переписывает сохранённую settings.

### Snapshot v1

Полевая основа — [session_snapshots](database-physical-session-ledger.md): ID/среда/формат, session/version/sessionVersion, settingsRevision, ledgerSequence, projectionCalculationVersion, lifecycle/control/content/dataOrigin/coverage, unit, initialFunding/free/reserved/positionCost/positionValue/equity/tradingResult, tradeCount/positionCount/orderCount, asOf/createdAt.

Все суммы и счётчики обязательны. В первом пустом запуске initialFunding=free=equity=B; reserved/positionCost/positionValue/tradingResult=0/1, счётчики=0. Funding не добавляется дважды. Текущий снимок выбирается по pointer сессии; settings — по его ссылке, не по max(createdAt). Нет/повреждён обязательный snapshot — техническая недоступность после авторизации, без NULL→0, ремонта или нового funding.

### Receipt v1

Полевая основа — [command_receipts/details](database-physical-operations-access.md) с принятым дополнением §2. API объединяет key metadata, core outcome и details в один результат, не создавая второй источник истины. Формат parent receipt определяет details; у details нет независимой версии.

Успешный C06 требует исходные sessionId/settingsRevisionId/snapshotVersion/sessionVersion; успешный C04 — результат §2. Эти варианты не взаимозаменяемы. Rejected требует безопасную reasonCode; связанная блокирующая session допустима только собственная и при текущем разрешении. Outcome только succeeded/rejected; pending относится к наблюдению Q05. У каждого нового receipt ровно одни обязательные details; их отсутствие — неисправность, не доказанный архив.

## 5. Fingerprint и восстановление результата

command-jcs-v1: строгий разбор/структурная проверка → каноническое намерение → JCS → SHA-256, 32 байта request_hash. Фиксируются версия канонизации и алгоритм. [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) — техническое основание, прочитано 29.10.2026.

Включаются доверенная область/тип команды, версия запроса, target/операция, ожидаемые версии и значимые сохраняемые значения. Для C04 — все поля формы, в том числе сохраняемые locale/step, create/update и draft при update. Для C06 — review, ожидаемые версии/слот и проверенная конфигурация из immutable review; браузерные балансы не используются.

Порядок JSON-ключей и пробелы вне строк не влияют. Raw-строки влияют точно; нет trim/NFC. Cookie, loginId, correlationId и локализованные подписи не участвуют. Серверные новые IDs/моменты выполнения не должны делать одинаковое намерение различным при повторе.

Старый ключ сравнивается по сохранённой версии канонизации. Истёкший review, новая policy или новое устройство не переисполняют успешный ключ. Неизвестный/повреждённый receipt не равен отсутствию. Повтор после новой авторизации возвращает прежний успех/отказ; не создаёт второго start audit/outbox. Неизвестный commit выясняется на исходном ключе из основного хранилища; отсутствие результата при первом Q05 не доказывает rollback.

Для нового C06: повторный допуск после ожиданий; максимум три попытки всего при доказанном serialization/deadlock rollback; общий монотонный бюджет 5 секунд, включая ожидания и случайные паузы 50–150 мс. Пауза, не помещающаяся в остаток, не сокращается ради новой попытки. Unique violation разбирается отдельно, business rejection не повторяется, unknown commit не считается rollback. Эти числа не распространяются автоматически на C04/C05/Auth.

## 6. Границы детализации и проверки

Приняты отображение полей и основные варианты, но исполняемые DTO/декодеры ещё не написаны. До их реализации необходима полная сверка полей с физической схемой после C04, включая вложенную форму ожидаемого слота/проекции Q06 и точные обязательности.

Не утверждены молча: принятие десятичной запятой/точки/экспоненты во внешнем raw-парсере; приоритет нескольких одновременно верных причин; полная структура reasonDetails/fieldErrors и безопасных параметров; таймауты/повторы остальных API; физический guest key/поиск после claim. Эти детали фиксируются явно перед реализацией в пределах принятых правил. Строгое сохранение исходного raw не предрешает допустимость его числового разбора.

Проверить: типы/64–65 границы/вложенность/дубли; n/d без float; все NULL-варианты; полный round-trip каждого формата; эталонные JCS-векторы и конфликт ключа; C04 create/update/no-op/replay после последующей правки/claim/expiry/used; C06 после нового login; сохранённые отказы; история после обновления; повреждение details/snapshot. Ссылки — A54–A57/A79–A99/A101–A107/A110–A112 и [матрица](database-integrity-matrix.md). Все проверки запланированы.
