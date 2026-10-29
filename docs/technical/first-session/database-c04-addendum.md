# Дополнение БД после пакета бэкенда — C04 и стыки H01–H06

29.10.2026 · Baseline main `3a1acea7bd087a955eb680735794cbf4ed1eddc1`, PR №169. Основания: [пакет бэкенда](backend-design.md), [DB-C04-01–10](backend-database-change-list.md), [контракты](backend-contracts.md), [реестры](backend-code-registry.md), [ADR-0065](../../decisions/0065_first_session_backend_contract.md). Исторические принятия [ADR-0064 §§30–33](../../decisions/0064_first_session_database_contract.md) сохраняются; первое дополнение принято в §34, результат и атомарность C04 — в §35 после PR №170.

**Блоки 1 и 2 приняты целиком пользователем, включая last_input_receipt_id. Блок 3 ниже — предложение для следующего согласования.** Принятое в бэкенде поведение C04 не пересогласовывается; конкретные принятые колонки и механизм полноты отделены от следующего предложения. Состав прикладных таблиц пока остаётся 34. Код, SQL, миграции, установка и развёртывание не начинаются; испытания не выполнены.

## 1. Принятый блок: постоянная область команды

### 1.1. Варианты command_keys

| Поле | Тип / обязательность | Принятое правило |
| --- | --- | --- |
| actor_realm | text, обязательно | user или guest; staff не исполнитель C04/C06 |
| actor_user_id | uuid, условно | Только user, обязательно в этом варианте; FK users своей environment |
| actor_guest_context_id | uuid, условно | Только guest, обязательно в этом варианте; постоянный серверный ID Auth-контекста до первого C04 |
| command_type | text, обязательно | C04 для user/guest; C06 только user |
| client_command_id | uuid, обязательно | UUID v4 клиента до отправки; не новый ключ при потере ответа |

Ровно один actor ID заполнен и соответствует realm. C06 с guest запрещён даже при существующем guest-контексте. Environment определяется сервером. ID контекста — ссылка, не bearer и не доказательство доступа; исходные секреты не попадают в command_keys/fingerprint/details.

Две отдельные условные уникальности:

- При actor_realm=user: environment + actor_realm + actor_user_id + command_type + client_command_id.
- При actor_realm=guest: environment + actor_realm + actor_guest_context_id + command_type + client_command_id.

Их условия вместе с обязательностью соответствующего ID закрывают NULL-лазейку. Не вводится общий unique по двум nullable actor IDs. Login/cookie/email/draftId не часть уникальности ключа; create/update — намерение C04 в fingerprint, не разные command_type/пространства повторов. Target/expectedVersion и сохраняемые поля также участвуют в fingerprint по backend-contracts; конкретные target-колонки завершаются следующими блоками.

Прежние canonical_request_version/hash_algorithm/request_hash и обязательная связь key↔окончательный receipt сохраняются. Принятый блок 2 добавляет отдельный результат C04; одних полей scope для полноты недостаточно. Точные типизированные FK завершаются блоком 3. Нет отдельного committed pending, удаления ключа по expiry draft или зависимости от login.

### 1.2. Гостевой контекст до draft и историческое владение

Auth-адаптер создаёт и устойчиво хранит постоянный guest context до первого C04. Потерянный ответ create восстанавливается через тот же подтверждённый context + clientCommandId без известного клиенту draftId. Фиктивный user и 35-я прикладная таблица для гостя не добавляются. Внутреннее служебное хранилище Auth и его конкретная физическая схема остаются H01; произвольный внешний FK на ещё не описанную Auth-таблицу не объявляется существующим ограничением Shadow.

В draft_ownerships добавляется guest_context_id uuid: обязателен только для guest, у user NULL. Guest-вариант одновременно содержит guest_context_id, guest_context_digest и guest_digest_version; owner_user_id NULL. User-вариант содержит owner_user_id, все три guest-поля NULL. Context ID неизменен, устанавливается сервером из доказанного Auth-контекста. Несколько drafts одного guest context не запрещены; unique только по context ID не вводится.

**Два уровня доказательства различаются:** подтверждение гостевого Auth-контекста до создания draft и доказательство доступа к конкретному draft после создания. Нельзя проверить digest, привязанный к ещё не существующему draft, вместо первого уровня. Принятый draft-bound digest guest-hmac-sha256-v1 и его версия сохраняются в прикладном ownership; исходный секрет не сохраняется. Подробный Auth-протокол первого уровня, выпуск/ротация и проверка proof должны быть описаны и испытаны отдельно; блок не придумывает второй криптографический алгоритм или готовую Auth-таблицу.

