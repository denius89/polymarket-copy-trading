# Полный перечень состояний 78 таблиц для будущей реализации

03.11.2026 · Документальный manifest, редакция 1. Проверенная основа: `main a967c5031be4265b7f40896b2808815a6bf3e1b6` (PR №211). **36 Shadow +42 Auth =78 собственных таблиц.** P01–P05 и последующее принятие U01–U03 учитываются; прежние срезы 34/36/73 сохраняют исторический смысл. D02/v6 остаётся проектом, текущий реестр v5. Перечень не принимает новые решения D02 и не меняет C04, `last_input_receipt_id`, карту ошибок, C06, Q02/Q06.

**Подготовлен документ, а не загружаемый набор.** Строки БД не созданы, данные не загружены, код, SQL, миграции и испытания не выполнялись. Полнота перечня таблиц не означает готовность всех исходных значений, внешних доказательств или будущей реализации. Неопределённые элементы явно обозначены зависимостями; неизвестное количество не равно нулю.

## 1. Источники, приоритет и граница каталога

| Обозначение | Источник |
| --- | --- |
| P1 | [Пользователь, draft и ownership](database-physical-design.md), включая принятый C04 |
| P2 | [Каталог, policy, review и Q02 scopes](database-physical-catalog-review.md) |
| P3 | [Session, slot, settings, funding, ledger, snapshot](database-physical-session-ledger.md) |
| P4 | [Команды, audit/outbox, staff и login](database-physical-operations-access.md), включая отдельный Q06 absence |
| AC | [Единая принятая карта AC01–AC42](auth-storage-unified.md) — текущие поля/связи/locks; [матрица полноты](database-auth-completeness-matrix.md), особенно §9, дополняет прежние AC01–37 |
| R/A | [R001–R071 и обратные указатели](database-constraint-register.md); [матрица A01–A112](database-integrity-matrix.md) и [приёмка](acceptance.md) |
| Примеры | [S/N/K/C04-E/D/J](database-synthetic-examples.md), [BASE/SEM/PUB/NEG/BAD/READ-FAULT, I01–I22](database-isolated-test-states.md), [AS01–AS28 и дельта78 §11](database-auth-synthetic-states.md) |
| История | [HR01–HR18/HE01–HE10](database-auth-history-erasure.md), **с принятой заменой старого erase-профиля в §10** |
| Гонки и сбои | [Транзакции](database-transaction-boundaries.md), [конкуренция](database-concurrency-locks.md), [F01–F24](database-fault-reconciliation.md), [E-план](database-evidence-plan.md), [MAP/DA](database-auth-handoff-review.md) |
| Незакрытая дельта | [BDR01–BDR08](database-auth-d02-review-2026-11-03.md), [D02 API](backend-auth-d02-contracts.md), [проект реестра v6](backend-auth-d02-registry.md) |

Названия таблиц в §§3–4 перечислены ровно один раз: SH01–SH36 здесь — **локальные номера строк перечня Shadow**, не числовые примеры S из другого документа. Auth сохраняет AC01–AC42. Номер строки не новое имя ограничения/таблицы/API. Все связи сохраняют environment и собственный realm/subject/purpose/venue там, где они обязательны; UUID сам по себе не право.

Provider internals, активные seed у provider, приватные passkeys, внешние ключи, witness head/evidence и test-control не входят в78. Они учитываются отдельным внешним приложением manifest, а не вымышленными таблицами. Orders/positions/fills/reserves/score и новые команды lifecycle не добавлены. Владельцы — «владелец 1» и «владелец 2», разные равноправные люди; синтетические IDs не доказывают независимость людей.

## 2. Как фиксировать состояние

Перечисление enum не разрешает все переходы между ними. Состояние задаётся строкой **вместе с полным связанным комплектом**, текущим временем и внешними предпосылками. Отсутствие строки и NULL конкретного поля — разные факты.

| Метка документа | Значение и правило счёта |
| --- | --- |
| `0 при условии` | Доказанное отсутствие строк **в указанном scope** и только при названной предпосылке. Это не total всей таблицы |
| `1`, `2`, `10`, `N` | Число выбранных строк/детей; N перед будущей подготовкой раскрывается перечислением IDs. Не разрешение пропустить неизвестный набор |
| `сохранить` | Исходный список IDs/полей/версий и count переносится без изменений. Не 0 и не DELETE перед повтором |
| `зависимость` | Обязательное значение, cardinality или подтверждение не определено. Набор нельзя объявить полностью замкнутым/готовым к исполнению |
| Вычисляемое | Expiry, актуальность approval, возможность доступа выводятся при чтении. Истечение не добавляет новый enum и не удаляет историю |
| Unknown | Сохранённая техническая неопределённость по принятому протоколу либо неизвестный commit у вызывающего. Это не окончательный отказ и не доказательство отсутствия эффекта |
| NEG / BAD / READ-FAULT | Соответственно будущая запрещённая запись, уже повреждённая изолированная копия или дефект чтения. Ни один вид не допустимая BASE |

До будущего исполнения у **каждого** сценария будет ровно78 строк учёта: таблица; исходный scoped список IDs и count; все вставки/разрешённые изменения/разрешённые удаления; итоговые IDs/count; ожидаемые значения/NULL; полный список родителей/детей; R/A/AS/HR и сценарий; источник внешних фактов; способ независимого чтения; незакрытые зависимости. Сумма: `после = до + вставки − разрешённые удаления`. UPDATE/erase не уменьшают count. Смена current pointer не удаляет прежнюю историю. Разрешённое удаление текущего Q02 membership не переносится на audit/receipt/ledger.

Таблицы ниже дают полный **инвентарь вариантов и обязательств** для этих78 строк. Они не задают один искусственный total для всех AS сразу: AS01 guest до draft и AS22 pair recovery — разные независимые срезы. У каждого сценария остаётся собственная исходная BASE, snapshot времени/версий и карта символов; строки из несовместимых срезов не складываются.

## 3. Shadow: 36 таблиц

Общие R001–R009/R068 действуют по применимости. Предметные R в последнем столбце ведут к точным A через обратный указатель реестра §6; дополнительная маршрутная карта дана в §6 этого документа. История защищена R007/R067; точные форматы ошибок — [отдельная принятая карта](database-error-field-map.md). Сроки/актуальность не превращаются в новые сохраняемые статусы.

### 3.1. Пользователь и ввод — P1

