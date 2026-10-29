# Физическая схема БД — блок 4: команды, аудит, события и доступ

29.10.2026 · **Предложение заключительного блока для согласования целиком.** Блоки [1](database-physical-design.md), [2](database-physical-catalog-review.md), [3](database-physical-session-ledger.md) приняты; этот блок ещё не принят. Baseline main `287e2639cecd751ff4812e15e815efa79ab3757e`. Основания: [ADR-0064](../../decisions/0064_first_session_database_contract.md), [data-model §22–23](data-model.md), [commands](commands.md), [auth-policy](auth-policy.md), [контракт доступа админки](../../design/admin/staff-access-2026-10-18/contract.md). Только документ: без SQL, кода, миграций, создания аккаунтов и развёртывания.

## 1. Общие соглашения и состав

16 таблиц shadow: command_keys, command_receipts, command_receipt_details, draft_claim_receipts; audit_events, audit_authorizations; outbox_events, consumer_event_receipts; staff_principals, staff_auth_identities, staff_assignments, staff_assignment_grants; login_policy_versions, login_policy_controls, auth_sessions, staff_login_slots. Разделение результата, деталей, аудита и доставки позволяет сохранить доказательства без превращения временного состояния worker в исход пользовательской команды.

Общие колонки **каждой** таблицы, если ниже не повторены: environment text NOT NULL, id uuid NOT NULL (серверный UUID v4), created_at timestamptz NOT NULL. PK `(environment,id)`. Все ссылки ниже включают environment; для условных FK сначала проверяется полнота соответствующего варианта, чтобы NULL не обходил принадлежность. Время — серверное UTC с миллисекундами; версии bigint положительны, без сброса при переполнении, в API строки. JSON — только безопасные типизированные дополнительные сведения, не контейнер вместо владельца/денег/обязательных ссылок; максимум 16 КиБ компактного UTF-8 на поле. Неизвестные коды не трактуются как разрешённые.

Ни одной общей учётной записи: **владелец 1** и **владелец 2** — отдельные равноправные staff principals. Настоящие identity, email, пароли, cookies, OTP, passkey private material и recovery-коды не добавляются в документы/fixtures/Git. Прикладной guard Auth не заменяет проверку провайдера. Recovery/регистрация ключей/OTP остаются отдельной проверяемой границей бэкенда; новый вход через обходной «готовый role» не допускается.

## 2. Ключ и окончательный результат команды

### 2.1. `command_keys`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| actor_realm | text | Да; user для C06 первого среза |
| actor_user_id | uuid | Да; FK users, постоянный актор, не login ID |
| command_type | text | Да; тип C06 по общему реестру, не произвольная строка клиента |
| client_command_id | uuid | Да; единственный логический ключ UUID v4, созданный клиентом до отправки |
| canonical_request_version, hash_algorithm | text | Да; известные серверу версии канонизации и отпечатка |
| request_hash | bytea | Да; отпечаток точного канонического намерения; размер/алгоритм фиксируются в H02 сводной передачи |
| receipt_id | uuid | Да; единственный окончательный receipt этого ключа, отложенный FK |

Unique(environment, actor_realm, actor_user_id, command_type, client_command_id). Дополнительный unique(environment,id,receipt_id) для обратной ссылки receipt. В транзакции заранее назначаются оба серверных ID. Вставка ключа с обязательным receipt_id резервирует уникальность, даже когда receipt ещё не вставлен; отложенный FK запрещает commit без результата. Это **не отдельный долговечный pending**: нет commit между ключом и receipt. После commit ключ/отпечаток/связь неизменны. Откат убирает оба. Нет самостоятельного фонового истечения ключа и нет TTL по login/draft.

Канонизация включает review/ожидаемые версии и смысловые параметры C06, но не RU/EN подписи. При повторе используется сохранённая версия канонизации/алгоритма; неизвестная версия закрывает чтение/исполнение, не делает ключ свободным. Другой payload того же key — конфликт без замены прежнего результата. Авторизация проверяется заново, смена устройства не создаёт новую область ключа.