Для guest C04 историческое result ownership должно принадлежать исходному actor_guest_context_id, своей environment и своему draft. Точные составные result FK/target keys и проверки этого равенства — блок 3. Сама строка с ID контекста не доказывает полный допуск операции.

### 1.3. Claim и граница чтения результата

После claim ключ остаётся в исходной guest-области. Current user получает доступ к соответствующему результату через проверенную цепочку current user ownership → draft_claim_receipt → исходное guest ownership → C04 result/key. Переноса ключа в user realm, смены actor и повторного исполнения нет. Старый guest proof больше не открывает переданный draft или его результаты. Один draftId/clientCommandId/email недостаточен.

Закрытие доступа относится к переданному draft/его результатам; не вводится молчаливый отзыв остальных независимых drafts данного контекста. Для create без созданного draft нет цепочки claim — передача чужому user такого отказа по одному ключу не разрешается. Точный безопасный поиск/авторизация отказов и полного восстановления после claim завершаются блоками 2–3; это не обещание готового Q05.

### 1.4. Что уже отражено и что ещё не завершено

| Передача | Статус после блоков 1–2 |
| --- | --- |
| DB-C04-01 | Приняты и описаны XOR actor-варианты, context до draft и два уровня proof; Auth-компонент не реализован |
| DB-C04-02 | Приняты колонки actor и две scoped уникальности без nullable-лазейки |
| DB-C04-03 | Поведение fingerprint принято бэкендом; полное физическое размещение target/operation/expectedVersion ещё впереди |
| DB-C04-04–07 | Приняты и отражены C04 result-поля, details, last_input_receipt_id, атомарность и различение unchanged/replay/stale; target/FK завершаются блоком 3 |
| DB-C04-08 | Принят принцип post-claim чтения без переноса ключа; полный поиск/FK/отказы — блок 3 |
| DB-C04-09 | C06 инварианты сохранены; типизированные связи общего receipt ещё предстоит завершить |
| DB-C04-10 | Приняты отдельные поля исходного результата и сохранение core/details/исторического ownership без TTL по draft/login; точные связи — блок 3 |

M01 **частично отражён физически**, не закрыт целиком. A01–A112 не пройдены. Реестры, evidence Q06, параметры H04 и H05/H06 сверяются заключительным блоком; их принятие в бэкенде не отменяется.

## 2. Принятый блок: результат и атомарность C04

**Статус: принят целиком после PR №170, включая last_input_receipt_id; ADR-0064 §35.** Поведение backend-contracts §2 отражено следующими документальными полями и правилами. Область: DB-C04-04–07/10, часть DB-C04-03. Полные условные FK и защита C06 — следующий блок 3, не повод ослаблять действующие требования сейчас.

### 2.1. Исходный результат в command_receipts

Приняты отдельные колонки C04; source raw-история каждой правки не создаётся.

| Колонка | Тип | Успешный C04 |
| --- | --- | --- |
| result_draft_id | uuid | Обязательна; исходный draft |
| result_ownership_id | uuid | Обязательна; историческое владение при исполнении |
| result_draft_version | bigint | Обязательна; версия сразу после исходного выполнения |
| result_change_kind | text | created, updated или unchanged |
| result_last_saved_at | timestamptz | Обязательна; время сохранения ввода в исходном результате |
| result_expires_at | timestamptz | Обязательна; expiry ввода в исходном результате |

Все шесть C04 result-полей заполнены вместе только при succeeded C04. Для rejected C04 и любого C06 они NULL. Сессионные result_session_id/result_settings_revision_id/result_snapshot_version/result_session_version обязательны только для succeeded C06 и NULL для C04/отказа. Это два разных успешных результата, а не общий набор необязательных ссылок.

Пример: первая команда сохранила version5, следующая version6. Exact replay первой возвращает сохранённые version5/lastSavedAt/expiresAt/changeKind и прежние fieldErrors. Q03 отдельно возвращает current draft version6. Старый ответ не откатывает форму. Историческая result_draft_version не ссылается FK на изменяемую текущую version черновика: иначе новая правка разрушила бы прежний receipt.

### 2.2. Details, ошибки и предметный отказ