| № / таблица shadow | Варианты, допустимое отсутствие | Обязательный комплект, изменение и сохранение | Запрещённый/неизвестный вариант; трассировка |
| --- | --- | --- | --- |
| SH01 `users` | 0 для нового неподтверждённого guest; постоянный user после подтверждённого связывания; status=active/blocked по реестру | Свои identities, security AC02 и guard version; блокировка меняет guard, не ID/историю. User не staff | Email-merge/фиктивный user для guest; missing после обязательной ссылки. R010/011/056/069; AS01/08/21 |
| SH02 `user_auth_identities` | 0 до подтверждения; 1 на выбранную пару provider/subject, у user возможны другие связи | Realm=user; неизменяемая привязка к user; подтверждённые сведения/version отдельно. Сохранить связь после logout/expiry | Email как глобальный unique или перенос subject другому user; строка не доказывает full login. R010/011/058/069; AS08/11 |
| SH03 `setup_drafts` | 0 до C04; editable/expired/used вычисляются; неполный raw допустим; used имеет приоритет | Создание:1 draft+1 ownership+успешный C04 комплект; реальная правка version+1/pointer/TTL, unchanged/replay не меняют их. Claim меняет ownership, C06 — used-пару, не ввод | Last_input на unchanged/чужой receipt, used только наполовину, обрезанный raw, expired=DELETE. R012–019/027/030/039/044; AS01/02/14 |
| SH04 `draft_ownerships` | На draft первоначально1 guest **либо** user; после claim2: прежний guest+новый user | XOR полей owner; current pointer своего draft; previous+claim оба NULL при прямом user-create либо оба заполнены при claim. История остаётся | 0 children при draft; второй user-перенос; исторический guest proof как текущий доступ. R012–014/024/030/039/044/069; AS02/13/14 |

### 3.2. Каталог, правила и проверка — P2

| № / таблица shadow | Варианты, допустимое отсутствие | Обязательный комплект, изменение и сохранение | Запрещённый/неизвестный вариант; трассировка |
| --- | --- | --- | --- |
| SH05 `venues` | В полном двухплощадочном наборе2: Polymarket/Limitless | Уникальный code в environment; собственные source/trader/scope по venue | Чужая площадка в составном FK; объединение одинаковых external IDs площадок. R015/020/055 |
| SH06 `catalog_sources` | В минимальном каталоге2 synthetic source; visible/hidden независимо от start_enabled | Disabled требует reason; true требует NULL reason. Публикация с guard; source identity/origin не переписываются | Hidden без current children, fixture как fallback real; смена данных без guard. R020–022/024; AS17/QCAT |
| SH07 `traders` | По одному выбранному synthetic trader каждой venue; read_visible и start_allowed независимы | Обязательная current revision своего trader/source/venue даже hidden; disabled+reason; новая revision/допуск/видимость меняют guards | Пустой current, чужая revision, фильтрация каталога только по start_allowed. R015/020–022/024; AS17 |
| SH08 `trader_revisions` | ≥1 на существующего trader; текущая и прежние версии | Immutable provenance/name/source/observed_at; публикация новой revision+current/guards атомарна; старые review ссылаются на старую | Перезапись истории/ложная live-статистика synthetic. R021/024/030; AS17 |
| SH09 `paper_policy_versions` | ≥1 опубликованная выбранная policy; прежние сохраняются | Полные точные числовые пределы, calculation version/hash; значения из принятой policy, не guessed defaults | Изменение уже использованной версии; округлённые n/d. R003/022–025/031; S/N-примеры |
| SH10 `paper_controls` | 1 выбранный control paper среды; запуск разрешён/запрещён | Active policy своей среды, guard и причина отключения по P2; полная публикация | Missing policy не бизнес-отказ и не default enabled. R022/024/027/056 |
| SH11 `setup_reviews` | 0 до C05; новые immutable reviews; user allowed/rejected или guest rejected; valid/invalid normalization | Полный raw, исторический ownership/version, policy/guards; valid: все нормализованные поля и один F/q; invalid: **все** normalized NULL. Guest slot=not_applicable; user absent/present+generation | Technical failure как review; частично normalized; переписывание expiry/ошибок при replay. R004/008/024–027/030/043/064 |
| SH12 `q02_read_scopes` | 0 только в профиле без Q02; ≥1 для выбранной разрешённой области, допустим scope с0 members | Venue/version/source_ref; состав и новая версия публикуются вместе, no-op не повышает; A→B→A новая revision | Missing обязательного scope как пустой каталог; смена venue/сброс версии. R001/005/009/020/022/062/066/068/069; AS17/QSC |
| SH13 `q02_read_scope_sources` | N≥0 членов **существующего** scope; 0 — доказанный пустой разрешённый набор | Уникальная пара scope/source своей venue. Удаление только membership; повторное включение с новым ID+guard | Удаление source/history вместе с membership; cross-venue; отсутствие parent как пустота. R001/007/009/020/022/068; AS17/QSC |

### 3.3. Сессия и виртуальный учёт — P3

| № / таблица shadow | Варианты, допустимое отсутствие | Обязательный комплект, изменение и сохранение | Запрещённый/неизвестный вариант; трассировка |
| --- | --- | --- | --- |
| SH14 `user_session_slots` | 0=absent; 1 present_free с NULL pointer; 1 occupied с current session. Scope user/paper без venue | Generation1 при первом сохранении; только смена pointer повышает. C05 не создаёт. C06 business rejection после резервирования может оставить free generation1+receipt | Unknown как free; logout/EMPTY/expiry освобождают slot; удаление/сброс generation. R028/029/037/062 |
| SH15 `paper_sessions` | 0 до C06;1 выбранная active/copying_not_connected | Полный замкнутый C06 комплект §5; source draft/review уникальны по всей истории; текущие settings/snapshot/ledger/funding обязательны | Частичный start; произвольные pause/stop/reset в BASE первого среза. Такие будущие lifecycle только SEM/зависимость. R016/028–032/034–037/042/048 |
| SH16 `settings_revisions` | 0 без session;1 начальная sequence1 с previous=NULL, fixed XOR percent | Полный валидный набор из review/policy, точные B/P/D; выбранный receipt/actor/session. История immutable; будущие версии требуют своего принятого writer | Одновременно F и q; неактивный raw как effective; пустой current. R003/025/031/034/035/037/042/064 |
| SH17 `funding_flows` | 0 без C06; ровно1 initial_paper_funding на выбранную session | Amount=B в virtual_USD; взаимные ссылки journal/session/receipt, полный ledger | Второе initial; повторное прибавление flow к уже рассчитанным проводкам. R003/032/033/037/042 |
| SH18 `journals` | 0 без C06; ровно1 initial journal sequence1 | Свой funding/receipt/unit; ровно2 entries до commit; current_ledger_sequence считает journals, не entries | Parent без детей/лишний child, несвой funding. R032–034/037/042 |
| SH19 `journal_entries` | 0 без journal; ровно2 на initial journal | Line1 paper_cash +B, line2 virtual_funding_source −B; same session/unit; нормализованный баланс0, immutable | Одна/три строки, неверный знак/счёт, ноль initial, несовпадающий B. R003/033/034/037 |
| SH20 `session_snapshots` | 0 без session;1 initial EMPTY; последующие только отдельная PUB-спецификация, история сохраняется | Free=equity=B; reserved/positionCost/positionValue/tradingResult=0/1, trade/position/order counts0; synthetic/no_trade_data; settings/ledger своей session | Missing current как EMPTY, пересчёт/ремонт на GET, смешивание версий. R003/008/034/035/037/046/048/049/064; I/PUB/F |