### 2.2. `command_receipts`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| record_schema_version | text | Да; v1 |
| command_key_id | uuid | Да; unique(environment,command_key_id); FK `(environment,command_key_id,id)` → command_keys(environment,id,receipt_id) |
| outcome | text | Да; succeeded либо rejected, только окончательный исход |
| reason_code | text | Обязателен при rejected, NULL при succeeded |
| result_session_id, result_settings_revision_id | uuid | Оба обязательны при succeeded, иначе NULL; результат именно исходного C06 |
| result_snapshot_version, result_session_version | bigint | Оба обязательны при succeeded, иначе NULL; исходные версии, при первом запуске 1 |
| related_session_id | uuid | NULL либо своя блокирующая session при rejected; не созданный результат |

Для ключа FK `(environment,receipt_id)` → receipts(environment,id); обе стороны замыкаются до commit. Unique(environment,id,result_session_id) обслуживает ссылки пакета C06. Результат settings/snapshot принадлежит result_session_id; составные FK используют ключи блока 3. До commit проверяется, что user созданной/связанной session равен actor_user_id ключа. related_session_id не даёт раскрыть чужую сессию и требует актуального доступа даже при повторном чтении отказа.

Session `(environment,start_receipt_id,id)` → receipts(environment,id,result_session_id). Settings/funding/journal `(environment,command_receipt_id,session_id)` → тот же ключ receipts для начального C06. Проверка полноты дополнительно требует один и тот же receipt во всех начальных записях, actor settings=actor key=user session, outcome=succeeded и правильный command_type. Receipt не может ссылаться на session, созданную другим receipt. У отказа нет создаваемых session/settings/funding/journal/snapshot; наличие связанной старой session не делает отказ успехом.

Техническая ошибка/таймаут/неизвестный commit не сохраняются как rejected. Q05 pending — состояние выяснения, не строка outcome=pending. Отсутствие receipt в старом снимке/кэше/backup не доказывает, что команда не исполнялась. Новый ключ автоматически не выдаётся. При конфликте уникальности чтение прежнего результата выполняется после rollback в свежей транзакции; не любая unique violation становится разрешением автоматического повтора.

### 2.3. `command_receipt_details`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| receipt_id | uuid | Да; unique(environment,receipt_id), FK receipts |
| reason_data | jsonb | Да; безопасные детали причины, пустой объект при отсутствии |
| response_data | jsonb | Да; типизированные дополнительные сведения исходного ответа, без bearer/сырых запросов |

Для нового receipt создаётся ровно одна неизменяемая строка details; формат определяется record_schema_version родителя, не отдельной версией результата. Обязательные IDs/исход/причина остаются в core, числа читаются по исходным неизменяемым settings/snapshot. Core — совместно command_keys + command_receipts; его нельзя удалять при возможном повторе команды. Будущий отдельно разрешённый архив деталей потребует явной отметки/процедуры и совместимого читателя; сейчас очистки нет. Неожиданно отсутствующие details означают техническую недоступность, не доказанный архив и не разрешение повторить C06.

## 3. `draft_claim_receipts` — однократная передача гостевого черновика

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| draft_id | uuid | Да; unique(environment,draft_id) для единственного guest→user перехода |
| previous_ownership_id, claimed_ownership_id | uuid | Да; две разные ownership того же draft; составные FK на draft_ownerships |
| actor_user_id | uuid | Да; FK users, совпадает с владельцем claimed ownership |
| completed_at | timestamptz | Да; серверный момент завершения claim |

Unique(environment,id,draft_id,claimed_ownership_id). Ownership `(environment,claim_receipt_id,draft_id,id)` → этот ключ. До commit previous — guest, claimed — user, claimed.previous указывает на previous, current_ownership_id draft=claimed. Изменение current pointer, прекращение допуска старого guest handle, новая ownership и receipt неделимы. Отдельное «успешное заявление» без фактической передачи невозможно.

Первичное действие требует полного входа и серверного guest-доказательства. Исходный секрет не хранится здесь; исторический digest блока 1 не восстанавливает гостевой доступ. Повтор разрешён тому же текущему user по сохранённому результату/доказанному контексту; чужой user не получает ни draft, ни сведения о нём. Не переносить гостевой review на нового владельца — нужен новый review. Ошибки/Auth-challenges не помещаются в денежный command key, нет автоматического user→user переназначения. Точный протокол восстановления guest-контекста остаётся H01, без выбора криптографии этим документом.

## 4. Неизменяемый аудит

