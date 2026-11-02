02.11.2026 · D01-A сопоставлена с принятой P01–P05 основой в [единой схеме Auth](auth-storage-unified.md). Отдельные18 таблиц не создаются: дубли объединены, claim unique consent принятой БД сохранён. [U01–U03](auth-storage-unified-decisions.md) — только новая адресная дельта; ниже исторический вариант, не альтернативный каталог.

# Точная карта хранения Auth: контексты, результаты, cookie и claim

02.11.2026 · **Последующее принятие в чате БД:** владелец принял P01–P05 и [карту AC01–AC37](database-auth-physical-map-proposal.md) с исправлениями; текущий собственный каталог73. Ниже сохранена параллельная D01-A PR №204 как источник адресного сведения, **не отдельно принятые18 таблиц и не текущий каталог54**. [Итог принятия §3](database-auth-acceptance-2026-11-02.md) перечисляет расхождения: verifier/completion, dispatch/attempts, unique consent/lock-порядок, reconciliation, лимиты/поздний outcome. Принятие P01–P05 не означает автоматической эквивалентности этих вариантов; D01 требует ответа о сведении. Исторические статусы ниже относятся к публикации PR №204.

Интеграция02.11.2026: во время публикации появился PR №203 (`32792c1`) с [более широкой картой БД AC01–AC37](database-auth-physical-map-proposal.md) и [BR01–BR09](database-backend-package-review.md). D01-A ниже — параллельная детализация части того же Auth-контура, **не ещё18 таблиц сверх37**. Имена/декомпозиция/lock-порядок двух проектов нельзя смешивать как уже принятую схему; перед DDL нужна одна согласованная карта. Обе версии сохранены для предметного сведения.

02.11.2026 · D01-A по прямому поручению владельца. Baseline main `abfecdc5b910f6aaee4482c47b80a298823e3eda` (PR №202). Статус: **предлагаемая физическая дельта для согласования с БД**, не SQL, миграция или созданная схема. Источники: [Auth-контракт](backend-auth-contracts-addendum.md), [проект механизмов после вычитки](backend-review-mechanisms.md), [ответ БД DA01–DA12](database-auth-handoff-review.md), [действующие таблицы доступа](database-physical-operations-access.md), [блокировки](database-concurrency-locks.md). Принятые правила C04/C05/C06, Q02/Q06, P-RESET и равноправие владельца 1/владельца 2 сохраняются.

Объём: постоянный контекст и доказательство, операция до/после внешнего эффекта, неизменяемый результат, локальный полный login и исходная cookie, историческое согласие на claim, допуск исполнителя и доказанная остановка после unknown. Это конкретная часть D01, **не весь Auth-provider, MFA/credentials/cases, счётчики, selector или инфраструктура witness**. Их границы и блокирующие зависимости перечислены в §12, а не спрятаны в JSON.

## 1. Состав и общие физические правила

Предлагается **18 новых таблиц** в закрытой схеме `auth_control`. Принятый baseline Shadow остаётся36 таблиц; после принятия именно этой дельты рассматриваемый прикладной каталог составит54 таблицы, без внутренних таблиц provider и ещё не описанных дополнений §12. Число54 не объявляется окончательным составом всей системы. В36 таблицах не добавляются bearer, pending login, второй CommandReceipt или постоянный claim-guard.

| № | Таблица | Единственный источник факта |
| --- | --- | --- |
| 1 | environment_gates | Текущий допуск среды и непереиспользуемая эпоха |
| 2 | contexts | Тип/срок/proof/стадия ограниченного контекста |
| 3 | context_subject_bindings | Проверенная привязка контекста к постоянному user/staff |
| 4 | context_email_bindings | Неизменяемый адрес намерения C01, отдельно от подтверждённой identity |
| 5 | challenges | Метаданные выпущенного challenge и его жизненный цикл |
| 6 | continuation_bindings | Одно immutable намерение продолжения |
| 7 | operations | Scoped намерение Auth и текущая установленность исхода |
| 8 | operation_dispatches | Право конкретного исполнителя на один внешний вызов и свидетельство его исхода |
| 9 | operation_results | Единственный окончательный неизменяемый Auth-результат |
| 10 | login_completions | Связь окончательной операции с одним локальным полным login |
| 11 | login_cookie_credentials | Проверка cookie полного login без хранения её открытого секрета |
| 12 | cookie_recovery_windows | Исторический deadline и отдельный факт закрытия восстановления |
| 13 | cookie_recovery_secrets | Короткоживущая зашифрованная копия ровно исходной cookie |
| 14 | claim_consents | Историческая связь выбранных draft/ownership/user/login |
| 15 | claim_executions | История допуска серверного запроса claim, без нового ключа клиента |
| 16 | claim_execution_attempts | Подтверждённые/неизвестные исходы до3 внутренних SQL-попыток |
| 17 | reconciliation_runs | Закрытие эпохи, drain и разрешённое открытие после сверки |
| 18 | reconciliation_items | Отдельное доказательство исхода каждого затронутого исполнения |

Далее U=uuid v4; V=bigint>0; T=timestamptz с UTC/миллисекундами; H=bytea ровно32 байта; B=boolean; S=text из явно названного закрытого словаря; nullable помечено `?`. Все остальные поля NOT NULL. Каждая таблица, кроме environment_gates, содержит environment:text, id:U, created_at:T и PK(environment,id); у environment_gates PK(environment), без искусственного id. Environment — непустой код доверенного descriptor, не браузерный ввод. Mutable строки дополнительно version:V от1 и updated_at:T; версии не сбрасываются/не оборачиваются. Поля-ссылки ниже всегда включают environment.

Все FK ограничивают удаление; каскадного удаления истории нет. Для связи с типом/владельцем добавляется указанный составной UNIQUE на родителе. Nullable FK сопровождается полным условием варианта, а не обходом через один NULL. Межстрочная полнота обеспечивается deferred constraint-проверкой к commit и закрытыми процедурами; не называется обычным CHECK. Новые constraints/индексы в этом документе — проект, не выполненные команды.

Все новые environment ссылаются на environment_gates(environment). Для scoped FK дочерних записей при необходимости добавляются UNIQUE(environment,id,context_id), UNIQUE(environment,id,login_id,context_id) и соответствующие перечисленные tuple, без смены PK. На existing Shadow дополнительно нужны адресные UNIQUE: draft_ownerships(environment,id,draft_id,owner_kind,guest_context_id), draft_claim_receipts(environment,id,draft_id,actor_user_id,previous_ownership_id), auth_sessions(environment,id,realm,user_id,user_identity_id) и staff-вариант. Они поддерживают ровно описанные typed связи, не разрешают новое владение/вход. Нельзя ссылаться на несуществующий unique tuple; состав проверяется БД перед DDL.