У каждого receipt остаётся ровно одна обязательная неизменяемая command_receipt_details; формат задаётся родителем receipt/v1. Принято хранить fieldErrors в закрытом типизированном response_data.fieldErrors, без новой таблицы/полной копии raw. Это массив известных полей и кодов из реестра с разрешёнными безопасными параметрами; отсутствие ошибок — пустой массив. Полная форма параметров/приоритет нескольких причин всё ещё требует точной H02-спецификации, а не свободного сообщения БД.

Успешный C04 может сохранить короткий невалидный raw и соответствующие fieldErrors: это не normalizationValid=true и не допуск запуска. При повторе fieldErrors берутся из исходных details, не пересчитываются по новой policy/текущему вводу.

Rejected C04 после допуска к scoped key хранит reason_code и безопасные details; result-поля пусты, draft не меняется. Ссылка на исходную доступную цель update — контекст запроса, не успешный result. Для create отказ не требует фиктивного draft/ownership/session. Принято отдельно от result хранить в command_keys C04-намерение create/update и expected version/проверенные target refs; точные nullable/FK/безопасные границы их заполнения завершаются блоком 3, без ссылки на непроверенный чужой ресурс. related_session_id остаётся только допустимым отказом C06, не C04.

Ранний отказ транспорта/доступа не создаёт предметного receipt. Неизвестный commit и техническая ошибка не становятся rejected. Отсутствующие details — неисправность, не архив. В первом стенде весь key/receipt/details и исторический ownership сохраняются; expiry/used/новый login их не удаляют.

### 2.3. Связь текущего ввода с командой его сохранения

Чтобы полнота работала в обе стороны, принято добавить setup_drafts.last_input_receipt_id uuid NOT NULL — ссылку на успешный C04, создавший текущую версию ввода. Она не указывает на последнюю попытку или последнее чтение.

- Create: первоначальный draft/ownership, версия1 и pointer на свой created receipt сохраняются вместе.
- Update с реальным изменением: raw/version/last_saved_at/expires_at и pointer на updated receipt меняются вместе.
- Новый unchanged: сохраняет отдельный receipt, но pointer/raw/version/last_saved_at/expires_at черновика не меняются.
- Claim/used: не новая версия ввода, pointer прежний. Receipt продолжает ссылаться на историческое ownership, а не требует вечного равенства current ownership.

Составная ссылка и отложенная полнота должны доказывать: pointer ведёт к C04 succeeded created/updated этого draft, result version и моменты равны текущей версии ввода. Проверка допустимого изменения raw требует правильного продвижения version и pointer; произвольный прямой UPDATE не обходит ограничение. Обратная result-ссылка receipt указывает на постоянный draft/историческое ownership, не закрепляет все прежние receipts за текущей version. Точный набор составных ключей и защита обновлений — блок 3/H05.

Это дополнительная колонка в существующей таблице, не журнал всех raw-правок. Для исторических реальных данных нужен был бы отдельный план совместимости; существующая реализованная БД в этой работе не заявляется и миграция сейчас не создаётся.

### 2.4. Неделимая операция и дельты

Для новой C04 одна транзакция сохраняет key с обязательным final receipt, сам receipt/details и соответствующее изменение draft; для create также первоначальную ownership и current pointer. Проверяются текущий доступ/guest proof, used/expiry, затем expectedVersion до сравнения полей. Новая unchanged команда отличается от exact replay. Ввод/raw сравнивается точно: «20» → «20.00» — изменение.

| Случай | Изменение draft | Новый key / receipt / details |
| --- | --- | --- |
| Create | +1 draft/+1 ownership, version1, pointer на created | По +1 |
| Update с изменением | Version+1, новое время/TTL и pointer на updated | По +1 |
| Новый unchanged с актуальной version | Нет изменений, включая pointer и время ввода | По +1 |
| Exact replay прежнего key/fingerprint | Нет изменений; исходный результат | +0 |
| Новый stale expectedVersion, даже при равном raw | Нет изменений; VERSION_CONFLICT | По +1 для окончательного отказа после допуска к ключу |
| Ранний invalid/access denied | Нет изменений | +0 |
| Подтверждённый rollback | Ни изменения, ни новых строк этой операции | +0 committed |
| Unknown commit | Не объявляется нулевой дельтой; сначала исходный key | Исход ещё выясняется |

