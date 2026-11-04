# V00 upstream ↔ БД: закрытый контракт перед реализацией

04.11.2026. Это согласуемые private signatures и границы транзакций, **не созданные
функции/таблицы и не результат испытаний**. Бэкенд и БД подтвердили local-adapter
профиль и generation instrumentation в переписке04.11.2026. Возможности actual
provider остаются по [PC01–PC12](provider-manifest.md). Продуктовый каталог78,
принятые DTO, AC09–AC11, U03 и D03-07 не меняются.

## 1. Область и доверие

Новая отдельная копия тестовой БД: `v00_upstream` плюс неизменённый dependency
`v00_session` из PR235. Никаких изменений старых стендов и установки на production.
Runtime executor имеет только опубликованные wrappers. Он не наследует
`v00_session_executor`, не может напрямую вызывать plan/complete, менять fixtures,
получать seed либо произвольные строки `auth`/Shadow. Observer читает только safe
проекции. Installer/operator отделён от runtime. SECURITY DEFINER owner не LOGIN;
закрытый search_path, явные qualified refs и отозванный PUBLIC EXECUTE обязательны.

Минимальный proposed bridge начинается с реально доставленного OTP отдельной
fixture; instrumentation работает **до** выдачи. Полная реализация C01/C03, resend,
неизвестной доставки письма и persistent HTTP quotas в этот bridge не включена.
Её нельзя объявить выполненной по успешному чтению письма. Фактическая выдача в
fixture выполняется один раз; unknown не вызывает скрытого повторного `/otp`.
При расширении до C01 требуется отдельная durable admission отправки до сети:
generation доказывает изменение provider state, не доставку SMTP.

Fixture setup подтверждает provider identity/factor и задаёт только server-owned
source mapping. HTTP клиент не передаёт actor/provider ID, factor ID/version,
matched steps, epoch, time, success, deadline, login ID или seed.
Отдельный trusted ingress фиксирует initial epoch и бюджет до очереди/ожидания.
Повтор не создаёт новый бюджет. Тестовый fixed clock доступен только operator,
обычный путь использует доверенное серверное время.

## 2. Точные общие типы и сохранённые источники

`U` — UUID, `T` — UTC timestamp, `H` — 64 lowercase hex, `S` — закрытая строка.
Все объекты имеют ровно перечисленные поля; неизвестные/лишние поля отклоняются.
Ни один private DTO не выдаётся HTTP-клиенту без обычного public projection.

| Обозначение | Ровно поля / назначение |
| --- | --- |
| ReadRef | `context_id:U, proof_digest:H, operation_id:U, action:C02/AUTH_TOTP_VERIFY` — исходный user Auth scope, включая ожидаемый commandType |
| WriteRef | ReadRef + `fingerprint:H, comparison_hmac:H, comparison_key_id:S` |
| AdmissionRef | `admission_id:U` — ссылка на ранее сохранённый admission; runtime не передаёт новые epoch/time/executor |
| CompletionIds | `login_id:U, secret_id:U` — trusted randomness; становятся исходными только с полным commit |
| CipherMaterial | `cookie_digest:H, ciphertext:base64, nonce:base64, key_id:S, credential_key_id:S` — прежний test codec, metadata/AAD из plan |

Fingerprint содержит только разрешённые несекретные bytes/source version.
Comparison HMAC с purpose/domain/environment/исходным scope хранится отдельно в
закрытой AC08-подобной записи и проверяет именно raw OTP bytes. Он не попадает в
обычный result, audit или observer. Срок/erasure исходного comparison не заменяется
бессрочным hash. Отсутствие нужного живого comparison не даёт признать replay точным.

Private storage связывает environment+provider user, immutable factor reference/
version, context, challenge, operation/action, admission/dispatch, email generation,
provider effect, результат и при completion — точную запись `v00_session.results`.
Для `auth_step_required`, `verification_rejected`, `auth_completion_not_issued`
ссылки на full login отсутствуют законно. Для `login_completed` обязательны весь
dependency bundle и равенство result JSON/source tuple, без nullable bypass.
Внешние generation/outcome refs не имеют каскадного удаления от provider sessions.