Для JSON разрешён только **закрытый версионированный DTO**, не произвольный словарь; не более16КиБ компактного UTF-8 на поле. Владение, ссылки, стадия, provider outcome, секрет и разрешение не прячутся в JSON. RequestId/correlationId/observedAt/nextAction/restrictedGroups не становятся историческим result. Недоступная/повреждённая обязательная запись даёт технический отказ, не NULL/пустой массив/unresolved. Времена проверяются доверенными часами; для интервалов expiry действует now≥deadline.

Ниже краткие refs results/completion/window означают operation_results/login_completions/cookie_recovery_windows из каталога, не дополнительные таблицы. Один серверный executor_id обозначает конкретный процесс/запуск, никогда не переиспользуется после restart; permit — случайный ≥256bit секрет, в БД только его HMAC с отдельным purpose. Перезапуск не восстанавливает право на внешний вызов по одному id строки.

## 2. Среда и ограниченные контексты

### 2.1. environment_gates — mutable

Поля: epoch:V, state:S(open/closed), last_reconciliation_id:U?, descriptor_version:V, witness_sequence:V, witness_head_digest:H, closed_at:T?, version,updated_at. State=closed требует closed_at; open требует NULL. Epoch увеличивается при fence/restore, не при обычном запросе; последующее открытие не возвращает прежний epoch. Last_reconciliation_id — FK на runs той же среды, NULL только при первоначальном закрытом bootstrap; открытие требует завершённого разрешающего run. Witness-поля — проверенный последний head, не самостоятельное доказательство свежести внешнего журнала.

Gate создаётся заранее закрытым доверенной процедурой; отсутствие строки не означает open. Для обычного изменяющего запроса берётся S до G1, для fence — X в отдельной короткой транзакции. Все связанные writers, включая закрытый Auth-controller и сверку, исполняют один протокол. Нельзя ждать provider под удерживаемым SQL gate; внешний dispatch сначала регистрируется и далее учитывается при drain.

Epoch здесь ограничивает **допуски исполнителей**, не заменяет срок login. Created_epoch контекста — история: обычный claim fence не отзывает все независимые login только из-за отличия epoch. Новый запрос после открытия получает текущую epoch при новом admission; старый permit никогда не переоформляется на неё. Закрытый source consent остаётся закрытым. Restore отдельно требует явного отзыва старых proofs/login по принятому протоколу, без неявного смешения двух механизмов.

### 2.2. contexts — mutable оболочка, immutable назначение

| Поля | Тип/обязательность | Ограничение |
| --- | --- | --- |
| context_kind | S | user_auth / staff_auth / guest / user_logout / staff_logout / user_claim |
| realm | S | user / staff / guest; точное соответствие kind |
| created_epoch | V | Эпоха создания; допускается только при текущем open gate/доверенном bootstrap |
| stage | S | По матрице ниже; не значение из provider без decoder |
| expires_at | T | После created_at; immutable кроме явно разрешённого продления guest |
| proof_key_id | text | Непустая ссылка на внешний purpose-specific key; immutable |
| proof_digest | H | HMAC полного domain/env/kind/id/secret, не открытая cookie |
| access_confirmed_at | T? | Первый доказанный GET; меняется только NULL→T, не полный вход |
| source_context_id | U? | FK contexts; только продолжение logout, исходник того же kind/target/principal, immutable |
| target_login_id | U? | FK shadow.auth_sessions; обязателен для logout/claim, NULL для user_auth/staff_auth/guest; immutable |
| current_challenge_id | U? | FK на challenges именно этого context; по stage |
| revoked_at | T? | NULL→T, служебный отзыв; не стирает результат |
| execution_closed_at | T? | NULL→T; запрещает новые исполнения, не сам по себе разрешённое позднее чтение |
| version,updated_at | V,T | Guard всех зависимых изменений контекста |

| Kind | Realm / субъект | Stages и challenge | Срок |
| --- | --- | --- | --- |
| user_auth | user; subject до доказательства отсутствует, после него immutable | ready; email_verification с email current; totp_verification с totp current; totp_enrollment/completed без current | Ровно30min |
| staff_auth | staff; subject после проверки passkey | ready/challenge/completed; current только при challenge, kind=webauthn_login | Ровно10min |
| guest | guest; subject отсутствует | active; current NULL | По reviewed guest-профилю: исходно7d, refresh/C04 по его правилам |
| user_logout / staff_logout | Соответствующий субъект target_login | active; current NULL | Ровно15min, continuation создаёт новый context |
| user_claim | user; выбранный получатель target_login | active; current NULL; обязательно consent §8 | Ровно10min |

Email/TOTP значения времени API читаются из current challenge, сохраняются при его expiry, но не переносятся в неподходящий stage. Прежние challenges остаются историей. Target_login требует составного FK с realm и соответствующим principal через typed binding; child/target/kind проверяются к commit. Source_context_id не разрешает циклы: ссылка только на уже существующий контекст с тем же неизменным target; создание и immutable refs через процедуру. Created_at одинаковой миллисекунды не доказательство порядка — проверяется существование до текущего создания.

Этот конкретный каталог не включает mfa/mfa_result/staff_registration/staff_recovery/staff_recovery_codes из общего проекта: их точные factor/case/approval связи составляют отдельную дельту §12. Нельзя записать их как user_auth с произвольным stage. До её принятия соответствующие маршруты не считаются физически специфицированными/готовыми. Здесь нет нового API-кода отказа для них.

### 2.3. context_subject_bindings — immutable

Поля: context_id:U UNIQUE, realm:S(user/staff), user_id:U?, staff_principal_id:U?, user_identity_id:U?, staff_identity_id:U?, bound_at:T, evidence_source:S(provider_verified/full_login), evidence_ref:text. Ровно один principal и соответствующая identity по realm, FK на shadow.users/staff_principals и identity именно этого principal. Evidence_ref — непустая безопасная серверная ссылка; источник проверен, текст не authority. UNIQUE(environment,context_id,realm,user_id) и staff-вариант — для typed ссылок.