### 3.4. Команды, аудит и доставка — P4

| № / таблица shadow | Варианты, допустимое отсутствие | Обязательный комплект, изменение и сохранение | Запрещённый/неизвестный вариант; трассировка |
| --- | --- | --- | --- |
| SH21 `command_keys` | 0 до финализации либо доказанного полного rollback;1 на scoped C04/C06 key | C04 user/guest до draft, C06 user; один immutable payload/scope и reciprocal receipt. Exact replay не вставка | Committed pending без результата; перенос guest key после claim; техническая неопределённость как разрешение нового key. R038–041/044/045/062/067 |
| SH22 `command_receipts` | Ровно1 на key; succeeded/rejected; C04 created/updated/unchanged, C06 start/refusal | Исходные IDs/версии/ошибки/время неизменны после следующих правок/claim. У C06 success полный source/result tuple; у refusal нет созданной session | Исторический outcome из текущих данных; HTTP GET200 как succeeded; Auth/claim в обычном CMD. R017–019/037/039/041–045/064/067 |
| SH23 `command_receipt_details` | Ровно1 обязательная detail на новый receipt; нет автоматического удаления старой | `reason_data` объект отдельно от API reasonDetails-списка; C04 исходные fieldErrors/response, без пересчёта; format родителя | NULL/[] вместо нужного объекта, текущие requestId/navigation/restrictedGroups как immutable outcome. R008/017–019/041/043/063/064/067 |
| SH24 `draft_claim_receipts` | 0 до успешного claim; ровно1 на переданный draft | Полный old guest→new user ownership/current pointer/audit; AC19/40 committed совпадают. Старый guest ID/key не переносится | Второй receipt, orphan claimed ownership, отсутствующий receipt как доказанный no-effect. R014/044/046/070; AS13–16 |
| SH25 `audit_events` | 0 без соответствующего действия; typed start/claim/Q06 session/Q06 absence | Start/claim свои source refs; Q06 session требует session+snapshot; absence требует target user/slot observation, **NULL** session/snapshot, одно evidence. История immutable | Подмена session audit видом absence; отсутствие обязательного аудита как успешный Q06. R008/037/042/046–048/068; AS24/NA |
| SH26 `audit_authorizations` |0 у start/claim без staff-выдачи; достаточный комплект Q06 по разрешённым группам; absence ровно1 | Целый grant+assignment version того же staff; closed group не получает фиктивную строку/пустые данные | Части разных grants, evidence закрытой группе, отсутствие обязательного child. R047/048/055/056; AS24/NA |
| SH27 `outbox_events` | 0 без события;1 start event на C06; pending/processing/retry_wait/processed/needs_review | Исходный payload/session/snapshot immutable; delivery-поля по H04. Lease loss/timeout не доказательство локального consumer effect | Повтор funding/актуализация payload из новой snapshot; processed без consumer proof. R008/037/042/049–052/067/068 |
| SH28 `consumer_event_receipts` | 0 до локального consumer effect;1 на consumer/event после него | Эффект и receipt в одной T; duplicate возвращает прежний факт, счётчик не растёт | Receipt отдельно от эффекта, удаления dedup ради retry. R052/067/068; A14/A20/F |

### 3.5. Сотрудники и полный вход — P4 + AC

| № / таблица shadow | Варианты, допустимое отсутствие | Обязательный комплект, изменение и сохранение | Запрещённый/неизвестный вариант; трассировка |
| --- | --- | --- | --- |
| SH29 `staff_principals` | Полный staff-набор:2, владелец 1/владелец 2; status=active/blocked по реестру | Личные identities/security/assignments; authorization guard; ограниченный recovery не третий principal | Один человек/credential за двух, user как staff. R053/054/056/058/060/069; AS18/20–22 |
| SH30 `staff_auth_identities` | Своя подтверждённая staff identity; status=active/revoked | Realm staff, immutable provider/subject→principal; version/guard при изменении | Переназначение subject, личный user-email как staff grant. R053/056/058/069 |
| SH31 `staff_assignments` | Status=active/revoked;0 допустимо как отсутствие права, не как Owner по умолчанию | Current grant set/version и principal guard меняются атомарно; прежние наборы сохраняются | role=owner без полного опубликованного набора; смешение версий. R047/054–056/069; AS21/24 |
| SH32 `staff_assignment_grants` | N конкретных grants каждого набора; для двух владельцев равноправные полные наборы | Исторические строки immutable; цельная комбинация action/screen/group/mode/scope/venue; новые reset/absence права только явной публикацией | Неизвестное G=0, соединение половин разрешения, all/one неправильного варианта. R047/048/054–056/069 |
| SH33 `login_policy_versions` | Минимум1 user+1 staff policy для полного набора; история | Принятые absolute/idle лимиты и realm; immutable использованная версия | Новая policy меняет сроки прежнего login. R057–059; AS08/10/20 |
| SH34 `login_policy_controls` | По1 на используемый realm; собственная active policy | Guard/pointer публикации; отсутствие обязательной policy — неисправность | Default policy при missing; чужой realm. R056/057 |
| SH35 `auth_sessions` | 0 до full completion; user/staff login, действующий/expired/revoked вычисляются по полям | Full completion требует AC03/05/07/16/38 и guards; staff current slot, отзыв старого. Target logout и authorizing login могут быть разными | Restricted context как login; второй login на replay; window erase как отзыв; неизвестная запись как logout success. R046/056–060/070; AS08–11/20/23 |
| SH36 `staff_login_slots` | 0 до первого полного staff login;1 на staff: current pointer либо NULL; исторический pointer на отозванный login не даёт доступа | Новый полный вход+отзыв прежнего+смена slot атомарны; history login сохраняется | Два текущих рабочих входа; slot чужого staff/realm; подмена logout target новым login. R048/056/060/070; AS20 |

