# D02: полная документальная дельта API Auth

02.11.2026 · При финальной интеграции 03.11.2026 учтены main3c832f0/PR №210, AS01–AS28 и HR/HE; адресные дельты к 78 таблицам добавлены в AS §11 и карту истории §10. Baseline main2165b86 (PR №207). Основание: принятие P01–P05/PR №205, ответ D01-U/PR №206 и ответ владельца «давай» на следующий шаг согласования U01–U03. **U01–U03 приняты; D02 ниже — подготовленная точная редакция для единой вычитки, не реализация.** Она конкретизирует новые маршруты/результаты и прежний review-пакет; не выдаёт проектные DTO за уже опубликованное рабочее API. Реестр v5 остаётся действующим до пакетного принятия D02/v6; [полный проект v6](backend-auth-d02-registry.md) приложен.

Принятая физическая основа — [42 Auth +36 Shadow](auth-storage-unified.md). Первоначальный [API review](backend-review-api-spec.md) сохраняется как источник требований; при расхождении в точности новых форм применяется этот D02-проект. Формы C04/C05/C06/Q01–Q06, финансовые правила, CommandReceipt/Q05, claim и user logout не расширяются неявно. Владелец 1 и владелец 2 равноправны. Код, SQL, миграции, установка, база и предметные испытания не выполнялись.

03.11.2026 · Адресная редакция по [BDR01–BDR08](database-auth-d02-review-2026-11-03.md): [ответ и границы решений](backend-auth-d02-bdr-response.md). Основа a967c50/PR №211; U01–U03 и 78 таблиц сохранены, D02/v6 остаётся проектом.

## 1. Типы, оболочки и проверка

U — канонический UUIDv4; V — десятичная строка положительного signed bigint без ведущих нулей; T — UTC Z с ровно3 десятичными знаками миллисекунд; B — JSON boolean. Все поля обязательны, только явно указанные `|null` допускают null. Перечень полей закрыт на каждом уровне; массивы без лишних/повторных идентификаторов, порядок задан формой. Неподдерживаемое значение не ближайший известный enum.

Каждый POST body включает requestSchemaVersion=v1; таблицы ниже перечисляют остальные поля. POST без query. GET без тела, query ровно requestSchemaVersion=v1 и action там, где это GET операции. Дубли/неизвестные ключи/ошибки UTF-8/media/размеров/Origin разбираются строго по [принятому Auth §2](backend-auth-contracts-addendum.md). Лимит8192/depth8; только registration verify POST65536 по U02. C04/C05/C06/claim сохраняют прежние65536. Wire-limit не storage-limit: AC04 nonsecret16384, AC05 result65536, AC32 audit16384. Никакого truncation.

Обязательный порядок: transport parsing → Origin/CSRF → proof → право цели → transport quota → integrity scoped operation → совпадение намерения → сохранённый результат → условия нового исполнения. Повреждение503 до payload-conflict. Все источники current прав проверяются заново; ни result, ни approval не bearer. Повтор HTTP расходует transport quota, внутренний retry нет. Все ответы no-store. Секреты не URL/лог/ordinary history. Ошибка без результата ровно reasonCode,reasonDetails,nextAction,nextActionParams; reasonDetails={code:reasonCode,params:{}}. Сохранённый rejected result не вставляется в этот error-конверт.

**Новая общая оболочка NReply:** operationRef,status,result,resolvedAt,observedAt,nextAction,nextActionParams. Status=resolved/unresolved; resolved требует result и T, unresolved оба null. GET200/202 соответственно, navigation всегда null/{}. Прямое неизвестное исполнение503, не202. Сохранённая email dispatch acceptance202 — resolved. Direct ответы ниже могут быть специальными закрытыми проекциями, исторический GET всегда secret-free NReply. `observedAt` текущее, `resolvedAt` неизменяемое.

**NRef** для новых management/staff/guest операций ровно namespace,scopeId:U,operationId:U,action. Namespace=context/bootstrap_handle/recovery_handle/security_case/reset_request/login; scopeId — непрозрачный ID этого исходного основания, не секрет и не provider ref. Это исправляет ранний универсальный contextId, который не мог выразить операцию до создания контекста. Raw bootstrapHandle никогда не scopeId. Отображение namespace→storage scope: context→AC03.id, bootstrap_handle→AC22.id, recovery_handle→AC23.id (найденный по recovery_handle), security_case→AC25.id, reset_request→AC30.id, login→Shadow auth_sessions.id. Все ссылки scoped environment; публичный NRef может содержать этот opaque ID только после разрешённого чтения. Исходный namespace не меняется после создания context/case. GET созданного контекста может найти его create-result через AC05.result_context_id, но не переназначает ключ операции.

Старые UReply/URef из Auth §7 (authContextId/authOperationId/commandType), logout Reply §9 и claim202 остаются отдельными формами; они не NRef. Форматы wire v1/registry-v6/storage formats/version resource различаются. Нельзя по совпадению ID смешивать namespaces.

Для специальных direct-ответов `E(x)` означает ровно x,observedAt,nextAction=null,nextActionParams={}. `R(x)` означает ровно перечисленные в x поля плюс observedAt, без автоматически добавленной navigation. Все result kinds со своими полями перечислены в §4, а не допускают произвольную JSON.

## 2. Источники полномочий и сроки