У guest binding запрещён; logout/claim требует binding при создании, совпадающий с target_login. У user_auth email challenge ещё не даёт subject; insert происходит только после доказанной identity, в транзакции с её локальным отражением и stage/result. Повтор не меняет principal по совпадающему email. У staff binding создаётся после доказанного credential→principal. Связь сохраняется после expiry/revoke; историческое наличие не полный доступ.

### 2.4. context_email_bindings — immutable адрес, отдельно стираемый ciphertext

Поля: context_id:U UNIQUE, normalized_email_digest:H, address_key_id:text, encrypted_email:bytea?, email_cipher_key_id:text, email_nonce:bytea(24), email_cipher_deadline_at:T, email_erased_at:T?, bound_by_operation_id:U, normalized_format:S(auth-email-v1). Ciphertext — XChaCha20-Poly1305, tag16 включён, максимум1024 bytes; AAD связывает environment/context/id/purpose/format. Исходный email не публикуется через API/логи. Для отправки хранится нормализованный адрес в ciphertext; сырой C01 payload сравнивается отдельным HMAC §4, не нормализованным digest.

До первого возможного C01-effect binding и операция сохраняются вместе. Адрес не заменяется C03/unknown. Digest служит адресной области счётчика, не user identity. Cipher deadline=context.expires_at; поле encrypted_email очищается только с email_erased_at, несекретный binding остаётся. Продление хранения ради неизвестности не выполняется: reconciler использует provider ref, не новую отправку. Потеря необходимого cipher до deadline — ошибка, не пустой email.

Email-address и cookie-recovery encryption используют разные purpose keys. Для каждого UNIQUE(environment,cipher_key_id,nonce), для email имя колонки email_cipher_key_id/email_nonce; nonce24 CSPRNG, один раз на новую запись, не переиспользуется при erasure/retry. Внешний каталог ключей подтверждает среду/назначение; значение key_id из строки само по себе не разрешение decrypt.

### 2.5. challenges — mutable жизненный цикл, immutable выдача

Поля: context_id:U, challenge_kind:S(email/totp/webauthn_login), issuer_operation_id:U, issuer_source:S(provider/local_adapter), issuer_ref:text, issued_at:T, expires_at:T, factor_version:V?, state:S(active/replaced/consumed), replaced_by_challenge_id:U?, consumed_by_operation_id:U?, version,updated_at. UNIQUE(environment,context_id,id); все operation refs того же context. Email expires=issued+10min (действия всё равно ограничены context); totp/webauthn expires=min(issued+5min,context expiry). Factor_version обязателен только totp; его доверенный источник и used-steps не заменены этой колонкой (§12).

Active имеет оба terminal refs NULL; replaced — только replaced_by; consumed — только consumed_by. Replacement того же context/kind и подтверждённый issuer result; переход обратно запрещён. Истечение вычисляется по времени, не фоновым state=expired. Новый current pointer, замена/потребление challenge и окончательный результат публикуются атомарно. Unknown отправки не создаёт «подтверждённый новый current». Нет OTP/seed/WebAuthn private key в таблице.

### 2.6. continuation_bindings — immutable

Поля: context_id:U UNIQUE, continuation_kind:S(default/setup_draft), draft_id:U?. Только user_auth; default↔NULL, setup_draft↔FK shadow.setup_drafts. Created_at — время первого binding. Права на draft проверяются при вставке и каждом разрешённом чтении, FK не permission. Нет update/delete, одинаковый повтор возвращает исходную строку; иной binding конфликтует. Навигация/текущая session сюда не сохраняются. Достоверное отсутствие строки означает default; ошибка чтения не отсутствие.

## 3. Операции, dispatch и неизменяемые результаты

### 3.1. operations — mutable разрешение исхода

Поля: context_id:U, operation_id:U (внешний authOperationId/operationId), action_code:S, request_schema_version:S(v1), canonical_request_data:jsonb, request_digest:H, request_digest_version:S(auth-request-v1), secret_compare_digest:H?, secret_compare_key_id:text?, secret_compare_deadline_at:T?, secret_compare_erased_at:T?, phase:S(admitted/dispatched/uncertain/resolved/closed_without_dispatch), result_id:U?, admitted_epoch:V, request_started_at:T, admitted_at:T, execution_deadline_at:T, execution_closed_at:T?, version,updated_at.

UNIQUE(environment,context_id,action_code,operation_id) — единственная область Auth dedup. Внутренний id не заменяет клиентский ID. Canonical_request_data содержит только разрешённые несекретные поля конкретного action, без OTP/token/raw email; raw C01 email включён в secret comparison с locale. HMAC domain включает environment/context/action/operation ID и длины исходных секретных bytes, key вне БД. Все четыре comparison-поля NULL для действия без секретов; при наличии key/deadline immutable, digest удаляется только с erased_at после deadline. Проверка другого payload не обращается к provider.

Request_digest=SHA256 UTF-8 JCS объекта ровно {format,environment,contextId,action,operationId,requestSchemaVersion,nonSecretPayload}; format=auth-request-v1, nonSecretPayload=canonical_request_data. HMAC сравнивается дополнительно, digest не доказывает равенство секретов. Secret_compare_deadline_at=context.expires_at; удаление не стирает исторический result. Request_started_at задаётся доверенным серверным началом исходного HTTP, admitted_at не раньше него. Execution_deadline_at=request_started_at+принятый бюджет:10s для C01/C02/C03/TOTP verify/staff verify,5s для renew/logout/options. Admission и последующие внутренние шаги не начинают бюджет заново; исполнитель контролирует оставшееся время монотонными часами. Replay имеет собственный бюджет чтения и не продлевает исходное разрешение внешнего действия.

В этой дельте action whitelist: user_auth — C01/C02/C03/AUTH_TOTP_VERIFY/AUTH_TOTP_CHALLENGE_RENEW; user_logout — C07; staff_auth — login_options/staff_login; staff_logout — staff_logout. Последние staff значения — кандидатные storage names reviewed API, подлежат D02, не объявляются уже добавленными в реестр v5. Guest/claim не получают обычных Auth-operation строк для передачи draft. Guest refresh и email-link — отдельная полнота D02/§12, не допускаются выдуманным action.

Resolved↔result_id NOT NULL; в остальных состояниях result NULL. FK(environment,result_id,id) → results(environment,id,operation_row_id); UNIQUE(environment,id,context_id,action_code) для children. Результат не переписывается. Closed_without_dispatch требует execution_closed_at и доказательства, что dispatch никогда не выдавался; это служебный terminal admission, **не новый API-result отказа**. GET в разрешённой области по прежнему контракту может дать202 без result; не объявляет rollback/право нового действия.

