# D02: закрытая дельта реестра first-session-registry-v6

02.11.2026 · При финальной интеграции 03.11.2026 учтены main3c832f0/PR №210, AS01–AS28 и HR/HE; адресные дельты к 78 таблицам добавлены в AS §11 и карту истории §10. **Проект полного издания v6 для единой вычитки**, связан с [точным D02 API](backend-auth-d02-contracts.md). Текущий опубликованный принятый реестр пока v5. U01–U03/P01–P05 приняты отдельно; выбор новых DTO/словари этой редакции не подменяется фактом создания файла. После пакетного принятия v6 запись §15 [общего реестра](backend-code-registry.md) становится указателем текущего издания без переписывания v1–v5.

Все прежние Shadow команды/причины/права/audit/форматы сохраняются. Новых top-level reasonCode не вводится. AUTH_COOKIE_RECOVERY_NOT_APPLICABLE расширяет применимость только на явно названные Auth namespaces; CATALOG_CHANGED остаётся только Q02-list. Неизвестное значение клиенту400, обязательная неизвестная сохранённая форма503 RECORD_UNAVAILABLE. Словари перечислены полностью для новых групп; строки не разрешают декартово произведение всех action/result.

03.11.2026 · Уточнение по [BDR01–BDR08](database-auth-d02-review-2026-11-03.md): [ответ для повторной сверки](backend-auth-d02-bdr-response.md). Все новые точные профили ниже остаются проектом D02, принятые P01–P05/U01–U03 не расширяются автоматически.

## 1. Операции, разрешённые результаты и источники

Для всех новых action authoritative ключ AC04(environment,namespace,scope,action,client_operation_id); source namespace до context не переназначается. Каждый result AC05 имеет ровно одну operation, typed refs и обратную полноту. Rows ниже задают **весь whitelist**; кроме явно отмеченных verify paths результат verification_rejected недопустим. Поздний auth_completion_not_issued допускается только в трёх строках полного login и старом user verify.

| Action / область | Разрешённый result.kind | Обязательные источники сверх AC04/05/08 |
| --- | --- | --- |
| C01/C03 · прежний user Auth | email_dispatch_accepted | AC03/07 email-binding, AC09 current email, AC39 send proof |
| C02/AUTH_TOTP_VERIFY · прежний user Auth | auth_step_required,login_completed,verification_rejected,auth_completion_not_issued | AC03/09/10/11/12/39; full login только с AC38/16/07 и Shadow login |
| AUTH_TOTP_CHALLENGE_RENEW · прежний user Auth | totp_challenge_renewed | AC03/09 current/replaced, без нового factor |
| AUTH_EMAIL_LINK_VERIFY · user Auth, новый | Те же допустимые C02 result | AC09 email challenge, одно потребление link/code; AC39 при provider verification |
| email_request/email_resend · MC | email_dispatch_accepted | AC03 identity binding, AC09 email family, AC12/39 |
| email_verify · MC | mfa_stage_ready,verification_rejected | AC09/12; stage/current challenge одного MC |
| factor_prepare · MC enroll/reenroll | mfa_factor_prepared | AC10 prepared, AC09 TOTP challenge, временный AC07 factor_reveal, AC39 |
| factor_secret · MC | mfa_secret_accessed | AC07 доступен только до закрытия reveal; result не seed |
| challenge_renew · MC | mfa_challenge_renewed | AC09/replaced ID, тот же factor, нет unresolved verify |
| mfa_confirm · MC enroll | mfa_enabled,verification_rejected | AC02/10/11/12/39, audit/notification; старые login сохраняются |
| mfa_confirm · MC disable | mfa_disabled,verification_rejected | AC02/10/11/12/39 + отзывы прежних login, audit/notification |
| mfa_confirm · MC reenroll | mfa_reenrolled,verification_rejected,auth_completion_not_issued | Активация + при full completion AC38/16/07/Shadow login; late outcome не отменяет доказанную активацию |
| reset_request · исходный UA | mfa_reset_requested | AC30 с теми же context/client op/user, typed source через AC04/30 |
| case_create · reset_request namespace | mfa_reset_case_created | AC25/26/27/29/30; result_case/result_case_version обязательны |
| approval_options · reset security_case | mfa_reset_approval_options | AC09 точный case/version/actor tuple |
| approve · reset security_case | mfa_reset_approved,verification_rejected | AC27/28, consumed AC09, current SL/grants, AC32/33 |
| reset_execute · security_case | mfa_reset_completed | AC04 exact approvals, AC02/10/security revokes, AC25/26/30, audit/notification |
| login_options · SA | staff_authentication_options | AC09 WebAuthn discovery challenge |
| staff_login · SA | staff_login_completed,verification_rejected,auth_completion_not_issued | AC20/02/09; full комплект AC05/38/16/07/Shadow login+staff slot |
| bootstrap_create · bootstrap_handle | staff_registration_context_created | AC21/22 consumed + AC03/06 + result_context в одной T |
| registration_options · RG bootstrap | staff_registration_options | AC09 webauthn_create, тот же AC22/staff/manifest |
| registration_verify · RG bootstrap | staff_credential_registered,verification_rejected | AC20 active + source result, staff/handle/RP фиксированы; не login |
| recovery_create · recovery_handle | staff_recovery_context_created,verification_rejected | AC23/24 consume + AC03/06/result_context; invalid unknown handle не фиктивная operation чужого subject |
| recovery_registration_options · SR | staff_registration_options | AC09 webauthn_create собственного staff |
| recovery_registration_verify · SR | staff_credential_registered,verification_rejected | AC20 limited, AC25/26/27 single case, source context/version |
| pair_create · меньший из двух context IDs | staff_recovery_pair_created | Оба AC03, AC25/26/27 common pair; замыкание прежних неисполняемых single proposals |
| recovery_options · security_case | staff_recovery_approval_options | AC09 конкретной версии/approver, limited key только для своего pair |
| recovery_approve · security_case | staff_recovery_approved,verification_rejected | AC28/27 + consumed challenge; single current SL, pair оба SR |
| recovery_complete · security_case | staff_recovery_completed | Exact approval tuple, AC20/02/Shadow identity/grants/revokes, обе стороны pair одной T |
| recovery_code_context_create · login | recovery_code_context_created | AC03/06/result_context, исходный current SL |
| recovery_code_options · SC | recovery_code_options | AC09 fresh passkey того же staff |
| recovery_code_issue · SC | recovery_codes_issued,verification_rejected | AC23/24 ровно10, прежний set revoked, AC07 reveal, audit; secret отдельно |
| guest_refresh · GP | guest_context_refreshed | AC03/06, неизменный ID/proof; expiry max, no-op/replay не новый срок |
| C07 · user/staff logout | logout_completed (только storage) | AC03 typed target A/authorization B, AC05.target_login_id; wire204 либо специальный LogoutReply |