### 4.1. `audit_events`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| event_kind, event_schema_version | text | Да; закрытые типы фактов и поддерживаемый формат |
| actor_realm | text | Да; user либо staff для событий этого среза |
| actor_user_id, actor_staff_id | uuid | Ровно один по actor_realm, FK users либо staff_principals |
| actor_login_id | uuid | Да для C06/claim/Q06; FK auth_sessions именно того actor/realm |
| request_id | uuid | Да; серверный ID обработки, не ключ денежной команды |
| command_receipt_id, claim_receipt_id | uuid | Ссылка соответствующего события, для Q06 обе NULL; одновременно обе запрещены |
| session_id, snapshot_version | uuid, bigint | Для C06-success и Q06 обязательны вместе; составной FK на snapshot своей session; у claim NULL |
| draft_id | uuid | Для claim обязателен; для start — исходный draft; для Q06 NULL |
| actor_authorization_version | bigint | Да; исторический guard user/staff, не FK на текущий номер |
| occurred_at | timestamptz | Да; время проверенного действия |
| outcome_code | text | Да; типизированный исход, не сырое сообщение БД |
| safe_context | jsonb | Да; безопасные дополнительные сведения, пустой объект при отсутствии |

Unique(environment,event_kind,command_receipt_id) при ненулевом receipt — один факт данного типа на исходную команду; для claim аналогичный unique по claim_receipt_id. Для Q06 unique(environment,event_kind,request_id) — один факт выдачи конкретного ответа; новый запрос чтения получает новый request_id. Наличие audit не означает доставку ответа или просмотр человеком. При повторе успешного C06 не создаются ещё один start audit или outbox.

Границы actor/login подтверждаются условными составными FK на auth_sessions и проверкой варианта до commit; событие C06 имеет user key, Q06 — staff. Для отказа C06 отдельный безопасный audit может указывать receipt и связанную session только после проверки доступа; не превращать отказ до авторизации в существующий финансовый ресурс. Состав новых типов аудита не создаёт endpoints.

### 4.2. `audit_authorizations`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| audit_event_id | uuid | Да; FK audit_events, только Q06 |
| assignment_id, grant_id | uuid | Да; составной FK на неизменяемую разрешающую строку staff_assignment_grants |
| assignment_version | bigint | Да; историческая версия действовавшего назначения |
| authorized_data_code | text | Да; разрешённая группа данных по общему реестру Q06 |

Unique(environment,audit_event_id,grant_id,authorized_data_code). Для Q06 до commit требуется достаточный набор этих строк для всех выдаваемых групп данных; актор всех назначений совпадает с actor_staff_id события. Это фиксирует происхождение доступа, не копирует финансовые значения и не выдаёт доступ в будущем. Выбранные grants неизменяемы, прежние назначения/identity не удаляются каскадом. Обычное чтение требует заново текущих прав независимо от старого audit.

## 5. Событие и доставка

### 5.1. `outbox_events`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| event_type, event_schema_version | text | Да; первый тип — факт успешного старта, точные коды H02 |
| consumer_name | text | Да; доверенный серверный получатель, не URL/имя из запроса |
| command_receipt_id | uuid | Да; исходный успешный C06 |
| session_id, session_version, snapshot_version | uuid, bigint, bigint | Да; неизменяемые ссылки/версии опубликованного результата |
| occurred_at | timestamptz | Да; время исходного события |
| payload | jsonb | Да; безопасное дополнительное содержимое; обязательные scope/IDs вынесены в колонки |
| delivery_state | text | Да; pending, processing, retry_wait, processed, needs_review |
| attempt_count | integer | Да; 0…5, увеличивается при успешном захвате |
| next_attempt_at | timestamptz | Для pending/retry_wait обязателен; иначе NULL |
| lease_token, lease_until | uuid, timestamptz | Обе обязательны только при processing; иначе NULL |
| last_safe_error_code | text | NULL при отсутствии ошибки; обязателен для retry_wait/needs_review |
| processed_at | timestamptz | Обязателен только при processed, иначе NULL |
| version | bigint | Да; guard служебного состояния, от 1 |
| updated_at | timestamptz | Да; время изменения доставки |

ID строки является стабильным eventId. Unique(environment,event_type,command_receipt_id,consumer_name). Composite FK `(environment,command_receipt_id,session_id)` → успешный receipt результата; snapshot относится к той же session. Первый срез использует одного зарегистрированного локального потребителя факта старта; его действие — безопасно подтвердить наблюдение исходного результата, без создания денег/сессии/обязательной проекции. Это не отправка Telegram/email и не торговля. Расширение на fan-out/внешние эффекты требует отдельного протокола; один processed не объявляется доставкой всем возможным потребителям.