### 3.2. operation_dispatches — mutable факт одного внешнего вызова

Поля: operation_row_id:U, ordinal:integer≥1, executor_id:U, permit_digest:H, admitted_epoch:V, sealed_at:T, provider_code:text, provider_request_ref:text?, outcome:S(sealed/uncertain/confirmed_not_sent/confirmed_effect), evidence_ref:text?, outcome_recorded_at:T?, version,updated_at. UNIQUE(environment,operation_row_id,ordinal). На provider_code/provider_request_ref только обычный индекс поиска, без выдуманной гарантии внешней уникальности. Корреляция доказывается адаптером вместе с исходной operation/dispatch/subject/purpose, неоднозначный ref не допускает финализацию.

Seal фиксируется **до сети**, permit принадлежит одному исполнителю и не передаётся по lease/таймауту. Неизвестность не выдаёт новый permit. Следующий ordinal возможен только при доказанном confirmed_not_sent всех предыдущих, живом исходном допуске и внутри принятого бюджета; это не автоматический повтор неизвестного эффекта. Confirmed_effect означает подтверждённый ответ provider, включая проверенный отрицательный ответ, а не обязательно успешный login. Evidence_ref непустой и время обязательны для terminal outcome; uncertain может иметь дополнительное свидетельство, но не выдаётся за доказанный rollback. Подтверждение физически неотправленного вызова и обычный timeout различаются.

Reconciler не делает внешний эффект повторно. Если provider не даёт достоверного outcome, phase=uncertain остаётся, action блокируется. Процесс, остановленный между seal и сетью, учитывается в drain; одного отсутствующего provider ref недостаточно для confirmed_not_sent.

### 3.3. operation_results — immutable

Поля: operation_row_id:U UNIQUE, context_id:U, action_code:S, result_kind:S, result_schema_version:S(auth-result-v1), historical_http_status:smallint, result_data:jsonb, result_digest:H, resolved_at:T, subject_binding_id:U?, issued_challenge_id:U?, replaced_challenge_id:U?, login_completion_id:U?, logout_target_login_id:U?. Typed FK к операции/context; refs не извлекаются только из JSON. Для указанных refs проверяются context/realm/principal; issued/replaced — challenges того же context, logout target — прежняя цель context. JSON ровно DTO исторического результата, его дублирующие значения совпадают с typed refs. Digest от JCS неизменяемой проекции с format/action/context/operation/result; plaintext secrets и текущая навигация отсутствуют.

| Result kind | Допустимые действия / status прямого ответа | Обязательные refs / result_data |
| --- | --- | --- |
| email_dispatch_accepted | C01/C03;202 | issued_challenge; ровно kind,acceptedAt,challengeId,resendNotBeforeAt |
| auth_step_required | C02;200 | subject_binding; stage=totp_verification требует issued_challenge и его времена; totp_enrollment без challenge, DTO принятого §6 |
| login_completed | C02/AUTH_TOTP_VERIFY;200 | subject_binding+login_completion; ровно kind,completion по принятому §7 |
| verification_rejected | C02/AUTH_TOTP_VERIFY/staff_login;401 | Нет нового completion; kind,reasonCode=AUTH_VERIFICATION_FAILED; binding только если уже доказан |
| totp_challenge_renewed | AUTH_TOTP_CHALLENGE_RENEW;200 | issued+replaced, оба challenge; закрытый DTO §6 |
| logout_confirmed | C07/staff_logout;204 | logout_target_login, subject_binding; storage DTO kind,loginId,confirmedAt; внешний прямой ответ остаётся204 без тела |
| staff_authentication_options | login_options;200 | issued_challenge; DTO reviewed staff options, без credential-secret |
| staff_login_completed | staff_login;200 | subject_binding+login_completion; reviewed completion staff, не user C02 DTO |

Неприменимые typed refs NULL. Исторический HTTP не копируется в GET автоматически: например verification_rejected читается200, logout — своей оболочкой. Новый negative business result не выдумывается для любого раннего400/403/409/429/503. Они не становятся сохранённым verification_rejected. Коды результата дополнения не меняют четыре прежних recordSchemaVersion=v1 Shadow.

Result_digest=SHA256 UTF-8 JCS объекта ровно {format,environment,contextId,action,operationId,result,resolvedAt}; format=auth-result-v1, result=result_data, resolvedAt — канонический UTC Z/миллисекунды. FK-поля проверяются на равенство этому DTO отдельно. Digest проверяет неизменность bytes/формата, не подтверждает истинность provider outcome.

## 4. Завершение login и три разных объекта cookie

### 4.1. login_completions — immutable

Поля: context_id:U UNIQUE, operation_row_id:U UNIQUE, result_id:U UNIQUE, subject_binding_id:U, login_id:U UNIQUE, realm:S(user/staff), completed_at:T. Все UNIQUE scoped environment. FK к соответствующим context/operation/result/subject и shadow.auth_sessions того же realm/principal. Completion допускается только результатом полного user/staff Auth; stage промежуточного MFA не создаёт строку. Completed_at=auth_sessions.authenticated_at; resolved_at результата — время его фиксации и не обязан совпадать до миллисекунды с подтверждением внешнего эффекта.

Context.completed, operation.resolved/result, completion, новый auth_session, credential, window/secret и при staff замена slot/отзыв прежнего сохраняются **в одной локальной транзакции**. Обязательная полнота проверяется к commit в обе стороны: нельзя оставить login без completion или completion без result/credential/window. Существующий provider full-auth сначала достоверно установлен; общей транзакции с ним нет. Unique context/login/operation запрещают два login при разных verify ID одного контекста; replay не меняет staff slot снова.

### 4.2. login_cookie_credentials — immutable проверочное представление

Поля: login_id:U UNIQUE, completion_id:U UNIQUE, realm:S(user/staff), credential_format:S(login-cookie-v1), key_id:text, secret_digest:H, issued_at:T. Составные FK completion/login/realm. Digest=HMAC отдельного purpose над version/environment/realm/loginId/секретом ≥256 случайных бит; secret не равен context-proof. Cookie name детерминирован realm/loginId по принятому контракту. Нет нового token вместо provider_session_ref и нет refresh-rotation этого credential.

Digest сохраняется после expiry/revoke: он нужен в том числе для ограниченного доказательства logout по прежнему credential. Его наличие **не делает login действительным** — каждое действие проверяет актуальные guards/epoch/identity/срок/slot. Закрытие окна восстановления не удаляет digest и не отзывает действующий login. Секрет без login/realm/env не принимается.

