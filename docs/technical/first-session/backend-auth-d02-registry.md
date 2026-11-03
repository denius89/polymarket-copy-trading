# D02: закрытая дельта реестра first-session-registry-v6

02.11.2026 · При финальной интеграции 03.11.2026 учтены main3c832f0/PR №210, AS01–AS28 и HR/HE; адресные дельты к 78 таблицам добавлены в AS §11 и карту истории §10. **Проект полного издания v6 для единой вычитки**, связан с [точным D02 API](backend-auth-d02-contracts.md). Текущий опубликованный принятый реестр пока v5. U01–U03/P01–P05 приняты отдельно; выбор новых DTO/словари этой редакции не подменяется фактом создания файла. После пакетного принятия v6 запись §15 [общего реестра](backend-code-registry.md) становится указателем текущего издания без переписывания v1–v5.

Все прежние Shadow команды/причины/права/audit/форматы сохраняются. Новых top-level reasonCode не вводится. AUTH_COOKIE_RECOVERY_NOT_APPLICABLE расширяет применимость только на явно названные Auth namespaces; CATALOG_CHANGED остаётся только Q02-list. Неизвестное значение клиенту400, обязательная неизвестная сохранённая форма503 RECORD_UNAVAILABLE. Словари перечислены полностью для новых групп; строки не разрешают декартово произведение всех action/result.

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

GET-whitelist: M — email_request/email_resend/email_verify/factor_prepare/factor_secret/challenge_renew/mfa_confirm; SA — login_options/staff_login; B — bootstrap_create/registration_options/registration_verify; K — recovery_create/recovery_registration_options/recovery_registration_verify/recovery_options/recovery_approve/recovery_complete; P — pair_create/recovery_options/recovery_approve/recovery_complete; Z — recovery_code_context_create/recovery_code_options/recovery_code_issue; GP — guest_refresh. Case reset и MR описаны в API. Action не из своего списка400, а не поиск по чужому namespace. Для K/P operations case-scope определяется сохранённой связью результата/версии, не выбором клиента; смена current version не скрывает свой прежний результат.

### 1.1. Обязательные typed refs результата

Full completion → result_login_id+completion_context_id+completed_at; source context/realm/subject/login совпадают, AC38/16/07 полны. Context-create → result_context_id и соответствующий consumed handle/code/source login. Options/renew → result_challenge_id, для renew ещё replaced_challenge_id. Prepared/enabled/reenrolled → result_factor_id; disabled/reset → исторический factor той версии, не current pointer. Reset/case/recovery → result_case_id/result_case_version_id, credential registration → result_credential_id, issue → result_recovery_set_id. Logout → target_login_id, никогда result_login_id. Остальные variant refs NULL, если точная строка не требует их. Email accept → result_challenge; email verify new TOTP stage → result_challenge; factor_prepare → factor и challenge вместе. У auth_completion_not_issued full-completion refs все NULL, доказанный внешний effect требует AC39, локальный WebAuthn требует AC09/20 и outcome адаптера без AC39; при MFA reenroll result_factor_id сохраняет подтверждённую активированную версию, не выдачу login.

AC05 JSON refs и typed refs равны; read-only projection не сочиняет ID из current row. DecidedAt/ResolvedAt для позднего результата совпадают, completedAt null. У других result временные поля следуют факту действия, не текущему GET. AC04 historical result pointer immutable после resolved; повтор не создаёт ещё AC05.

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
| AC01 state | open,closed; closure_reason=claim_unknown,environment_restore,security_incident,initialization; null только open |
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

AC07 cipher_format=short-secret-xchacha20poly1305-v1: nonce24, tag16 внутри ciphertext, key32 вне БД; nonce сохраняется после erasure, AAD env/id/purpose/typed owner/format/deadline. AC08 comparison_format=auth-sensitive-compare-v1. Вход HMAC-SHA256: ASCII domain и00; затем UTF-8 поля environment,namespace,canonical scope ID,action,canonical client operation ID,purpose и raw sensitive bytes — каждый с uint32BE length prefix. UUID в этом профиле canonical ASCII, не смешивается с16byte UUID guest-draft-proof-v1. Для WebAuthn сравнивается canonical JCS объекта assertion/credential (raw поля base64url сохраняют точный принятый смысл), для code/token/email — исходная строка после строгого JSON parse без trim/нормализации. Исходные raw email и нормализованный адрес сравнения разных целей не подменяют друг друга. AC04 nonsecret canonical digest — SHA256 JCS только несекретных полей, все секретные именованные части отражены AC08; одинаковый публичный digest недостаточен.

Нормативные байтовые test-vectors/библиотечная совместимость/ключевые процедуры ещё D03. Документ не обещает криптографический proof корректности реализации. Расширение closed format должно иметь новое явное издание/decoder, не silent fallback.

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
| auth.mfa_enabled,auth.mfa_disabled | operation/result/context, source factor через result; с effect/security/отзывами |
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

Это закрытый whitelist AC32, не новые значения Shadow audit_events. Архив/очистка истории не включены. Witness и notification не второе бизнес-исполнение. Для отказов до допуска/без trusted actor обязательный полноценный Auth event не выдумывается; безопасная техническая телеметрия отдельно, без секретов. Сама недоступность audit/witness блокирует защищённый commit, не позволяет вернуть успех без evidence.

## 5. Соответствие и единая вычитка

| Проверяемое место | Документальная точность / будущая проверка |
| --- | --- |
| Все маршруты | R01–R50,4 staff-logout routes; source proof/body/query/success/error/GET/unknown/cookie/replay API §§1–8; отсутствие отдельного GET для create допустимо только с определённым replay POST |
| Все результаты | Whitelist §1, поля API §4; user/logout/claim/NReply раздельны; payload/types/NULL обратны scoped FK |
| Все context/purpose/stage | §2 и matrix AC03; не всякая комбинация enum разрешена; текущие expiry/revoke отдельно от исторической stage |
| Case/approvals |2 reset rows/2 single rows/4 pair rows;1 либо2 execution approvals; старое approval не обновляется, current version/TTL/access проверяются перед эффектом |
| Секреты | Temporary reveal vs immutable history, source proof reissuance profile, verifier vs cipher; opaque public refs не bearer, no-store/Origin/CSRF обязательны |
| Новые технические уточнения | NRef namespace до context; current-case GET; pair approverContextId и атомарное связывание; отдельный recovery grant; derived proof profile; late-outcome DTO/HTTP. Это перечисленный объём D02 для одной пакетной вычитки, не новые финансовые правила |

D02 готов как документальный проект полной дельты, не как прошедшая реализация. Принятые U01–U03 отражены в физической карте отдельно; принятие этой новой точной редакции ещё не выдумывается. D03/BR08 остаётся будущей проверкой возможности реализации на реальных компонентах. Ни один новый API/кодек/grant/ключ/SQL этой работой не создан. После вычитки/принятия — адресное издание v6 и D04, не самостоятельное начало кода.