Для C07 storage result ровно kind=logout_completed,loginId:U,confirmedAt:T; он не добавляется к wire union user GET §7. Неподтверждённый C07 не хранится как completed. Claim не AC04/05: AC03 consent → AC19/40 → прежний Shadow claim receipt; Q05 не расширяется.

GET-whitelist: M — email_request/email_resend/email_verify/factor_prepare/factor_secret/challenge_renew/mfa_confirm; SA — login_options/staff_login; B — bootstrap_create/registration_options/registration_verify; K — recovery_create/recovery_registration_options/recovery_registration_verify/recovery_options/recovery_approve/recovery_complete; P — pair_create/recovery_options/recovery_approve/recovery_complete; Z — recovery_code_context_create/recovery_code_options/recovery_code_issue; GP — guest_refresh. Case reset и MR описаны в API. Action не из своего списка400, а не поиск по чужому namespace. Для K/P действует точный resolver API §6.1: K всегда исходный single scope через AC20.source_case_version_id и registering AC04, P свой pairId. Unresolved ищется в AC04 без обязательного AC05; current pointer не locator истории.

### 1.1. Обязательные typed refs результата

Обозначения таблицы: перечислены **все непустые variant refs AC05**, прочие из result_context_id/result_login_id/completion_context_id/completed_at/target_login_id/result_challenge_id/replaced_challenge_id/result_factor_id/result_case_id/result_case_version_id/result_credential_id/result_recovery_set_id — NULL. `FULL` означает result_login_id+completion_context_id+completed_at и matching AC38/16/07/Shadow login. completed_at AC05 — только время полного login; похожее поле payload у factor/case не заполняет его автоматически. operation_id/kind/record_format/resolved_at и прочие общие обязательные поля не nullable.

| Result.kind + action/purpose | Непустые variant refs | Источник / обратная полнота |
| --- | --- | --- |
| email_dispatch_accepted | result_challenge_id | Подтверждённо выданный AC09 своей send operation; provider dispatch в AC39 |
| auth_step_required: totp_verification | result_challenge_id | Прежний user C02, тот же TOTP challenge/subject/context |
| auth_step_required: totp_enrollment | Нет | Restricted исходный context через AC04; нет подготовленного factor/login по факту одного email |
| login_completed / staff_login_completed | FULL | Исходный AC03/realm/principal, staff slot для staff; один полный комплект |
| totp_challenge_renewed / mfa_challenge_renewed | result_challenge_id,replaced_challenge_id | Новый и заменённый AC09 одного context/purpose, атомарный current pointer |
| verification_rejected во всех разрешённых action §1 | Нет | Scope/источник отказа через AC04, challenge/factor/case через исходную операцию и её проверенные refs; не создаются фиктивные result children. Истечение по API §7.1, не универсальный rejected |
| mfa_stage_ready: factor_prepare | Нет | Email доказан, factor ещё не создан |
| mfa_stage_ready: totp_verification | result_challenge_id | Disable challenge AC09; закреплённый factor через AC03/09 |
| mfa_factor_prepared | result_factor_id,result_challenge_id | Одна prepared AC10 и AC09, временный reveal AC07 |
| mfa_secret_accessed | result_factor_id | Точная историческая версия factor; секрет не часть AC05 |
| mfa_enabled / mfa_disabled | result_factor_id | Активированная либо историческая отключённая AC10, не новый current pointer при чтении |
| mfa_reenrolled | result_factor_id,FULL | Подтверждённая активация и полный новый login в finalizer; §4.3 |
| mfa_reset_requested · R14 | Нет | AC30 найден по AC04.context_id+client_operation_id/user; payload.resetRequestId равен AC30.id. Case/version ещё законно отсутствуют |
| mfa_reset_case_created · R16 | result_case_id,result_case_version_id | AC25/26 созданного reset, AC30 из исходного reset_request scope; обязательные participants/evidence |
| mfa_reset_approval_options | result_case_id,result_case_version_id,result_challenge_id | Версия из decisionVersion операции, её AC09; не latest version при replay |
| mfa_reset_approved | result_case_id,result_case_version_id | AC28.operation_id=исходной AC04, её AC27/09/версия; audit/grants §4.1 |
| mfa_reset_completed | result_case_id,result_case_version_id,result_factor_id | Execution tuple AC04 и исторический AC26.factor_id; AC30 завершён matching result, revokes/security полный комплект |
| staff_authentication_options | result_challenge_id | AC09 собственного SA; discovery subject может ещё отсутствовать |
| staff_registration_context_created · R29 | result_context_id | Новый RG и consumed AC22 того source scope, без case/credential |
| staff_registration_options · bootstrap либо recovery | result_challenge_id | AC09 соответствующего RG либо SR; registration ещё не создаёт case/credential |
| staff_credential_registered · registration_verify/bootstrap | result_credential_id | AC20 active, registered_by_operation_id=AC04; source_case_version_id NULL; case refs NULL |
| staff_credential_registered · recovery_registration_verify/R36 | result_credential_id,result_case_id,result_case_version_id | AC20 limited + исходный single AC25/26/27 одной T; AC20.source_case_version_id равен result_case_version_id; это обязательный внутренний комплект даже без публичных case полей |
| staff_recovery_context_created · R33 | result_context_id | Consumed AC24/23 и новый SR; **case/version/credential ещё NULL**, limited status не наличие limited credential |
| staff_recovery_pair_created | result_case_id,result_case_version_id | Pair AC25/26/четыре AC27, оба исходных SR и закрытие single proposals одной T; два context не вмещаются в один result_context_id, поэтому он NULL |
| staff_recovery_approval_options | result_case_id,result_case_version_id,result_challenge_id | Exact case/version из исходного scope/payload, selected approver в AC09; API §6.1 |
| staff_recovery_approved | result_case_id,result_case_version_id | AC28 и свой AC27/09/credential; наличие результата не текущее разрешение |
| staff_recovery_completed | result_case_id,result_case_version_id | Single/pair определяется AC25; все subject credentials через exact AC27, не произвольно один result_credential_id для pair; approvals/отзывы/уведомления полны |
| recovery_code_context_created | result_context_id | SC из source login AC04, собственный staff |
| recovery_code_options | result_challenge_id | AC09 этого SC/selected staff |
| recovery_codes_issued | result_recovery_set_id | AC23 и ровно десять AC24, старый set revoke, AC07 reveal; payload handle/version того же set |
| guest_context_refreshed | Нет | Уже существующий guest через AC04.context_id; result_context_id не означает обновлённый context |
| logout_completed (storage C07) | target_login_id | Исходная цель A; не authorizing B и не новый result_login_id |
| auth_completion_not_issued · user/staff verify | Нет | Доказанный outcome AC39 либо local AC09/20, execution closure; full refs NULL |
| auth_completion_not_issued · mfa_confirm/reenroll | result_factor_id | Доказанно активированная AC10 и §4.3; full refs NULL, activation не откатывается |