### 4.3. cookie_recovery_windows — mutable одноразовое закрытие

Поля: login_id:U UNIQUE, completion_id:U UNIQUE, source_context_id:U, deadline_at:T, first_confirmed_at:T?, closed_at:T?, close_reason:S(first_confirmed/deadline/login_revoked/context_revoked/reconciled)? , version,updated_at. FK completion с login/context; deadline=min(completed_at+5min,context.expires_at) immutable. При создании first/closed/reason NULL; effective open вычисляется по сроку и всем guards, не только по NULL.

Closed_at и reason либо оба NULL, либо оба заполнены; first_confirmed_at может появиться только после действительного Q01/current-staff. Если окно ещё открыто, первая проверка задаёт closed_at=first_confirmed_at и reason=first_confirmed. Если оно уже закрылось по deadline/revoke, историческая причина/время не переписываются; более позднее допустимое Q01 может отдельно заполнить first_confirmed_at (например cookie сохранилась после deadline). Закрытие необратимо. Deadline не заменяется closed_at. Нельзя восстановить окно сбросом first_confirmed_at или новым context.

### 4.4. cookie_recovery_secrets — отдельно стираемый секрет

Поля: window_id:U UNIQUE, credential_id:U UNIQUE, cipher_format:S(xchacha20poly1305-v1), cipher_key_id:text, nonce:bytea(24), ciphertext:bytea?, secret_deadline_at:T, erased_at:T?. Ciphertext содержит ровно исходный cookie-secret плюс tag16, максимум1024 bytes; AAD связывает environment/window/credential/login/realm/format/deadline. Deadline равен window.deadline и не продлевается. Секрет сравнивается с credential digest до выдачи. Неоднозначность/отсутствие до разрешённой выдачи —503, не генерация нового секрета.

При first-confirm/revoke/явном закрытии window в той же транзакции ciphertext→NULL, erased_at→T. При достижении deadline выдача немедленно запрещена логически; отдельный eraser либо ближайшее разрешённое обслуживание удаляет ciphertext и фиксирует факт. Задержка eraser не продлевает доступ. Это не обещание стереть старые WAL/backups: они зашифрованы отдельно, ключи/restore gate не дают повторно разрешить старый секрет. История window/credential/result остаётся. Eraser не имеет права менять результат или открывать окно.

## 5. Q01, восстановление cookie и отзыв: одна локальная граница

Применяется общий порядок §10. Перед транзакцией provider-проверка без долгих SQL locks; внутри заново проверяются current local guards. Q01/current-staff заранее выбирает X window (без S→X upgrade), current login S либо заранее X только при действительно разрешённом другом эффекте. Q01 не продлевает idle.

1. Q01: подтвердить выбранную cookie/login и актуальный допуск; X window; закрыть/отметить first_confirmed и стереть recovery ciphertext; commit; только после подтверждённого commit200 и проверенный X-Shadow-Login-Id. Потеря результата commit →техническая неизвестность, не гарантированный200. Следующее Q01 безопасно проверяет/дозавершает тот же служебный факт.
2. POST recovery и replay completion: текущий proof исходного context, его outcome/completion, доступ user/staff/login, deadline и slot; X той же window; если открыта — расшифровать и проверить **тот же** secret. Подготовить response в памяти, завершить транзакцию, только после подтверждённого commit Set-Cookie. Recovery не создаёт новый completion/result/login/window и не меняет deadline.
3. Если Q01 первой закрыла window, новая выдача409 CLOSED. Если recovery первой получила право ответа, её уже подготовленный HTTP может дойти после Q01 — сеть не отзывается. Это не новая выдача с новым секретом; поздняя cookie всё равно не обходит текущий отзыв/slot/epoch.
4. Logout/revoke заранее берёт X login, затем X window/secret, меняет guard/отзыв и закрывает выдачу вместе. Q01/recovery, ждущие этот guard, не продолжают по устаревшему снимку. Подтверждённый closed-window не равен logout, а недоступность Q01 не равна logout.

Служебные ошибки 409 NOT_APPLICABLE/CLOSED и503 сохраняют прежние смыслы. Сначала установлен результат: non-login result →NOT_APPLICABLE; result должен существовать, но повреждён/непрочитан →503, не NOT_APPLICABLE. Нет открытой window →CLOSED только при достоверном закрытии/сроке, не при отсутствующей обязательной строке.

## 6. Авторизация, повторы и атомарность Auth-операций

Admission применяет точный proof/current scope/transport quota до lookup replay. Сохранённый результат сравнивает исходное намерение и возвращается до проверки нового stage/challenge; текущий доступ и окно cookie всё равно обязательны. Другой payload — прежний409 KEY_REUSE_CONFLICT. Public ID не proof. Если требуется secret comparison, но ключ/данные недоступны, не угадывать равенство.

В короткой транзакции: заблокировать context X, создать/read scoped operation; закрепить C01 email, phase/admitted epoch. Новый внешний action закрыт, пока предшествующий конфликтующий action context dispatched/uncertain. Перед сетью — сохранить единственный dispatch seal; после доказанного provider outcome — одной локальной транзакцией stage/challenge/pointers, счётчик неверной проверки или успешные security-факты, result/completion/operation.resolved. Не сохранять результат отдельно от учитываемой неверной попытки. Счётчики/used steps — зависимость §12, отсутствие реализации не разрешает неполный commit.

Unknown сохраняет допуск и адрес/цель. Expiry/revoke запрещает новое исполнение, но не отменяет внешний эффект и не чистит историю. Reconciler может сохранять доказанный поздний outcome; если нужен новый локальный полный login, повторно проверяется текущий security допуск. После expiry не создаётся «свежий» login с новым временем по старому ответу; требование к позднему provider-факту остаётся отдельно от выдачи полного допуска. Уже закоммиченный completion возвращается как история только по разрешённому reader.

Если внешний эффект подтверждён, но локальный completion не был сохранён и текущий security допуск его запрещает, dispatch фиксирует confirmed_effect, а операция не получает выдуманный login_completed/verification_rejected. Окончательная API-классификация такого сочетания должна быть явно отражена D02; до этого сохранённые факты достаточны для сверки, но маршрут нельзя объявить полностью готовым. Не добавлять новое result_kind произвольной строкой. Это ограничение полноты реестра, не потеря внешнего факта.

## 7. Согласие на claim