Ожидаемый `action` сверяется с исходной operation **в том числе при unresolved**.
Одна уникальность environment/context/op не допускает другую команду под тем же ID.
Read/recovery не возвращают чужой commandType по одному совпадению context/op.
Внутренняя dependency может сохранить прежнюю сигнатуру без action: проверку делает
bridge до делегирования. Если операции нет вообще, авторизованное scoped чтение
не выдумывает её action;202 относится только к запрошенному допустимому scope.

### 2.1. Неподменяемый admission и исходный бюджет

Отдельный trusted ingress до передачи handler в исполнимую очередь фиксирует
immutable capture: environment/context/op/action, ingress ID, назначенный executor,
initial epoch, время начала и deadline начала+10s. Он использует отдельную роль,
недоступную runtime executor; время/epoch не принимаются от HTTP клиента. Capture
нельзя создавать постфактум из уже ожидавшего worker или читать свежую epoch как
исходную. Пока capture не подтверждён, request не передаётся исполнителю.

Операционная admission-T под G0/actor/context создаёт immutable admission по этому
capture либо читает прежний admission того же context/op. Runtime получает только
его ID. Уникальность исходного operation scope не позволяет второму capture заменить
epoch/executor/start/deadline. `seal_email`/`plan_totp` повторно читают admission,
проверяют source tuple, назначенного executor и остаток исходного бюджета; поля из
повторного HTTP не продлевают срок. `plan_email` использует только admission своего
сохранённого seal. Отдельная выдача admission не даёт права network до committed seal.

Точные capture/admission procedures и role grants входят в будущую реализацию и
PC08/UB04; слово trusted не считается испытанной защитой. Сохранённый result ищется
после текущего доступа/transport limits, но **до** текущего challenge/pause/бюджета.
Истёкший budget не скрывает законно читаемый прежний result и не создаёт новый permit.

## 3. Предлагаемые private signatures

Имена описывают будущий интерфейс в namespace `v00_upstream`; SQL ещё не создан.
Все функции возвращают `http`, а остальные варианты перечислены ниже. Техническое
`503` не сохраняется как предметный отказ. Статусы чтения не подменяют исход команды.

| Private call | Вход | Результат и права |
| --- | --- | --- |
| `seal_email(p)` | WriteRef с action=C02 + `challenge_id:U` + AdmissionRef | Короткая отдельная T. Новый подтверждённый seal возвращает `http=200, dispatch_allowed=true, dispatch_id:U`; только исходному executor. Exact repeat возвращает тот же ID и `dispatch_allowed=false`. Иной payload409; чужой pending503. Provider user/family/generation берутся только из current fixture/challenge. До подтверждённого COMMIT network запрещена |
| `read_operation(p)` | ReadRef | Authorized200: `status=resolved,result,resolved_at`; достоверное отсутствие окончательного результата202: `status=unresolved,result=null,resolved_at=null`. Нет provider call, cookie/secret/нового permit. Corrupt source503, known closed-without-dispatch409. Проверка proof/current access раньше раскрытия |
| `plan_email(p)` | WriteRef с action=C02 + CompletionIds | В живой интерактивной T читает immutable exact provider outcome. Если нужен TOTP — сохраняет прежний `auth_step_required` и новый исходный challenge с5min/context bound; возвращает `http=200,replay=false,result`, **без plan/cookie**. Если MFA не требуется — под всеми guards создаёт bound completion plan и возвращает `http=200,replay=false,metadata,completed_at,login_expires_at`. Нет witness→503 без final result. Exact replay возвращает исходный result без новых effects |
| `plan_totp(p)` | WriteRef с action=AUTH_TOTP_VERIFY + `challenge_id:U, code:ровно6ASCIIцифр` + AdmissionRef + CompletionIds | Новая проверка только в живой T. Trusted verifier сам получает active factor/profile/time, считает весь ±1 set и проверяет one-use. Неверный/used code сохраняет один `verification_rejected` и counter; возвращает `http=401,replay=false,result`. Успех создаёт bound plan как `plan_email`; steps пока внутри той же незавершённой T. Client-supplied steps/success не допускаются |
| `complete(p)` | WriteRef + CipherMaterial | Только та же T/plan/action/source admission, что успешный plan. Полный `v00_session` bundle + bridge result + steps/challenge/counters/audit коммитятся вместе. Возврат `http=200,result,login_expires_at` сам по себе ещё не доказывает COMMIT. После ошибки complete caller откатывает всю T; не коммитит частичный plan |
| `recover(p)` | ReadRef | Только исходный доказанный login_completed и current guards; делегирует прежнюю window/credential/cipher проверку. Не-completion409 NOT_APPLICABLE. Unknown503, corrupt503, window closed409. Не вызывает provider и не создаёт plan/login |
| `q01(p)` | `login_id:U,cookie_digest:H` | Прежний selected-login Q01, global gate/current guards добавляются wrapper, idle не продлевается. Закрытие окна/erasure атомарно |
| `snapshot(actor:U)` | Operator/observer, synthetic actor ID | Только safe facts по §5. Не runtime API и не источник разрешения на выполнение |