Если публичный DTO содержит ID/версию соответствующего ref, они обязаны совпасть. Дополнительные обязательные внутренние refs таблицы выводятся из исходной операции/атомарно созданных children, не из latest current state; отсутствие публичного поля не снимает их D-полноту. Исторические timestamps не заменяются временем GET. DecidedAt=resolvedAt для U03, completedAt payload там NULL. Resolved AC04/result immutable; повтор не создаёт AC05 или новый case.

## 2. Контексты, purpose и stage

| AC03.kind / realm | Полный purpose whitelist | Stage whitelist / начальная стадия |
| --- | --- | --- |
| user_auth / user | login | ready,email_verification,totp_verification,totp_enrollment,completed; ready |
| guest / guest | guest_access | active; active |
| mfa / user | enroll,disable,reenroll | email_required,email_verification,factor_prepare,totp_verification,completed; reenroll сразу factor_prepare, остальные email_required |
| mfa_result / user | result_read | active; active |
| logout / user | logout | active; active |
| staff_logout / staff | logout | active; active |
| user_claim / user | claim | active; active |
| staff_auth / staff | login | ready,challenge,completed; ready |
| staff_registration / staff | bootstrap,recovery | ready,challenge,completed; ready; recovery-вариант зарезервирован исходной картой, в D02 writer запрещён; K использует SR, не создаёт второй context |
| staff_recovery / staff | recovery | limited,awaiting_approvals,committing,completed,expired; limited |
| staff_recovery_codes / staff | recovery_codes | ready,challenge,completed; ready |

Purpose=recovery у staff_registration сохранён только как известный вариант исходной схемы, не активный путь записи D02. Публичный K сохраняет SR и отдельные registration-challenge/credential refs, без второго registration context и без маскировки limited как SA. Включение reserved варианта требует отдельной явной дельты, D03 проверяет выбранный единственный путь. Source/authorization ссылки и NULL матрица принятой карты обязательны. Реестр не разрешает все пары переходов: whitelist переходов — API §6. Unknown execution хранится в AC04, не новый stage=error.

AC06 proof purpose ровно context_proof; domain содержит kind/realm, поэтому logout proof не user_auth. Новый D02 issuance profile для R29/R33/R43 называется derived-context-proof-v1; обычные случайные proofs random-context-proof-v1. key_id — immutable trusted key-bundle ref с разными derivation/verifier ключами, не один общий ключ всех целей. Прежние draft-bound proof и AC38 full-login — отдельные форматы. Ротация не обнуляет текущие scopes/replay counters и не позволяет пересоздать context.

AC09 challenge purpose: user_email_login,user_totp_login,mfa_email_enroll,mfa_email_disable,mfa_totp_enroll,mfa_totp_disable,mfa_totp_reenroll,staff_login,staff_bootstrap_registration,staff_recovery_registration,mfa_reset_approval,staff_recovery_approval,recovery_codes_issue. Kind соответственно email/totp/webauthn_get/webauthn_create. Case-specific purpose требует case_version_id и approver staff; discovery staff_login может subject NULL до успешной проверки. Email-link не новый challenge purpose: тот же user_email_login и общий consume.

AC12 counter purpose: email_verification для email_family; totp_login/totp_enrollment/totp_disable для user_purpose (reenroll использует enrollment); recovery_code для recovery_handle. WebAuthn anti-abuse не выдумывает user TOTP counter. AC13 quota purpose — закрытый составной ключ realm+context purpose+route class из context_create,prepare,verify,read,secret_reveal,cookie_recovery,guest_refresh,logout_prepare,logout_read,email_send,email_verify,preidentity_prepare; допустимость только из маршрутов/API и прежних user Auth limits, не клиентское поле.

## 3. Точные enum хранения и форматы