| Proof | Точный допуск |
| --- | --- |
| UA | Действующий user Auth-context cookie/ID; для restricted ветвей дополнительно доказанный email/текущая identity и server MFA requirement |
| UL | Выбранный X-Shadow-Login-Id и действующая user full cookie, актуальные identity/security/сроки |
| MC | Cookie __Host-shadow-mfactx-<contextId>, свой context/назначение; для enroll/disable текущий выбранный login, для reenroll исходный email-proven restricted UA. Исключение чтения: после собственного успешного disable живой MC proof до expiry читает только этот исход, несмотря на отзыв выбранного UL |
| MR | Cookie __Host-shadow-mfaresult-<id>, связь source mfa и authorizing restricted UA одного user; только outcome read |
| SA | Cookie __Host-shadow-staffctx-<id>, ограниченный staff_auth; не полный доступ |
| SL | Выбранный staff full login, current slot/identity/security и необходимые current grants/assignment; user cookie не подходит |
| RG | Cookie __Host-shadow-staffreg-<id> для bootstrap либо исходный staff recovery cookie для registration в recovery; limited credential не SL |
| SR | Cookie __Host-shadow-staffrecovery-<id>, свой staff/context/case; для pair оба SR, для approval именно ключ соответствующего участника |
| SC | Cookie __Host-shadow-staffcodes-<id> и исходный SL для выдачи/чтения набора; не offline recovery code |
| GP | Cookie __Host-shadow-guestctx-<id> и X-Shadow-Guest-Context-Id при Q02/C04; selected UL имеет приоритет без fallback |

Новые proof cookies Secure/HttpOnly/SameSite=Strict/Path=/, без Domain; fixed Expires=context.expiresAt. Исключения: прежняя UA session-cookie без browser expiry; GP Max-Age=2592000, server expiry отдельно. Full user/staff cookie Expires=исходный absolute expiresAt, без продления от refresh/replay. Серверные absolute/idle30d/7d user и8h/30min staff сохраняются. Context expiry: UA30min; MC10min (reenroll≤source expiry); MR10min≤authorizing UA; SA/RG/SC10min; SR24h; pair=min двух SR; logout15min; claim10min. Email challenge10min; TOTP/WebAuthn challenge5min, все ограничены expiry исходного контекста и case version, когда применимо. Now≥deadline закрывает новый допуск; expiry не откат executing.

Новые management/staff подготовки/чтения5s одна попытка; external verify/effect10s без неизвестного auto-retry. Принятые старые бюджеты не меняются. HTTP preparation/options/reveal3/60s, confirm/approve/execute10/60s, GET30/60s по environment+principal+purpose; до доказанной личности20 preparations/15min source network и1000/15min environment. IPv4/32, IPv6/64 только от trusted ingress. Guest refresh3/60s/context. До8 живых contexts каждого purpose/principal, без eviction pending. Code-family/TOTP/recovery-code counters независимы и строже. C07 сохраняет свой принятый профиль без выдуманного нового numeric limit.

## 3. Полный каталог новых маршрутов

Сокращения путей используются только в таблицах: M=/api/auth/mfa/contexts; S=/api/admin/auth/contexts; B=/api/admin/auth/bootstrap/contexts; K=/api/admin/auth/recovery/contexts; P=/api/admin/auth/recovery/pairs; Z=/api/admin/auth/recovery-code-contexts; X=/api/admin/auth/mfa-reset/cases. `{id}` всегда U, `{op}` клиентский U. R01–R50 — метки документов, не runtime-коды. Result names раскрыты в §4. Каждый proof в таблице дополнен current access; все перечисленные routes требуют Origin-защиту POST.