## 4. Auth: 42 таблицы

Все имена ниже принадлежат `auth_control`. Поля/enum из AC-карты; у каждого обязательны среда/PK и полная вариантная проверка N/L/U/F/D/W/T. Время действия и возможность replay не выводятся из одного state. Точные action/result/audit/writer-детали D02 не считаются принятыми только потому, что для них предусмотрены строки. HR-ссылки читаются вместе с актуализирующим §10 истории.

### 4.1. Контексты и результаты

| AC / таблица | Состояния и допустимый ноль | Полнота, история и запрещённое состояние | AS / HR / открытый стык |
| --- | --- | --- | --- |
| AC01 `environment_gates` |1 на выбранную среду: closed/open; первоначальный closed без checkpoint допустим | Open только с внешней свежестью/допуском; epoch монотонна. Last run NULL только до первой сверки; missing не open. Fence не автоматический отзыв всех независимых login | AS15/16/25/26; HR01/17; BDR07 |
| AC02 `principal_security` |1 обязательный security выбранного principal: active/transition/blocked | XOR user/staff; transition→своя AC04; user current factor/MFA requirement, staff stable RP/handle. NULL factor при enrollment_required не email-only. Guard Shadow меняется вместе | AS05/08/20/21; HR01/06; BDR08 |
| AC03 `contexts` |0 до bootstrap своей процедуры; guest, user_auth/mfa/mfa_result/logout/user_claim, staff_auth/registration/recovery/recovery_codes/staff_logout по §4 AC | По kind обязательные source/authorization/target/subject/challenge; до подтверждения допустим NULL subject; исторические source/expiry не переназначаются. Guest: явный подтверждённый refresh того же ID/proof → max прежнего expiry и refresh+7d; C04 created/updated → max прежнего expiry и draft expiry. GET/unchanged/replay не продлевают; revoked/execution_closed не DELETE | AS01/02/08/11–16/18–22; HR02/09; BDR02/03 |
| AC04 `operations` |0 до admission; admitted/dispatched/uncertain/resolved/closed_without_dispatch | Ровно один исходный namespace; unique scoped action/client ID; resolved↔одна AC05; closed_without_dispatch только с доказательством. Seal в AC39. Case execution фиксирует версию/точные approvals | AS03/04/08/11/18–22; HR03/14; BDR02/03/08 |
| AC05 `operation_results` |0 у unresolved **либо** доказанной closed_without_dispatch без финального result;1 окончательный immutable result | Typed refs/NULL по kind/action; полный login требует context/login/completed_at и весь комплект. Result_context не full login, logout target не новый login; current HTTP/navigation отдельно. Unknown не final rejection | AS03/04/08/11/18–22/27; HR03/09; BDR01–04/08 |
| AC06 `proof_verifiers` |По1 на context/purpose; digest существует либо законно erased+marker | История context/key/format остаётся; erased не новый proof/допуск. Guest context proof не draft-bound ownership proof и не AC38 | AS01/13/26; HR02; HE04/05; BDR06 |
| AC07 `secret_material` |По1 typed owner/purpose; ciphertext существует либо NULL+erased_at | **Nonce/key/format остаются** после erase, nonce не переиспользуется; tag внутри cipher. Login cookie, factor reveal, codes reveal, email_delivery различны. Cipher срока не продлевает; отсутствие обязательного material не законный erase | AS08–10/19/26; HR04 §10/09/13; BDR05 |
| AC08 `secret_comparisons` |По1 operation/purpose, если исходное намерение сравнивает sensitive bytes; erased tag с marker только после закрытия путей | Raw-sensitive HMAC отдельно от canonical nonsecret payload; неизвестный key/tag не равенство. GET по самостоятельному допуску не требует выдумать POST equivalence | AS03/04/26; HR03; HE04; BDR06 |

### 4.2. Challenge, лимиты и продолжение

| AC / таблица | Состояния и допустимый ноль | Полнота, история и запрещённое состояние | AS / HR / открытый стык |
| --- | --- | --- | --- |
| AC09 `challenges` |0 до выдачи; email/totp/webauthn_get/webauthn_create; active/replaced/consumed; expiry вычисляется | Свой context/purpose/issuer; replaced→свой replacement, consumed→operation/time; current refs целы. Email code/link одно потребление. Provider-owned proof не получает фиктивный local digest | AS03/05/06/08/18–22; HR05; BDR01 |
| AC10 `factor_versions` |0 до enrollment; prepared/active/disabled/revoked | Свой user/version/provider/profile; prepared не login; один active с AC02; provider seed не локальная колонка, временный reveal отдельно | AS05/21; HR06; BDR08 |
| AC11 `used_totp_steps` |0 до расхода; N всех совпавших допустимых steps после успешной операции | Unique factor/step; весь совпавший набор атомарно с результатом. Уже использованный среди совпавших запрещает частичный новый расход; expiry не удаляет историю | AS05/26; HR06; BR08 |
| AC12 `failure_counters` |Один на используемый scope/purpose; series≥0, pause либо NULL по принятому правилу | Последний финализированный outcome; exact replay не увеличивает; resend не новая email-family серия. Transport error не неверный код | AS03/06; HR07; BDR01 |
| AC13 `quota_scopes` |N полного набора обязательных scopes запроса;0 только вне его применимости | Typed subject/purpose/digest/policy; published limit/window>0; смена key не обнуляет активное окно; guard всех затронутых parents | AS07; HR07; полный route-profile D02 |
| AC14 `quota_admissions` |0 до admission; по1 на каждый требуемый scope/token допущенного HTTP | Все scopes или ни одного; token серверный, не operation ID. Новое HTTP replay может дать новые admissions, внутренний attempt не вторую quota. Старые вне окна сохраняются | AS03/07; HR07; D02 |
| AC15 `continuation_bindings` |0 до выбора;1 default с NULL draft либо setup_draft с реальным draft | Один immutable binding auth context; target не меняется текущим nextAction. Нет binding только по доверенному чтению, не ошибке БД | AS12; HR08 |
| AC16 `cookie_recovery_windows` |0 до full login;1 на login, open/closed выводятся из полей и deadline | Source AC05/03/login/AC38/AC07 совпадает; deadline неизменен. Закрытие с причиной и разрешённым erase; Q01/recovery/eraser один window guard. Нет reopen/новой cookie | AS08–10/26; HR09/04; HE01–03 |