### 7.1. claim_consents — immutable

Поля: context_id:U UNIQUE, draft_id:U, previous_ownership_id:U, actor_user_id:U, actor_identity_id:U, original_login_id:U, guest_context_id:U, confirmed_at:T. FK context kind=user_claim; actor/identity/login одной среды/user, target_login context=original_login; subject binding совпадает. Composite FK previous ownership на тот же draft и owner_kind=guest, guest_context_id совпадает с историческим владением. Guest context имеет kind=guest; это отдельный контекст от user_auth. Created/expires берутся только из context, не копируются расходящимся TTL.

Consent создаётся после доказанного Q01 исходного полного login и current guest доступа, без изменения draft/current ownership/version. Не резервирует draft и не подтверждает будущий успех. Контекст хранится после expiry/loss; execution_closed_at/revoked_at в оболочке закрывают новые действия. Секрет consent не требуется для принятого ограниченного GET исхода под новым полным login того же user.

При создании сервер проверяет first_confirmed_at window именно original_login, а не клиентский флаг «Q01 выполнен». Realm/identity/login сверяются под текущими guards. Последующая обычная Q01 не меняет immutable consent.

Для существующего draft-bound guest digest предлагается точное B1-D2 дополнение: guest_digest_version=guest-draft-proof-v1; HMAC-SHA256 отдельным guest-draft key над ASCII domain `shadow.guest.draft.v1`, байтом00, uint32BE длины UTF-8 environment, environment bytes,16 UUID bytes guest_context_id,16 UUID bytes draft_id и32 bytes исходного guest secret. Общий context proof имеет другой domain/key и не подставляется вместо этого digest. Context proof secret для этого профиля ровно32 CSPRNG bytes (удовлетворяет ≥256bit). Для проверки исторического draft digest версия должна однозначно определять key: keyId закрепляется доверенным version→key каталогом, не выводится из текущего active key; при ротации новая версия, старые digests не переписываются. После claim даже верный старый digest не даёт доступа, потому что current ownership уже user. Это предложенное физическое уточнение старых трёх guest-полей, не новая owner-роль.

Существующие draft_claim_receipts/ownership остаются единственным успешным результатом и областью однократности environment/draft. В receipt не добавляются operationId/consentId как новый dedup-key. Для typed ссылок допускаются дополнительные UNIQUE без новой колонки на existing receipt/ownership/login; это явная часть физической дельты БД, не смена прежней семантики.

## 8. Допуск claim и внутренние попытки

### 8.1. claim_executions — журнал, не постоянный guard

Поля: consent_id:U, draft_id:U, actor_user_id:U, original_login_id:U, admitted_epoch:V, request_started_at:T, admitted_at:T, deadline_at:T, executor_id:U, permit_digest:H, phase:S(admitted/uncertain/committed/confirmed_not_committed), receipt_id:U?, finished_at:T?, closure_evidence_ref:text?, reconciliation_item_id:U?, version,updated_at. FK consent с draft/actor/login; receipt только этого draft/actor/previous ownership; internal id — серверный UUID запроса, **не поле HTTP и не второй ключ идемпотентности**. Deadline=request_started_at+5s от доверенного серверного начала HTTP, не от позднего admission; admitted_at≥request_started_at и меньше deadline. Моносчётчик исполнителя включает prechecks/ожидания/все попытки, сохранённое UTC-время само по себе не механизм таймаута.

Нет UNIQUE(draft_id) или partial UNIQUE для «активного исполнения», lease takeover либо permanent guard-row. Индекс(environment,draft_id,phase,id) только для поиска допусков под прежним G3. Полная передача защищена прежним advisory G и unique(environment,draft_id) receipt. Допуск двух конкурентов не разрешает двум выполнить эффект; таблица хранит все поступившие факты, не резервирует владение.

Committed требует receipt/finished и доказанную полную CLAIM-OK; confirmed_not_committed — NULL receipt, finished/evidence и доказательство, что **все** допущенные попытки закончились без эффекта и исполнитель больше не может выполнить этот запрос. Остальные phase без receipt/finished. Истечение deadline само не terminal. Reconciliation_item допускается только этого исполнения и того же fence; неоднозначность не маскируется confirmed_not_committed.

### 8.2. claim_execution_attempts — история каждой SQL-попытки

Поля: execution_id:U, attempt_no:smallint1…3, executor_id:U, admitted_epoch:V, started_at:T, outcome:S(admitted/committed/proved_rollback/unknown), ended_at:T?, rollback_cause:S(serialization/deadlock/no_effect_before_start)?, evidence_ref:text?, receipt_id:U?, version,updated_at. UNIQUE(environment,execution_id,attempt_no); FK refs/actor/epoch согласованы с execution. Для committed требуется receipt и ended/evidence; proved_rollback — ended/cause/evidence без receipt; admitted/unknown не являются разрешением повтора. Unknown может перейти в доказанный terminal после сверки, прежние времена допуска не меняются.

Попытка регистрируется отдельным коротким commit до предметного исполнения. Это новый служебный факт Auth; прежняя CLAIM-OK атомарная граница не меняется. Настоящий DB transaction ID/backend ref в evidence полезен, но сам по себе не доказывает commit/rollback. Только serialization/deadlock с подтверждённым полным rollback допускают следующую внутреннюю попытку по принятому бюджету/паузам; отмена/timeout не такой случай. No_effect_before_start закрывает запрос без автоматического нового исполнения.

### 8.3. Протокол исполнения

До допуска: текущий полный user, прежний разрешённый lookup результата. Если успешный receipt этому user уже есть — вернуть его по прежнему replay, новый execution не нужен. Для нового исполнения проверить consent/proof/guest/target/current login и quota. В отдельной короткой admission-транзакции под gate S/G2/G3 зафиксировать execution+attempt1; при наличии чужого незавершённого допуска этого draft новое исполнение не выдавать. Эта проверка — дополнительная консервативная защита, не доказательство rollback отсутствующих строк.

Возможны одновременно принятые до видимости друг друга admission-записи. Безопасность не полагается на один SELECT «нет pending»: основной effect всегда под G3, X draft/ownership и прежними полными constraints. В effect-транзакции исполнитель доказывает собственный permit, живой context/login/guest и captured epoch, повторно читает receipt/прочие unresolved admission; иной неизвестный запрос закрывает новое действие. При несовместимом Serializable-снимке — полный rollback/свежая сверка, а не подтверждение отсутствия. Консервативная взаимная остановка двух admission разрешается сверкой, не перехватом lease.