C04 не создаёт FIN, start audit или outbox; новый гостевой тип audit не вводится. У новой unchanged записи свой receipt.created_at, но result_last_saved_at/result_expires_at — прежние моменты ввода. Даже если время двух изменений совпало до миллисекунды, версии различаются. Ключ остаётся окончательным и неизменяемым; no-op не превращается в скрытую запись TTL.

### 2.5. Будущие проверки принятой детализации

Расширить A54–A57/A98/A100–A107/A110–A112 и F05/F06/F17/F19: потерянный create, два одинаковых ключа, разные payload, две команды одной expectedVersion, replay version5 после version6, stale no-op, исходные fieldErrors, claim↔C04, expired/used, неизвестный commit, родитель без обязательного receipt/details, подстановка C04 receipt в C06 и backup до сохранения. Варианты используют S/N/K с существующими числовыми эталонами. Реальные прогоны остаются «запланировано».

## 3. Следующий блок: восстановление после claim и строгие связи — предложение

**Статус: блок 3 не принят в чате БД.** Ниже предлагаются точные target-колонки, составные связи и правила поиска, завершающие DB-C04-03/05/08/09 и механизм полноты принятых блоков. Дополнительные колонки этого раздела ещё не перенесены в таблицы как принятые. Область команды/результат/last_input_receipt_id из блоков 1–2 не переоткрываются.

### 3.1. Намерение и проверенная цель в command_keys

| Предлагаемое поле | Тип | C04 create | C04 update | C06 |
| --- | --- | --- | --- | --- |
| c04_operation | text | create | update | NULL |
| target_draft_id | uuid | NULL | Обязателен после подтверждённого доступа к цели | NULL |
| target_ownership_id | uuid | NULL | Обязателен, историческое владение при допуске новой команды | NULL |
| expected_draft_version | bigint | NULL | Обязательна, положительная версия из проверенного запроса | NULL |

У create серверный новый draft ID появляется в результате, не становится target/fingerprint при повторе. У update target-пара заполнена вместе и соответствует одной environment/draft/ownership; данные сырого чужого ID не записываются как проверенная цель. Неверная структура/нет доступа/чужой или скрытый ресурс отвергаются до допуска к ключу без предметного receipt. Если доступ подтверждён, но draft expired/used/version stale, окончательный отказ может сохранить именно доступную target-пару и expected version, без успешного result.

Предлагаемый составной FK: (environment,target_draft_id,target_ownership_id) → draft_ownerships(environment,draft_id,id); имеющийся ключ ownership уже подходит. Для create/C06 target-пара вся NULL; для C04 update все компоненты обязательны. Historical target не обновляется при claim. Canonical intent использует исходную версию/операцию/поля запроса, а не заново прочитанную текущую версию. Серверное historical ownership фиксирует допуск; оно не подменяется current ownership при повторе.

### 3.2. Тип результата должен совпадать с типом ключа

Предлагается command_receipts.command_type text NOT NULL (C04/C06) как проверяемый discriminator, а не независимо изменяемое значение. В command_keys добавить target unique(environment,id,receipt_id,command_type). Связь receipt (environment,command_key_id,id,command_type) → этот ключ делает невозможным C04 key с receipt типа C06. Обратный key.receipt_id, unique receipt.command_key_id и запрет изменения core сохраняются; оба конца существуют к commit.

Локальная полнота результата:

- succeeded C04: шесть result_draft/ownership/version/changeKind/time-полей обязательны, все session-result и related_session_id NULL;
- succeeded C06: все четыре session-result поля обязательны, все C04-result и related_session_id NULL;
- rejected: все успешные result-поля NULL, reason_code обязателен; related_session_id разрешён только для C06 и собственной доступной блокирующей session;
- reason_code у succeeded NULL; других outcome, в том числе pending, нет.

Тип/исход/полнота не определяются по одному заполненному UUID. У каждого результата ровно одни обязательные details до commit, включая rejected и unchanged. Проверка запускается также от родителя, у которого детали вообще не вставлены. Format receipt/v1 определяет details; guest C04 не превращается в user/staff audit.

### 3.3. Строгие ссылки C04 и текущего ввода