### 4.3. Каталог и передача draft

| AC / таблица | Состояния и допустимый ноль | Полнота, история и запрещённое состояние | AS / HR / открытый стык |
| --- | --- | --- | --- |
| AC17 `catalog_bindings` |0 у неразрешённой комбинации realm/venue;1 на разрешённую user/guest+venue | Current AC18 обязателен своего binding/realm/venue; разрешены разные profiles, не guessed «все всем». Missing обязательной версии не пустой каталог | AS17; HR08; MAP02/03 |
| AC18 `catalog_binding_versions` |≥1 на binding; immutable версии, одна current | Свой scope/venue, trusted publication proof; A→B→A новая scopeRevision даже при прежнем наборе. История не current authority | AS17; HR08; MAP02/03 |
| AC19 `claim_admissions` |0 у consent без допуска;1 на consent: admitted/uncertain/committed/closed_without_effect | Unique consent, не unique draft; actor/login/ownership/epoch/permit неизменны. Committed↔matching Shadow receipt+AC40; closure требует доказанных исполнителей/attempts. Unknown запрещает новый обходящий consent | AS13–16; HR10 §10; MAP04–06 |

### 4.4. Staff, reset и recovery

| AC / таблица | Состояния и допустимый ноль | Полнота, история и запрещённое состояние | AS / HR / открытый стык |
| --- | --- | --- | --- |
| AC20 `webauthn_credentials` |0 до регистрации; limited/active/revoked | Личный staff/RP/handle/public key и source operation/case; несколько ключей того же staff имеют один handle. Limited только свой recovery, не ordinary grant; counter0/synced не обход challenge | AS18/20/22; HR11; BDR02/03 |
| AC21 `bootstrap_manifests` |0 до церемонии;1 на выбранную версию trusted manifest | Ровно2 AC22 разных заранее проверенных staff; signature/source/grants digest; история после expiry | AS18/26; HR12; HE07 |
| AC22 `bootstrap_handles` |Ровно2 на manifest; unused/consumed, expired/erased по полям | Один staff на handle, consuming operation/result сохраняются; digest erase только разрешённым путём с marker, без нового bootstrap. Сам expiry не DELETE | AS18/26; HR12; BDR05/06; writer для отдельных erase-вариантов ещё D02 |
| AC23 `recovery_code_sets` |0 до выдачи; по1 активному набору выбранного staff плюс revoked/superseded история | Version/handle/source operation; выдача нового+отзыв старого+10 children+result атомарно. Reveal deadline отдельно от действительности code verifiers | AS19/22/26; HR13 |
| AC24 `recovery_codes` |Ровно10 ordinal1…10 на каждый set; unused/consumed, erased по полям | Unique set/ordinal; consumption+limited context/result одной T; replay не второй расход. Cipher reveal erase не стирает ещё пригодные code verifiers | AS19/22/26; HR13; BDR05/06 |
| AC25 `security_cases` |0 до принятой точки создания; mfa_reset/single/pair; collecting/authorized/executing/completed/rejected | Current AC26 своего case; reset target/request; selected execution links. До case его refs законно NULL в исходном ограниченном процессе; после создания полный bundle | AS21/22; HR14; BDR02/03 |
| AC26 `security_case_versions` |≥1 на существующий case; current и прежние | Target factor/evidence/proposal/expires/required approvals; изменение предмета — новая версия, не обновление старой. Expiry не откат уже unknown execute | AS21/22; HR14; BDR02/04 |
| AC27 `security_case_participants` |Полный набор конкретной версии: reset два approver; single subject+другой approver; pair два разных человека с ролями | Typed recovery context/new credential каждого участника и XOR по виду; число людей не автоматически число role-строк. Точная role-развёртка D02 | AS21/22; HR14; BDR04 |
| AC28 `security_case_approvals` |0 до approval; исторические и новые свежие approvals одной версии допустимы | Unique operation/challenge; неизменяемые participant/credential/version/time; execution AC04 хранит точные выбранные IDs. Повтор свежего approval не перезаписывает старое | AS21/22/26; HR14 §10; UST01/02; BDR04 |
| AC29 `verification_evidence` |0 без reset evidence;1 выбранная версия доказательства своего user | Независимый канал проверен до обращения; human verifier/source/digest/context. FK/hash не доказывают правдивость/удаление внешнего документа | AS21; HR14; D03 внешняя предпосылка |
| AC30 `reset_requests` |0 до request; requested/under_review/completed/rejected | Свой email-proven restricted context/client ID; создание с исходной operation/result; completed со своим case/result. Request не полное право reset | AS21; HR14; BDR02 |

### 4.5. Activity, аудит, witness и уведомления

| AC / таблица | Состояния и допустимый ноль | Полнота, история и запрещённое состояние | AS / HR / открытый стык |
| --- | --- | --- | --- |
| AC31 `activity_tickets` |0 до выдачи; unused/consumed, expiry вычисляется | Login+route+target none/draft/session; цель проверена при выдаче/consume; один consume и разрешённый idle touch атомарны. Q01 не touch | AS23; HR15; HE09 |
| AC32 `auth_audit_events` |N обязательных typed событий пути,0 только при доказанной неприменимости | Actor user/staff/system по варианту; свои operation/result/target/case/run; обязательные children. Отдельно от Shadow Q06; safe_details не secret dump | AS16/21/24/26/27; HR16; BDR04/05/08 |
| AC33 `auth_audit_evidence` |N достаточных целых grants по событию; количество определяется вариантом | Assignment/grant/version/actor и exact approval. System/limited path не получает фиктивный ordinary grant; отсутствие AC33 не освобождает от других proof chains | AS21/22/24; HR16/14; BDR04; candidate 3/1/0 ещё не принятый факт |
| AC34 `witness_batches` |N защищённых изменений; intent_registered/local_committed/confirmed/no_effect_proven/uncertain | External intent и полный declared closure; local commit с AC35, ack отдельно. Ack loss не меняет финальный business outcome; gate checkpoint не новый на каждый batch | AS15/25/26; HR17; BDR05 |
| AC35 `witness_changes` |N=declared_change_count для local-committed batch, N>0 | Ровно один typed root на строку, полный набор children в digest; count roots не count физстрок. Нет orphan/пустого parent; key publication — внешний signed ref | AS25/26/28; HR17; UST06; BDR05 |
| AC36 `notification_jobs` |0 без обязательного уведомления; по1 source result/purpose/recipient; pending/dispatching/sent/uncertain/failed | XOR recipient, template/source security result; не OTP и не Shadow observer. Сбой письма не повторяет reset/factor и не откатывает результат | AS27; HR18; BDR08 |
| AC37 `notification_attempts` |0 до dispatch; последовательные attempts: pending/accepted/not_sent_proven/uncertain | Seal/performer/provider proof; следующий только по допустимому доказанному основанию. Timeout/истечение не not_sent; H04 retries не переносятся автоматически | AS27; HR18; HE10 |