| ID / method path | Body/query сверх общей версии; proof | Успешная форма / исходный scope |
| --- | --- | --- |
| R01 POST M | purpose=enroll/disable; UL. Иной вариант purpose=reenroll,recoveryAuthContextId; UA |201 E(mfaContext); без operationId, новый ограниченный контекст |
| R02 GET M/{id} | MC |200 E(mfaContext) |
| R03 POST M/{id}/email/request | operationId,locale=ru/en; MC |202 NReply email_dispatch_accepted; context/email_request |
| R04 POST M/{id}/email/resend | operationId,expectedChallengeId,locale; MC |202 NReply email_dispatch_accepted; context/email_resend |
| R05 POST M/{id}/email/verify | operationId,challengeId,code:6 ASCII digits; MC |200 NReply mfa_stage_ready; context/email_verify |
| R06 POST M/{id}/factor | operationId; MC enroll/reenroll |200 NReply mfa_factor_prepared; context/factor_prepare |
| R07 POST M/{id}/factor/secret | operationId,factorVersion:V; MC |200 R(contextId,factorVersion,totpUri,secretExpiresAt); context/factor_secret; history mfa_secret_accessed |
| R08 POST M/{id}/challenge-renew | operationId,expectedChallengeId; MC |200 NReply mfa_challenge_renewed; context/challenge_renew |
| R09 POST M/{id}/confirm | operationId,challengeId,code; MC |200 NReply mfa_enabled/mfa_disabled/mfa_reenrolled; context/mfa_confirm |
| R10 GET M/{id}/operations/{op} | action из MFA списка; MC либо разрешённый current UL того же user |200/202 NReply, без секрета/cookie; lookup исходного scope |
| R11 POST M/{id}/operations/{op}/login-cookie | action=mfa_confirm; исходный MC |200 E(login); не новая operation; только result mfa_reenrolled |
| R12 POST /api/auth/mfa/result-contexts | sourceContextId,authContextId; доказанный restricted UA того же user |201 R(resultContextId,sourceContextId,createdAt,expiresAt); MR cookie |
| R13 GET /api/auth/mfa/result-contexts/{id}/operations/{op} | action=mfa_confirm; MR |200/202 исходный NReply; только read |
| R14 POST /api/auth/mfa/reset-requests | authContextId,operationId; UA с доказанным email и утраченным требуемым TOTP |201/точный повтор200 E(resetRequestId,createdAt); context/reset_request |
| R15 GET /api/auth/mfa/reset-requests/{id} | исходный UA |200 R(resetRequestId,status) |
| R16 POST X | operationId,resetRequestId,reasonCode=lost_authenticator,verificationEvidenceId; SL reset-review |201 E(resetCase); точный повтор200 NReply mfa_reset_case_created; reset_request/case_create |
| R17 GET X/{id} | SL reset-review |200 E(resetCase); текущее состояние/approvedBy не immutable result |
| R18 POST X/{id}/approval-options | operationId,decisionVersion; SL reset-review, участник |200 NReply mfa_reset_approval_options; security_case/approval_options |
| R19 POST X/{id}/approve | operationId,decisionVersion,challengeId,assertion; тот же SL |200 NReply mfa_reset_approved; security_case/approve |
| R20 POST X/{id}/execute | operationId,decisionVersion; SL reset-execute |200 NReply mfa_reset_completed; security_case/reset_execute |
| R21 GET X/{id}/operations/{op} | action=case_create/approval_options/approve/reset_execute; SL нужного права |200/202 NReply; case_create ищется через его source reset_request, scope не меняется |
| R22 POST S | только общая версия |201 E(staffContext), SA cookie; не ищет staff по email |
| R23 GET S/{id} | SA |200 E(staffContext) |
| R24 POST S/{id}/options | operationId; SA |200 NReply staff_authentication_options; context/login_options |
| R25 POST S/{id}/verify | operationId,challengeId,assertion; SA |200 E(completion); history staff_login_completed; context/staff_login |
| R26 GET S/{id}/operations/{op} | action=login_options/staff_login; SA |200/202 NReply |
| R27 POST S/{id}/operations/{op}/login-cookie | action=staff_login; исходный SA |200 E(completion), исходная cookie; текущий staff slot обязателен |
| R28 GET /api/admin/me | SL |200 E(authenticated=true,staff={staffId}); проверенный X-Shadow-Login-Id; первый успех закрывает окно без idle touch |
| R29 POST B | bootstrapHandle:canonical base64url32 bytes (43 символа),operationId; доверенный незакрытый manifest/handle |201/повтор200 E(registrationContext); bootstrap_handle/bootstrap_create, RG cookie |
| R30 POST B/{id}/options | operationId; RG |200 NReply staff_registration_options; context/registration_options |
| R31 POST B/{id}/verify | operationId,challengeId,credential; RG; body65536 |200 NReply staff_credential_registered; context/registration_verify |
| R32 GET B/{id}/operations/{op} | action=bootstrap_create/registration_options/registration_verify; RG |200/202 NReply; create lookup через result_context |
| R33 POST K | operationId,recoveryHandle,recoveryCode; исходный код |201/повтор200 R(recoveryContext); recovery_handle/recovery_create, SR cookie |
| R34 GET K/{id} | SR либо действующий SL назначенного второго владельца |200 R(recoveryContext); минимальная собственная процедура, без кодов |
| R35 POST K/{id}/credentials/options | operationId; SR |200 NReply staff_registration_options; context/recovery_registration_options |
| R36 POST K/{id}/credentials/verify | operationId,challengeId,credential; SR; body65536 |200 NReply staff_credential_registered; context/recovery_registration_verify; credential limited |
| R37 POST P | operationId,firstContextId,secondContextId; оба SR разных staff |201/повтор200 R(pair); context/pair_create, scope=min(context IDs) по байтам, порядок payload всё равно сравнивается |
| R38 GET P/{id} | оба SR |200 R(pair) |
| R39 POST K/{id}/approval-options либо P/{id}/approval-options | operationId,requestVersion; single SL второго владельца; pair оба SR + выбранный approverContextId только для pair |200 NReply staff_recovery_approval_options; security_case/recovery_options |
| R40 POST K/{id}/approve либо P/{id}/approve | operationId,requestVersion,challengeId,assertion; тот же proof; pair дополнительно approverContextId |200 NReply staff_recovery_approved; security_case/recovery_approve |
| R41 POST K/{id}/complete либо P/{id}/complete | operationId,requestVersion; single SR subject; pair оба SR |200 NReply staff_recovery_completed; security_case/recovery_complete |
| R42 GET K/{id}/operations/{op} либо P/{id}/operations/{op} | action из whitelist recovery соответствующего пути; SR/оба SR; SL второго владельца только его options/approve |200/202 NReply; исходный namespace определяется закрытым resolver §6.1, включая unresolved; K не следует current pair pointer |
| R43 POST Z | operationId; SL |201/повтор200 R(contextId,createdAt,expiresAt); login/recovery_code_context_create; SC cookie |
| R44 POST Z/{id}/options | operationId; SC |200 NReply recovery_code_options; context/recovery_code_options |
| R45 POST Z/{id}/issue | operationId,challengeId,assertion; SC |200 R(contextId,recoveryHandle,setVersion,codes,issuedAt,secretExpiresAt); context/recovery_code_issue; history без codes |
| R46 GET Z/{id}/operations/{op} | action=recovery_code_context_create/recovery_code_options/recovery_code_issue; SC |200/202 NReply; create lookup source login |
| R47 POST /api/guest/contexts; GET /api/guest/contexts/{id} | POST только общая версия; GET GP |201/200 E(guestContext); create GP cookie, GET подтверждает доступ |
| R48 POST /api/guest/contexts/{id}/refresh; GET /api/guest/contexts/{id}/operations/{op} | POST operationId; GET action=guest_refresh; GP |200 NReply guest_context_refreshed; GET200/202, context/guest_refresh |
| R49 POST /api/auth/email-link/verify | authContextId,authOperationId,challengeId,token:canonical base64url32 bytes; UA |Прямые формы C02; отдельный AUTH_EMAIL_LINK_VERIFY, не Shadow command type |
| R50 POST /api/auth/activity-contexts | routeCode,targetId:U|null; выбранный UL/SL |201 R(activityContextId,expiresAt); без operationId/исторического GET |

R01/R12/R22/R47-create/R50 без operationId не дают exactly-once подготовки. При потере ответа создаётся новый контекст только по явному действию в пределах лимитов; это не повтор claim/C04/Auth effect. R14/R16/R29/R33/R37/R43 имеют устойчивый namespace до нового ресурса, lost response не разрешает новое потребление handle/code.