| Таблица/поле | Закрытые значения |
| --- | --- |
| AC01 state | open,closed; closure_reason=claim_unknown,environment_restore,initialization; null только open. security_incident — зарезервированное проектное имя, не разрешённое значение writer/decoder v6, см. §3.2 |
| AC02 state / user mfa_requirement | active,transition,blocked / none,required,enrollment_required; staff mfa_requirement null |
| AC03 revoke_reason | logout,principal_blocked,identity_revoked,security_revocation,source_revoked,environment_restore; expiry отдельно, не revoke |
| AC04 namespace / phase | context,bootstrap_handle,recovery_handle,security_case,reset_request,login / admitted,dispatched,uncertain,resolved,closed_without_dispatch |
| AC04 resolution_basis | local_commit,provider_confirmed,reconciled_effect,reconciled_no_dispatch; null до финального решения |
| AC07 owner_kind / purpose | operation,factor,recovery_set,login,context / login_cookie,factor_reveal,recovery_codes_reveal,email_delivery. Login_cookie→login; factor_reveal→factor; codes→recovery_set; email→context. Operation-owner зарезервирован схемой, не используется текущим перечнем secret, неизвестное сочетание запрещено |
| AC08 purpose | raw_email,otp_code,email_link_token,bootstrap_handle,recovery_code,webauthn_assertion,webauthn_attestation,source_cookie. Только реально присутствующая sensitive часть; нет фиктивной пустой строки для операции без неё |
| AC09 state / issuer_source | active,replaced,consumed / provider,local_adapter. Expiry вычисляемый |
| AC10 state / provider | prepared,active,disabled,revoked / supabase_auth; profile_code=user-totp-login-v1, параметры прежнего принятого Auth |
| AC12 scope_kind | user_purpose,email_family,recovery_handle |
| AC13 scope_kind | user,staff,guest,context,login,email,source_network,environment |
| AC15 kind | default,setup_draft |
| AC16 close_reason | first_confirmation,deadline,login_revoked,context_revoked,reconciled; null до закрытия |
| AC17 realm | user,guest |
| AC19 state | admitted,uncertain,committed,closed_without_effect |
| AC20 state / algorithm | limited,active,revoked / -7,-257 |
| AC25 kind / state | mfa_reset,staff_recovery_single,staff_recovery_pair / collecting,authorized,executing,completed,rejected |
| AC27 role | subject,approver; cardinality API §6 |
| AC30 status | requested,under_review,completed,rejected |
| AC31 route_code / target_kind | user_catalog,user_setup,user_review,user_session,staff_session_view / none,draft,session; допустимые пары API §9 |
| AC32 outcome | succeeded,rejected,closed,uncertain; uncertain только факт технического неизвестного исполнения, не финальный business result |
| AC34 state | intent_registered,local_committed,confirmed,no_effect_proven,uncertain |
| AC35 target_kind | command_receipt,claim_receipt,review,auth_operation,auth_login,cookie_window,claim_admission,secret_material,reconciliation_run,security,context,binding_version,read_scope,staff_assignment,factor,credential,case_version,catalog_source,trader,paper_control,login_policy_control,user_identity,staff_identity,key_publication; ровно одна соответствующая typed ссылка |
| AC36 purpose / state | mfa_enabled,mfa_disabled,mfa_reset_completed,staff_credential_changed,staff_recovery_completed,recovery_codes_issued / pending,dispatching,sent,uncertain,failed |
| AC37 outcome | pending,accepted,not_sent_proven,uncertain |
| AC38 credential_format | login-cookie-v1 |
| AC39 outcome / provider_code | sealed,uncertain,confirmed_not_sent,confirmed_effect / supabase_auth; local WebAuthn не внешний dispatch, результат его локальной проверки в AC05/09/20 |
| AC40 outcome / rollback_cause | admitted,committed,proved_rollback,unknown / serialization,deadlock,no_effect_before_start; rollback_cause только доказанному rollback |
| AC41 purpose / phase | claim_unknown,environment_restore / fenced,draining,verified,reopened,blocked |
| AC42 verdict | committed,not_committed_and_fenced,unresolved |

AC21/22/23/24/26/28/29/33 не получают выдуманного lifecycle enum: у них typed references/version/consumption/expiry и права записи по принятой карте. Сохранённый consumed код не unconsumed после expiry. Прочие внешние source_ref/key_id/policy_ref/provider_ref/descriptor IDs — доверенные ссылки, не arbitrary client enum. Полный provider capability/параметры не подтверждены одним названием.

Auth record_format для AC05: user-auth-result-v1 (прежняя область с явной v6 дельтой union), mfa-operation-result-v1, staff-auth-result-v1, staff-bootstrap-result-v1, staff-recovery-result-v1, staff-recovery-codes-result-v1, mfa-reset-result-v1, guest-operation-result-v1, logout-result-v1. Decoder выбирает tuple namespace/context-kind/action/record_format, не одно kind. Предыдущий потребитель, не знающий нового result, закрывается технически, не читает как старый. До rollout нужен проверенный совместимый decoder inventory D03; рабочих сохранённых Auth-данных эта задача не меняет.

AC07 cipher_format=short-secret-xchacha20poly1305-v1: nonce24, tag16 внутри ciphertext, key32 вне БД; nonce сохраняется после erasure, AAD env/id/purpose/typed owner/format/deadline. AC08 comparison_format=auth-sensitive-compare-v1 — точные bytes ниже. AC04 nonsecret canonical digest — SHA256 JCS только несекретных полей; sensitive parts отдельно AC08. Одинаковый публичный digest недостаточен.

### 3.1. Нормативный проект кодирования proof и сравнения

Это дополнительный профиль D02, подлежащий пакетному принятию; не новая генерация ключей и не доказанная реализация. Одно имя формата допускает только одно кодирование. D03 строит проверки по этой спецификации, не выбирает формулу через test vectors.

Обозначения: `F(x)` — длина **bytes** x как unsigned 32-bit big-endian (ровно 4 bytes), затем x; переполнение/невалидное кодирование отклоняется, не truncation. `D(literal)` — ASCII ровно указанного literal, затем один byte 0x00. Конкатенация строго слева направо, без пробелов/разделителей вне F/D. Строки — UTF-8 без BOM, Unicode normalization/trim/case-fold запрещены; enum/domain/UUID — ASCII, UUID canonical lowercase с дефисами. Environment — точное каноническое значение environment из trusted descriptor/строк БД; не клиентская строка и не hostname. UUID не преобразуется в 16-byte форму. Все HMAC ниже — HMAC-SHA256, полный 32-byte результат, без усечения.