### 4.6. Принятые дополнения U01

| AC / таблица | Состояния и допустимый ноль | Полнота, история и запрещённое состояние | AS / HR / открытый стык |
| --- | --- | --- | --- |
| AC38 `login_cookie_credentials` |0 до full login; ровно1 постоянный verifier на login/source result | Source result/context/realm/principal целы; AC16/07 closure не отзывает AC38. Сохраняется допустимое историческое logout proof; current доступ отдельно | AS08–11/20/26 §11; HR09 §10; UST04 |
| AC39 `operation_dispatches` |0 у локального WebAuthn пути/до внешнего seal; sealed/uncertain/confirmed_not_sent/confirmed_effect | Свой operation+ordinal/executor/permit/epoch; seal до сети. Новый ordinal только после доказанного not_sent прежних и живого исходного бюджета; нет lease takeover | AS04/27 §11; HR03/18 §10; BR08/BDR08 |
| AC40 `claim_attempts` |0 до admission; сохранённый AC19 требует исходный attempt1 в той же Admission-T; attempt_no1…3: admitted/committed/proved_rollback/unknown | Тот же executor/epoch/budget; committed с matching receipt/AC19 в одной T; proved rollback после доказанного полного отката. Retry только serialization/deadlock в остатке прежних5s | AS14–16 §11; HR10 §10; UST03 |
| AC41 `reconciliation_runs` |0 до первой сверки; claim_unknown/environment_restore; fenced/draining/verified/reopened/blocked | Claim требует draft, restore NULL; run+closed gate новой epoch атомарны. Полный inventory всех исполнителей, drain, независимый witness и authorization; unknown не verified | AS15/16/25/26 §11; HR01/10/17 §10; BDR07 |
| AC42 `reconciliation_items` |N полного inventory адресуемых admission/dispatch targets; delayed handler без AC19 не получает фиктивный AC19/AC42 | Один target claim admission XOR Auth dispatch; committed/not_committed_and_fenced/unresolved; immutable evidence. Claim committed требует receipt; Auth effect не всегда уже local result, безопасная финализация обязательна до reopen | AS04/15/16/25/26 §11; HR10/17 §10; UST05/08 |

## 5. Комплекты и количественные опоры будущих срезов

Следующие дельты — **предметная часть**, не готовые totals78. Для каждого пути добавляется полное сопровождение §5.2 и сохраняются прежние строки всех остальных таблиц. Нет произведения всех enum между собой: совместимость вариантов задают constraints/контракт конкретного пути.

### 5.1. Замкнутые предметные комплекты

| Срез | Доказуемая из проекта дельта и обязательная связность | Что нельзя заключать |
| --- | --- | --- |
| Guest до draft — AS01 | Собственный AC03 guest+AC06 по профилю; draft/ownership/CMD выбранного нового guest=0 | Не все таблицы БД пусты: gate/quota/witness/config отдельно |
| C04 create/change/no-op/replay — AS02 | Create +1 draft/+1 ownership/+1 key/+1 receipt/+1 detail. Changed existing: три command-строки+изменение version/pointer/TTL. New unchanged: три command-строки, draft неизменен. Exact replay:0 новых предметных CMD/draft строк | Replay HTTP не гарантирует0 AC14; historical guest receipt после claim не переносится; fieldErrors не пересчитываются |
| C05 | +1 immutable review при сохранённой предметной проверке;0 CMD/slot/session/финансов. Ошибка формы/доступа/техническая ошибка по своему контракту | C05 не получает выдуманный command key/receipt; существующий review не «освежается» повтором |
| C06 success — BASE-START | +1 session/settings/funding/journal/snapshot/key/receipt/detail/start audit/outbox; **+2 entries**; slot+1 при absent или UPDATE своего present; draft used UPDATE. Все reciprocal links сходятся | Нельзя записать часть и потом «достроить»; нет второго funding от повтора; replay сохраняет исходный snapshot результата |
| C06 refusal | +1 key/receipt/detail только при окончательном сохраняемом отказе;0 новых session/settings/funding/journal/entries/snapshot/start audit/outbox; новый free slot возможен только по достигнутому резервированию P3 | Unknown commit не этот срез; отсутствие ответа не право нового key |
| Claim — AS13/14 | Если был guest ownership: +1 user ownership/+1 Shadow claim receipt/+1 claim audit, current pointer UPDATE; AC19=1 на consent, один committed AC40. Предыдущий guest ownership/receipt C04 сохраняются | Не новый AC05/CMD/Q05 outcome; нет C06/финансов. Consent без admission законно AC19/40=0 (AS16), это не доказанный откат уже допущенного исполнения |
| Full completion — AS08 | +1 Shadow login/+1 AC05/+1 AC38/+1 AC16/+1 AC07 login-cookie; source AC03/04 связаны и завершены. Staff: slot create/update и отзыв прежнего login в той же T | Ограниченный context/result не требует ложного login; поздний подтверждённый effect U03 может законно не создать этот комплект |
| Q01/window close — AS09/10 | В существующих AC16/07 разрешённое закрытие/erase; count не падает; AC38/login/result сохраняются; первый confirmation по контракту | Нет нового login, продления idle/recovery deadline; cipher ещё есть после deadline ≠ можно выдать |
| Q02 — AS17 | Две venue; выбранные bindings/версии/scopes/members фиксируются явно. Исторический пример AS17:2 bindings,2→4 binding versions,3 scopes/2 memberships в его срезе | Это не универсальный total для user+guest всех комбинаций; отсутствие неразрешённого binding не повреждение обязательного scope |
| Q06 session / absence — AS24, NA | Session: +1 Shadow audit и N evidence только разрешённых групп. Absence: +1 audit/+1 evidence, target user+slot observation, session/snapshot refs NULL | Auth audit не заменяет Q06; restricted group не empty/zero; READ-FAULT не законный absence |
| Bootstrap — AS18 | Один AC21+ровно2 личных AC22; staff родители/identity/security/полномочия перечислены отдельно | Два handle не доказывают двух людей; bootstrap не выдаёт два полных login автоматически |
| Codes — AS19 | На каждую выдачу +1 AC23/+10 AC24, свои result/cipher; прежний set отзывается без удаления. Два последовательных набора дают20 исторических code rows | Erase reveal не удаляет ещё действующие verifiers; consumption одного code не полный login |
| Reset / recovery — AS21/22 | Полные AC25/26/27/28 с личными credentials/challenges и exact выбранными approvals. Новое свежее approval той же версии отдельная AC28. Набор final audit по D02-дельте ещё зависим | Число участников не число role rows/AC33; 0 обычных grants у limited pair не отсутствие доказательств |
| Fence/restore — AS15/16/25/26 | AC01 закрыт в новой epoch + AC41; AC42 перечисляет все существующие admission/dispatch targets. Полный внешний inventory/drain включает также handlers без AC19: для них consent closure+audit, без фиктивных AC19/42. History/attempts/dispatches не удаляются | Число локально найденных dispatches не полнота исполнителей; unresolved не verified; старый backup не новая authority |
| Notification — AS27 | Один job по source result/purpose/recipient и отдельная попытка; source result/factor остаются прежними | Lost send reply не not_sent и не новый reset; delivery counts не H04 Shadow observer |