При успехе в одной предметной транзакции: ownership/current pointer/закрытие прежнего guest-доступа/receipt/audit **и** собственные execution.phase=committed/attempt.outcome=committed/refs. Отказ по доступу/сроку/конфликту до эффекта может закрыть только собственный допуск доказательством; чужой не помечается rollback. При известном rollback запись о нём сохраняется отдельно, т.к. сама предметная транзакция откатилась. Crash до этой записи оставляет admitted/unknown, не свободное разрешение.

Обрыв ответа после commit: fresh авторизованное чтение находит receipt и полную цепочку, старый результат не исполняется снова. Обрыв до G3: запись допуска и epoch не позволяют назвать его отменённым лишь потому, что G3 свободен. Новый consent/operation/user не обходят неизвестность. Никакой код/SQL этого протокола пока не выполнялся.

## 9. Fence, drain и восстановление разрешения

### 9.1. reconciliation_runs — mutable служебная процедура

Поля: purpose:S(claim_unknown/environment_restore), draft_id:U?, from_epoch:V, to_epoch:V, phase:S(fenced/draining/verified/reopened/blocked), fenced_at:T, drained_at:T?, verified_at:T?, reopened_at:T?, inventory_evidence_ref:text?, drain_evidence_ref:text?, verification_evidence_ref:text?, authorization_evidence_ref:text?, witness_sequence:V, witness_head_digest:H, version,updated_at. Claim_unknown требует draft; restore — NULL. To_epoch>from_epoch и равно новой gate epoch; UNIQUE(environment,to_epoch). Связь gate.last_reconciliation_id создаётся deferred в одной транзакции с новым run; времена/refs заполняются только при доказанном соответствующем шаге. Blocked не даёт открыть gate.

### 9.2. reconciliation_items — immutable доказанный исход

Поля: run_id:U, claim_execution_id:U?, auth_dispatch_id:U?, verdict:S(committed/not_committed_and_fenced/unresolved), receipt_id:U?, result_id:U?, evidence_ref:text, evidence_digest:H, checked_at:T. Ровно одна target-ссылка; UNIQUE(environment,run_id,claim_execution_id) и dispatch-вариант для NOT NULL. Claim committed требует receipt, Auth committed — result либо подтверждённый provider evidence с отдельно указанной незавершённой локальной финализацией; такой неполный локальный случай **не позволяет verified/reopened** до её завершения. Остальные варианты result/receipt NULL. Новая проверка создаёт новый run/item, не переписывает прошлое свидетельство. Нет verdict, который назначает успех по count/таймауту.

### 9.3. Порядок

1. Под X gate закрыть admission, увеличить epoch, создать run и закрепить внешний witness intent/head. Захват X дожидается завершения транзакций, удерживавших S; не доказывает прекращения handlers до их SQL/внешних вызовов.
2. Составить полный inventory старых permits/executors/connections/external dispatches. Запретить возобновление старых очередей; доказанно завершить/остановить старые процессы и DB transactions. Worker может быть задержан до G3 — его captured epoch immutable и не обновляется на актуальный при продолжении. Provider-effects сверяются отдельно; нет доказательства остановки/исхода — blocked/closed.
3. Лишь после drain создать свежий primary Serializable snapshot, текущий допуск reconciler, G3 по нужному draft; сверить receipt/ownership/audit/fullness и каждый execution/attempt. Получение свободного G3 в старом snapshot не этот шаг. Unresolved item не позволяет объявить безопасное новое исполнение.
4. Если эффект отсутствует и поздний writer исключён, зафиксировать item, закрыть старые execution/consent для исполнения. Если эффект есть, подтвердить receipt/полноту и сохранить ссылки. Отсутствующий receipt при user ownership без полной цепочки — повреждение, не разрешение нового claim.
5. Подписанный отчёт/авторизация и свежий witness, все старые writers/dispatch в inventory имеют определённый исход →verified; отдельная короткая транзакция X gate открывает **новую** epoch и отмечает reopened. Разрешается только новое явное согласие с новой проверкой условий. Не восстанавливаются старый permit или proof. Gate блокирует среду консервативно, как в reviewed механизме; сужение до одного draft требует отдельного доказанного проекта.

Reconciler использует выделенный путь при closed gate, но не пользовательскую команду claim; он не создаёт новую передачу. Доступ к этому пути не возникает из роли Owner в UI. Restore дополнительно сверяет отзывы/ключи/login/scope с внешним источником; старый backup не возвращает прежний epoch/окно. Точное размещение/ACL внешнего witness — отдельная зависимость, локальные поля не заменяют его.

## 10. Порядок locks, полнота и права

Предлагаемое уточнение общего порядка: **gate S → прежний G1 → G2-A principals/identities/security → G2-B auth_sessions/staff slot → G2-C contexts → subject/email/continuation → operations → dispatches → challenges → completions/credentials → windows → secrets → claim executions/attempts → G3 → G4/G5/G6**. Ресурсы одного вида по полному environment/id; candidate refs определяются заранее, под lock перепроверяются. Claim consent immutable читается после context. Result/immutable refs — чтение с текущим доступом. Updates execution после G3 разрешены только если его X уже взят в G2; вставка собственных children не разрешает поздний захват чужого G2. Staff slot/неявные FK locks входят в проверяемый полный граф.

Типичная Auth подготовка не берёт X всех пользователей. Действие выбирает заранее S/X только затронутых guard/rows; новый субъект после provider verify определяется до локальной finalizer-транзакции. Q01/window не начинается S с последующим upgrade. Reconciler закрывает gate отдельно и не держит X gate, ожидая внешний provider/drain. Открытый admission не означает право обойти G1–G6. При обнаружении после G5 новой нужной ссылки G2 — rollback, не изменение порядка.

| Путь/роль | Разрешённая запись | Что запрещено |
| --- | --- | --- |
| Auth context/action procedures | contexts/bindings/operations/dispatches/challenges и атомарный result/completion; только проверенный scope | Прямой arbitrary DML, полный login из pending, произвольный result JSON |
| Login verifier/Q01 | Проверка credential; служебные first-confirm/window/secret | Продление idle Q01, новый login/rotation/новый deadline |
| Claim handler | consent preparation отдельно; execution/attempt и полный прежний CLAIM-OK | Второй клиентский key/постоянный per-draft guard, смена получателя при unknown |
| Secret eraser | Ciphertext/digest →NULL и точный erased_at по сроку/закрытию | Удаление history/receipt, продление срока/выдача cookie |
| Reconciler/control publisher | runs/items/gate, подтверждённая финализация старого исхода | Новое пользовательское действие/самовольный внешний повтор/открытие без evidence |
| Runtime API/staff | Только разрешённые projections через процедуры | Чтение секретных таблиц/сырого audit; роль Owner не DB superuser |

