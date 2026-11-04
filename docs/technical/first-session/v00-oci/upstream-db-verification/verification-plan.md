# V00 upstream: ожидаемые доказательства bridge

04.11.2026. Все новые UB-сценарии ниже **NOT RUN**. Старые39 SQL/24 HTTP/37 browser
checks D03-07 и108 условий независимой сверки остаются историческими фактами своих
пакетов; они не добавляются к новым pass. Полный Auth/V00, BR08, D03 и V01 открыты.
Предусловия — [provider manifest](provider-manifest.md),
[private contract](private-contract.md), синтетические данные в отдельной копии.

Fixture setup отдельно фиксирует успешный `/otp` response, изменение generation и
получение реального тестового письма. Эти три факта не взаимозаменяемы. Письмо
связывается с исходными user/family/generation доверенным setup-процессом; raw code,
email/provider token/seed не публикуются. Утраченный send response не даёт повтор.
TOTP fixture сначала действительно enroll/verify у provider; прямой INSERT active
фактора не доказывает это. All-matching collision fixture маркируется отдельно,
не выдаётся за фактор, полученный по обычному provider enrollment.

| ID / источник | Изолированное состояние и действие | Ожидаемый независимый факт |
| --- | --- | --- |
| UB01 · AC04/09/39, D03-04 | Existing confirmed user, реально полученный recovery-family OTP; C02 no-MFA | Seal ровно исходной generation; consume и ровно provider session одной T; один Shadow completion и полный source bundle |
| UB02 · AC09/10/11, D03-05 | Реальный active factor; C02, затем отдельный AUTH_TOTP_VERIFY | C02 result только auth_step_required с исходным challenge/5min bound; TOTP result другого op создаёт единственный login; никакой full cookie после одной email стадии |
| UB03 · AC04/05/16/38, D03-07 | Потеря email verify HTTP после provider COMMIT | Read exact witness восстанавливает исходный процесс без повторного `/verify`, refresh или JWT mint; если original deadline/current guards не позволяют completion, login не создаётся |
| UB04 · AC04/39, D03-04/12 | Потеря подтверждения seal COMMIT до разрешения отправки | Ни тот же HTTP replay, ни новый operation/context не получают новый network permit; отсутствие response не считается доказанным not-sent |
| UB05 · AC04/05, D03-04 | Exact POST replay после последующей стадии/Q01 и другой payload того же op | Исходный result/время/challenge неизменны; без counter/steps/login delta; конфликт payload409. GET сохранённого отказа200 при разрешённом чтении |
| UB06 · AC11/12, D03-05 | Код совпадает с двумя допустимыми steps; затем один из них уже consumed | Первый успех расходует весь matching set одной T. Уже использованный среди совпавших отклоняет весь новый набор без частичного расхода остальных; один failure result/counter |
| UB07 · AC10/11/12, D03-05 | Два context одного user/factor одновременно проверяют тот же code | Наблюдаемый lock wait, общий factor-version one-use; не два login от одного step. Отдельный actor не сериализуется без причины на global X |
| UB08 · AC05/11/16/38, D03-07 | После успешного plan сбой crypto/complete или rollback | Ноль нового result/login/step/stage/counter-reset/plan после rollback; отдельный commit plan без полного bundle отклонён ограничением |
| UB09 · P03/G0–G3, D03-12 | Одновременные provider transition, seal, finalizer и fence | Наблюдаемые waiter/lock IDs и завершение без инверсии; gateX не ждёт внешнюю сеть; доказанный drain всех старых permits, а не actor-only fence |
| UB10 · AC05/16/38, D03-07 | Потеря подтверждения local COMMIT после полного bundle | Исходный result найден; cookie только после подтверждённого commit/read recovery; один исходный login/secret/deadline, без нового provider call |
| UB11 · AC16, D03-07 | Первый Q01 против recovery, затем expiry/erasure | Та же window X, один исходный credential сохраняется после cipher erasure; first Q01 закрывает новую выдачу, поздний уже подготовленный HTTP не оживляет отозванный login |
| UB12 · logout target/authorizer, D03-07 | Восстановление logout A через живой B | Отозван только A; B не становится target; исходный logout result неизменен и не дублируется под новым source context |
| UB13 · AC09, D03-04 | Replacement token, в том числе одинаковые bytes, затем старый seal | Новая выдача — новое доказанное поколение; старый unknown не перепривязан. Неразличимая issuance закрывает восстановление, не успешный guessed match |
| UB14 · AC39, D03-04 | Служебное обновление user; очистка без session; лишняя session другой T; transaction rollback | Нет ложного success; служебный update не создаёт generation; rollback не оставляет witness; неоднозначность503, не выбор первой session |
| UB15 · U03, D03-12 | Provider effect есть, но original actor/context/epoch/budget уже не допускает full completion | Не новый login/used-step promise. После доказанного окончательного закрытия — точный auth_completion_not_issued с приоритетом cause; один timeout или closed gate без сверки остаётся unknown |
| UB16 · AC09/10, BR08 | Подготовленный/чужой/отозванный/повреждённый factor, непроверенные часы, unsupported encrypted seed | Нет login/false wrong-code/counter increment. Missing current source503; доказанный revoked/access — свой принятый guard. Никакого fallback к старому seed |
| UB17 · security boundary | Runtime пытается direct plan/complete, SELECT provider seed, fixture time change, forge generation/steps | Отказ роли/закрытого input; safe observer не выдаёт секреты. Успех этой проверки не делает operator безопасным runtime role |
| UB18 · D03-13, E14/E15/E17 | Внешняя encrypted base/WAL после появления нового namespace | Scoped source/restored manifest совпадает по обязательным типам/связям; no-data явно; local primary witness не выдаётся за внешний trusted freshness head |

Email final rejection после действительного, но неверного OTP требует отдельной
проверенной классификации **исходного** provider response и атомарного counter/result.
До согласованного private call/allowlist эта ветвь **NOT IMPLEMENTED**, не UB-pass.
Произвольные401/4xx/5xx, отсутствие witness и timeout не становятся неверным кодом.
Публичные C01/C03, resend/mail uncertainty, persistent quota и полный lifecycle
фактора также **NOT IMPLEMENTED** в этом узком проекте; допустимость очереди решает
ведущий по действующему V00, без автоматического переноса зависимостей в V01.

## Формат безопасного actual

Для каждого UB: исходный commit/image digest, fixture alias, независимые before/after
IDs/counts/source relations, ожидаемое и наблюдённое, `pass/fail/not_run`, причина
отсутствия проверки. Отдельно DB/protocol/browser/provider/backup evidence и точный
scope. Нельзя считать подготовленные assertions выполненными или число assertions
числом интеграционных сценариев. При actual failure сохраняется безопасный факт;
исправление создаёт новый run, прежний результат не заменяется молча.

Независимые связи проверяет БД после получения safe snapshots от серверного
оператора; сетевой dispatch count и Set-Cookie подтверждает отдельный trace.
Внешний restore должен получить именно объект из private storage. [Backup gates](backup-gates.md)
разделяют это текущее поручение, безопасное reopening и полную будущую приёмку.