Для S01–S04 числовых примеров: две площадки × fixed/percent — **четыре независимые копии**, а не четыре активных session одного user. Для принятого примера B=200/1, F=20/1 либо q=300, p=1000,d=1500 сохраняются P=20/1,D=30/1. Другие бюджеты/границы берутся из S/N/K исходного документа, не заменяются200. Начальная сумма funding равна именно выбранному B; каждая денежная величина нормализована без float/округления. Принятый расчёт календарного deadline с IANA/tzdb хранится, а не выводится из нового времени чтения.

### 5.2. Сопровождение, которое запрещено потерять в totals

| Сопровождение | Как включать в каждую строку будущего manifest |
| --- | --- |
| Полные ancestors | Перечислить IDs всех user/staff/identity/policy/security/context/scope родителей; сохранить связанные предыдущие версии. Ссылка на существующую BASE допустима только с конкретным перечнем/отпечатком, не «всё остальное0» |
| Quota | В каждом разрешённом HTTP — конкретные AC13 scopes и AC14 tokens. Отдельно показать exact replay HTTP и внутренний повтор той же admission. Число обязательных scopes до закрытия route-profile — зависимость |
| Audit | Перечислить каждый Shadow/AC32 event и требуемые AC33/Shadow authorization children с actors/grants. Event одного вида не доказательство другого; pair proof chains не заменяются счётчиком AC33 |
| Witness | На каждый защищённый переход — конкретный batch, declared roots и полная closure children. `declared_change_count` сверяется с roots, а отдельно — физические counts. Ack/drain/evidence исключения требуют закрытого D02 списка, не самовольного0 |
| Исполнители и попытки | Внешние AC39/37 и внутренние DB attempts AC40 учитываются отдельно: свои performer/permit/outcome и доказательства внешнего исхода либо полного локального rollback. Нет «timeout значит не было»; локальный WebAuthn/claim не получают фиктивный внешний dispatch |
| History/erase | Поле стерто, строка/nonce/метаданные/refs сохранены; старые keys/backup/WAL отслеживаются вне78. Нет нового срока удаления строк или ключей |
| Read effects | Q01 window closure, Q06 audit, разрешённая activity и quota считаются по своему пути. GET result может читать исходный отказ с HTTP200; response requestId/nextAction/restrictedGroups не переписывают result |

## 6. Трассировка и отрицательные варианты

Точные предметные R для36 перечислены в §3; [реестр ограничений §6](database-constraint-register.md) содержит полный обратный указатель **каждого A01–A112**. Этот перечень не обещает доказать UI/провайдера/эксплуатацию одним состоянием БД. Следующие группы добавляют адресные ссылки, а не заменяют полный R→A указатель.

| Группа | R и A | Сценарии / независимое ожидание |
| --- | --- | --- |
| User/guest/claim | R010–019/038–045/058/069/070; A01/02/15/21–27/35/54/56/98/103/107 | AS01–04/11–16, C04-E, F/CC из карт сбоев/конкуренции; исторический scope/исход сохраняются |
| Catalog/review | R020–027/062/066/069/071; A03/07/08/16/23/28/33/36/39/47/100/102/103/110 | AS17, QCAT/QSC, S/N/K; текущее и историческое состояние различимы |
| Session/ledger | R028–037/042; A04/11–13/17–19/27/31/32/39/40 | BASE-READY/START/V3, I01–I22, F01–F24; все части C06 вместе либо отсутствуют по доказанному откату |
| Q06/staff | R046–048/053–060/069/071; A05/23–25/30/100/104/107 | AS20–24, NA01–NA32; отсутствие/закрытая группа/повреждение разные |
| Delivery/history/formats | R049–052/064–068; A14/20/34/95/99/110–112 | F/E-план, AS25–28, HE; отсутствие повторного эффекта не удалением истории |
| AC01–08 | R001/002/005/007/010/011/058/066/068–070; A01/21/23/25/100/107 | MAP01/04–08; AS01–04/08/11/13–16/26; HR01–04 |
| AC09–16 | R006/008/058/059/062/070; A21/22/25/29/39/47/107 | MAP01/07/08; AS03/05–12/26; HR03–09 |
| AC17–19 | R005/014/022/044/062/066/069/070; A23/26/33/35/100/103/107/110 | MAP02–06; AS13–17; HR08/10 |
| AC20–30 | R046–048/054–060/069/070; A24/30/100/104/107 | MAP01/05/07/08, DA12; AS18–22/26; HR11–14 |
| AC31–37 | R007/046/059/062/066–071; A25/33/34/100/107/111 | MAP01/04–08; AS23–28; HR15–18 |
| AC38 | R007/058/059/066/070; A21/25/29/30/107 | AS08–11/20/26 §11, ASC04–09/UST04; HR09 §10 |
| AC39 | R007/058/062/066/070; A21/25/100/107 | AS04 §11, ASC01–03/18/UST05; HR03 §10 |
| AC40 | R014/044/062/066/070; A23/26/35/100/103/107 | AS14–16 §11, ASC13–15/UST03; HR10 §10 |
| AC41 | R062/066/069/070; A34/100/107/111 | AS15/16/25/26 §11, ASC14/16/17/UST08; HR01/17 §10 |
| AC42 | R007/044/066/070; A25/35/100/107/111 | AS04/15/16/25/26 §11, ASC16/18/UST05/08; HR10/17 §10 |