Key-bundle по AC06.key_id содержит отдельные 32-byte `Kderive` и `Kverify`, разные случайные ключи с различными назначениями; ссылка immutable, ключи вне БД. Random-context profile не использует Kderive. Ключ AC08 `Kcompare` — отдельный 32-byte ключ по своему key_id; он не Kderive/Kverify/AC38/cipher/witness key. Недоступность/неизвестная допустимость ключа —503; нет default key или нового key_id для старого result. Lifecycle ключей остаётся D03/M05, scope этим не обнуляется.

**derived-context-proof-v1:**

`secret = HMAC(Kderive, D("shadow.auth.context-derive.v1") || F(environment) || F(realm) || F(context-kind) || F(context-id) || F(source-namespace) || F(source-id) || F(source-proof))`.

| Маршрут | context-kind / realm / source | Точные source-proof bytes |
| --- | --- | --- |
| R29 | staff_registration / staff / bootstrap_handle + AC22.id | 32 decoded bytes canonical base64url bootstrapHandle (не его 43 ASCII символа); проверенный исходный handle этой операции |
| R33 | staff_recovery / staff / recovery_handle + AC23.id | 32 ASCII bytes recoveryCode после строгого JSON parse; ровно A–Z/2–7, без дефисов/trim. recoveryHandle разрешает именно этот set, не код другого set |
| R43 | staff_recovery_codes / staff / login + выбранный Shadow login ID | Точные ASCII bytes значения выбранной full-login cookie, уже проверенной AC38; без cookie-name/знака '=' перед значением/кавычек, без URL/base64-декодирования или иной нормализации. Не другая cookie браузера и не provider token |

Source operation и source namespace неизменны; context-id — только исходный AC05.result_context_id. Cookie limited context содержит canonical base64url этих 32 secret bytes без padding (43 символа). AC06.digest_format=derived-context-proof-v1; одинаковые исходные bytes/ключи/context дают ту же cookie. Для random-context-proof-v1 secret — исходные 32 криптографически случайных bytes, сохранённый verifier не позволяет их заново вывести. Это не обещание восстановления любого потерянного random proof.

**Verifier AC06 для обоих profiles:**

`digest = HMAC(Kverify, D("shadow.auth.context-verify.v1") || F(environment) || F(realm) || F(context-kind) || F(context-id) || F("context_proof") || F(digest_format) || F(secret))`.

Проверка получает secret через строгое canonical base64url-декодирование limited cookie. Purpose/kind/realm/context/profile берутся из ожидаемой trusted записи. Digest — 32 binary bytes; сравнение без раскрытия секрета. Derivation и verifier имеют разные ключи/domain; полный login AC38 не переводится на этот профиль. В R43 исходная cookie служит только проверенным входом для создания SC, не восстанавливается/не меняется.

**auth-sensitive-compare-v1:**

`comparison_tag = HMAC(Kcompare, D("shadow.auth.sensitive-compare.v1") || F(environment) || F(namespace) || F(scope-id) || F(action) || F(client-operation-id) || F(purpose) || F(sensitive-bytes))`.

Все строковые части имеют описанное кодирование. Raw email/code/token/handle/source_cookie — исходная строка после строгого JSON parse либо точное выбранное cookie value, без trim/Unicode normalization; bytes UTF-8 (ASCII у ограниченных алфавитов). WebAuthn assertion/credential — UTF-8 JCS целого принятого закрытого объекта; base64url поля сначала проверены на canonical spelling, не переинтерпретируются при сравнении. Разные sensitive parts хранятся по разным AC08 purpose, а не склеиваются без границ. Raw email comparison не подменяется нормализованным адресом доставки. Формула comparison **намеренно** отличается от R29 derivation: сравнивает исходную строку, derivation принимает decoded handle bytes.

Exact POST replay требует исходного proof/AC08 comparison, живого разрешённого context/reveal пути и исходных ключей. Consumed handle/code не разрешается другой операции; источник восстанавливает только свою прежнюю операцию. Erased comparison/digest либо утраченное исходное доказательство не дают равенство/новую cookie. Исторический GET использует собственный текущий допуск; он не извлекает bytes. Новые реальные ключи, test vectors и криптографические испытания здесь не создаются.

### 3.2. Зарезервированный security_incident

BDR07: security_incident не является поддерживаемым writer-вариантом этого D02. Ни API, ни control writer не записывают его в AC01, не создают AC41 с выдуманным purpose и не маскируют incident под claim_unknown/environment_restore. Decoder неизвестного сохранённого значения закрывается503 RECORD_UNAVAILABLE; reserved не означает допустимую рабочую строку.

Действуют только принятые claim_unknown (draft обязателен), environment_restore (draft NULL) и первоначальный закрытый initialization без первой AC41. Самостоятельный incident-протокол потребует отдельного решения владельца по purpose/inventory/drain/reopen и инфраструктурным полномочиям. Эта редакция исправляет неподдерживаемое имя проекта v6, не расширяет AC41 и не отменяет существующие способы закрытия/защиты среды вне пока не реализованного Auth API. Рекомендация и точная граница будущей дельты — [ответ БД §3](backend-auth-d02-bdr-response.md).

## 4. Права и обязательный аудит

Физические имена grant: environment,action_code,section_code,data_type_code,product_mode,venue_scope,venue_id. Ранние logical screen/field_group/scope отображаются именно на section/data_type/venue_scope. Не выдавать половины права из разных grants.

| Назначение | Полный документальный grant / статус |
| --- | --- |
| Создание/просмотр reset case, options/approve | mfa_reset_review / ADM-02 / user.mfa_reset_case / paper / all / venue_id=null; принят P02 |
| Reset execute | mfa_reset_execute / ADM-02 / user.mfa_reset_case / paper / all / null; принят P02. Для чтения собственного execute-result то же право, для current case нужен review |
| Подтверждение single staff recovery второго владельца | staff_recovery_approve / ADM-14 / staff.auth_recovery / paper / all / null; точная техническая конкретизация D02 для вычитки, не уже выданное право |