Staff logout — четыре точных маршрута `/api/admin/auth/logout-contexts`, `/api/admin/auth/logout`, `/api/admin/auth/logout-contexts/{logoutContextId}/operations/{authOperationId}`, `/api/admin/auth/logout-contexts/continue`. Методы/поля/ответы/status/лимиты строго как [user logout §9](backend-auth-contracts-addendum.md), с realm=staff, staff proof и authorizationMode=original_login/current_staff. Cookie __Host-shadow-stafflogoutctx-<id>. Новый staff login доказывает право продолжить выход из прежнего, но не становится целью. Это отдельный staff namespace C07, не NReply и не CommandReceipt.

## 4. Точные объекты и result-варианты

MfaContext ровно contextId,purpose,stage,createdAt,expiresAt,emailChallengeId:U|null,emailCodeIssuedAt:T|null,emailCodeExpiresAt:T|null,totpChallengeId:U|null,totpChallengeIssuedAt:T|null,totpChallengeExpiresAt:T|null,factorVersion:V|null. Email triple задан только email_verification; TOTP triple только totp_verification; expired текущий challenge сохраняет исторические времена. FactorVersion задан после prepare или для disable с закреплённым active factor; completed сохраняет соответствующую историческую версию. Unknown обязательного источника503, не null.

StaffContext ровно contextId,stage,createdAt,expiresAt,challengeId:U|null,challengeExpiresAt:T|null; оба challenge-поля заданы только stage=challenge. RegistrationContext ровно contextId,purpose=bootstrap,createdAt,expiresAt. RecoveryContext ровно contextId,subjectStaffId,requestVersion,status,createdAt,expiresAt; статус limited/awaiting_approvals/committing/completed/expired — текущая проекция, не результат операции. Pair ровно pairId,requestVersion,firstContextId,secondContextId,createdAt,expiresAt; порядок first/second сохраняется от создания, не переименовывает principal. GuestContext ровно guestContextId,createdAt,expiresAt,accessConfirmed:B; false при create, true после доказанного GET. Context/result-create replay возвращает исходные createdAt/expiry, current GET — действующее состояние отдельно.

ResetCase ровно caseId,userId,factorVersion,decisionVersion,verificationEvidenceId,requiredApprovals=2,approvedBy:[U],status,createdAt,expiresAt,completedAt:T|null. approvedBy — уникальные staff IDs свежих подходящих approvals текущей версии, отсортированы по UUID; это проекция, не доказательство исполнения. Status collecting/authorized/executing/completed/rejected; completedAt только completed. На executing authoritative tuple — сохранённые AC04 approval IDs, не меняющийся approvedBy. Истечение сохраняет историю, закрывает новый execute; отдельно status=expired не добавляется к AC25.

StaffCompletion ровно contextId,operationId,loginId,realm=staff,completedAt. MfaLogin ровно loginId,realm=user,completedAt,cookieRecoveryDeadlineAt. Последний deadline=min(completedAt+5min,исходный context expiry), неизменный. UserCompletion прежний authContextId/authOperationId/loginId/realm/completedAt не переименован.

Все строки таблицы — **ровно kind и перечисленные дополнительные поля**. U/V/T по §1; label «Options» раскрывается §5. Поля, отсутствующие в строке, запрещены, включая secrets/navigation/observedAt.

| kind | Дополнительные поля immutable result |
| --- | --- |
| email_dispatch_accepted | acceptedAt:T,challengeId:U,resendNotBeforeAt:T |
| verification_rejected | reasonCode=AUTH_VERIFICATION_FAILED |
| mfa_stage_ready | stage=factor_prepare/totp_verification,challengeId:U|null,challengeIssuedAt:T|null,challengeExpiresAt:T|null; все null только factor_prepare |
| mfa_factor_prepared | factorVersion:V,challengeId:U,challengeIssuedAt:T,challengeExpiresAt:T |
| mfa_secret_accessed | factorVersion:V,accessedAt:T |
| mfa_challenge_renewed | replacedChallengeId:U,challengeId:U,challengeIssuedAt:T,challengeExpiresAt:T |
| mfa_enabled | factorVersion:V,completedAt:T |
| mfa_disabled | previousFactorVersion:V,completedAt:T |
| mfa_reenrolled | factorVersion:V,completedAt:T,login:MfaLogin; времена completedAt совпадают |
| mfa_reset_requested | resetRequestId:U,createdAt:T |
| mfa_reset_case_created | caseId:U,decisionVersion:V,createdAt:T; current ResetCase берётся GET отдельно |
| mfa_reset_approval_options | caseId:U,decisionVersion:V,challengeId:U,challengeExpiresAt:T,publicKey:AuthenticationOptions |
| mfa_reset_approved | caseId:U,decisionVersion:V,approverStaffId:U,approvedAt:T |
| mfa_reset_completed | caseId:U,userId:U,previousFactorVersion:V,completedAt:T |
| staff_authentication_options | challengeId:U,challengeExpiresAt:T,publicKey:AuthenticationOptions |
| staff_login_completed | completion:StaffCompletion |
| staff_registration_context_created | contextId:U,purpose=bootstrap,createdAt:T,expiresAt:T |
| staff_registration_options | challengeId:U,challengeExpiresAt:T,publicKey:RegistrationOptions |
| staff_credential_registered | credentialRef:U,completedAt:T |
| staff_recovery_context_created | contextId:U,subjectStaffId:U,requestVersion:V,createdAt:T,expiresAt:T; direct RecoveryContext status limited |
| staff_recovery_pair_created | pairId:U,requestVersion:V,firstContextId:U,secondContextId:U,createdAt:T,expiresAt:T |
| staff_recovery_approval_options | challengeId:U,challengeExpiresAt:T,publicKey:AuthenticationOptions |
| staff_recovery_approved | recoveryId:U,requestVersion:V,approverStaffId:U,approvedAt:T |
| staff_recovery_completed | recoveryId:U,requestVersion:V,completedAt:T |
| recovery_code_context_created | contextId:U,createdAt:T,expiresAt:T |
| recovery_code_options | challengeId:U,challengeExpiresAt:T,publicKey:AuthenticationOptions |
| recovery_codes_issued | recoveryHandle:U,setVersion:V,issuedAt:T,secretExpiresAt:T; нет codes |
| guest_context_refreshed | guestContextId:U,expiresAt:T |
| auth_completion_not_issued | completionAttemptRef,completedAt:null,login:null,cause,decidedAt:T; точная матрица §8 |

