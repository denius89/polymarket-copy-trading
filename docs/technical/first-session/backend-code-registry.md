# Закрытые реестры кодов первого сценария — H02 и H03

30.10.2026 · **Текущее издание first-session-registry-v2.** По явному принятию владельца добавлен только CATALOG_CHANGED для изменения каталога между страницами Q02: HTTP409, форма ошибки и перезапуск списка — [дополнение API §14](backend-api-forms-addendum.md). Предыдущие коды/значения/роли и четыре recordSchemaVersion=v1 сохраняются. Описания v1 ниже отражают исходное издание; это не миграция сохранённых данных. Q06 без session не получает новый audit-kind или grant этим изданием; DB-API-09 открыт.

29.10.2026 · По поручению владельца после PR №177 завершена [точная карта ошибок API ↔ БД](database-error-field-map.md): контейнеры reasons/fieldErrors, закрытые params и источник ошибок Q03. Это уточнение документов в рамках T01–T17, без пересогласования C04. Прежние пометки о незавершённости именно этой карты ниже исторические; полные DTO/Auth/компоненты и испытания остаются отдельно.

29.10.2026 · **Принято владельцем целиком.** Издание first-session-registry-v1, часть [пакета](backend-design.md). Дополнения T01–T17 и точное употребление кодов — в [едином контракте §§6–22](backend-contracts.md). Набор runtime-кодов этим дополнением не расширен. Реестр документальный; наличие кода не означает реализованный endpoint, выданное право или прошедший тест.

## 1. Правила

Код имеет одно значение в конкретном поле. Различаются: поддерживаемый первым сценарием; известное действие/раздел без реализованной операции; неизвестное значение. Неизвестное отклоняется, сохранённая неизвестная запись не читается как ближайшая знакомая. Изменение реестра — новое проверяемое издание; сохранённая история не переименовывается. Формат записи/версия ресурса/версия реестра независимы.

Идентификаторы environment, provider_subject, source_ref, role_revision_ref и фактических назначений — проверяемые ссылки/конфигурация, не свободный клиентский выбор и не вымышленные enum. Полный environment allowlist закрепляется с конфигурацией стенда; paper — режим продукта, не автоматически имя среды. Личные ID владельца 1 и владельца 2 не являются разными ролями.

## 2. Команды, результаты и форматы

| Поле/реестр | Значения |
| --- | --- |
| Команды | C01 RequestEmailEntry; C02 VerifyEmailEntry; C03 ResendEmailEntry; C04 SaveSetupDraft; C05 ReviewSetup; C06 StartPaperSession; C07 Logout |
| Чтения | Q01 профиль; Q02 каталог; Q03 draft; Q04 собственная session; Q05 результат команды; Q06 административный просмотр |
| command_keys.command_type | C04, C06; C04 после явного дополнения физических документов |
| Операция C04 | create, update |
| receipt.outcome | succeeded, rejected |
| Результат изменения C04 | created, updated, unchanged |
| Наблюдение Q05 | pending, committed, rejected |
| Семейства форматов | review, settings, snapshot, receipt; у каждого recordSchemaVersion=v1 |
| Канонизация / hash | command-jcs-v1 / sha256; request_hash 32 байта |

Q05 committed соответствует найденному succeeded receipt. Pending означает отсутствие установленного окончательного результата, не доказательство текущего исполнения и не разрешение нового ключа. Claim имеет собственный draft_claim_receipt; C01–C03 не получают обычный receipt с credentials.

## 3. Политики, расчёты и источники

| Назначение | Код / формат |
| --- | --- |
| Числовая policy | paper-mvp-settings-v1 |
| Проверка/нормализация | paper-settings-calculation-v1 |
| Расчёт первого snapshot | paper-empty-snapshot-v1 |
| Срок оценки | paper-evaluation-deadline-v1 |
| User login policy | user-login-policy-v1 |
| Staff login policy | staff-login-policy-v1 |
| Guest proof | guest-hmac-sha256-v1 |
| source_hash | sha256: и 64 строчные hex-цифры, hash точных байтов закреплённого источника |