| Связь / проверка | Предлагаемый механизм |
| --- | --- |
| C04 succeeded → историческое владение именно результата | FK (environment,result_draft_id,result_ownership_id) → draft_ownerships(environment,draft_id,id); оба IDs обязательны |
| Actor ключа → владелец result/target | До commit user требует ownership.owner_kind=user и того же owner_user_id; guest — owner_kind=guest и того же guest_context_id. Проверка всех применимых target/result refs, а не только первой строки |
| Create → created | c04_operation=create, changeKind=created, result version1; первоначальное ownership без previous/claim, собственные draft/current pointer/result вместе |
| Update → updated/unchanged | result draft/ownership равны проверенной target-паре; updated version=expected+1, unchanged version=expected. Переполнение отклоняет весь комплект |
| Один исходный create на draft | Условный unique(environment,result_draft_id) для C04/succeeded/created; другие успешные правки того же draft разрешены |
| Current input pointer → свой успешный результат | Target unique receipts(environment,id,result_draft_id,result_draft_version); FK draft(environment,last_input_receipt_id,id,version) → этот ключ, все компоненты обязательны |
| Pointer нельзя направить на unchanged/отказ | Проверка до commit требует C04 succeeded created/updated; result_last_saved_at/result_expires_at совпадают с текущими моментами ввода |

Направление ссылки на текущую версию идёт **от draft к последней изменяющей команде**. Старые receipts ссылаются на постоянные draft/ownership IDs, не FK на изменяемую version draft. Поэтому сохранение version6 не ломает receipt version5 и не переписывает его времена/ошибки.

При новом created/updated receipt проверка финализации требует, чтобы именно он стал last_input_receipt_id своего draft и его version/моменты соответствовали результату. При новом unchanged receipt current version/моменты совпадают, raw/pointer/TTL не меняются. Эти проверки относятся к новой операции; последующая правка не заставляет старый immutable receipt равняться новой текущей версии. Разрешённый путь записи и защита переходов сравнивают старый/новый полный сохраняемый ввод: изменение требует version+1 и нового updated pointer. Обновление raw при прежнем pointer либо перестановка pointer без допустимой команды отклоняются.

Claim/used изменяют только свои служебные поля, не ввод/его pointer. После claim прежний pointer может законно вести к гостевому receipt: его историческое ownership сохраняется, новое current ownership не подставляется в прошлый результат. Новая пользовательская правка уже ссылается на user ownership. Все проверки включают environment; FK не заменяет проверку proof/полного входа.

### 3.4. C04 не может стать основанием C06

Существующий unique receipts(environment,id,result_session_id) и составные ссылки session/settings/funding/journal/outbox сохраняются. Для любого C04 result_session_id принудительно NULL; в C06-зависимых дочерних ссылках environment/receipt/session обязательны, поэтому FK на C04 не найдёт целевой непустой session. Вариант без типа/полупустая дочерняя ссылка не допускаются. Не требуется добавлять фиктивные session IDs к C04 или делать C06 nullable.

Для audit paper_session.started предлагается явный составной FK (environment,command_receipt_id,session_id) → receipts(environment,id,result_session_id), с обязательными обеими ссылками у этого event_kind. У Q06 command_receipt_id NULL по его отдельному варианту; у claim используется claim_receipt_id. Условия event_kind должны запрещать NULL-обход именно start-события.

Перед commit C06 по-прежнему проверяются: key/receipt C06+succeeded, user realm/actor=session user; одна session, settings1, initial funding=B, journal1 и ровно две сбалансированные entries, snapshot1, source draft/review/ownership, slot/used, start audit и outbox. Во всех начальных ссылках тот же receipt. Подстановка C04 или rejected C06, чужой session/settings/snapshot, отсутствие обязательного ребёнка или несовпадение actor отклоняют весь commit. Snapshot связан через свою session/settings и проверку полноты; лишняя таблица результата не вводится.

### 3.5. Восстановление результата до и после claim

Предлагается один безопасный порядок: текущая авторизация → разрешение исходной области ключа → проверка цепочки владения → чтение исходного результата поддерживаемым декодером. При повторном запросе команды также сравнивается fingerprint по сохранённой версии канонизации. Сам Q05 не требует повторно присылать всю старую форму и не превращается в запись.

| Кто восстанавливает | Как находится исходный key | Допуск |
| --- | --- | --- |
| User своего C04 | Постоянный userId + environment/C04/clientCommandId | Полный текущий вход; проверка допустимого собственного результата/цели, не login ID старого исполнения |
| Guest до claim, потерян ответ create | Доверенный постоянный Auth guest context + environment/C04/clientCommandId; draftId не обязателен | Действующее доказательство контекста, затем проверка результата/владения конкретного draft, если он создан; ID контекста сам не достаточен |
| User после claim гостевого C04 | Исходная guest-область определяется через подтверждённые ownership/claim; клиентский исходный context/key — только locator | Current ownership user совпадает с вошедшим user; claim того же draft/пользователя указывает на original guest ownership, совпадающее с result ownership (succeeded) или target ownership (rejected update) и actor_guest_context_id ключа |