При direct full completion выдаётся исходная full cookie; replay может вернуть тот же несекретный результат без Set-Cookie, если recovery-window уже закрыто. Явный login-cookie POST вне окна409; current access/revoke всегда проверяются раньше.

Direct201→replay200 меняет только транспортный статус/текущее observedAt; не создаёт новый context/case/version. Для R16 current ResetCase возвращается direct только после первоначального создания; exact replay возвращает NReply mfa_reset_case_created, чтобы не назвать изменившийся case исходным неизменяемым результатом. Клиент после replay читает R17. Эта явная развилка предпочтительнее скрытого перемешивания current state и saved outcome.

## 5. WebAuthn, secret и создание до контекста

AuthenticationOptions: challenge=canonical base64url32 случайных bytes,rpId,timeout:целое1…300000 ms,userVerification=required,allowCredentials:array. Login discovery даёт[]; fresh approval/issue — ровно разрешённые current credentials выбранного staff, каждый объект type=public-key,id:canonical base64url. Pair допускает только свой новый limited credential. Исторические options остаются прежними после истечения; их replay не делает challenge живым.

RegistrationOptions: challenge32 bytes; rp={id,name=Shadow}; user={id:base64url1…64 bytes,name:base64url тех же opaque user.id bytes,displayName:владелец 1/владелец 2}; pubKeyCredParams=[{type:public-key,alg:-7},{type:public-key,alg:-257}]; timeout=300000; attestation=none; authenticatorSelection={residentKey:required,userVerification:required}; excludeCredentials из credentials этого staff, каждый type/id. RP/origin/handle неизменны по trusted descriptor/AC02, не от браузера. Личные email в user.name/displayName не выдаются.

Assertion ровно id,rawId,type=public-key,response={clientDataJSON,authenticatorData,signature,userHandle:base64url|null},clientExtensionResults={}. Id=rawId canonical base64url, decoded credential ID1…1023 bytes. Decoded clientDataJSON≤4096,authenticatorData≤2048,signature≤1024,userHandle1…64 если nonnull; общий8192 сильнее суммы. ClientData type=webauthn.get, точные challenge/origin/RP hash/UV/UP, crossOrigin absent/false, topOrigin absent. Если userHandle null, subject берётся только из проверенного принадлежащего credential; nonnull обязан совпасть. Counter/backup flags проверяет адаптер, synced/zero counter не выключает одноразовый server challenge.

Credential регистрации ровно id,rawId,type=public-key,response={clientDataJSON,attestationObject},clientExtensionResults={}. Decoded clientDataJSON≤4096/attestationObject≤32768, body65536, type=webauthn.create; остальные проверки по trusted profile. Неизвестные расширения запрещены. COSE ES256/RS256 — выбранный документальный профиль, поддержка библиотек/устройств ещё D03, не испытана здесь.

TotpUri — только серверный otpauth из подготовленного factor, QR строится локально. SecretExpiresAt не позже MC expiry/активации/отзыва. Recovery codes ровно10 строк32 символа A–Z/2–7,160 random bits; API не принимает UI-дефисы. Новый набор отзывает старый атомарно при issuance, не при UI acknowledgement. Reveal deadline=min(issuedAt+5min,SC expiry). GET никогда не выдаёт seed/code/cookie; exact POST replay выдаёт тот же временный секрет лишь при живом разрешённом окне, иначе409 STATE_CONFLICT.

**Потеря ответа до context:** R29/R33 повторяются только с тем же operationId и исходным handle/code; replay проверяет право восстановления того же result, а не повторно расходует одноразовый proof. Применимость первоначального code не восстанавливается для другой операции. Unknown сначала разрешается по этому исходному namespace, публичный ID не proof. R43 использует тот же current SL и operationId. При missing исходного proof новый контекст по ID не выдаётся.

Чтобы повтор R29/R33/R43 вернул ту же cookie ограниченного context, применяется единственный нормативный байтовый профиль [реестра §3.1](backend-auth-d02-registry.md). Он задаёт literal domains, encoding, исходный proof каждого маршрута, derivation и отдельный verifier; альтернативная формула здесь не допускается. AC06 закрепляет профиль/key-bundle. При replay нужны тот же исходный secret, исходная версия ключей и тот же result_context; новый secret не генерируется. Недоступный ключ/невозможность технической проверки —503, доказанно неверный proof — прежний отказ доступа. Эта точность остаётся проектом D02; D03 проверит заданный профиль. Full-login cookie этим способом не восстанавливается: только AC07/AC16.

## 6. Состояния, право повторов и атомарные комплекты

MC: email_required→email_verification только подтверждённая отправка; resend остаётся email_verification и заменяет current challenge; email verify enroll→factor_prepare, disable→totp_verification. Reenroll создаётся сразу factor_prepare из доказанного restricted UA, без повторной email-отправки. Factor prepare→totp_verification; renew только TOTP stage после разрешённого истечения/current expected, без unknown/pause reset; confirm→completed. Неверный код stage не меняет, final rejection+counter атомарны. Complete/enroll сохраняет прежние login, disable отзывает прежние и mfa_requirement=none, reenroll создаёт новый полный login только после активации фактора. Второй новый confirm completed409; exact replay ищется раньше. Одна prepared factor-version на context, не второй seed после потерянного ответа.