Существующие policy-коды сохраняются: floor_min_session_position_and_day_usd, confirmed_individual_trader_buy_notional, session_budget_usd; signal_max_age_applies_to=signal. Версия алгоритма срока не подменяет сохраняемую фактическую tzdb. Источник первого стенда явно synthetic; код реального источника/автоматический fallback не добавляются.

## 4. Предметные значения

| Поле | Значения |
| --- | --- |
| venue code | polymarket, limitless |
| product mode | paper |
| locale | ru, en |
| sizing mode | fixed, percent |
| draft owner | guest, user |
| Вычисляемое состояние draft | editable, expired, used; used приоритетнее expired |
| slot observation | not_applicable, absent, present |
| Создаваемый lifecycle | active |
| control state | copying_not_connected |
| content state | EMPTY |
| data origin | synthetic |
| coverage | no_trade_data |
| money unit | virtual_USD |
| Initial flow/journal kind | initial_paper_funding |
| Initial account codes | paper_cash, virtual_funding_source |
| draft.step | select_trader, configure, review |
| draft.entryContext | catalog, trader_details, session_summary либо NULL |

Active не означает подключённую торговлю. p/d остаются лимитами по policy, d не stop-loss. Future paused/stopped/manual/unknown/dust не становятся допустимыми результатами C06; их изолированные тестовые состояния относятся к M02/H05. Step/entryContext не доказывают прохождение проверки и не дают права запуска.

## 5. Ошибки и причины

| Категория | Коды | Правило |
| --- | --- | --- |
| Транспорт/структура | INVALID_REQUEST, REQUEST_TOO_LARGE, UNSUPPORTED_MEDIA_TYPE | 400/413/415, без предметного исполнения |
| Вход | AUTH_REQUIRED, AUTH_EXPIRED, AUTH_REVOKED | 401; после входа восстановить прежнее намерение |
| Подтверждение | AUTH_VERIFICATION_FAILED, MFA_REQUIRED, MFA_ENROLLMENT_REQUIRED | Только нужный ограниченный этап; без выдачи полного доступа |
| Частота | RATE_LIMITED | 429 и безопасное время следующей попытки |
| Функция запрещена | ACCESS_DENIED | 403 без закрытых сведений |
| Ресурс отсутствует/скрыт | RESOURCE_NOT_FOUND | Одинаковый 404 без раскрытия чужого объекта |
| Ключ | KEY_REUSE_CONFLICT | 409; исходный результат не меняется |
| Draft | VERSION_CONFLICT, DRAFT_EXPIRED, DRAFT_USED | 409 для новой команды |
| Review | REVIEW_STALE, REVIEW_EXPIRED, SETUP_INVALID | 409 при запуске; исправление/новый review |
| Сессия мешает запуску | CURRENT_SESSION_EXISTS, SESSION_NOT_SETTLED | 409; только разрешённая собственная ссылка |
| Известный запрет | CAPABILITY_UNAVAILABLE | 409; durable business rejection после допуска к ключу |
| Каталог изменился между страницами | CATALOG_CHANGED | 409 только Q02-list; без durable receipt, следующая попытка списка явно с первой страницы |
| Техническая недоступность | SERVICE_UNAVAILABLE, RECORD_UNAVAILABLE | 503; не окончательный business rejection |
| Исход выясняется | COMMAND_OUTCOME_UNRESOLVED | 202 как наблюдение; исходный ключ сохраняется |

HTTP сам по себе не определяет существование durable receipt. AUTH_VERIFICATION_FAILED не раскрывает аккаунт. Внутренняя причина отзыва login не обязана раскрываться публично. Непрочитанная/повреждённая policy — техническая ошибка, не CAPABILITY_UNAVAILABLE.

Уточнения известного запрета: PAPER_START_DISABLED, CATALOG_SOURCE_DISABLED, TRADER_START_DISABLED. Причины незавершённого review: VENUE_REQUIRED, TRADER_REQUIRED, SIZING_MODE_REQUIRED, TIMEZONE_REQUIRED, NUMERIC_SETTINGS_INVALID, AUTH_REQUIRED. Review может содержать несколько причин и сохраниться как предметно отклонённый без технического провала C05. Приоритет причин принят в backend-contracts §8; семантика безопасных параметров — §9. Типизированное отображение в физический JSON определено [точной картой ошибок](database-error-field-map.md); исполняемая схема ещё не создана. Числовые правила не меняются.