R43–46 — собственное credential self-service current staff login/assignment и свежий passkey, не административное право на чужой набор. Pair использует ровно принятый ограниченный протокол обоих владельцев; limited key не предоставляет обычный grant. Проверка актуального principal/identity/security/published owner assignment остаётся обязательной. Bootstrap manifest содержит утверждённый grants digest; документ не назначает реальных людей/секреты и не расширяет инфраструктурные ACL. При отсутствии новых прав endpoint закрыт, не fallback к имени Owner.

Audit AC32 хранит typed refs и safe_details={} для перечисленных событий. Служебная диагностика не добавляет произвольный текст. Если actor имеет SL, actor_staff_id/actor_login_id и sufficient AC33 обязательны для административного grant-действия; собственное self-service доказывается login/context/credential, не фиктивным grant. User action — actor_user_id и context/operation, login только когда был full UL. Для pair/limited recovery системный controller фиксирует system_actor_ref, typed context/case/result; реальные участники доказаны AC27/28 и source contexts, не выдуманным full actor_login. Необходимые AC33 относятся только реально использованным действующим grants. Это точная audit-матрица D02, не разрешение обойти полномочия.

| kind | Обязательные typed цели и атомарная граница |
| --- | --- |
| auth.mfa_reset_requested | operation/result/context, AC30 через source tuple; с созданием запроса |
| auth.mfa_reset_reviewed | operation/result/case_version и review grant evidence; с case creation |
| auth.mfa_reset_approved | operation/result/case_version/context challenge, sufficient grant+approval_id; с AC28 |
| auth.mfa_reset_completed | operation/result/case_version, exact execution approvals и execute grant; с factor/revokes/result/notification |
| auth.factor_change_completed | operation/result/context/actor_user_id, точный factor через AC05.result_factor_id; обязательное принятое событие каждого подтверждённого enroll/disable/reenroll, полный состав §4.3 |
| auth.login_completed | operation/result/context/target_login; с полным login-комплектом |
| auth.login_not_issued | operation/result/context; AC39 proof либо доказательство локального WebAuthn outcome, никогда target_login |
| auth.logout_completed | operation/result/context/target_login; с доказанным завершением выхода |
| auth.cookie_recovery_closed | context/target_login; window через unique login, с закрытием/erasure |
| auth.staff_credential_registered | operation/result/context/credential; с registration, не full login |
| auth.staff_recovery_started | operation/result/context; с code consume/ограниченным context |
| auth.staff_recovery_pair_created | operation/result/case_version; с обоими contexts и четырьмя participants |
| auth.staff_recovery_approved | operation/result/case_version/context; AC28, у SL approver достаточный recovery grant |
| auth.staff_recovery_completed | operation/result/case_version; с полной активацией/отзывами/notification |
| auth.recovery_case_superseded | case_version/context/operation; закрывает прежний неисполняемый single proposal при pair-create, не executing |
| auth.recovery_codes_issued | operation/result/context/recovery_set; с10 children/отзывом старого набора |
| auth.claim_admitted,auth.claim_closed | context/claim_admission когда существует; при доказанном закрытии без admission — только исторический consent/context и служебный actor, без фиктивного AC19 |
| auth.environment_fenced,auth.environment_reopened | reconciliation_run, system_actor; с gate/epoch и проверенным внешним основанием |
| auth.reconciliation_outcome | reconciliation_run и целевой operation либо claim_admission/context; с разрешённой фиксацией outcome |
| auth.context_execution_closed | Принятый kind сохранён: исходный context/operation когда существует, system_actor_ref; с доказанным закрытием исполнения, не новый business result |
| auth.reconcile_outcome_recorded | Принятый kind сохранён: исходный operation/context, system_actor_ref и typed reconciliation_run когда есть; только доказанный outcome |

Это закрытый whitelist AC32, не новые значения Shadow audit_events. BDR08 сохраняет принятое имя auth.factor_change_completed; предлагавшиеся auth.mfa_enabled/auth.mfa_disabled не становятся отдельными значениями writer/decoder v6. Для одного и того же служебного факта старый auth.reconcile_outcome_recorded и новый auth.reconciliation_outcome не дублируются: первый — outcome исходной Auth operation/context, второй — verdict reconciliation-run/item по §4.2. auth.context_execution_closed — closure Auth context/operation; auth.claim_closed — claim consent/admission. Точные ограничения каждой области сохраняются. Архив/очистка истории не включены. Witness и notification не второе бизнес-исполнение. Для отказов до допуска/без trusted actor обязательный полноценный Auth event не выдумывается; безопасная техническая телеметрия отдельно, без секретов. Сама недоступность audit/witness блокирует защищённый commit, не позволяет вернуть успех без evidence.

### 4.1. Полнота audit/evidence по варианту полномочий

Эта D-матрица уточняет AC32/33; обязательные grant/assignment поля AC33 не становятся nullable. Каждый ряд AC33 содержит **один целый достаточный grant**, его assignment/version и реального staff, а не сумму частей прав. На указанное действие выбран ровно один достаточный grant; наличие дополнительных выданных grants не требует их копирования. Полнота включает исторический допуск и текущую проверку перед исполнением, где она предусмотрена; event не даёт будущие права.