SA: ready→challenge через options, challenge→completed только full completion. Options новым ID заменяет только истёкший challenge при отсутствии unresolved verify; verify wrong остаётся challenge. RG: ready→challenge→completed; результат зарегистрированного credential не login. SC: ready→challenge→completed после выдачи10 codes, повтор issue не новый набор. GP: active до expiry/revoke; refresh сохраняет ID/proof и max(прежний expiry,now+7d); только C04 created/updated может продлить до срока draft, остальные paths нет.

AC04: admitted→dispatched после сохранённого AC39 seal; admitted→resolved для локальной операции; dispatched→resolved при доказанном finalizer; dispatched→uncertain при неустановленном исходе; uncertain→resolved только после доказанного исхода. Closed_without_dispatch допустим только доказанно без dispatch; не объявляется verification_rejected. Внешний confirmed_not_sent допускает следующий AC39 ordinal лишь при живом исходном допуске/остатке бюджета, не после timeout одного только HTTP. Execution deadline не продлевается replay. Неизвестный результат не разрешает смену ключа.

AC25 collecting→authorized после достаточных approvals; authorized→collecting при новой версии либо утрате свежести до исполнения; authorized→executing только с exact tuple текущей версии и достаточными действующими правами; executing→completed после доказанного эффекта/полного finalizer. Executing unknown не rejected по expiry. Rejected только окончательное доказанное решение без незавершённого внешнего эффекта; API D02 не вводит отдельную кнопку reject. Новый tuple/evidence/участник — новая immutable AC26 и повтор approvals, не UPDATE старой версии. Публикация такой версии — закрытый case writer, не произвольный PATCH клиента.

**Точная развёртка AC27:** reset —2 approver rows разных staff, requiredApprovals=2; single recovery —1 subject row с его SR/новым limited key и1 approver row другого current SL, requiredApprovals=1; pair —4 rows (subject+approver каждого из2 staff), requiredApprovals=2, у каждого свои SR/limited key. Для single AC04.execution_approval_1_id задан, approval_2_id=null; для reset/pair оба заданы, staff разные. Freshness5min проверяется на начале execution; expiry потом не откатывает эффект. Approver никогда не подменяется инициатором complete. В pair approverContextId выбирает одну сторону tuple и должен соответствовать assertion, оба SR всё равно обязательны.

Recovery SR создаётся limited с version1; успешная registration создаёт limited credential и single case/version/participants одной T, переводит в awaiting_approvals. До pair creation оба контекста должны иметь limited credential и собственный single case в collecting/authorized, без unresolved исполнения; уже связанный pair повторно в новый pair не включается. Pair writer под guards обоих контекстов закрывает их неисполняемые single proposals без внешнего эффекта, создаёт общий case/version/четыре rows и привязывает оба контекста атомарно; старые approvals в новый case не переносятся. Current case pointer — отдельная изменяемая ссылка, прежние case/version остаются историей. Смена tuple/new key требует новой версии; обычный повтор registration с новым ID не создаёт второй key completed-контекста, нужен разрешённый новый процесс. Исторический AC20.source_case_version_id ограниченного ключа сохраняет первоначальное происхождение; его принадлежность новому pair доказывается AC27 и тем же SR/subject, не переписыванием источника. Pair complete активирует обе стороны/отзывы старых ключей/login и результат одной T; затем отдельный обычный staff login.

Atomic sets: context-create+proof+source-consume+result; dispatch seal+operation pointer; verify+used steps/counters+result/stage; full login+AC05+AC38+AC16+AC07+source context (и staff slot/revoke); claim остаётся своим прежним полным комплектом с AC19/40; approval+consumed challenge+result+audit; reset/recovery effect+security/revokes+result+audit+notification; issue codes+10 rows+old-set revoke+result; local witness change-set с каждым защищённым эффектом. Ни один partial parent не успех. Network effect не атомарен с локальной T.

### 6.1. Исторический resolver K/P и scope операции

Эта редакция BDR03 использует существующие immutable связи; новых колонок, wire-полей и глобальной уникальности operationId нет. Перед поиском — текущий разрешённый reader; ошибки чтения/неоднозначная обязательная связь —503 RECORD_UNAVAILABLE, не поиск «первого подходящего» результата.

| Путь/action R42 | Единственный исходный scope и источник |
| --- | --- |
| K: recovery_create | recovery_handle / AC23.id из AC03.recovery_code_set_id. Исходная AC04 найдена по scope/action/client_operation_id; её AC05.result_context_id должен равняться K context |
| K: recovery_registration_options / recovery_registration_verify | context / сам K context ID. Наличие AC05 не требуется для поиска AC04 |
| K: recovery_options / recovery_approve / recovery_complete | Только исторический **single** case. Найти единственный AC20, зарегистрированный action=recovery_registration_verify с AC04.namespace=context/context_id=K. По неизменяемому AC20.source_case_version_id → AC26.case_id → AC25(kind=staff_recovery_single). AC27 subject той исходной версии обязан связывать тот же staff/context/credential. По этому AC25.id ищется AC04 security_case/action/client_operation_id, в том числе до AC05 |
| P: pair_create | context / min двух исходных SR ID по байтам UUID, через subject rows исходной AC26 pairId=AC25.id. First/second в сохранённом payload не сортируются заново |
| P: recovery_options / recovery_approve / recovery_complete | security_case / сам pairId=AC25.id, kind=staff_recovery_pair. Исторический requestVersion из AC04.nonsecret_payload разрешается в AC26 того case; для исполнения дополнительно exact execution_case_version_id |

K case-POST после привязки к pair не начинает новое single-действие:409 AUTH_CONTEXT_STATE_CONFLICT. При exact replay сначала ищется прежняя операция в историческом single scope, её текущий допуск чтения всё равно обязателен. Работа с pair выполняется через P; старый K GET никогда не переключается на pair. Новая версия внутри того же case не меняет namespace/ключ операции. SL второго владельца через K читает только собственные options/approve при текущем праве; ни prior approval, ни прежний grant сами по себе не bearer.