| fieldErrors.code | Значение |
| --- | --- |
| REQUIRED | Обязательное значение не задано |
| INVALID_DECIMAL | Строка не является допустимым десятичным числом |
| OUT_OF_RANGE | Нарушен принятый диапазон |
| INVALID_STEP | Нарушена сетка policy |
| FIXED_LIMIT_EXCEEDED | Новый fixed выше точного допустимого предела |

Field errors привязаны к известному полю; по одной ошибке на поле, порядок REQUIRED → INVALID_DECIMAL → OUT_OF_RANGE → INVALID_STEP → FIXED_LIMIT_EXCEEDED. Допустимы только типизированные безопасные границы/шаг/единица/предел по backend-contracts §§7–9. Сырые сообщения БД/библиотек не попадают в ответ. Неактивный ввод не становится действующим параметром.

Warnings: SYNTHETIC_DATA, COPYING_NOT_CONNECTED. Информируют, не запрещая согласованный пустой запуск.

NextAction: authenticate, complete_totp, enroll_totp, select_trader, continue_setup, review_setup, view_session, view_summary, recover_setup, resolve_command, retry_later. При отсутствии безопасного действия nextAction=NULL, без нового enum. Карта выбора — backend-contracts §12. Это навигация, не разрешение; автоматического start нет. Resolve_command работает с исходным ключом; recover_setup не обещает несуществующий перенос draft.

## 6. Аудит и outbox

| audit event_kind | Момент | outcome_code |
| --- | --- | --- |
| paper_session.started | Успешный C06 в общей транзакции | succeeded |
| setup_draft.claimed | Успешный claim в общей транзакции | succeeded |
| admin_session.read_authorized | Разрешённая выдача Q06 вместе с evidence | authorized |

Все event_schema_version=v1. Audit выдачи не доказывает доставку/прочтение. Установленный actor/login и ссылки обязательны по физическому контракту. Отказы до установления личности — защищённая техническая диагностика без вымышленного actor; новые виды прикладного audit требуют расширения реестра. Этот пакет не добавляет гостевой C04 в user/staff-only audit_events.

| Outbox | Значения |
| --- | --- |
| event_type | paper_session.started |
| event_schema_version | v1 |
| consumer_name | paper_start_observer |
| consumer result_code | observed |
| delivery_state | pending, processing, retry_wait, processed, needs_review |
| Первый payload | Пустой объект; обязательные scope/IDs/версии в колонках |

Ошибки доставки: EVENT_TYPE_UNSUPPORTED, EVENT_FORMAT_UNSUPPORTED, EVENT_CONSUMER_UNSUPPORTED, EVENT_DATA_INVALID, EVENT_RECEIPT_INVALID, EVENT_TEMPORARILY_UNAVAILABLE, EVENT_PROCESSING_TIMEOUT, EVENT_LEASE_EXPIRED. Неизвестный формат/тип/потребитель и повреждение требуют разбора; временный сбой подчиняется H04. Старый token не разрешает записать ошибку поверх новой попытки.

## 7. Auth, статусы и отзыв

| Поле | Значения |
| --- | --- |
| Полный login realm | user, staff |
| User provider | supabase_auth |
| Staff provider | staff_webauthn |
| assurance | email_verified, email_totp_verified, webauthn_uv_verified |
| user/staff principal status | active, blocked |
| staff identity status | active, revoked |
| assignment status | active, revoked |
| Вычисляемое состояние assignment | not_started, effective, expired, revoked |

Email_verified — полный вход только когда TOTP не требуется. Для Owner первого стенда — webauthn_uv_verified. Pending MFA/recovery не auth_sessions. Пользовательской identity новый status-столбец не добавляется.

Login revoke reasons: logout, superseded_login, principal_blocked, identity_revoked, mfa_reset, mfa_disabled, owner_recovery, security_revocation.

Assignment revoke reasons: assignment_withdrawn, access_reconfigured, principal_blocked, security_revocation.