| Действие / final event | AC32 actor / обязательный комплект | AC33 cardinality и смысл |
| --- | --- | --- |
| Reset case_create / approve | Human actor_staff_id+его current actor_login_id; case/version. Approve — собственный AC28 и consumed AC09 | По 1 строке reset-review grant; у approve approval_id=его AC28, у case_create NULL |
| Reset execute/completed | Human executor и его current login; exact AC04.execution_case_version_id и **два** выбранных AC28 разных staff | Ровно 3 строки: 1 reset-execute grant исполнителя с approval_id=NULL; 2 reset-review grants соответствующих approving staff с их exact approval_id. Если исполнитель один из approvers, это всё равно отдельные execute и review строки с разными authorized_action; unique AC33 не нарушается |
| Single recovery approve | Human approving_staff+current SL другого владельца; AC28/27/challenge/version | 1 sufficient staff_recovery_approve grant, approval_id своего AC28 |
| Single recovery complete | System controller, typed operation/result/case/version; subject через свой SR/AC27, selected approval_1 через AC04, approval_2 NULL | 1 evidence выбранного approver с его достаточным current recovery grant и exact approval_id. Controller/limited subject не получают выдуманный SL/grant. Re-check approver grant обязателен перед execution |
| Pair recovery approve | System controller, typed operation/case/version/context; конкретный реальный approver определяется AC28/27 и его SR/limited credential, оба proofs обязательны | 0 AC33; вместо grant обязательна целая AC28→AC27→SR/credential цепочка. Недостающая цепочка — повреждение/запрет commit, не «нулевые доказательства» |
| Pair recovery complete | System controller, typed result/operation/case version; exact **2** AC04 approval IDs разных staff, соответствующие 4 participant rows, оба SR/limited keys и security/assignment проверки | 0 AC33. Оба AC28 и их AC27/AC09/AC20/source contexts — обязательные неразрывные evidence. Ordinary grants/полные login не изобретаются |
| Собственный bootstrap / recovery-code self-service | Bootstrap — ограниченный context и approved manifest/source; issue codes — собственный current SL/SC/credential. Credential/recovery_set refs обязательны | 0 административных AC33; собственная authority-цепочка и prior events полны. Это не право на чужой набор |

Final case event имеет ровно **одну** запись AC32 своего final kind на operation; её result/case/version и выбранные execution approvals неизменны. Approval events сохраняются отдельно для каждого фактического approval; они не исчезают после expiry. Предметный transition/result и весь обязательный audit/evidence комплект коммитятся одной T. Для reset 3 строки финального evidence не означают трёх владельцев; два разных approvers остаются достаточными и обязательными. Safe_details={} не заменяет любую цепочку. Проверка current grants не переписывает исторические evidence/AC28.

### 4.2. Закрытый перечень служебных witness-переходов

BDR05: исключение от нового witness-intent ниже относится **только к метаданным самого протокола**, уже привязанным к исходному batch/run. Защищённое предметное изменение всегда имеет зарегистрированный intent, AC34/35 и полный declared closure в той же локальной T. Нельзя дописывать новые targets в уже local_committed batch или объявлять N=0. Никаких новых ролей/прав БД здесь не выдаётся; названия writer — роли будущего механизма с отдельным D03 назначением.

| Переход / writer | Допустимая запись и источник | Witness / граница / запрет |
| --- | --- | --- |
| W01 external intent registration / witness coordinator | AC34.intent_registered по проверенному внешнему intent, точные roots/digest/epoch | Это начало собственного batch, не отдельный бизнес-эффект и не «intent для intent». No local protected mutation до него |
| W02 ack / witness confirmer | Только AC34 external_confirmed_ref/state=confirmed после доказанного ack исходного local_committed batch | Тот же batch; без нового batch для ack. AC35/бизнес-результат/полученные права не меняются |
| W03 uncertain/no-effect evidence / witness reconciler | AC34.uncertain либо no_effect_proven+resolution_evidence_ref только по независимому доказательству; no_effect не для уже доказанного local commit | Тот же исходный batch и существующий run, если выполнялась сверка. Unknown не no-effect; исходный AC05/receipt неизменен |
| W04 inventory/drain/verdict / reconciler | AC41 inventory/drain evidence/phase и новые immutable AC42 verdict для уже созданного fenced run; current run/epoch и все targets проверены | Связь с исходным run, его fence batch/внешним checkpoint. Обновление метаданных протокола не новый intent. Не менять gate open, ownership/factor/login/grants/исходный result в этом шаге. AC42 verdict audit auth.reconciliation_outcome входит в evidence того run |
| W05 external outcome recording / adapter-reconciler | AC39 outcome/evidence и event auth.reconcile_outcome_recorded, только доказанный факт прежнего sealed dispatch, либо ограниченная техническая отметка unknown | Исходный operation/dispatch и его batch; при reconciliation — исходный run. Никакого нового dispatch, factor activation, login или новой epoch. Самостоятельная предметная финализация — W09 |
| W06 Q01/admin-me window close / authorized reader-finalizer | AC16.first_confirmed_at/closed_at/reason и допустимый AC07 cipher erase; auth.cookie_recovery_closed. Late first confirmation сохраняет уже установленный close_reason | Собственный зарегистрированный intent, root cookie_window; closure включает AC16/07 и обязательный audit. Одна T до успешного protected ответа. Это защищённое изменение, **не** исключение ack; idle не touch |
| W07 standalone allowed secret erase / eraser | Только разрешённые поля и marker по HR; AC07 nonce/key/owner/format остаются. Для AC07 — ciphertext/erased_at; AC06/08/09/22/24 только их допустимые verifier поля после закрытия proof-путей | AC07 root secret_material; AC06/09 root context; AC08 root auth_operation; AC24 root auth_operation из AC23.issued_operation_id; consumed AC22 root auth_operation из AC22.consumed_operation_id. Closure перечисляет точные стираемые rows/поля/markers и сохраняемые parents/children. Для **непотреблённого AC22 writer erase не включён**: expiry запрещает использование независимо от digest, нового TTL или скрытого manifest-процесса нет. Собственный batch; исходные audit/events сохраняются, новый generic audit-kind не выдумывается |
| W08 erase внутри закрытия / исходный предметный writer | Те же разрешённые поля/marker, но уже часть W06 либо другого заранее объявленного полного эффекта | В том же batch и **той же T** родительского эффекта; отдельного рекурсивного batch нет. Поздний отдельный erase после commit — W07, не изменение старого closure |
| W09 safe finalizer / ограниченный reconciler | Только завершение доказанного исхода ранее допущенной операции, полный AC04/05/factor/security/audit/notification комплект по action; либо закрытие consent/admission с evidence без эффекта | Предметная T имеет собственный ранее зарегистрированный и ещё не local_committed batch с root auth_operation/claim_admission/context. При новом отдельном local commit нужен свой intent, нельзя расширять закрытый batch. Closed gate допускает только уже принятую reconcile-only финализацию: без нового external effect/full login/cookie/передачи прав. Ссылка на исходный run/dispatch сохраняется. Недоступный witness блокирует commit |
| W10 fence / reopening / trusted control writer | AC01 epoch/state+AC41 и typed auth.environment_fenced/reopened, прежние purpose/inventory/freshness/authorization | Собственный intent/root reconciliation_run с gate/audit/full closure, краткая T X G0. Это защищённое изменение, не W04. Reopen после всех verdict и актуального внешнего основания; старые permits не оживают |