До успешной recovery registration отсутствие single case законно: на K ещё нет допустимой case-operation; соответствующий lookup —404 RESOURCE_NOT_FOUND, без создания case. После registration нет AC20/source case/обязательного participant либо найдено несколько credentials вместо единственного исходного —503 RECORD_UNAVAILABLE. Существующая незавершённая AC04 даёт202 по прежнему правилу; запись, отсутствующая после достоверного поиска в разрешённом единственном scope, не доказывает откат/отсутствие внешнего эффекта и не разрешает новый ключ. AC05 используется только после нахождения AC04 и проверки её целостности, а не как единственный locator.

## 7. Матрица ошибок и восстановления

| Случай | Точный ответ/дальнейшее действие |
| --- | --- |
| Неверные bytes/media/shape/enum/UUID/query |413 REQUEST_TOO_LARGE /415 UNSUPPORTED_MEDIA_TYPE /400 INVALID_REQUEST по порядку; нет сохранённого отказа/Set-Cookie |
| Нет proof / доказанно истёк / отозван |401 AUTH_REQUIRED /AUTH_EXPIRED /AUTH_REVOKED; revoked сильнее expiry если оба доказаны |
| Чужой/скрытый context/challenge/case |404 RESOURCE_NOT_FOUND, без признака существования; отсутствие необходимого права на уже разрешённую цель403 ACCESS_DENIED |
| Иной payload того же ключа |409 KEY_REUSE_CONFLICT после целостности записи и сравнения sensitive bytes; нет нового dispatch |
| Stale version/не та стадия/заменённый challenge |409 AUTH_CONTEXT_STATE_CONFLICT; новый explicit action только после разрешения прежнего unknown |
| Действующий challenge, неправильный OTP/assertion |401 AUTH_VERIFICATION_FAILED, result verification_rejected; один предметный учёт. GET такого результата200 resolved |
| Текущий challenge истёк |Точная развёртка §7.1 ниже; email, TOTP и WebAuthn не объединяются в один отказ |
| Пауза OTP/TOTP либо transport quota |429 RATE_LIMITED/retry_later; retryAt только достоверный внутри context срока, иначе{}; replay найден до предметной паузы, но после transport quota |
| Unknown исполнения/нет provider proof |Direct503 SERVICE_UNAVAILABLE; authorized GET202 unresolved только после достоверного scoped чтения. Не новый key/неверный код |
| Доказанно closed_without_dispatch, окончательного result нет |GET409 AUTH_CONTEXT_STATE_CONFLICT, не202; нет эффекта доказано closure evidence, новый вход/действие только явно по действующему допуску. Это не verification_rejected и не неизвестность |
| Повреждённый record/неподдерживаемый storage format |503 RECORD_UNAVAILABLE; не202, не пустой result/field list |
| Cookie recovery по известному не-completion result |409 AUTH_COOKIE_RECOVERY_NOT_APPLICABLE. Для нового namespace допустимый completion только staff_login_completed/mfa_reenrolled; user список расширен явно §8 |
| Cookie recovery закрыта/первый current GET уже был |409 AUTH_COOKIE_RECOVERY_CLOSED; не новый secret/login/deadline. Current revoke проверяется раньше и остаётся401 |
| Secret reveal закрыт |409 AUTH_CONTEXT_STATE_CONFLICT, исторический GET result сохраняется при разрешённом чтении; новый seed/набор не выдаётся |
| Несовпадающий consumed bootstrap/code при другом operationId |401 AUTH_VERIFICATION_FAILED без раскрытия причины/аккаунта; свой exact replay проверяется через прежний source result, не повторный consume |

Общий error-конверт §1 сохраняется. nextAction у новых технических ошибок null/{} кроме принятого retry_later; не добавляются произвольные URL. Для известного этапа прежнего user Auth остаются complete_totp/enroll_totp с authContextId. Direct завершение/GET исхода не считаются пользовательской foreground активностью.

Q01/recovery/revoke сериализуются по X AC16, window→secret. Первый доказанный Q01/admin-me закрывает окно до200, idle не продлевает. Поздний уже подготовленный HTTP может доставить ту же cookie после закрытия окна; серверный current guard сильнее. Первый Q01 позже expiry recovery разрешён по действующей cookie/AC38, отсутствие законно стёртого cipher не повреждение login. Logout target A и authorization B раздельны.

### 7.1. Истечение и отрицательная проверка по маршрутам

Для прежних C02/AUTH_TOTP_VERIFY действуют [Auth §§5–6](backend-auth-contracts-addendum.md); D02 не меняет их семантику. Порядок §1 сохраняется: replay доказанного результата раньше текущей стадии/срока challenge, но после текущего proof/доступа и transport quota. Применимая предметная пауза429 проверяется по прежнему профилю до новой проверки. Таблица ниже — случай, когда более ранний отказ не сработал; новые маршруты отмечены как точность проекта D02.

| Kind / маршруты | Истёкший текущий challenge при живом контексте | AC05 / counter / challenge для нового ID |
| --- | --- | --- |
| Email: прежний C02; новый R49 email-link и MC email_verify R05 |401 AUTH_VERIFICATION_FAILED | Один verification_rejected в разрешённом исходном scope; counter не увеличивается, code/link не потребляются, stage/срок не продлеваются. Для новых R49/R05 это явный профиль D02; C02 прежний |
| TOTP: прежний AUTH_TOTP_VERIFY |409 AUTH_CONTEXT_STATE_CONFLICT до проверки кода | Нет verification_rejected/новой AC05, нет dispatch/used steps/counter increment/consume; expiry не закрывает старый unknown. Только разрешённый explicit renew |
| TOTP: новый mfa_confirm R09, enroll/disable/reenroll |409 AUTH_CONTEXT_STATE_CONFLICT до проверки кода | Та же нулевая предметная дельта AC05/09/11/12; подготовленный factor не активируется/отключается. Это профиль D02, не переопределение user login |
| WebAuthn: R19 reset approve, R25 staff login, R31/R36 registration, R40 recovery approve, R45 code issue |409 AUTH_CONTEXT_STATE_CONFLICT до криптографической проверки | Нет verification_rejected/новой AC05/consume/credential/codes; не выдумывать TOTP counter. Новые options только по своему разрешённому пути |