Причина не даёт право выполнить отзыв. Истечение вычисляется, не записывается как ручной отзыв. Блокировка попытки OTP не равна users.status=blocked.

## 8. Роли, действия и разделы

Единственная системная роль — owner. Владелец 1 и владелец 2 имеют разные identities/назначения той же роли; нет ролей owner_1/owner_2. Изменяемые пресеты/кастомные роли используют доверенные role_ref/role_revision_ref, название не даёт полномочий. Учебная role-matrix не является правами по умолчанию.

Действия: read, create, edit, publish, run, stop, export. Для Q06 используется read; остальные известны как действия общего контракта, но не создают исполняемых операций первого среза.

| section_code | Раздел |
| --- | --- |
| ADM-01 | Обзор |
| ADM-02 | Пользователи |
| ADM-03 | Сессии |
| ADM-04 | Инциденты |
| ADM-05 | Сверка |
| ADM-06 | Площадки и данные |
| ADM-07 | Данные и рейтинг |
| ADM-08 | Тарифы и рефералы |
| ADM-09 | Поддержка |
| ADM-10 | Уведомления |
| ADM-11 | Обратная связь |
| ADM-12 | Журнал действий |
| ADM-13 | Финансы и выплаты |
| ADM-14 | Сотрудники и доступ |
| ADM-15 | Подключения и безопасность |
| ADM-16 | Тексты и языки |
| ADM-17 | Аварийное управление |
| ADM-18 | Маркетинг |

Q06 data_type_code: session.summary, session.settings, session.financial_snapshot (read/ADM-03); user.minimal_context (read/ADM-02). Содержание и обязательность — [доступ §6](backend-auth-access.md#6-q06-и-доказательства-выдачи).

Venue_scope: one с venue_id либо all с NULL venue_id; всегда в рамках остальных полей grant. Пустое поле не означает all. Product_mode=paper; environment точная. Нет нового приоритета запретов, склеивания частей grants или права export из read. Набор групп Q06 — проекция полной Owner-роли на первый сценарий, не новая сокращённая системная роль.

## 9. Проверка

Неизвестные/недопустимые сочетания; история без переименования; невозможность частичный snapshot выдать за полный; безопасные причины; Q06 groups=evidence; отсутствие маршрута по одному известному action; старый receipt после обновления реестра. Для фактической реализации нужны проверенные декодеры/guards/публикация, не только этот список.

## 10. Полевая карта пояснений

[Карта ошибок](database-error-field-map.md) определяет закрытые ключи params для уже перечисленных code: min/max/unit, step/origin/unit, max/unit, пустой объект либо capabilityReasonCode. Новых error/reason codes и ролей нет. percentage_points — существующая единица policy, virtual_USD — денежная единица первого paper-среза. Q03 fieldErrorsSource — происхождение исторических ошибок, не новый исход команды. Прежняя пометка о полевой сверке в §5 закрыта в этом объёме.

## 11. Издание v2: CATALOG_CHANGED и границы ответа

CATALOG_CHANGED используется только после проверки допустимого cursor/контекста и текущего доступа, когда установлено изменение состояния разрешённого каталога между страницами. Полная форма: reasonCode=CATALOG_CHANGED; reasonDetails — один code=CATALOG_CHANGED/params={}; nextAction=select_trader; nextActionParams ровно разрешённый venueId. Полей items/nextCursor/receipt нет. UI явно начинает новый обход и не смешивает страницы/поздние ответы; сохранённый draft/выбор не стирается.

Malformed cursor/несовпадение параметров —400 INVALID_REQUEST; потеря права — access/hidden ответ; невозможность прочитать состояние —503, не CATALOG_CHANGED. Нет новой причины сохранённого C04/C06/review. COMMAND_OUTCOME_UNRESOLVED остаётся наблюдением202, не reasonCode прямого503; закрытая форма Q05 не получает дополнительный reasonCode.

Остальные точные формы early/technical errors, warnings, nextActionParams и correlationId — [дополнение §§2/5/6](backend-api-forms-addendum.md). Реестр событий аудита не расширен: ответ Q06 без существующей session требует отдельного решения по правам/хранению/evidence. Реализация и испытания не выполнены.