W01–W05 исчерпывают метаданные протокола без рекурсивного intent; W06–W10 не исключения из P04. Ключи/rights/factor/ownership нельзя менять через W02–W05. Существующие typed roots задаются AC35; новый root/неперечисленная служебная операция не разрешаются общим словом «reconcile». Доверенные ссылки batch/run берутся из полного объявленного closure исходного intent и проверенного внешнего журнала, не свободного JSON. Неизвестная связь/неполный inventory закрывают writer. Реальный граф locks/внешних acknowledgements/latency и crash-поведение остаются D03, не доказаны этой таблицей.

### 4.3. Подтверждённое изменение фактора и late reenroll

Семантика P02/U03 сохраняется: факт активации и право выдать login — разные факты. Ни отзыв context, ни поздний ответ, ни ошибка письма не превращают доказанную activation в verification_rejected или разрешение повторить её.

| Исход mfa_confirm | Factor/security после доказанного effect | AC05 / login | Обязательные события и уведомление |
| --- | --- | --- | --- |
| enroll | Точная AC10 active; AC02.current_factor_id эта версия, mfa_requirement=required; завершена только принадлежащая операции transition; прежние login сохранены | mfa_enabled, result_factor_id; full refs NULL | 1 auth.factor_change_completed; 1 AC36 purpose=mfa_enabled |
| disable | Исторический AC10 disabled, current_factor_id NULL, requirement=none; прежние login отозваны по принятому правилу | mfa_disabled, result_factor_id исторической версии; новых full refs нет | 1 auth.factor_change_completed; 1 AC36 purpose=mfa_disabled |
| reenroll, полный login разрешён | Подтверждённая новая AC10 active/current, requirement=required, завершается собственная enrollment transition. Прежний reset не отменяется | mfa_reenrolled, result_factor_id и FULL AC05/38/16/07/Shadow login | 1 auth.factor_change_completed **и** 1 auth.login_completed; 1 AC36 purpose=mfa_enabled |
| reenroll, доказанная activation, login окончательно не выдан | Та же подтверждённая activation/current factor/requirement=required, если исходная версия transition всё ещё принадлежит этой операции. Текущий независимый block/revoke сохраняется; контекст не оживает | auth_completion_not_issued, result_factor_id; все FULL refs NULL, нет window/cookie | 1 auth.factor_change_completed **и** 1 auth.login_not_issued; 1 AC36 purpose=mfa_enabled |

Каждый AC36 имеет source_result_id именно этого AC05 и recipient_identity_id исходной закреплённой user identity, recipient_staff_id=NULL; адрес извлекается только защищённым permitted delivery path. Если identity недоступна/отозвана, job не подменяет получателя и не разрешает доставку; исходный security result сохраняется, доставка регулируется собственным состоянием/доказательствами. Purpose=mfa_enabled означает подтверждённую активацию, а не успешный login, поэтому применим к late reenroll. Новое purpose mfa_reenrolled не требуется.

Factor/security/собственный transition, AC11 steps/AC12 однократный учёт, AC04/05, указанные AC32 и AC36, а при успехе полный login-комплект — один локальный finalizer с AC34/35; внешняя activation не объявляется атомарной с БД. Поле completedAt у mfa_reenrolled — время полного login; AC10.activated_at хранит фактическую activation отдельно. У late result completedAt NULL/decidedAt по U03, activated_at не стирается. Replay не создаёт второй event/job/activation.

При security_revoked/current block нельзя переводить AC02.blocked в active ради фиксации истории. Разрешено снять только **собственную** завершённую transition при совпадении её operation/version; независимый более новый transition/current factor не перезаписывается. При конфликте/неустановленном provider состоянии — сохранение evidence и закрытая сверка, не ложный final success/отказ. Завершение допустимо только после разрешения этого конфликта по принятому протоколу; таблица не вводит новую политику «последний ответ побеждает».

## 5. Соответствие и единая вычитка

| Проверяемое место | Документальная точность / будущая проверка |
| --- | --- |
| Все маршруты | R01–R50,4 staff-logout routes; source proof/body/query/success/error/GET/unknown/cookie/replay API §§1–8; отсутствие отдельного GET для create допустимо только с определённым replay POST |
| Все результаты | Whitelist §1, поля API §4; user/logout/claim/NReply раздельны; payload/types/NULL обратны scoped FK |
| Все context/purpose/stage | §2 и matrix AC03; не всякая комбинация enum разрешена; текущие expiry/revoke отдельно от исторической stage |
| Case/approvals |2 reset rows/2 single rows/4 pair rows;1 либо2 execution approvals; старое approval не обновляется, current version/TTL/access проверяются перед эффектом |
| Секреты | Temporary reveal vs immutable history, source proof reissuance profile, verifier vs cipher; opaque public refs не bearer, no-store/Origin/CSRF обязательны |
| Новые технические уточнения | NRef namespace до context; current-case GET; pair approverContextId и атомарное связывание; отдельный recovery grant; derived proof profile; late-outcome DTO/HTTP. Это перечисленный объём D02 для одной пакетной вычитки, не новые финансовые правила |

BDR01–BDR08 получили адресную редакцию для повторной вычитки; замечания ещё не объявлены закрытыми БД. D02 остаётся документальным проектом, не прошедшей реализацией. Принятые U01–U03 отражены в физической карте отдельно; принятие этой новой точной редакции ещё не выдумывается. D03/BR08 остаётся будущей проверкой возможности реализации на реальных компонентах. Ни один новый API/кодек/grant/ключ/SQL этой работой не создан. После вычитки/принятия — адресное издание v6 и D04, не самостоятельное начало кода.