Для действительного challenge доказанно неверный OTP/повторный использованный TOTP step или неверная подпись в **разрешённом** verify action дают401 и один verification_rejected; предметный counter меняется только там, где его scope/purpose предусмотрен. WebAuthn не увеличивает AC12 TOTP. Синтаксически невалидный assertion/credential отклоняется раньше400, техническая невозможность проверить —503 без ложного verification_rejected. Ошибка регистрации не создаёт credential/single case. Expired/consumed recovery code R33 — не challenge AC09: действует его самостоятельный source-proof/replay профиль, не строка WebAuthn. Нулевая предметная дельта не означает отсутствие transport quota или безопасной технической телеметрии.

## 8. U03: точный поздний исход без выдачи login

Новый result.kind=auth_completion_not_issued относится только к C02/AUTH_TOTP_VERIFY/AUTH_EMAIL_LINK_VERIFY, staff_login или mfa_confirm purpose=reenroll, когда доказано подтверждение, но **локальный полный login ещё не создан** и finalizer доказанно закрыл возможность его выдать. Сохранённый успешный completion после revoke не переписывается. Timeout/лишь закрытый gate без завершённой сверки не основание final result.

Result ровно kind,completionAttemptRef,completedAt:null,login:null,cause,decidedAt:T. CompletionAttemptRef для user UReply ровно authContextId,authOperationId,commandType; для нового NReply ровно contextId,operationId,action (только исходный context этой login-попытки). Это nested discriminant по внешнему namespace, не смешанный ref и не произвольный union с null-полями.

Cause закрыт: security_revoked / context_revoked / context_expired / execution_closed. Если доказаны несколько — именно такой приоритет. Security_revoked охватывает подтверждённую потерю current principal/identity/selected-login/security разрешения; execution_closed — явное необратимое закрытие после доказанной сверки, не timeout. DecidedAt — момент локального окончательного решения, resolvedAt=decidedAt. Provider evidence/effect time остаются AC39; для локального WebAuthn — доказанный outcome адаптера/consumption AC09 и credential AC20, без фиктивного внешнего dispatch. Эти доказательства не выдаются в публичном ответе. Нет cookie/loginId/completion/возобновления окна; AC05.result_login_id/completion_context_id/completed_at NULL. Для внешнего эффекта AC39 обязательно, для чисто локального WebAuthn его отсутствие законно при указанном доказанном локальном комплекте.

Direct после фиксации: если текущий reader ещё имеет право на этот процесс,409 AUTH_CONTEXT_STATE_CONFLICT с обычным четырёхполевым error-конвертом, без result. Если proof уже expired/revoked/нет права — соответствующий более ранний401/403/404. Это не ранний отказ без записи: AC05 хранит отдельный доказанный исход. Authorized GET200 resolved возвращает этот result; при утрате права GET не раскрывает его. При unknown самой фиксации503, повтор ищет исходную operation, не создаёт login.

Реестр user GET §7 явно расширяется только AUTH_EMAIL_LINK_VERIFY и auth_completion_not_issued, не staff/MFA kinds. User login-cookie POST дополнительно допускает commandType=AUTH_EMAIL_LINK_VERIFY для доказанного login_completed того же context; прочие прежние поля/5min/first-Q01 неизменны. Для auth_completion_not_issued recovery409 NOT_APPLICABLE при разрешённом чтении. MFA/staff GET используют свои NReply, не user UReply. После этого результата новый вход возможен только новым явным разрешённым процессом; он не возобновляет исходный operation ID.

Для reenroll полная таблица factor/security/result/audit/notification — [реестр §4.3](backend-auth-d02-registry.md). Подтверждённая активация сохраняется и при auth_completion_not_issued; отсутствие login не заменяет аудит изменения фактора.

## 9. Activity и аудит, проверка полноты D02

Activity routes: user_catalog targetId=null; user_setup/user_review draftId; user_session/staff_session_view sessionId. Билет30s — AC31 с typed target, выбранным login и current access, consume+один допустимый idle touch одной T с Q02/Q03/C05/Q04/Q06 соответственно. Staff ticket не продлевает user. C04 с реальным изменением/C06 могут touch в своей T без билета. Q01/refresh/poll/observer/replay без нового интерактивного допуска не touch. Невалидный ticket не даёт idle touch; обязательность и отказ400/404/401 следует его форме/цели/current login, не скрытому fallback. Билет не доказывает присутствие человека.

[Реестр v6](backend-auth-d02-registry.md) перечисляет action/result/proof-purpose/stage/audit/grant и AC-отображение, включая все маршруты §3 и staff logout. Проверяются разные направления: route→schema/proof/result/storage; result→разрешённые actions; stored ref→тот же environment/subject/context/version; нет недостижимого публичного enum или неучтённого endpoint. Секретные ответы R07/R45 отдельно от исторического result. Не создаются новые Shadow command types/audit_events/recordSchemaVersion.

Адресная редакция BDR01–BDR08 подготовлена к повторной вычитке; автоматического закрытия замечаний нет. Новые маршруты описаны по request/success/error/replay/expiry/unknown/proof и источникам хранения; полнота теперь проверяется также по реестру §§1.1/3.1/4.1–4.3. Особые уточнения D02 (NRef до context, GET текущего case, pair approver selector/четыре participant rows, proof re-issuance profile, отдельные recovery grants, late-outcome wire) выделены в реестре для единой вычитки. Их подготовка не означает независимое принятие всего RD02 без просмотра. Принятые U01–U03/73→78 от этого не откатываются. D03 — будущие реальные capability/crypto/lock/budget/restore проверки; D04 после согласованного D02 и паспорта D03. Все испытания пока «не выполнялось».