Logout wrappers сохраняют **точные** private payload/target A и authorizer B из
`scripts/v00-session-db/003-logout.sql`. Глобальный guard добавляется до делегирования;
расширение input для смены target или новая синтетическая команда завершения не нужны.
`read_operation` не становится обычным CommandReceipt/Q05.

### 3.1. Закрытые return variants

| Вариант | Ровно ключи |
| --- | --- |
| Error любого wrapper до/без предметного результата | `http,reason`; reason — принятый runtime error code, не произвольный provider text |
| Seal новый/повторный | `http,dispatch_allowed,dispatch_id`; true только первому исполнителю после подтверждённого commit |
| Plan exact replay | `http=200,replay=true,result`; для сохранённого отрицательного результата это private lookup, HTTP POST projection сохраняет его принятый отрицательный статус |
| Plan новый промежуточный/отрицательный результат | `http,replay=false,result`;200 auth_step_required или401 verification_rejected |
| Plan новый full completion | `http=200,replay=false,metadata,completed_at,login_expires_at` |
| Complete | `http=200,result,login_expires_at` |
| Read resolved | `http=200,status=resolved,result,resolved_at` |
| Read unresolved | `http=202,status=unresolved,result=null,resolved_at=null` |
| Recover успех | `http=200,result,ciphertext,nonce,key_id,credential_key_id,cookie_digest,metadata,login_expires_at` |
| Q01 успех | `http=200,authenticated=true,login_id,actor_id` |

Metadata — ровно объект `v00_session.metadata` из
[`001-storage.sql`](../../../../../scripts/v00-session-db/001-storage.sql):
environment, realm, login_id, secret_id, source_context_id, source_operation_id,
owner_kind, owner_id, purpose, cipher_format, credential_format, reveal_until.
Его test environment/codec не переименовываются независимо от encryption/AAD.
Logout inputs/return variants — точные функции logout_prepare/logout_continue/
logout/logout_result и logout_view из
[`003-logout.sql`](../../../../../scripts/v00-session-db/003-logout.sql), baseline `41123ec`.
Общая error форма dependency — только http/ reason из `v00_session.error`.
Новые unknown поля или скрытый discriminator запрещены; future schema version
требует адресного обновления контракта. Snapshot не public DTO; его versioned схема
должна быть замкнута отдельно до coding, §5 пока перечень требуемых фактов.

### 3.2. Как заканчивается транзакция