Event ID/type/format/consumer/resource/receipt/payload/occurred_at неизменяемы; UPDATE разрешён только полям доставки. Начально pending, attempt_count=0, next_attempt_at=created_at. При захвате +1, новый lease token и ограниченный срок, state=processing. Повторы временного сбоя/истёкшего lease: всего 5 попыток, задержки после неудачных попыток 1–4 равны 1/5/30/120 секунд. Падение worker расходует попытку. При истёкшем lease задержка отсчитывается не раньше lease_until; поздний worker не получает более ранний повтор. Пятая неудача, неизвестный формат или постоянная ошибка → needs_review, без удаления. Длительность/продление lease — H04 до worker, не выдуманные числовые defaults.

Локальный эффект, ConsumerEventReceipt и перевод в processed по возможности одной транзакцией. Worker блокирует outbox и проверяет действующий token/срок перед эффектом и перед завершением; старый token не завершает новую попытку. Нет безусловного ACK по одному eventId. Повтор не создаёт новый eventId и не заменяет payload. Ограничение C06 (3 попытки/5 секунд) не смешивается с этим бюджетом.

### 5.2. `consumer_event_receipts`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| consumer_name | text | Да; тот же доверенный consumer |
| event_id | uuid | Да; FK на outbox этого consumer |
| result_code | text | Да; типизированный окончательный локальный результат |
| result_session_id | uuid | Да для наблюдения старта; та же session исходного события |
| processed_at | timestamptz | Да; время подтверждённого эффекта |

Unique(environment,consumer_name,event_id). Для составного FK outbox имеет unique(environment,id,consumer_name). Отметка неизменяема, сохраняется в одной транзакции с локальным эффектом. Если эффект/receipt уже сохранены, а outbox processed нет, восстановление только завершает доставку после проверки соответствия результата; effect не повторяется. Даже после пятого захвата существующий receipt имеет приоритет перед needs_review. Такое служебное завершение при отсутствии активного lease не является шестой попыткой эффекта; конкурентные завершения сериализуются на outbox. Неизвестный/повреждённый receipt не считается отсутствующим.

Processed требует совпадающий consumer receipt до commit, при обычном исполнении — также действующий lease. Needs_review не выдаёт автоматического разрешения повторно выполнить эффект. Внешние эффекты не становятся exactly-once от локальной отметки. После restore worker закрыт до сверки; автоматическое повторение истёкших leases из старой копии запрещено.

## 6. Прикладная граница сотрудников

### 6.1. `staff_principals`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| status | text | Да; закрытый статус аккаунта по H03; неизвестный запрещает доступ |
| locale | text | Да; ru/en, не scope |
| authorization_version | bigint | Да; guard доступа от 1 |
| updated_at | timestamptz | Да |

Постоянный staff principal отделён от users; совпадение email не связывает права автоматически. Нет role=Owner в браузере или глобального is_admin у обычного user. Identity/назначения этого человека используют один principal и один staff slot; несколько назначений не создают несколько физических участников. Bootstrap обязан подтвердить двух разных людей, UUID сам по себе этого не доказывает. Изменение identity, состава назначений/доступа и общая блокировка увеличивают authorization_version в той же транзакции.

### 6.2. `staff_auth_identities`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| staff_principal_id | uuid | Да; FK staff_principals |
| realm | text | Да; staff |
| provider, provider_subject | text | Да; проверенная постоянная внешняя identity |
| status | text | Да; действующая/отозванная привязка по реестру H03 |
| version | bigint | Да; guard привязки |
| updated_at | timestamptz | Да |

Unique(environment,realm,provider,provider_subject), unique(environment,id,staff_principal_id). Связь с principal не переназначается. Внешний provider может быть отдельным WebAuthn-компонентом; таблица не объявляет Supabase поддерживающим весь staff-контракт. Открытые ключи/credential IDs/challenges и recovery-секреты остаются у проверенного auth-компонента, здесь не дублируются. Удаление/отзыв провайдерской записи не удаляет audit/финансовую историю; подтверждение identity не равно действующему назначению.