Для **каждой** строки §§3–4 применяются адресные отрицательные дочерние срезы AS28/I/NEG/BAD: отсутствует обязательный parent/child; лишний child; чужая environment/subject/realm/venue/purpose; нарушен XOR/условный NULL; дублируется scoped key; переписан immutable факт; возвращена прежняя версия/доступ после restore. Отрицательный срез выбирает только применимые ограничения конкретной таблицы — например,0 members scope законно,0 entries initial journal незаконно. Одно изменение на дочернюю копию; отказ по более ранней permissions/форме не доказательство целевого D/F/W. Положительный законный erase обязательно сопоставляется с повреждением marker/cipher; законное unresolved — с повреждённой обязательной связью.

Отдельно нужны обе очередности одновременных C04/claim/C06, два ключа/две площадки на одном slot, Q01/recovery/eraser, revoke/approve/execute, binding publication/Q02, fence/задержанный исполнитель. Порядок G0…G6 и временный draft guard — из принятой AC-карты; документ не проверяет implicit FK/index locks или отсутствие deadlock. Unknown после потери ответа не превращается в rollback ради удобного expected count.

## 7. Реестр зависимостей и передача бэкенду

| Зависимость | Что уже определено | Что остаётся до полностью конкретного исполняемого manifest |
| --- | --- | --- |
| D02 / BDR01 | Challenge имеет typed состояние, consumption/counters/history раздельны | По каждому route/kind точные expiry HTTP/reason и отсутствие/наличие сохранённого результата; не переносить один общий expiry-отказ на старый TOTP |
| D02 / BDR02–03 | Исходный namespace immutable; pre-case отсутствие законно; созданный case требует полноты | Точные action/result refs/NULL, before-case→single комплект, исторический K/P resolver, включая lookup AC04 при AC05=0 |
| D02 / BDR04 | Exact approvals и два разных человека обязательны; обычный grant не выдумывается для limited pair | Final audit/evidence variants с точным числом role-строк и AC33. Предложенные бэкендом reset3/single1/pair0 остаются candidate до повторной вычитки/надлежащего принятия; pair0 ≠ proof0 |
| D02 / BDR05 | Полный witness обязателен, nonce сохраняется; expiry не удаляет историю | Закрытые writer/root/closure/служебные исключения, в том числе standalone erase и unconsumed bootstrap handle. Отсутствие выбранного erase-writer не разрешает обходной UPDATE/новый root |
| D02 / BDR06 | Раздельные key domains/raw-sensitive comparisons/derived context proof | Точные normative bytes/encoding/length prefixes и профили; placeholders в manifest не криптографические свидетельства |
| D02 / BDR07 | AC41 purpose только claim_unknown/environment_restore | Не активировать security_incident как writer/decoder без принятого run-протокола. Новый purpose не добавляется этим перечнем |
| D02 / BDR08 | Подтверждённый поздний внешний эффект U03 не откатывается из-за запрета login | Полный factor/security/audit/notification комплект late reenroll и ordinary variants; не снимать независимый block, не повторять отзыв на replay |
| Полный transport/grants/config профиль | Scoped quota, отдельные reset/absence grants, обе площадки, selector/gate известны | Для каждого сценария перечислить все AC13/14, реальные ID/version разрешённых grant sets/политик/roots; неизвестные N не заменить0 |
| BR08 / D03 / M05 | Ожидания AS/MAP/DA/HE/E и ограничения сформулированы | Provider correlation и all-matching TOTP steps, selected components/версии/ключевые ACL, независимые evidence/отчёт/часы/restore. Никаких выполненных испытаний этим документом |
| Будущие lifecycle M02–M03 | SEM/PUB/NEG/BAD разграничены | Реальное физическое представление новых торговых/lifecycle состояний, если оно потребуется; запрещённые значения не становятся BASE первого сценария |
| Разрешение реализации | Разрешены документы и их публикация | Отдельное поручение на реализацию/SQL/миграции/создание БД/испытания; D04 сам его не выдаёт |

Во время подготовки получен [PR №212](https://github.com/denius89/polymarket-copy-trading/pull/212), HEAD `248b5b2315c0f21b977cc4e6abe92bea2eb7c338`, с подготовленными исправлениями BDR. Это **входящая candidate-дельта**, не часть проверенной основы данного перечня. Пересечение отражено в зависимостях выше; повторная адресная вычитка выполняется отдельно. Смена статуса замечания требует проверки конкретного изменения, не только сообщения об исправлении.

По прямому поручению пользователя от03.11.2026 чаты БД и бэкенда обмениваются заданиями/замечаниями напрямую. Техническое уточнение внутри принятого правила сверяется между чатами; реальное изменение принятой гарантии или новый выбор выносится владельцу с рекомендацией. Нужны адресные дельты к этому перечню, а не ручная передача сообщений пользователем и не повторное открытие C04.

## 8. Статус готовности документа

Выполнена документальная взаимная вычитка с чатом бэкенда. Уточнения MF01–MF04 сверены с принятой основой и отражены: явный guest refresh наряду с C04; законный AC05=0 при proved closed_without_dispatch; AC19+первый AC40 одной Admission-T; полный drain всех handlers отдельно от AC42 для существующих typed targets. Внешние dispatch и внутренние DB attempts разграничены. Это не повторная вычитка PR №212 и не испытание поведения.

- **Согласовано ранее:** каталог78, P01–P05/U01–U03, источники полей/связей/полноты, продуктовые правила и принятые финансовые ограничения.
- **Отражено здесь:** каждая из78 таблиц, допустимое отсутствие/состояние/комплект/история, количественные опоры, связи R/A/AC/AS/HR и границы отрицательных срезов.
- **Остаётся документально:** повторная сверка D02, окончательные варианты result/audit/witness/proof, конкретные profile-scoped totals и все обязательные значения будущего набора, паспорт D03.
- **Не проверено испытаниями:** constraints, транзакции, конкуренция, криптография, provider capability, длительности/лимиты, восстановление и поведение API. Нет созданной БД или исполняемых fixtures.

Перед будущей подготовкой набора необходим независимый просмотр78 строк: нет пропущенной таблицы; scoped0 имеет основание; каждый N раскрыт; все FK/обратная полнота замкнуты; каждый секрет только допустимого синтетического класса; каждый отрицательный вариант отделён от BASE; внешнее доказательство не заменено локальной строкой. До этого можно говорить «перечень полон», но нельзя «набор готов/испытан».