| Полученный private вариант | Действие caller до HTTP |
| --- | --- |
| Новый seal | COMMIT и подтверждение; только затем один dispatch. Потерянное подтверждение→503, без dispatch |
| Plan_email auth_step_required | COMMIT промежуточного result/challenge/audit, подтверждение до200; full complete не вызывается |
| Plan_totp verification_rejected | COMMIT отрицательного result/counter, подтверждение до401; не rollback по одному non-2xx |
| Новый successful full plan | Trusted crypto → complete в той же T → подтверждённый COMMIT; cookie только затем |
| Ошибка crypto/complete либо precheck error | ROLLBACK всей T; незавершённый plan/steps не коммитятся |
| Exact replay / чистое read | Завершить T без новых предметных эффектов; исходный result не пересчитывается |
| Recover409 AUTH_COOKIE_RECOVERY_CLOSED | COMMIT законного закрытия/erasure, если функция впервые закрыла expired window; повторное уже closed тоже безопасно завершить. Ошибка/unknown commit503 |
| Recover успех, Q01, logout | Подтверждённый COMMIT прежде допускающего HTTP/cookie; Q01/ logout могут закрыть window/стереть cipher |
| Повреждение/непредусмотренный variant | ROLLBACK,503; не угадывать успешность по наличию отдельных полей |

Полного C02 negative classifier в этом пакете нет. Непокрытый отрицательный provider
response сохраняет операцию технически неразрешённой: direct503, authorized GET202
при доказанном scoped unresolved, без login/verification_rejected/counter delta.
Он не разрешает новый key или зависимое действие. Proven wrong-code classification,
expiry-without-counter и её атомарный finalizer остаются необходимой отдельной
ветвью полного C02; одного provider401 для неё недостаточно.