### 6.3. `staff_assignments`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| staff_principal_id | uuid | Да; FK staff_principals |
| role_ref, role_revision_ref | text | Да; точная доверенная версия системной роли/существующего пресета, не права по имени |
| source_ref | text | Да; безопасное доказательство bootstrap/назначения, без секретов |
| status | text | Да; закрытый реестр действующих/отозванных состояний H03 |
| valid_from, valid_until | timestamptz | Начало обязательно; конец NULL только для явно бессрочного назначения, иначе позже начала |
| revoked_at, revoke_reason_code | timestamptz, text | Оба заполнены для отзыва, иначе оба NULL |
| current_grant_set_version | bigint | Да; текущий полный набор grants, от 1 |
| version | bigint | Да; guard состояния назначения |
| updated_at | timestamptz | Да |

Unique(environment,id,staff_principal_id). Начальный состав — только два отдельных Owner, без создания дополнительных сотрудников/ролей. Нет нового редактора ролей/инвайтов. Права материализуются из проверенной версии роли в полный набор grants, а не из переданного role_ref. Смена актуального набора или статуса увеличивает assignment.version и staff.authorization_version атомарно. Текущий набор не может быть пустым или частично опубликованным: проверка полноты до commit. Отзыв не стирает историю наборов.

### 6.4. `staff_assignment_grants`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| assignment_id | uuid | Да; FK staff_assignments |
| grant_set_version | bigint | Да; версия полного набора, историческая, не FK на изменяемый current номер |
| grant_key | text | Да; стабильный код строки в наборе; unique(environment,assignment_id,grant_set_version,grant_key) |
| action_code, section_code, data_type_code | text | Да; одна разрешающая комбинация, машинные коды H03 |
| product_mode | text | Да; paper для выдачи первого сценария |
| venue_scope | text | Да; all либо one, явная область |
| venue_id | uuid | Только для one, FK venues; при all NULL |

Unique(environment,assignment_id,id) для audit evidence. Строки опубликованного набора неизменяемы; дописывать строки в уже опубликованный набор также запрещено. Изменённый набор получает новый grant_set_version и публикуется целиком. Для Q06 разрешается только read нужного раздела/типа данных в той же environment/venue/paper. Право экспорта, изменения, запуска или реального режима из read не выводится. Полная роль может быть шире первого реализуемого endpoint, но этот пакет не реализует её остальные операции.

Каждая разрешающая строка проверяется целиком. Нельзя взять действие из назначения A и площадку из B. При нескольких назначениях сохраняется источник каждого реально использованного разрешения в audit_authorizations. Изменение роли-источника, влияющее на действующий доступ, обязано перепубликовать затронутые наборы/guards по общему порядку; нельзя оставить устаревшие grants после отзыва источника. Механизм обновления/проверенная версия реестра — H03, не разрешение строить отдельный несовместимый RBAC.

## 7. Политика и действующий вход

### 7.1. `login_policy_versions`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| realm | text | Да; user либо staff |
| policy_code | text | Да; unique(environment,realm,policy_code) |
| max_lifetime_seconds, inactivity_seconds | integer | Да; положительные согласованные пределы |
| source_ref | text | Да; ссылка на принятую политику/версию |
| published_at | timestamptz | Да; опубликованная неизменяемая версия |

Первый user-профиль: 2 592 000 и 604 800 секунд (30/7 суток). Staff: 28 800 и 1 800 секунд (8 часов/30 минут). Unique(environment,id,realm) для FK. Эти сроки не сроки access token и не 14-дневная оценка paper. Вход сохраняет свою версию до истечения/отзыва; новая обычная публикация не переписывает старые входы. Неизвестный источник или неподдерживаемая версия закрывают новый вход.

### 7.2. `login_policy_controls`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| realm | text | Да; user/staff, unique(environment,realm) |
| active_policy_version_id | uuid | Да; FK на опубликованную policy того же realm |
| version | bigint | Да; guard активного указателя |
| updated_at | timestamptz | Да |

Публикация и изменение pointer атомарны. Отсутствие строки не создаёт defaults на лету. Это прикладное выражение версий политики, не новый экран или полномочие менять staff-сроки; любые будущие изменения требуют действующего решения по соответствующему realm. В порядке блокировок этот pointer относится к группе policy, а не захватывается после login.