Нельзя искать по одному clientCommandId среди всех пользователей/контекстов. Совпадение такого ID в разных scopes допустимо. Если draftId потерян, разрешение кандидатов ограничено уже подтверждёнными claim текущего user; при нескольких подходящих исходных scopes нельзя выбрать первый или раскрыть чужие результаты — нужен уточнённый locator из доступного контекста/своего draft. Точный DTO такого поиска определяется в H02, право не берётся из переданного actorId/draftId. Исходный actor, использованный при сравнении fingerprint, берётся из найденного неизменяемого key, а текущий пользователь является читателем результата, не новым актором исполнения.

Для guest create, отклонённого без draft, нет result/target ownership и цепочки claim: после входа нельзя автоматически приписать этот отказ пользователю по email/key. Его чтение возможно только в исходной допустимой guest-области. Ранний access denied вообще не имеет предметного receipt. Rejected update может быть доступен после claim только через сохранённую проверенную target-пару, без подстановки успешного result.

После claim старый guest proof не открывает переданный draft и его C04 results; работа с другими независимыми drafts того же context не отзывается этим фактом автоматически. User через claim получает чтение прежнего результата, **не право исполнить отсутствующий guest key**. Если результат ещё не установлен, сначала свежая сверка исхода исходной транзакции. Неизвестный/повреждённый результат не считается отсутствием и не создаёт новый draft. Новый допустимый C04 user — отдельное явное намерение со своей областью/ключом, после разрешения неизвестного исхода.

Expiry/used не удаляют прежний receipt и не требуют повторного допуска к редактированию для чтения прежнего результата. Текущий доступ обязателен всегда. Для неподтверждённой цепочки нет данных/признака чужого существования; для повреждения после установленного доступа — безопасная техническая недоступность, без автоматического ремонта и обхода через raw read. Q05 не создаёт FIN/новый receipt/start audit/outbox.

### 3.6. Гонка claim и C04, сохранность и проверки

Предлагаются обе допустимые сериализованные очередности. C04 раньше claim: целый результат с guest ownership и возможным изменением ввода; затем claim сохраняет этот результат/last_input_receipt_id, закрывает guest-допуск и открывает чтение user по цепочке. Claim раньше нового guest C04: нет записи под утраченным правом; история и ввод не меняются от этой попытки. Прежний committed результат читается current user, а не старым proof. Serialization rollback не объявляется предметным отказом; retry-бюджет C06 не переносится на C04/claim.

Ни key, receipt/details, historical ownership/claim, source draft, ни C06 children не удаляются каскадом или по expiry. Первый стенд без archive/cleanup; пропавшие details — неисправность. После backup до C04/claim сохраняется барьер восстановления: отсутствие старой команды в копии не разрешает новое создание/исполнение до сверки.

После принятия добавить точные проверки к A23/A35/A54–A57/A60–A63/A98/A100–A107/A110–A112 и F05/F06/F10/F17/F19: create без draftId; тот же client ID разных scopes; чужая цепочка; rejected create/update; обе гонки claim; старый guest proof; user replay после изменения/expiry/used; receipt type≠key type; C04 подставлен в каждую C06-ссылку; полупустые refs; draft без current input receipt; unchanged как pointer; старый result version после новой правки; parent без детей; backup без последнего C04/claim. Это план, не результаты тестов.

## 4. Очередь оставшейся сверки

Блоки 1–2 приняты и отражены; блок 3 выше предложен. После него — заключительный блок 4: H02/H03 реестры/форматы/evidence, параметры H04, решения H05/H06/время/WAL/evidence и сводная актуализация проверочного пакета. Точный wire-протокол восстановления и безопасные параметры fieldErrors/reasonDetails требуют спецификации H02; принятие DB-колонок не объявляет готовый декодер.

Статусы ведутся раздельно: **согласовано → отражено в документах → проверено испытаниями**. M01 остаётся частично закрытым документально до полного согласования связей/поиска; испытания не выполнены. Код, SQL, миграции, установка и развёртывание не начинаются.