Процедуры с отдельными NOLOGIN owners/фиксированным search_path, минимальные права, RLS как дополнительная граница; никаких superuser/BYPASSRLS в runtime. Локальный result и связанные guard/children неделимы; отсутствие child не обходит полноту. Политика хранения M04 сохраняет историю, секреты удаляются отдельно. Существующие shadow constraints не ослабляются.

## 11. API ↔ источник и необходимые индексы

| Выдача/правило | Источник | Не подменять |
| --- | --- | --- |
| Auth-context stage/times/accessConfirmed | contexts + current challenges | last_user_activity_at/пустой объект при ошибке |
| GET Auth operation resolved | operations.result_id → immutable result, validated refs | текущий stage/пересчитанный результат |
| GET Auth operation unresolved | разрешённый context, достоверный scoped поиск без final result | недоступный/повреждённый storage |
| Completion/loginId | login_completions + result + auth_sessions | provider token/email/последний login пользователя |
| Восстановление cookie | исходный context/result/completion, current credential/login, window, cipher | новая cookie/new login/старый permissive cache |
| Logout target/recovery | context.target_login/source + binding + C07 result | login B, применённый лишь как доказательство |
| Claim200 | shadow.draft_claim_receipts и обе ownership, текущий полный получатель | последний consent/execution как «успех» |
| Claim202 после loss/expiry | сохранённый consent→тот же user/draft/environment + новый действительный login, достоверный поиск | public draftId, пустой receipt без разрешённой связи |
| Новый claim после unknown | runs/items + epoch/drain/закрытые старые permits + текущие условия | expiry/HTTP timeout/свободный advisory guard |

Кандидаты индексов помимо PK/описанных UNIQUE: contexts(environment,context_kind,expires_at,id) и target_login; contexts по source_context; challenges по context/issued_at; operations по context/phase и epoch/phase; dispatches по epoch/outcome; window по deadline/closed_at; cipher по secret_deadline/erased_at; consent(environment,actor_user_id,draft_id,context_id); executions(environment,draft_id,phase,id) и epoch/phase; attempts по execution/attempt_no; runs по phase/to_epoch; items по run/target. Secret digest не индексируется как публичный lookup. Plan/производительность не измерены; индекс не разрешает неполную сверку.

## 12. Честная граница D01-A и проверка БД

Готова точная предлагаемая карта перечисленных18 таблиц, local completeness/locks/retention и источников API. БД должна подтвердить physical constraints/typed FK/полный граф неявных locks и отразить принятую дельту в своём каталоге/матрице. Этот документ не меняет состав принятой схемы до такого отражения и не объявляет весь D01 завершённым.

Совместимость: до будущего включения writer и reader должны понимать один принятый storage format/action whitelist; неизвестный формат закрывается, не читается как v1. Обновление синтетических BASE-примеров должно включить полный новый login-комплект. Нельзя задним числом придумывать provider evidence/completion для ранее существующей auth_session; при будущем переносе таких данных нужен отдельный подтверждённый план, а не nullable-исключение, обходящее полноту. Формат claim-guard у одновременно работающих handlers один; смена только по принятому fence/drain. Этот раздел не содержит миграций или разрешения их выполнять.

Не покрытые этим поручением источники остаются явными зависимостями: principal security/factor versions/одноразовые TOTP steps и атомарные failure counters; транспортные sliding quotas; mfa management/reset evidence/двойные approvals/staff bootstrap/recovery; trusted selector/bindings; внешний witness/key service и подтверждённые полномочия reconciler. Их нельзя «дописать потом» внутри generic context/result JSON или запускать зависимый endpoint без enforcement. Работающий provider и его outcome correlation тоже ещё не доказаны. Provider table FK не выдумывается.

В [проверочных сценариях карты](backend-auth-storage-cases.md) перечислены обе очередности Q01/recovery/revoke, повтор операции/полнота, задержанный claim до guard, конкурирующие согласия, fence/crash/restore и secret erasure. Все варианты **не выполнялись**. Проверка документов не подтверждает DB/API/Auth/конкурентность/восстановление. Код, SQL, миграции, установка и развёртывание не начинались.

## 13. Сведение с параллельной картой БД PR №203

| Предмет D01-A | Соответствующая часть БД | Что нужно выбрать/свести, не складывая таблицы |
| --- | --- | --- |
| contexts + subject/email bindings | AC03 + AC06 | Отдельные typed children и proof в context против общей typed оболочки с отдельным verifier; состав неизменяемых целей/сроков должен остаться одинаковым |
| operations/dispatch/results | AC04/05/08 | Отдельная история dispatch и попыток против seal в operation; БД также покрывает namespace до context, который вне D01-A |
| completion/credential/window/cipher | AC05/07/16 + полный login | Явная локальная полнота и постоянный login verifier; storage split выбрать единым, не завести два окна одного login |
| consent/execution/attempts | AC03/19 | D01-A допускает несколько серверных request-records, AC19 unique consent; согласовать точную единицу admission и отсутствие повторного permit, сохранив единственный claim receipt |
| gate/runs/items и locks | AC01/19/34/35, карта БД §7 | Одно согласованное место claim-admission locks: D01-A держит свои execution/attempt X до G3, БД размещает AC19 в G3. Не смешивать эти порядки. Witness change-set из БД шире D01-A и требует собственного принятия |

BR01/02 (Q02 G1 и ABA), BR05 (witness change-set), BR06/07 (guest lifecycle и typed права) относятся к широкому пакету и не закрываются публикацией этой узкой карты. BR04/09 имеют пересекающиеся решения в D01-A (captured epoch/reconcile-only/стирание), но эквивалентность двух физических вариантов ещё должна быть проверена. BR08 остаётся capability gate. Историческое REVIEW-01 не переписывается: новые находки БД появились отдельно.

Числа54 и73 описывают разные объёмы предложений, не последовательные утверждённые расширения. Принятый baseline по-прежнему36. Следующий результат — единая согласованная физическая дельта на основе обоих пакетов, затем D02; текущий PR публикует подготовленную карту и не выбирает архитектуру за владельца/БД.