### 7.3. `auth_sessions`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| realm | text | Да; user либо staff |
| user_id, staff_principal_id | uuid | Ровно один по realm; FK users/staff_principals |
| user_identity_id, staff_identity_id | uuid | Ровно одна по realm; составной FK на identity именно выбранного principal |
| provider, provider_session_ref | text | Да; безопасная серверно подтверждённая ссылка на полный вход, не bearer |
| login_policy_version_id | uuid | Да; FK policy того же realm |
| effective_max_lifetime_seconds, effective_inactivity_seconds | integer | Да; копия пределов закреплённой policy |
| assurance_code, authentication_evidence_ref | text | Да; доказанный уровень полного входа и безопасная ссылка проверки, H01 |
| authenticated_at, last_user_activity_at, expires_at | timestamptz | Да; полный вход, подтверждённая foreground-активность, абсолютный срок |
| revoked_at, revoke_reason_code | timestamptz, text | Оба заполнены при отзыве, иначе оба NULL |
| version | bigint | Да; guard входа |
| updated_at | timestamptz | Да |

Unique(environment,realm,provider,provider_session_ref). Для условных FK audit добавить unique(environment,id,realm,user_id) и unique(environment,id,realm,staff_principal_id); проверка actor-варианта обязательна. У user_auth_identities блока 1 добавить unique(environment,id,user_id), у staff identity ключ уже указан. Identity/provider/realm/login должны соответствовать друг другу, проверяется до commit. Разные provider login refs не дают обойти один staff slot.

Строка создаётся **только после полного входа**: email + включённый TOTP для user, обязательный WebAuthn/passkey с пользовательской проверкой для Owner полигона. Pending OTP/MFA/recovery не является auth_sessions и не открывает Q06. Assurance-код хранит факт проверки, но актуальная identity/блокировка/назначение проверяются заново; доверия клиентскому assurance нет. Если компонент не даёт стабильного безопасного session ref, совместимый адаптер должен обеспечить привязку; придумывать её из email запрещено.

Expires_at=authenticated_at+закреплённый max lifetime. При now≥expires_at либо now≥last_user_activity_at+inactivity, отзыве/блокировке — вход недействителен. Обновление активности проверяет действительность **до** продления и не уменьшает время; background refresh/worker/админский просмотр пользователя не продлевают его вход. Refresh не создаёт новую строку полного входа. Список допустимых foreground-действий и отзыв provider-сессий — H01. После logout своего user login остальные независимые user-входы сохраняются; операции reset MFA следуют отдельной принятой политике отзыва всех входов, не реализуются здесь.

### 7.4. `staff_login_slots`

| Дополнительные колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| staff_principal_id | uuid | Да; FK staff_principals; unique(environment,staff_principal_id) |
| realm | text | Да; staff |
| current_login_id | uuid | NULL означает отсутствие рабочего входа; иначе FK на staff auth_session именно этого principal |
| version | bigint | Да; guard от 1 |
| updated_at | timestamptz | Да |

Составной FK `(environment,current_login_id,realm,staff_principal_id)` → auth_sessions(environment,id,realm,staff_principal_id). После полной проверки passkey и текущего назначения новый login, отзыв предыдущего и смена slot pointer сохраняются атомарно; ошибочная/отменённая проверка не отзывает прежний login. Все выдачи требуют, чтобы login совпадал с current pointer и не истёк/не отозван. До commit проверка замены запрещает два неотозванных рабочих staff-входа; истечение не реанимируется refresh. Вкладки одного login не создают разные slots, несколько ролей тоже. Отзыв по logout/блокировке закрывает доступ сразу, даже если pointer ещё исторически указывает на отозванный login; его очистка не возвращает старый вход.

Auth-провайдер и Shadow не объявляются одной внешней транзакцией. После неоднозначного verify сначала устанавливается действительный факт identity/full-auth; затем локальная атомарная замена. Если итог неясен, читаются подтверждённая identity и slot, а не создаётся второй полный вход по предположению. Recovery одного/обоих Owner сохраняет правила [auth-policy §17–18](auth-policy.md): ограниченный процесс не становится рабочим login, старые ключи/входы отзываются, нужен новый полный вход и актуальное назначение. Формат секретов/recovery-таблиц компонент определяет отдельно до своей реализации.

## 8. Транзакции, ограничения и проверка доступа