Late-effect reconciliation — отдельный закрытый операторский путь, **не новый
HTTP endpoint** и не общий runtime bypass. Он требует exact outcome + доказанные
current cause/closure evidence по [D02 §8](../../backend-auth-d02-contracts.md#8-u03-точный-поздний-исход-без-выдачи-login).
Signature closure ещё не является executable: `reconcile_email(context_id:U,
operation_id:U,reconciliation_run_id:U)`; отдельный внутренний допуск к run, не
истёкший пользовательский proof. Cause/decidedAt вычисляет БД из доказательств, caller
не выбирает их строкой. Gate closed/timeout без завершённой сверки не final outcome.

## 4. Порядок блокировок и commit

Обозначения: S — SHARE, X — UPDATE; environment gate всегда первый у обычного
wrapper. Actor X общий для всех context/login одного synthetic user. Невзаимные
прочтения immutable rows ниже не требуют нового X. Один актуальный tuple после
locks перечитывается; stale optimistic read не доказательство допуска.

| Путь | Expected lock sequence |
| --- | --- |
| seal_email | G0 S → actor X → context X → provider user X → current generation X → challenge X → operation/admission/seal X |
| plan_email | G0 S → actor X → context X → provider user S → current factor source при MFA (provider factor S, local version X) → generation X → challenge X → operation/seal X; immutable consume/outcome read → bridge/dependency plan или stage result |
| plan_totp | G0 S → actor X → context X → provider user S → provider factor S → local factor version X → challenge X → operation/admission X → used steps/full plan |
| complete | Только та же живая T после своего plan, с уже удерживаемыми locks; dependency повторяет actor/context, создаёт собственные новые bundle rows |
| read_operation | G0 S → actor X → context X → operation read; immutable result/outcome read, без provider locks/network |
| recover | G0 S → actor X → source context X → immutable result/login read → recovery window X → secret X; current login защищён общим actor X |
| q01 / logout_prepare | G0 S → actor X → selected login X → его source context X; затем window X → secret X для Q01 либо новый logout context для prepare |
| logout_continue | G0 S → actor X → target/authorizer logins X по ID → их source contexts X по ID → source logout context X; новый logout context сохраняет исходный target |
| logout / logout_result | G0 S → actor X → target login X → его source context X → logout context X; logout затем window X → secret X и result/audit |
| fence | G0 X; persist closed+next epoch и COMMIT; отдельный drain без удержания G0 X. Reconcile-only — отдельный допуск, не вход обычных wrappers |
| provider token issuance/consume hooks | Provider user уже X → generation X → чтение seal/outcome или вставка witnesses. Никогда gate/actor/context; hook не запускает finalizer |
| provider session hook | Provider session INSERT в той же T после user transition; immutable consumption read → witness INSERT. Не берёт user/Shadow parent в обратном порядке |

Ключевой запрет инверсии: wrapper не берёт generation/seal, а затем provider user.
Hook с удерживаемым user не должен ждать actor/context или иной ранний Shadow lock.
Если реальный порядок provider отличается, PC09 блокирует этот проект hook; таблица
не позволяет подогнать evidence под ожидаемую последовательность.

Recovery context-first и logout login-first допустимы в **этом узком dependency**
только потому, что все writers/read-for-update данного actor сначала держат один
actor X. Другой путь того же actor не может уже держать второй из этих locks.
Это не разрешение произвольной инверсии: installer/fixture mutation запрещена во
время runtime; observer только читает; bypass роли и фоновые writers без actor gate
должны быть исключены PC08/UB09. Для нескольких actors заранее единый sorted actor
order; текущие функции не выполняют cross-actor операции. Provider hooks не входят
в эту сериализацию, поэтому для них отдельный user→generation порядок обязателен.
До PC09/UB09 таблица остаётся expected, не заявленным доказательством отсутствия deadlock.

1. Email seal-T короткая; только после подтверждённого COMMIT — один внешний вызов
   без DB locks. Crash до/после dispatch сохраняет исходный seal/unknown.
2. Provider T атомарно фиксирует generation consumption + exact new session witness.
   Это не distributed transaction с Shadow. Потерянный HTTP response не стирает факт.
3. Local plan-T заново проверяет original epoch/budget/current proof/identity/factor.
   All-matching вычисляется после locks по текущему времени. Trusted crypto создаёт
   тот же cookie/AAD внутри этой живой T; затем complete и проверенный COMMIT.
4. Отдельно commit plan/used steps без полного bundle запрещён deferred integrity.
   Ровно один successful result ссылается на тот же dependency result/login. Ошибка
   crypto/complete/rollback не оставляет steps, counter-reset, stage или login.
5. Потеря подтверждения COMMIT возвращает техническую неопределённость. Read/recovery
   находят исходный результат; ни новый operation ID, ни новый secret не создаются.
6. Global fence отдельной T берёт X gate, закрывает его и повышает epoch. Drain
   охватывает старые handlers/queues/permits/DB/network; X не удерживается в ожидании
   сети. Reconcile-only не выдаёт full login/cookie. Reopening — только после полного
   доказательства и свежего внешнего checkpoint, старые permits не возобновляются.

Для TOTP expired challenge409 без counter/result; malformed code400; unavailable
factor/clock/crypto503; exact replay до текущей стадии/паузы после access/quota.
Использованный среди нескольких совпавших steps отклоняет **весь** набор и не
расходует остальные. Пятая предметная ошибка запускает принятую15min паузу; GET,
replay, timeout и техническая невозможность проверить не увеличивают её.

## 5. Независимое наблюдение

Safe snapshot содержит source IDs/версии/состояния/время/transaction IDs, action,
epoch/executor refs, количество и точные steps, result kind/DTO, current stage,
связи plan→dependency result→login→credential/window/secret row, признаки сохранности
credential/cipher, counters/pause, audit kinds и отсутствие лишнего login.
Никаких proof/comparison/cookie digests, ciphertext/nonce, seed, provider tokens,
сырых request bodies или URLs с bearer.

Сверять реальные связи, а не только `valid=true` или counts. Before/after snapshots
нужны там, где утверждается отсутствие изменения; один final snapshot не доказывает
число HTTP Set-Cookie или порядок сетевой доставки. Provider witness/DB commit,
controller HTTP, браузер и external backup — разные доказательства.

## 6. Что осталось перед исполнением

Бэкенд сверяет signatures, бюджет/replay и narrow C01/C03 boundary. Сервер подтверждает
PC01–PC12 после разрешённого preflight. Затем выбирается фактический verifier и
пишутся минимальные SQL/functions/проверки в отдельном namespace. Новый runtime
результат до этого — **NOT RUN**. [Сценарии](verification-plan.md) и
[backup gates](backup-gates.md) не дают допуска V01 и не закрывают BR08 полностью.