| Операция | Что обязательно сохраняется/проверяется вместе |
| --- | --- |
| C06 новый успех | Уникальный key, весь финансовый комплект блока 3, receipt/details, один start audit и один outbox для зарегистрированного consumer; двусторонние связи и суммы до commit |
| C06 окончательный отказ | Тот же scoped key + rejected receipt/details, без новой финансовой истории; при достигнутом резервировании slot — правило блока 3 |
| Повтор C06 | Текущий доступ и прежний key/fingerprint; исходные результат/версии, без start audit/outbox/funding повторно |
| Claim | Guest-доказательство + полный user-вход, новая ownership/current pointer, закрытие guest-допуска и claim receipt |
| Q06 | Текущие staff principal/identity/login/slot/назначения/grants, область конкретной session и групп данных, один целый snapshot, audit + authorization evidence; ответ после commit |
| Worker | Действующий lease, дедуп consumer/event, локальный эффект и receipt, по возможности processed вместе; повтор лишь завершает доставку |
| Staff login replacement | Полное доказательство identity, текущий допуск, отзыв прежнего login + новый login + один slot pointer |

Serializable и общий lock order остаются из data-model §22; guard principal покрывает появление/отзыв дочерних назначений, не только существующие строки. Для Q06 login, актуальные назначения и slot берутся в этом порядке групп; предварительно найденные IDs перепроверяются под защитой, изменение набора вызывает перечитывание/конфликт, а не захват ранней группы после поздней. Worker использует стабильный порядок собственных outbox/consumer ресурсов и не входит задним числом в финансовый C06.

Условные CHECK/NOT NULL задают варианты; PK/unique защищают scope, FK — принадлежность. Отложенные FK/constraint triggers блока 3 дополняются полнотой key↔receipt, success↔session, receipt/details/audit/outbox, claim↔ownership, Q06↔evidence и processed↔consumer receipt. Проверка запускается и от создания родителя без детей. Частичный success невозможно опубликовать, даже если API пропустил шаг. Исторические версии guards не FK на изменяемый номер.

Обычные роли API/worker не имеют прав отключать ограничения, менять схему, переписывать core/audit/финансовую историю или напрямую публиковать назначения. Читающий сотрудник не получает SQL-доступ. Конкретная матрица DB-ролей/закрытых процедур — H05; выбранный механизм ещё должен быть испытан. Нет строки роли/кнопки, которая заменяла бы эти ограничения.

## 9. Угрозы и будущие проверки

| Риск | Контроль в проекте | Нужное доказательство / остаточная зависимость |
| --- | --- | --- |
| Повтор/потерянный ответ C06 | Scope key, immutable receipt, атомарный финансовый пакет | Гонки двух ключей/одного ключа и unknown commit; H02/H05 |
| Просмотр чужой session обычным user | Проверка постоянного owner до раскрытия, составные ссылки | Прямые Q04/Q05/Q06 и отсутствие утечки через ошибки |
| Старый staff login или отозванное назначение | Current slot, сроки, guards и текущие grants | Гонка revoke/read и login replacement, совместимость Auth H01 |
| Составление расширенных прав из разных назначений | Проверка каждой полной grant-комбинации, audit evidence | Scope Polymarket не открывает Limitless; read не export; H03 |
| Дубли worker/старый lease | Consumer unique + атомарный эффект, token/expiry, пять попыток | Crash до/после effect commit, пятая попытка с уже записанным receipt; H04 |
| Restore возвращает старые права/утрачивает dedup | Закрытый запуск/worker до сверки после точки копии | Изолированный restore и полный обход четырёх форматов; H06 |
| Обход через bootstrap/recovery/прямую БД | Доверенная привязка двух разных Owner, ограниченный recovery, разделённые DB-роли | Проверка реального auth-компонента/прав до открытия стенда; сейчас не выполнена |

Состояние needs_review не добавляет экран или команду повторного денежного исполнения. Подробные JSON не содержат токенов, кодов или полного входящего запроса. Для диагностики повреждения — тип/полный ID/формат/безопасный код без содержимого. Очистка истории и выдача реальных доступов не разрешаются этим проектом.

Техническая сверка 29.10.2026: [PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html), [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html). Ссылки подтверждают свойства механизмов, не готовность Shadow или выбранной версии Auth.

**Сводная передача и оставшиеся зависимости:** [database-backend-handoff.md](database-backend-handoff.md). Блок 4 ещё требует принятия владельцем; после него новая серия продуктовых микровопросов не предполагается. Завершение документального согласования не является поручением начать SQL, код или развёртывание.
