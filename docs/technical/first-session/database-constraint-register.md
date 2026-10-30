# Реестр физических ограничений первого сценария

30.10.2026 · [Изолированные тестовые состояния M02–M03](database-isolated-test-states.md) подготовлены документально: BASE-наборы, SEM-факты допуска, stand-only публикация и отдельные отрицательные/повреждённые варианты I01–I22. Подготовка/загрузка/испытания не выполнялись; будущие lifecycle-представления и инструменты остаются явными зависимостями.

30.10.2026 · По поручению владельца. Baseline актуальной main: `9e401a7e2c8f49adf44e324f023897d99f5a8588` (PR №178). Реестр сводит принятые правила в проект механизмов обеспечения; код, SQL, миграции, установка и испытания не выполняются. **Статус всех R001–R071: отражено в документах; не реализовано и не проверено испытаниями в рамках этой задачи.** Он не создаёт новые правила продукта и не переоткрывает C04/last_input_receipt_id или полный C06.

## 1. Как читать и источники

Каждая строка связывает правило с существующими таблицами/полями, механизмом, ответственным путём записи/чтения и критериями A. Дополнительная связь в обратную сторону дана для всех A01–A112. Это карта покрытия требований, не доказательство прохождения приёмки.

| Ссылка | Источник действующего контракта |
| --- | --- |
| P1 | [Пользователь, ввод и владение](database-physical-design.md) |
| P2 | [Каталог, policy и review](database-physical-catalog-review.md) |
| P3 | [Сессия, слот, ledger и snapshot](database-physical-session-ledger.md) |
| P4 | [Команды, audit/outbox, доступ и login](database-physical-operations-access.md) |
| C04 | [Принятое дополнение C04 и последующие уточнения](database-c04-addendum.md) |
| ERR | [Точная карта errors и Q03](database-error-field-map.md) |
| REG / CONTRACT | [Закрытый реестр](backend-code-registry.md) / [T01–T17 и общие контракты](backend-contracts.md) |
| AUTH / ACCESS | [Протоколы и доступ бэкенда](backend-auth-access.md), [общая auth-policy](auth-policy.md) |
| OPS | [H04–H06: БД, worker, время, совместимость и восстановление](backend-operations.md) |
| POLICY | [Принятые числовые значения](../../policies/paper-mvp-settings-v1.json), [ADR-0058](../../decisions/0058_paper_mvp_numeric_settings_policy.md) |
| A | [Матрица A01–A112](database-integrity-matrix.md), [исходная приёмка](acceptance.md) |
| История | [ADR-0064 §§30–38](../../decisions/0064_first_session_database_contract.md), [ADR-0065](../../decisions/0065_first_session_backend_contract.md) |

Таблицы принадлежат схеме shadow; краткие draft/review/session/receipt в строках обозначают соответствующие setup_drafts/setup_reviews/paper_sessions/command_receipts, не дополнительные таблицы. Группы *_n/*_d и другие * обозначают только перечисленные поля физических спецификаций. Каждая связь сохраняет environment и предметный scope. Указание «свой» означает составную принадлежность из P1–P4, не FK лишь на случайный UUID. Два владельца обозначаются «владелец 1» и «владелец 2», полномочия равны.

Непосредственная обязательность/nullable каждого столбца остаётся в P1–P4. R001/R002/R005/R007/R008 применяются к соответствующим полям каждой таблицы вместе с предметными строками, а не заменяют их. Все поддерживающие unique для составных FK сохраняются, даже если не являются отдельной бизнес-уникальностью. Названия R — идентификаторы документа, не будущие имена SQL-ограничений.

## 2. Уровни обеспечения и границы

| Метка | Что должно обеспечивать | Когда / чего не доказывает |
| --- | --- | --- |
| N | Обязательность столбца и тип | При записи; nullable разрешён только в описанном варианте |
| L | Локальная проверка строки/дискриминатора/точного значения | Не читает другие строки или текущее время ради динамического допуска |
| U | PK/scoped unique, включая условные варианты | В том числе гонки на отсутствующей строке; не доказывает наличие обязательных детей |
| F | Составной FK и подходящий unique целевого ключа | Принадлежность; циклические обязательные ссылки должны замкнуться до commit. NULL не служит способом обойти полный вариант |
| D | Отложенная проверка межстрочной полноты и согласованности | До commit, от всех затрагивающих родителей/детей; проект constraint triggers уже принят в P3/OPS, конкретной реализации ещё нет |
| W | Разрешённый переход записи и запрет обхода/изменения истории | Сравнение старого/нового, рабочие роли и процедуры записи; одного FK для этого недостаточно |
| T | Одна транзакция, общий порядок locks, guards/изоляция | Атомарность/сериализуемый порядок локальной БД. Не объединяет Auth-провайдера и Shadow в распределённую транзакцию |
| B | Доверенный бэкенд/адаптер/чтение; при указании UI — клиент | Proof/MFA, исходный HTTP, разбор, авторизация, таймеры и выдача не гарантируются одним CHECK/FK |
| O | Эксплуатационная проверка и внешнее доказательство | Backup/restore, compatibility scan, privileges/query plans требуют отдельного выполнения и evidence |

D/W — требуемые механизмы будущей реализации в уже принятой архитектуре, а не заявление, что триггеры/процедуры созданы. Конкретные имена функций, обработка ошибок, точный DDL/привилегии и проверка всех путей записи остаются задачей реализации. Отдельно нельзя объявлять CHECK с межтабличным чтением заменой D, Serializable заменой guards, или строку audit доказательством доставки ответа.

## 3. Реестр правил

### 3.1. Общие типы и защита истории

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R001 · Идентичность и среда | Все 34 таблицы: environment, id, created_at; каждый FK включает environment | N/L/U/F: PK (environment,id), UUID v4 собственных IDs, непустая доверенная среда, обязательные моменты; условный FK применяется только к полному варианту | Все writers; B устанавливает environment из доверенного контекста. UUID/FK не доказывает право доступа | A19, A23, A39, A40, A103 | P1–P4 |
| R002 · Словари и варианты NULL | Все discriminators/коды/обязательные поля P1–P4: realm, mode, kind, outcome, status, units, форматы | N/L: закрытые допустимые значения и условная полнота; неизвестное не становится default. Обязательность каждого поля берётся из строки физической спецификации | Все writers/readers; B проверяет wire-типы до БД; D — межстрочное соответствие. Не вводятся дополнительные значения/статусы | A03, A40, A50, A95, A98 | P1–P4, REG |
| R003 · Точные суммы и проценты | paper_policy_versions/setup_reviews/settings_revisions/funding_flows/journals/journal_entries/session_snapshots: существующие *_n/*_d и процентные integer | L: конечные целые numeric без округляющего scale, d>0, gcd=1, ноль=0/1, ≤64 цифр без знака; знак по полю, entries signed. Integer процентов — сотые п.п. | Writer проверяет тип и пределы; D сверяет расчёт/единицы по ссылкам. B/драйвер передают строки и точную арифметику; промежуточный float недопустим | A07, A08, A19, A31, A32, A39, A40, A96 | P2/P3 |
| R004 · Сохранение raw | setup_drafts/setup_reviews: raw_budget, raw_fixed_amount, raw_copy_percent, raw_market_limit_percent, raw_loss_limit_percent | L: nullable text, максимум 64 Unicode code points, без обрезания. W сохраняет NULL/пустое/пробелы/20/20.00 различными; короткая нечисловая строка допустима C04 | C04/C05; B — точный T01 parser и fieldErrors. CHECK длины не является числовой проверкой и не разрешает запуск | A07, A08, A54, A56, A96, A98 | P1/P2, ERR |
| R005 · Версии и счётчики | Все существующие version, sequence, generation, authorization_version, current_grant_set_version; snapshot trade_count/position_count/order_count; outbox attempt_count отдельно | L: положительные версии, неотрицательные счётчики. W/T: разрешённый переход и увеличение без сброса/переполнения; timestamp не заменяет версию | Изменяющий соответствующий агрегат writer. B сохраняет bigint как строку; конкретные переходы уточнены ниже, не все номера увеличиваются при каждом UPDATE | A33, A43, A45, A97 | P1–P4 |
| R006 · Время и сроки | draft last_saved_at/expires_at/used_at; review checked_at/expires_at; auth_sessions времена; session started_at/deadline; snapshot as_of/created_at | L/W: серверная миллисекундная точность и постоянные вычисленные сроки. B/T: now≥expires_at означает истечение, повторная проверка после ожиданий; не CHECK с текущим временем | C04/C05/C06/claim/Auth/read; монотонный бюджет отдельно от UTC. as_of не подменяется created_at; истечение не требует фонового UPDATE | A28, A39, A43, A44, A47, A58, A59, A66, A70 | P1–P4 |
| R007 · Неизменяемая история и защита удаления | Identity-связи; ownerships; trader_revisions; опубликованные policies; reviews; settings/funding/journals/entries/snapshots; command core/details; claim; audit/evidence; grants; consumer receipts; постоянные поля session/outbox | W/F: запрет UPDATE/DELETE исторических фактов и переназначения identity; отсутствие каскадного удаления истории. Обновляемые guards/поля доставки — только разрешённые варианты P1–P4 | Все writers, schema/runtime roles. Точное разделение privileges/процедур остаётся реализацией; наличие FK само по себе не обеспечивает неизменяемость | A28, A33, A34, A36, A46, A63, A112 | P1–P4 |
| R008 · Формат JSON и его размер | reviews.reason_details/warnings; receipt_details.reason_data/response_data; audit.safe_context; outbox.payload; record_schema_version review/settings/snapshot/receipt | N/L/W: типизированные закрытые варианты и ≤16 384 байт каждого целого компактного UTF-8 поля, без усечения. D: согласие с core. Версия details — версия родителя | B проверяет дубли ключей до jsonb и выбирает decoder по типу+версии; нельзя измерять исходные дубли или wire-байты по jsonb. Формы errors — ERR, остальные — свой контракт | A40, A49, A51, A79, A80, A81, A82, A83, A95, A99, A110 | P2–P4, ERR |
| R009 · Ограничения и индексы | PK/unique/FK ключи всех 34 таблиц; доступ по command scope/current pointers/due outbox | U/F: поддерживающие составные target keys из P1–P4 обязательны для целостности; одинаковые индексы не дублируются | O: планы на реальной истории и допустимые запросы, затем дополнительные индексы. Наличие ключа не доказывает скорость/план | A41 | P1–P4, OPS |

### 3.2. User, draft, ownership и claim

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R010 · Постоянная пользовательская identity | users.id; user_auth_identities.user_id/realm/provider/provider_subject/verified_email | U(environment,realm,provider,provider_subject), F на users; target unique(environment,id,user_id). W запрещает переназначение. Email не PK и не глобальный unique | Auth writer: подтверждённый subject, полный вход отдельно, атомарное разрешение user/identity; нет email-merge или внешнего FK к невыбранной Auth-схеме | A01, A21, A23, A34, A107 | P1/P4 |
| R011 · Guard пользователя и создание входа | users.status/version; user_auth_identities.version/user_id; auth_sessions.user_id/user_identity_id | T/W: изменения дочернего доступа поднимают users.version в той же локальной транзакции; provider verify не считается частью одной внешней транзакции с Shadow | Auth/access writer подтверждает актуальную identity/MFA/блокировку. БД не доказывает факт email/OTP или двух разных людей | A01, A16, A21, A22, A25, A102, A107 | P1/P4, AUTH |
| R012 · Полные варианты ownership | draft_ownerships.owner_kind/owner_user_id/guest_context_id/guest_context_digest/guest_digest_version | L: user ⇒ user ID, остальные три guest-поля NULL; guest ⇒ три guest-поля, user ID NULL. F user; U(environment,draft_id,owner_kind) | Create/claim; B проверяет proof и доверенный guest context, существующий до C04. ID/digest сами не дают доступа; Auth-context FK не выдумывается | A02, A23, A26, A35, A40 | P1, C04 |
| R013 · Текущий владелец своего draft | setup_drafts.current_ownership_id; draft_ownerships.draft_id/id; previous_ownership_id | F draft(environment,id,current_ownership_id) → ownership(environment,draft_id,id), обязательный pointer и обратный draft FK; U target(environment,draft_id,id), D замыкает создание цикла | C04 create/claim; T согласует current pointer и историю. Старый ownership не даёт права редактировать текущий draft | A02, A19, A23, A26, A35, A103 | P1/P4 |
| R014 · Один полный claim | draft_claim_receipts.draft_id/previous_ownership_id/claimed_ownership_id/actor_user_id; ownership.previous_ownership_id/claim_receipt_id; draft.current_ownership_id | U(environment,draft_id) receipt; F обе ownership того же draft, обратный F ownership(environment,claim_receipt_id,draft_id,id) → receipt(environment,id,draft_id,claimed_ownership_id); D previous=guest, claimed=user того actor, pointer=claimed | Claim: один T с новой ownership/receipt/закрытием guest proof/аудитом. Повтор тому же получателю без новой передачи; новый user-review, прежний guest-review не переписывается | A02, A26, A35, A100, A103, A107 | P1/P4, C04 |
| R015 · Выбор в черновике | setup_drafts.locale/step/entry_context/selected_mode/venue_id/trader_id/proposed_timezone | L: ru/en, принятые step/entry_context, fixed/percent/NULL, trader требует venue; F(environment,venue_id,trader_id) → trader(environment,venue_id,id), venue FK | C04; B проверяет IANA и допустимые формы. Step/locale не полномочие на start; отсутствие выбора не заполняется молча | A03, A10, A23, A27, A40, A54 | P1/P2 |
| R016 · Использованный draft и недоступность новых изменений | setup_drafts.used_at/used_by_session_id/version/expires_at; paper_sessions.started_from_draft_id/started_at | L: used-пара вместе; F на session с тем же исходным draft. D при start used_at=started_at. W после used запрещает правки ввода; B/T проверяет expiry/ownership/version до новых C04/C06 | C04/C06 конкурируют по тому же draft. Claim/used не меняют version ввода/TTL. Used приоритетнее expired; worker не нужен для expiry | A27, A28, A44, A47, A57, A58, A59, A62 | P1/P3 |
| R017 · Текущий ввод имеет создавший его receipt | setup_drafts.last_input_receipt_id/id/version/last_saved_at/expires_at; receipts.result_draft_id/result_draft_version/result_change_kind/result_*_at | F(environment,last_input_receipt_id,id,version) → receipts(environment,id,result_draft_id,result_draft_version); U target. D/W: C04 succeeded created/updated, совпадают времена, реальная правка меняет pointer/version атомарно с CMD | C04 create/update; D начинается также от draft без детей. Исторический receipt не получает FK на будущую изменяемую version draft; claim/used допустимы со старым guest receipt | A19, A54, A55, A56, A57, A100, A103 | P1/P4, C04 |
| R018 · Updated, unchanged и replay различаются | setup_drafts сохраняемые поля/version/TTL/pointer; command_keys.expected_draft_version; receipts.result_change_kind/result_draft_version | W/T: сначала expectedVersion, затем сравнение полного ввода. Created=1; updated=expected+1; unchanged=expected и без правки draft/TTL/pointer. Exact replay без нового CMD | C04: новый unchanged имеет свой receipt/details; stale одинаковый raw — отказ, не no-op. Нельзя обойти обязательную запись результата прямым UPDATE | A15, A54, A55, A56, A57, A100 | P1/P4, C04 |
| R019 · Ошибки Q03 происходят от текущего ввода | draft.last_input_receipt_id/version; receipts.result_draft_id/result_draft_version; details.response_data.fieldErrors | F/D как R017; B читает одну согласованную цепочку и выдаёт fieldErrorsSource(receiptId,draftVersion). Нет нового сохраняемого поля source | Q03: не последний receipt/не C05, без пересчёта после policy change. Missing/malformed после авторизации — RECORD_UNAVAILABLE, не []; Q03 не разрешает start | A28, A54, A55, A56, A110 | P1/P4, ERR |

### 3.3. Каталог, policy и review

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R020 · Площадка и область внешнего трейдера | venues.code; catalog_sources.venue_id/source_environment; traders.catalog_source_id/venue_id/external_trader_id | U venue(environment,code), source(environment,venue_id,source_environment), trader(environment,catalog_source_id,external_trader_id); F trader→source с venue, дополнительные target keys P2 | Catalog writer; нормализация external ID только по контракту источника. Одинаковые внешние ID разных площадок не склеиваются; synthetic не выдаётся за live | A03, A12, A23, A36, A39 | P2 |
| R021 · Revision принадлежит своему трейдеру | traders.current_revision_id/id; trader_revisions.trader_id/venue_id/catalog_source_id/revision | U(environment,trader_id,revision) и target(environment,trader_id,id); F current→своя revision и revision→полный scope trader; D первый цикл до commit | Catalog publication: новая immutable revision и current pointer/guards одним T; старые ссылки reviews/session не переписываются | A19, A33, A36, A100, A103 | P2 |
| R022 · Controls и guards изменяются вместе с детьми | paper_controls.mode/active_policy_version_id/start_enabled/unavailable_reason_code/version; sources/traders.start_*/unavailable_reason_code/version | U controls(environment,mode); F active policy; L причина обязательна при запрете и NULL при разрешении. T/W публикация policy/revision/допуска и всех затронутых guards вместе | Control/catalog writer и C05/C06 читают/блокируют совместимые guards. Новый child тоже меняет guard; FK на исторический номер не заменяет проверку текущего допуска | A16, A28, A33, A36, A47, A102 | P2, OPS |
| R023 · Политика чисел целостна и неизменна | paper_policy_versions.policy_version_code/source_hash/calculation_version/currency_unit; группы budget_*/fixed_*/copy_percent_*/market_percent_*/loss_percent_*; fixed_selection_limit_rule, percent_product_min_n/d, signal_max_age_* | U(environment,policy_version_code); N/L точные принятые min/max/step/origin/default, положительный step, допустимая сетка; v1 product minimum NULL, signal age=30/non-editable. W опубликованная policy неизменна | Доверенная публикация сверяет source_hash точных байтов, принятые числа/версию расчёта. Группы * здесь обозначают перечисленные колонки P2, не новые колонки или wildcard SQL | A07, A08, A32, A33, A40 | P2, POLICY |
| R024 · Review ссылается на свой источник и policy | setup_reviews.draft_id/draft_version/ownership_id/owner_kind/owner_user_id/policy_version_id/paper_control_id; venue/source/trader/revision и guard versions | F scope draft/ownership и полного trader revision; D владелец совпадает с historical ownership. N/F опубликованные policy/control; L группа trader заполнена полностью либо отсутствует по P2 | C05 создаёт immutable копию актуального доступного draft; номера guards/version сохраняются как история, не FK на будущие current versions | A02, A19, A23, A28, A36, A60, A103 | P2 |
| R025 · Полная числовая нормализация review/settings | review.normalization_valid/selected_mode/raw_* и B/F/q/p/d/P/D; settings.sizing_mode и соответствующие нормализованные поля | L XOR fixed/percent и все NULL при невалидной нормализации review; D/W диапазоны/сетки policy, P=B×p/10000, D=B×d/10000, F≤floor(min(P,D)); только выбранный размер действует | C05/C06 и публикация settings: точная арифметика без округления ввода/default B200. Неактивный raw хранится только как ввод; зависимый fixed limit не вычисляется при неверных B/p/d | A03, A07, A08, A19, A32, A40, A96 | P2/P3, ERR |
| R026 · Допуск review, причины и ошибки | setup_reviews.allowed_to_start/requires_authentication/owner_kind/slot_observation/expected_slot_generation/primary_reason_code/reason_details/warnings | L/D: guest требует auth, allowed=false, slot=not_applicable; user slot absent/present с соответствующей generation. Reasons/fieldErrors по ERR, primary совпадает; allowed требует полного валидного набора | C05 достоверно устанавливает причины T03, не превращает технический сбой в отрицательный review. HTTP 200 review не разрешает start; warnings не новые запреты | A02, A07, A08, A17, A28, A40, A49 | P2, ERR |
| R027 · Review не становится правом вечного запуска | setup_reviews.draft_version/ownership_id/guard versions/checked_at/expires_at; draft current ownership/version/used/expiry; current controls и slot | W сохраняет snapshot review; B/T C06 повторно сверяет текущий доступ/ownership/версии/сроки/допуск, после ожиданий; expires_at=checked_at+10 минут | C05/C06; несколько reviews разрешены, каждый immutable. Истечение после состоявшегося старта не отменяет session; утрата результата C05 не создаёт CMD/Q05 | A15, A16, A28, A44, A47, A57, A60 | P2/P3, CONTRACT |

### 3.4. Сессия и финансовая полнота

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R028 · Один текущий слот для двух площадок | user_session_slots.user_id/mode/current_session_id/id; session.slot_id/user_id/mode | U(environment,user_id,mode) без venue; F current(environment,current_session_id,id,user_id,mode) → session(environment,id,slot_id,user_id,mode); обратный F session→свой slot | C06: блокировка/резервирование отсутствующего slot в своём T. Проверка пустоты в приложении без unique не защищает гонку разных ключей/площадок | A04, A11, A12, A17, A19, A101 | P3 |
| R029 · Поколение слота и отсутствие не теряются | slot.generation/current_session_id; review.slot_observation/expected_slot_generation | L generation>0; W начально 1, +1 при изменении pointer, без удаления/сброса/no-op increment. T absent защищён резервированием; present сравнивает конкретное поколение | C05 не создаёт slot. При допущенном отказе после его резервирования допустим свободный slot generation=1 вместе с rejected receipt; это не START. Logout/TTL/ошибка не освобождают slot | A12, A17, A27, A45, A97, A101, A106 | P3 |
| R030 · Draft/review запускаются исторически один раз | session.started_from_draft_id/started_from_review_id/started_from_ownership_id/start_receipt_id; draft.used_by_session_id | U session(environment,started_from_draft_id) и (environment,started_from_review_id); F на review того draft/ownership и обратный used FK; D совпадение actor/источников | C06 сохраняет ссылки навсегда; освобождение slot в будущей операции не обходит уникальность. Used timestamps/current slot сверяются при создании, не навязываются всем историческим session как current | A19, A57, A60, A61, A62, A63 | P3/P4 |
| R031 · Settings принадлежат session и образуют историю | settings_revisions.session_id/sequence/previous_revision_id/policy_version_id/calculation_version/signal_max_age_seconds/command_receipt_id/actor_user_id; все нормализованные поля | U(environment,session_id,sequence), U(environment,session_id,command_receipt_id), target U(environment,session_id,id); составные F на previous своей session и parent/receipt; L sequence1⇒previous NULL; D первая revision точно копирует review/policy, actor=session.user | C06: sequence=1; будущая цепочка требует предыдущую sequence, одно состояние current settings/snapshot. Эта гарантия не создаёт команд редактирования активной session | A03, A19, A31, A33, A60, A63, A103 | P3 |
| R032 · Initial flow и журнал — одна операция | funding_flows.session_id/kind/amount_n/d/unit/journal_id/command_receipt_id; journals.session_id/sequence/kind/unit/funding_flow_id/command_receipt_id; session.initial_funding_flow_id/current_ledger_sequence | U flow(environment,session_id,kind), flow.journal_id; journal(environment,session_id,sequence), funding_flow_id, (environment,session_id,command_receipt_id). F/D зеркальные flow↔journal одной session, kind initial, B=settings B, sequence=1 | C06; initial financing не прибыль и не второе изменение бюджета. Наличие обязательного flow проверяется от session, а не только unique, ограничивающим максимум | A04, A11, A19, A31, A61, A62, A100, A103 | P3/P4 |
| R033 · Ровно две сбалансированные проводки | journal_entries.session_id/journal_id/unit/line_number/account_code/amount_n/d; journal.kind/unit; funding.amount_n/d | U(environment,journal_id,line_number), (environment,journal_id,account_code); F с session/journal/unit. D от journal: ровно line1 paper_cash +B и line2 virtual_funding_source −B, сумма=0, ненулевые entries | C06; проверка должна ловить journal с нулём детей и удаление/подмену строки. Локальный CHECK строки не доказывает количество/баланс | A04, A19, A31, A32, A100, A103 | P3 |
| R034 · Первый снимок полный и не дублирует funding | session_snapshots.session_id/version/record_schema_version/settings_revision_id/ledger_sequence/unit/content_state/data_origin/coverage_state; initial_funding/free/reserved/position_cost/position_value/equity/trading_result n/d; trade_count/position_count/order_count | U(environment,session_id,version), F settings/ledger той же session. L/D начально version=1, EMPTY, B/free/equity, остальные суммы 0/1, счётчики 0; free из paper_cash, result=equity−initialFunding=0 | C06 создаёт snapshot сразу; worker/read не создают поздний баланс. Формулы ограничены первым пустым запуском, не методикой будущей торговли | A03, A04, A05, A19, A31, A53, A103, A110 | P3 |
| R035 · Current snapshot публикуется согласованно | session.current_snapshot_version/current_settings_revision_id/current_ledger_sequence/version/lifecycle/control_state; snapshot.version/session_version/settings_revision_id/ledger_sequence/as_of | F current→свой snapshot; D current набор/состояние совпадают, W pointer только вперёд, тот же version no-op, назад отказ. Исторические snapshot версии не FK на будущий current номер | C06/будущий разрешённый publisher одним T; Q04/Q06 читают единый выбранный snapshot/settings, не max(created_at). M03 — отдельный изолированный механизм, не обход ограничений | A05, A33, A52, A53, A64, A65, A66, A100, A110 | P3 |
| R036 · Календарный deadline сохраняется | paper_sessions.started_at/iana_timezone/evaluation_deadline_at/deadline_calculation_version/timezone_database_version | N/W: неизменные zone/UTC deadline/algorithm/tzdb; B рассчитывает 14 местных дней, gap первый существующий момент, overlap первое вхождение. Простое прибавление часов не гарантия | C06; реализация/независимые fixtures для выбранного времени/библиотеки ещё нужны. Чтение/обновление tzdb не пересчитывает историю | A39, A42, A44 | P3, OPS |
| R037 · Полнота START до commit | session + settings1 + flow + journal1 + две entries + snapshot1 + slot/used draft + command key/receipt/details + start audit/outbox, их обязательные pointers и actor | D/F/T: все элементы одного успешного C06 и одной session, взаимные ссылки, B и source совпадают; проверять со стороны каждого затронутого родителя/детей, включая создание пустого parent | C06 атомарно, ответ после commit. Одного writer-кода/unique или триггера на entries недостаточно; обязательные связи C06 нельзя удовлетворить C04/rejected | A03, A04, A11, A13, A19, A31, A60, A100, A103 | P3/P4, C04 |

### 3.5. CommandReceipt и исходный результат

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R038 · Область ключа и XOR actor | command_keys.actor_realm/actor_user_id/actor_guest_context_id/command_type/client_command_id | L user/guest XOR, C06 только user; два U по полному scope: environment, realm, соответствующий actor ID, command_type, client_command_id; nullable IDs не один общий unique | C04/C06; B устанавливает постоянный actor до draft, не loginId/устройство. C04 create/update делят область одного типа команды; user и guest не смешиваются | A11, A15, A23, A29, A35, A54, A101 | P4, C04 |
| R039 · Target/expected C04 и исходный create | command_keys.c04_operation/target_draft_id/target_ownership_id/expected_draft_version; receipts.result_draft_id/result_ownership_id/result_change_kind/result_draft_version | L create/C06 target+expected NULL, C04 update обязательны; F target/result→ownership своего draft; D actor совпадает со всеми ссылками. U succeeded C04 created по (environment,result_draft_id) | C04: created/version1/первичное ownership, update result=target; rejected update сохраняет разрешённый target, ранняя недоступная цель не создаёт CMD | A15, A19, A23, A54, A55, A98, A103 | P4, C04 |
| R040 · Fingerprint не меняется при повторе | command_keys.canonical_request_version/hash_algorithm/request_hash и scope/target/client_command_id | L command-jcs-v1/sha256 и ровно 32 байта hash; W исходные key/отпечаток неизменны. B JCS исходного намерения с точными raw и доверенным scope; другой payload — конфликт | C04/C06 replay проверяет сохранённый алгоритм/actor, не текущего читателя после claim. RequestId/cookie/loginId/correlationId не fingerprint; hash не доказывает права доступа | A11, A15, A29, A46, A56, A76 | P4, CONTRACT |
| R041 · Ключ, результат и details неделимы | keys.receipt_id; receipts.command_key_id/id/command_type; details.receipt_id | U key typed target (environment,id,receipt_id,command_type); receipt unique(environment,command_key_id); details unique(environment,receipt_id); F взаимные key↔receipt и details→receipt; D ровно одни details от parent | C04/C06: резервирование key внутри T, ни key-only, ни долговечного pending. Nullable/несовпадающий discriminator не допускает разрыв связи | A11, A13, A19, A38, A54, A100, A101, A103 | P4 |
| R042 · Результат C04 не подставляется в C06 | receipts.command_type/outcome/reason_code, обе result-группы, related_session_id; session/settings/flow/journal/start audit/outbox command_receipt_id+session_id | L complete result C04 только succeeded C04, complete result C06 только succeeded C06, rejected обе группы NULL. U receipt(environment,id,result_session_id); F обязательные C06 receipt/session и D actor/outcome | C04 result_session_id всегда NULL; у C06 обязательные FK-компоненты NOT NULL. Related_session только своя блокирующая rejected C06, не созданный результат | A03, A19, A23, A31, A54, A98, A103 | P4, C04 |
| R043 · Причины/ошибки — исходный типизированный результат | receipt_details.reason_data/response_data; receipts.reason_code; review.primary_reason_code/reason_details; existing related_session_id отдельно | L/W/D: succeeded reason_data={}, rejected объект reasons с первым code=core; C04 success response_data.fieldErrors, остальные {}; review reasons/fieldErrors. Полные keys/params/порядок/units и пустые варианты ERR | Writer фиксирует серверные факты T02–T04; replay/Q05 не пересчитывает. Missing/порча не превращается в []; runtime decoder/ограничения JSON ещё предстоит реализовать | A07, A08, A28, A40, A46, A49, A55, A80, A99, A110 | P2/P4, ERR |
| R044 · Исторический результат после claim | key.actor_guest_context_id; target/result ownership; claim.previous_ownership_id/claimed_ownership_id/actor_user_id; draft.current_ownership_id | F/D защищают сохранённую цепочку; B текущий user доказывает доступ через конкретный completed claim, ключ/actor не переносятся. Старый guest proof больше не открывает переданный draft/result | Q05/replay: успех через result, rejected update через target; rejected create без draft не получает фиктивную цепочку. Неоднозначный поиск не разрешает первое глобальное совпадение | A02, A23, A26, A29, A35, A55, A106, A107, A110 | P4, C04 |
| R045 · Окончательный отказ отдельно от unknown | receipts.outcome/reason_code/result_*; keys scope; details неизменны | L/W: только succeeded/rejected как окончательный результат; business rejection после допуска сохраняется в своём T, не переписывается после исчезновения причины. Technical/unknown не durable rejected | B C04/C06 держит исходный key; Q05 HTTP 200 может читать rejected, pending — наблюдение. C05/claim/Auth не получают обычные CMD вследствие неизвестности | A15, A17, A18, A29, A46, A48, A55, A69, A105, A106, A107 | P4, CONTRACT |

### 3.6. Аудит и административная выдача

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R046 · Типизированный audit своей операции | audit_events.event_kind/outcome_code/actor_realm/actor_user_id/actor_staff_id/actor_login_id/request_id; command_receipt_id/claim_receipt_id/session_id/snapshot_version/draft_id | L XOR actor и полные варианты start/claim/Q06; F login того actor/realm, start→C06 receipt/session, snapshot scope. U по kind+command receipt, kind+claim receipt, Q06 kind+request_id | C06/claim/Q06: только три принятых вида; отдельного audit отказа C06 нет. Новый HTTP read — свой audit, replay start не дублирует его. Audit не доказывает доставку | A05, A11, A13, A23, A37, A52, A100, A103 | P4, REG |
| R047 · Audit содержит достаточное evidence всех групп | audit_authorizations.audit_event_id/assignment_id/grant_id/assignment_version/authorized_data_code; audit.actor_staff_id | U(environment,audit_event_id,grant_id,authorized_data_code); F grant своего assignment; D Q06-event/actor/полная достаточность evidence по каждой фактически выданной группе | Q06 выбирает достаточный целый grant детерминированно по assignmentId/grantId. Current authorization проверяется B/T; старая audit-запись не даёт новых прав | A05, A24, A37, A52, A100, A103, A104 | P4, ACCESS |
| R048 · Q06: одна проекция и audit до выдачи | session.current_snapshot_version; snapshot/settings; staff/access/login guards; audit/evidence; restrictedGroups только API | T/D: согласованный snapshot/settings/access и целый audit до commit/выдачи. B summary обязательна; закрытые группы отсутствуют, разрешённые полны; corrupted не NULL/0/пустой объект | Q06: read/ADM-03 для session.*, read/ADM-02 для user.minimal_context (только user ID). Нет обходного raw read; ошибочный audit закрывает ответ | A05, A23, A24, A30, A37, A52, A53, A100, A104, A110 | P3/P4, ACCESS |

### 3.7. Событие и worker

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R049 · Одно неизменяемое событие успешного C06 | outbox_events.event_type/event_schema_version/consumer_name/command_receipt_id/session_id/session_version/snapshot_version/payload/occurred_at | U(environment,event_type,command_receipt_id,consumer_name); F receipt/session и snapshot; D полный START. L первый paper_session.started/v1, paper_start_observer, payload={}. W факт не редактируется | C06 создаёт outbox вместе со START; worker меняет только доставку, не суммы/IDs/payload. Это локальный observer, не внешняя отправка | A11, A13, A14, A33, A103, A108 | P4, OPS |
| R050 · Доставка имеет полный вариант состояния | outbox.delivery_state/attempt_count/next_attempt_at/lease_token/lease_until/last_safe_error_code/processed_at/version | L attempt 0…5; pending/retry_wait требуют next_attempt_at; processing обе lease-поля; processed время; retry_wait/needs_review код ошибки; прочие NULL по P4 | Worker W/T: initial pending/attempt0, переходы по H04; постоянная ошибка/формат или пятый сбой → needs_review, не удаление | A14, A40, A97, A108, A109 | P4, OPS |
| R051 · Lease не допускает поздний эффект/ACK | outbox.lease_token/lease_until/attempt_count/version/next_attempt_at | W/T: захват атомарно +1/new token; DB time lease=30 секунд без продления; проверка token/срока под lock перед effect и завершением. Старый token не меняет новую попытку | Worker B: processing budget5s, lock≤1s и остатку, один event, пустая очередь poll1s, delays1/5/30/120 после неудач; истёкший lease не ускоряет retry. Таймер не обычный CHECK | A14, A48, A70, A108, A109 | P4, OPS |
| R052 · Consumer dedup и завершение неделимы | consumer_event_receipts.consumer_name/event_id/result_code/result_session_id/processed_at; outbox processed fields | U(environment,consumer_name,event_id); target U outbox(environment,id,consumer_name), F consumer/event; D result=session события, processed требует receipt; W отметка неизменна | Worker один T effect/receipt/processed. Существующая целая отметка приоритетна даже после 5-й попытки, только ACK/recovery без шестого эффекта; damaged не отсутствие | A14, A20, A33, A100, A103, A108, A109, A112 | P4, OPS |

### 3.8. Staff, разрешения и входы

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R053 · Staff identity отдельна от User | staff_principals.id/status/authorization_version; staff_auth_identities.staff_principal_id/realm/provider/provider_subject/status/version | U identity(environment,realm,provider,provider_subject), target(environment,id,staff_principal_id); F principal; L realm=staff; W запрет переназначения/каскадного стирания | Auth/bootstrap подтверждает отдельных владельца 1 и владельца 2 одной роли owner; UUID/имя/email не доказывают, что люди разные. Не вводится is_admin обычного user | A23, A24, A30, A34, A107 | P4, AUTH |
| R054 · Assignment с полным опубликованным набором | staff_assignments.staff_principal_id/role_ref/role_revision_ref/status/valid_from/valid_until/revoked_at/revoke_reason_code/current_grant_set_version/version; grants.assignment_id/grant_set_version | L сроки и парность revoke, F principal/assignment, target U(environment,id,staff_principal_id); D current set непустой и целый по доверенной публикации; старые наборы immutable | Access publisher атомарно публикует полный набор, pointer/assignment.version/staff.authorization_version. Count>0 не доказывает соответствие доверенному role definition | A24, A30, A34, A100, A103, A104 | P4, ACCESS |
| R055 · Разрешение — целая строка grant | staff_assignment_grants.grant_key/action_code/section_code/data_type_code/product_mode/venue_scope/venue_id | U(environment,assignment_id,grant_set_version,grant_key), F assignment/venue; L venue one⇒ID, all⇒NULL, закрытые комбинации и paper. W immutable grant | B проверяет каждую строку целиком с current set/сроком/principal; нельзя склеить action/venue из разных назначений. Owner-пресет не исключение из актуальной авторизации | A05, A23, A24, A40, A104 | P4, ACCESS |
| R056 · Отзыв доступа конфликтует с зависимыми действиями | users.version; staff_principals.authorization_version; identity.version; assignment.version/current_grant_set_version; auth_sessions.version; controls.version | T/W: каждое значимое изменение детей/назначений/блокировки/identity/входа меняет соответствующий parent guard в одном T; операции читают те же guards по общему порядку | Auth/access/catalog/control publishers и C06/Q06. Serializable без протокола обновления родителей не объявляется доказанным отзывом; нужны обе очередности гонки | A16, A24, A25, A30, A47, A102, A104 | P1/P2/P4, OPS |
| R057 · Версия политики входа своего realm | login_policy_versions.realm/policy_code/max_lifetime_seconds/inactivity_seconds; login_policy_controls.realm/active_policy_version_id/version | U policy(environment,realm,policy_code), target(environment,id,realm); U control(environment,realm), F policy того realm; L положительные сроки; W опубликованная policy неизменна | Publisher/Auth сохраняют принятую user30/7 суток, staff8ч/30мин. Новый pointer+guard атомарно, старые входы не переписываются; отсутствие control не создаёт defaults | A01, A25, A30, A33, A40, A44 | P4 |
| R058 · Полный login связан с actor и identity | auth_sessions.realm/user_id/staff_principal_id/user_identity_id/staff_identity_id/provider/provider_session_ref/login_policy_version_id/assurance_code/authentication_evidence_ref/effective_* | L XOR principal/identity по realm, U(environment,realm,provider,provider_session_ref); F identity своего principal и policy realm; target unique login с realm+actor. D provider/realm/actor/пределы policy согласованы | Auth writer создаёт только после доказанного полного входа. B email/TOTP при требовании или Owner WebAuthn UV; значения assurance/FK сами не доказывают MFA. Secrets не Shadow | A01, A21, A22, A23, A25, A30, A40, A107 | P4, AUTH |
| R059 · Активность и отзыв не оживляют вход | auth_sessions.authenticated_at/last_user_activity_at/expires_at/effective_max_lifetime_seconds/effective_inactivity_seconds/revoked_at/revoke_reason_code/version | L парность revoke и абсолютный срок по закреплённым пределам; W неуменьшение активности, неизменные identity/политика входа; B/T проверка действительности до обновления | Только разрешённая foreground-активность; background/worker/Q06 другого пользователя не продлевают login. Logout исходного user login не отзывает независимые входы | A06, A25, A30, A44, A47, A70 | P4, AUTH |
| R060 · Один рабочий staff login | staff_login_slots.staff_principal_id/realm/current_login_id/version; auth_sessions.realm/staff_principal_id/revoked_at | U slot(environment,staff_principal_id), L realm=staff; F(environment,current_login_id,realm,staff_principal_id) → свой login; D/T новый полный login+отзыв старого+pointer вместе | Auth replacement после полной проверки. Неуспешный passkey не отзывает прежний; актуальный Q06 требует current login и все guards. Несколько ролей/вкладок не несколько slots | A24, A30, A100, A103, A104, A107 | P4, AUTH |

### 3.9. Границы БД, протоколы и эксплуатация

| ID / правило | Таблицы и поля | Способ обеспечения | Writer / граница ответственности | A01–A112 | Источник |
| --- | --- | --- | --- | --- | --- |
| R061 · Транспорт нельзя заменить CHECK БД | Запросы C04/C05/C06/claim до записи; затрагиваемые draft/review/CMD/FIN остаются без новых строк при раннем отказе | B: исходный UTF-8≤65 536 байт, depth≤8, без сжатия, duplicate names/unknown fields/coercion; правильные типы/NULL/raw. У БД нет поля с исходным wire body | Parser/gateway/API; диагностируется безопасно без тела/секретов. Размер/глубина на границе не означают валидность остальных правил | A40, A49, A50, A73, A74, A75, A76, A77, A78, A98, A99 | CONTRACT, ERR |
| R062 · Гонки, блокировки, бюджет и неизвестный commit | Guards/keys/slots/draft/ownership/session и записи соответствующей операции; никаких новых timeout/pending-колонок | T/W: принятый Serializable/lock order, одно соединение, полный rollback набора; только доказанные serialization/deadlock разрешают повтор в бюджете. Unique conflict — отдельное свежее чтение | B: C04/C05/C06/claim до 5s/3 подтверждённых rollback attempts с 50–150мс; неизвестный commit не rollback. Прочие API имеют свои бюджеты, worker отдельно R051 | A11, A12, A13, A16, A18, A27, A35, A47, A48, A67, A68, A69, A70, A71, A72, A100, A101, A102, A103, A104, A105, A106, A107 | OPS, CONTRACT |
| R063 · Чтение не создаёт деньги и не чинит историю | session/slot/current snapshot/settings; draft/current input/receipt details; все сохранённые record_schema_version | F/D защищают записи, B текущая авторизация→decoder→целостная выдача. Missing/unknown/corrupted после доступа — техническая недоступность без NULL→0, нового funding/key, ремонта/очистки slot | Q03/Q04/Q05/Q06/replay; read-only example не создаёт пользовательскую session. HTTP и locale не меняют outcome; no-store/поздние ответы — обязанности B/UI | A05, A06, A09, A10, A18, A23, A33, A52, A53, A81, A95, A106, A110 | P3/P4, CONTRACT, ERR |
| R064 · Совместимость всех сохранённых форматов | reviews/settings_revisions/session_snapshots/command_receipts.record_schema_version, receipt details и все обязательные связи | O/B: полный обход реальных строк изолированной копии для каждой пары тип/версия, не выборка/одно поле. Неизвестная пара/обрыв блокирует gate, пустой тип — нет данных для проверки | Compatibility runner; новая версия одного типа не меняет прочие, изменение структуры требует версии по принятому протоколу. Это не constraint и не разрешение restore/обновления | A20, A51, A79, A80, A81, A82, A83, A84, A85, A87, A91, A92, A93, A94, A95 | OPS, ERR |
| R065 · Доказательство проверки неизменяемо и отдельно | Все четыре форматных типа/полный scope ID; отчёт вне 34 таблиц: server/schema/copy/format-set/counts/results | O: защищённый внешний отчёт/manifest, полный охват и источник, новый ID для исправления/нового контекста. Нет придуманной report-таблицы или публичного дампа | Оператор/проверяющий; M05 ещё требует конкретного формата/хранилища/прав. Хеш доказывает целостность относительно доверенного manifest, не сам по себе происхождение | A87, A88, A89, A90, A91, A92, A93, A94 | OPS |
| R066 · Restore не возвращает право повторить эффект | Все 34 таблицы, Auth-история, ключи/consumer dedup/отзывы после точки копии; внешние backup/WAL | O: Auth+Shadow daily backup, 7 успешных вне сервера, необходимый WAL и подтверждение получателя; изолированный restore, запрет login/worker/изменений до доказанной сверки | Оператор/проверяющий. Успешное чтение копии не доказывает отсутствие более позднего START/revoke; нельзя восстановить старую копию ради rollback сервера с потерей новых данных | A20, A34, A84, A85, A86, A87, A106, A111 | OPS |
| R067 · Первый стенд без архива и очистки истории | command keys/receipts/details, consumer receipts/outbox, ownership/source FK и финансовая история | W/F/O: нет cleanup по login/draft TTL, нет повторного использования ID; сохраняются core/details/dedup и обязательные ссылки. Неожиданно missing details — повреждение | M04 для первого стенда закрыт отсутствием архива. A38/A112 — требования к будущему отдельному разрешённому архиву, не функция текущего среза и не повод разрабатывать её сейчас | A20, A34, A38, A63, A110, A112 | P4, OPS |
| R068 · Runtime не обходит ограничения | Все 34 таблицы и разрешённые пути INSERT/UPDATE/DELETE; API/worker/Auth/schema/backup/verifier роли БД | W: runtime не владелец схемы, не отключает FK/triggers и не редактирует immutable историю; workers ограничены доставкой/dedup, Q06 без raw-read обхода audit | Конкретные privileges/процедуры не написаны и не испытаны; суперпользователь/операторская порча не объявляется невозможной. Bootstrap/recovery не скрытый второй API доступа | A19, A23, A34, A41, A100, A103, A104, A110 | OPS, P4 |
| R069 · Владение и доступ подтверждает сервер | User/guest ownership и claim-цепочки; session.user_id; staff identities/login/assignments/grants/guards | B/T вместе с F/D: действующий actor/realm и разрешение каждой операции до выдачи/записи; чужой ресурс не раскрывается. FK принадлежности не доказательство текущей авторизации | Все API/read/replay; guest proof закрывается для переданного draft, staff проверяется целым grant. Без доказательства со второго устройства нет claim | A02, A05, A23, A24, A25, A26, A35, A52, A104, A107 | AUTH, ACCESS, C04 |
| R070 · Auth/claim/logout имеют собственный протокол | user/staff identity, auth_sessions/provider_session_ref, staff slot, claim receipt; защищённый контекст Auth вне Shadow | B/T: unknown verify/claim/logout выясняется по доверенному исходному контексту; не добавлять их в command_keys/receipts/Q05. Logout действует на исходный login, не новый после позднего ответа | Auth: C01–C03 10s без автоматического одноразового повтора; C07 5s/одна попытка/204 только подтверждённый отзыв. Claim свой 5s/3 rollback протокол, не обычный CommandReceipt | A01, A02, A06, A21, A22, A25, A26, A30, A35, A107 | AUTH, CONTRACT |
| R071 · Отображение не новая гарантия БД | locale, сохранённые IDs/versions/units/errors; requestId/nextAction/restrictedGroups/HTTP/no-store/экран — проекции, не новые колонки результата | B/UI: точный wire mapping, ru/en тексты, одинаковый финансовый смысл, текущие ссылки и запрет позднего перезаписывания новой формы. RequestId различается по HTTP, не по бизнес-команде | A10 включает mobile/desktop и визуальную проверку: реестр БД этого не доказывает. HTTP Q05=200 при найденном rejected не делает исход успешным | A05, A06, A09, A10, A29, A33, A39, A43, A45, A46, A52, A55 | CONTRACT, ERR |

## 4. Обязательные проверки до commit и пути обхода

| Агрегат | Минимальный корень проверки и затрагивающие пути | Ожидаемый отказ |
| --- | --- | --- |
| C04 input/CMD | key, receipt, details, draft и его current input pointer; create/update/unchanged, вставка parent без детей, любая попытка прямой правки raw/pointer/version/TTL | Неполный комплект или несогласованный переход откатываются целиком; exact replay не создаёт комплект |
| Claim | draft/current ownership, новая ownership/previous/receipt и claim audit; попытка второй передачи/подмены actor, отсутствие любого участника | Нет half-claim или перехвата; внешний Auth unknown сначала выясняется своим протоколом |
| Catalog publication | trader/current revision, новая revision и source/trader guards; policy/control pointer | Нет опубликованного pointer на чужую/отсутствующую revision и неизменённого guard при значимой дочерней правке |
| START | Session со всеми обязательными pointers, каждый дочерний элемент R037, slot/used draft, key/receipt/details, audit/outbox | Нет session без денег/двух entries/snapshot/audit/event; C04 или rejected не удовлетворяет C06 FK |
| Journal | Сам journal, flow и entries: ноль/одна/три строки, иные счета/unit/сумма; вставка parent без entries и любой запрещённый UPDATE/DELETE | Нет commit без ровно двух согласованных противоположных B |
| Snapshot publication | Session/current pointers и новый snapshot/settings/ledger; сравнение прежней version | Нет смешанного current состояния или отката pointer назад. Исторический snapshot не обязан равняться текущему |
| Grants и Q06 | Assignment/current set и все grants при публикации; Q06 event/evidence и актуальные guards при выдаче | Неполный набор/чужой actor/недостаточное evidence не проходит; audit failure закрывает защищённый ответ |
| Staff replacement | Новый login, прежний login/revoke, staff slot и актуальный principal/identity/assignment | Нет двух рабочих login или отзыва старого из-за неподтверждённого нового входа |
| Observer | Outbox/token/state, consumer receipt и локальный эффект; обработка/ACK/recovery при конкуренции | Старый lease не завершает новый; processed без корректной отметки запрещён; повтор не создаёт деньги |

Это перечень точек проверки, не разрешение выполнять запрещённый UPDATE/DELETE в рабочей базе ради теста. Для будущей приёмки понадобятся изолированные механизмы M02–M03. Значимая смена guards проверяется в обеих допустимых сериализованных очередностях; полнота одного snapshot транзакции сама по себе не доказывает отсутствие гонок.

Порядок критических Serializable-транзакций сохраняется из OPS: policy/catalog/control → principal/identity/access/login/assignment → command/claim key → user/staff slot → draft/ownership → session/финансовые записи/audit/outbox. Внутри группы — стабильный полный ключ. Уникальности/FK могут брать дополнительные locks: фактические deadlock/планы/отмена ещё требуют испытаний, реестр не объявляет их отсутствующими.

## 5. Обратный указатель: все 34 таблицы

Общие R001–R009 и R068 действуют по применимости полей на весь каталог; R064–R067 задают общий режим совместимости/хранения. В таблице указаны предметные правила сверх общих.

| Таблица shadow | Правила |
| --- | --- |
| users | R010, R011, R056, R069 |
| user_auth_identities | R010, R011, R058, R069 |
| setup_drafts | R004, R012, R013, R014, R015, R016, R017, R018, R019, R027, R030, R039, R044 |
| draft_ownerships | R012, R013, R014, R024, R030, R039, R044, R069 |
| venues | R015, R020, R055 |
| catalog_sources | R020, R021, R022, R024 |
| traders | R015, R020, R021, R022, R024 |
| trader_revisions | R021, R024, R030 |
| paper_policy_versions | R003, R022, R023, R024, R025, R031 |
| paper_controls | R022, R024, R027, R056 |
| setup_reviews | R004, R008, R024, R025, R026, R027, R030, R043, R064 |
| user_session_slots | R028, R029, R037, R062 |
| paper_sessions | R016, R028, R029, R030, R031, R032, R034, R035, R036, R037, R042, R048 |
| settings_revisions | R003, R025, R031, R034, R035, R037, R042, R064 |
| funding_flows | R003, R032, R033, R037, R042 |
| journals | R032, R033, R034, R037, R042 |
| journal_entries | R003, R033, R034, R037 |
| session_snapshots | R003, R008, R034, R035, R037, R046, R048, R049, R064 |
| command_keys | R038, R039, R040, R041, R044, R045, R062, R067 |
| command_receipts | R017, R018, R019, R037, R039, R041, R042, R043, R044, R045, R064, R067 |
| command_receipt_details | R008, R017, R018, R019, R041, R043, R063, R064, R067 |
| draft_claim_receipts | R014, R044, R046, R070 |
| audit_events | R008, R037, R042, R046, R047, R048, R068 |
| audit_authorizations | R047, R048, R055, R056 |
| outbox_events | R008, R037, R042, R049, R050, R051, R052, R067, R068 |
| consumer_event_receipts | R052, R067, R068 |
| staff_principals | R053, R054, R056, R058, R060, R069 |
| staff_auth_identities | R053, R056, R058, R069 |
| staff_assignments | R047, R054, R055, R056, R069 |
| staff_assignment_grants | R047, R048, R054, R055, R056, R069 |
| login_policy_versions | R057, R058, R059 |
| login_policy_controls | R057, R056 |
| auth_sessions | R046, R056, R057, R058, R059, R060, R070 |
| staff_login_slots | R048, R056, R060, R070 |

## 6. Обратный указатель: A01–A112

Каждый исходный критерий перечислен ровно один раз. Связи указывают на требования обеспечения, не на пройденные испытания. Если критерий содержит UI/Auth/эксплуатацию, его часть вне БД сохраняется; «не обеспечивается только БД» не означает исключение из приёмки.

| Исходный критерий | Связанные правила |
| --- | --- |
| A01 · Новый полный email-вход | R010, R011, R057, R058, R070 |
| A02 · Guest review → вход | R012, R013, R014, R024, R026, R044, R069, R070 |
| A03 · Fixed и percent | R002, R015, R020, R025, R031, R034, R037, R042 |
| A04 · Первый EMPTY | R028, R032, R033, R034, R037 |
| A05 · Та же session у сотрудника | R034, R035, R046, R047, R048, R055, R063, R069, R071 |
| A06 · Reload/logout/login/язык | R059, R063, R070, R071 |
| A07 · B300 / F21 / q3,2% | R003, R004, R023, R025, R026, R043 |
| A08 · Диапазоны и шаги | R003, R004, R023, R025, R026, R043 |
| A09 · Read-only example | R063, R071 |
| A10 · RU/EN и размеры экрана | R015, R063, R071 |
| A11 · Два C06 одного key | R028, R032, R037, R038, R040, R041, R046, R049, R062 |
| A12 · Два разных key/venue | R020, R028, R029, R062 |
| A13 · Crash до/после commit | R037, R041, R046, R049, R062 |
| A14 · Дубликат outbox | R049, R050, R051, R052 |
| A15 · Другой payload / stale draft | R018, R027, R038, R039, R040, R045 |
| A16 · Отзыв controls/user | R011, R022, R027, R056, R062 |
| A17 · Текущая блокирующая session | R026, R028, R029, R045 |
| A18 · БД недоступна / unknown | R045, R062, R063 |
| A19 · Ошибочные ссылки/баланс/дубль | R001, R003, R013, R017, R021, R024, R025, R028, R030, R031, R032, R033, R034, R037, R039, R041, R042, R068 |
| A20 · Restore и повтор доставки | R052, R064, R066, R067 |
| A21 · Неверный/повторный verify | R010, R011, R058, R070 |
| A22 · Email enumeration/лимиты | R011, R058, R070 |
| A23 · U2 подменяет scope U1 | R001, R010, R012, R013, R015, R020, R024, R038, R039, R042, R044, R046, R048, R053, R055, R058, R063, R068, R069 |
| A24 · Нет/отозван scope staff | R047, R048, R053, R054, R055, R056, R060, R069 |
| A25 · CSRF/logout/секреты | R011, R056, R057, R058, R059, R069, R070 |
| A26 · Другой девайс без draft | R012, R013, R014, R044, R069, R070 |
| A27 · Два draft / save/start | R015, R016, R029, R062 |
| A28 · Изменение/expiry после review | R006, R007, R016, R019, R022, R024, R026, R027, R043 |
| A29 · Новый login, старый key | R038, R040, R044, R045, R071 |
| A30 · Два staff login / revoke | R048, R053, R054, R056, R057, R058, R059, R060, R070 |
| A31 · Учёт/units/initial flow | R003, R031, R032, R033, R034, R037, R042 |
| A32 · Точность/шаг процента | R003, R023, R025, R033 |
| A33 · Старые ответы/immutable/policy | R005, R007, R021, R022, R023, R031, R035, R049, R052, R057, R063, R071 |
| A34 · Provider deletion/DB-роли | R007, R010, R053, R054, R066, R067, R068 |
| A35 · Claim/retry/два user | R012, R013, R014, R038, R044, R062, R069, R070 |
| A36 · Новая trader revision | R007, R020, R021, R022, R024 |
| A37 · Сбой audit / потеря ответа | R046, R047, R048 |
| A38 · Архив подробностей receipt | R041, R067 |
| A39 · ID/bigint/UTC/зона | R001, R003, R006, R020, R036, R071 |
| A40 · Невалидные типы/NULL/JSON | R001, R002, R003, R008, R012, R015, R023, R025, R026, R043, R050, R055, R057, R058, R061 |
| A41 · Ключи/реальные query plans | R009, R068 |
| A42 · Обычная дата/gap/overlap | R036 |
| A43 · Миллисекунды/равные времена | R005, R006, R071 |
| A44 · До/ровно/после expiry | R006, R016, R027, R036, R057, R059 |
| A45 · Версии 1/2/10/большой bigint | R005, R029, R071 |
| A46 · Отказ RU/EN после перевода | R007, R040, R043, R045, R071 |
| A47 · Expiry за время lock wait | R006, R016, R022, R027, R056, R059, R062 |
| A48 · 1/2/3 конфликта/unknown | R045, R051, R062 |
| A49 · JSON 16384/16385 байт | R008, R026, R043, R061 |
| A50 · Неизвестное поле C06 | R002, R061 |
| A51 · Обновление читателя формата | R008, R064 |
| A52 · Повтор Q04/Q06 | R035, R046, R047, R048, R063, R069, R071 |
| A53 · Нет/повреждён snapshot | R034, R035, R048, R063 |
| A54 · Create/edit/no-op/read/fail C04 | R004, R015, R017, R018, R019, R038, R039, R041, R042 |
| A55 · Stale no-op против replay | R017, R018, R019, R039, R043, R044, R045, R071 |
| A56 · raw 20 → 20.00 | R004, R017, R018, R019, R040 |
| A57 · C04 vs START/used | R016, R017, R018, R027, R030 |
| A58 · Editable/expired/used | R006, R016 |
| A59 · Нет worker / used-пара | R006, R016 |
| A60 · Source review/rollback | R024, R027, R030, R031, R037 |
| A61 · Два key на один review | R030, R032 |
| A62 · Несколько review одного draft | R016, R030, R032 |
| A63 · Удаление источников | R007, R030, R031, R067 |
| A64 · Snapshot + pointer | R035 |
| A65 · Pointer 3→4/3/2 | R035 |
| A66 · as_of раньше created_at | R006, R035 |
| A67 · 5 секунд / 3 rollback | R062 |
| A68 · Пауза и остаток | R062 |
| A69 · Таймаут внутри commit | R045, R062 |
| A70 · Монотонный timer/скачок UTC | R006, R051, R059, R062 |
| A71 · 4 секунды потрачено | R062 |
| A72 · Остаток 80 мс, пауза 120 | R062 |
| A73 · Тело 65536/65537 байт | R061 |
| A74 · UTF-8/пробелы тела | R061 |
| A75 · Контрольный секрет в oversized | R061 |
| A76 · Повтор JSON key | R040, R061 |
| A77 · Глубина 8/9 | R061 |
| A78 · Сжатое тело | R061 |
| A79 · Новый формат только snapshot | R008, R064 |
| A80 · Реестр/декодеры | R008, R043, R064 |
| A81 · Неизвестный формат | R008, R063, R064 |
| A82 · Четыре разных v1 | R008, R064 |
| A83 · Смысловое изменение / опечатка | R008, R064 |
| A84 · Кандидат не читает историю | R064, R066 |
| A85 · Возврат старого сервера | R064, R066 |
| A86 · Возврат после новых записей | R066 |
| A87 · Изолированная проверка | R064, R065, R066 |
| A88 · Состав отчёта | R065 |
| A89 · Изменился контекст проверки | R065 |
| A90 · Исправление ошибочного отчёта | R065 |
| A91 · Фактический неизвестный формат | R064, R065 |
| A92 · Один тип пуст | R064, R065 |
| A93 · Ошибка вне выборки / обрыв | R064, R065 |
| A94 · Диагностика повреждения | R064, R065 |
| A95 · Обязательный text v1 | R002, R008, R063, R064 |
| A96 · 64/65 цифр и символов | R003, R004, R025 |
| A97 · Переполнение счётчика | R005, R029, R050 |
| A98 · Невалидное тело C04 | R002, R004, R039, R042, R061 |
| A99 · Компактный JSON/Unicode | R008, R043, R061 |
| A100 · Сбой каждого шага | R014, R017, R018, R021, R032, R033, R035, R037, R041, R046, R047, R048, R052, R054, R060, R062, R068 |
| A101 · Отсутствующие key/slot | R028, R029, R038, R041, R062 |
| A102 · Save/revoke/controls vs C06 | R011, R022, R056, R062 |
| A103 · Неполный комплект/циклы | R001, R013, R014, R017, R021, R024, R031, R032, R033, R034, R037, R039, R041, R042, R046, R047, R049, R052, R054, R060, R062, R068 |
| A104 · Q06 vs revoke/login replace | R047, R048, R054, R055, R056, R060, R062, R068, R069 |
| A105 · Классы ошибок | R045, R062 |
| A106 · Q05 сначала не видит receipt | R029, R044, R045, R062, R063, R066 |
| A107 · Unknown Auth/claim/staff | R010, R011, R014, R044, R045, R053, R058, R060, R062, R069, R070 |
| A108 · Crash/lease/consumer receipt | R049, R050, R051, R052 |
| A109 · Пять сбоев/формат/late | R050, R051, R052 |
| A110 · Нет/повреждён snapshot/receipt | R008, R019, R034, R035, R043, R044, R048, R063, R067, R068 |
| A111 · Backup до start/revoke | R066 |
| A112 · Cleanup и старый повтор | R007, R052, R067 |

A38/A112 сохраняются как исторические требования к будущему разрешённому архиву: в первом стенде архива/очистки нет (R067). A64–A66 и варианты будущих состояний не создают новые публичные команды; проверочный механизм M02–M03 ещё проектируется. A10 требует собственной UI-проверки, A21–A26/107 — доказанного Auth-протокола, A84–A94/111 — операционных доказательств. Полевая карта ERR не закрывает все DTO, M01 не объявлен завершённым.

## 7. Связь с уже подготовленными примерами и сбоями

| Область реестра | Существующие документальные примеры / карточки | Что должно стать доказательством позже |
| --- | --- | --- |
| R003/R004/R023–R027 | S01–S16, N01–N22, D01–D03, J01–J04; F07/F22 | Точные исходные значения/сохранённые нормализованные числа/ошибки, отсутствие частично действующих настроек |
| R012–R019/R038–R045 | C04-E01–E16, D03–D08, J05–J09; F02/F03/F05/F06/F17 | Полный SAVE/claim либо откат, неизменный receipt и источник Q03, корректный доступ после claim |
| R028–R037/R062 | S01–S16, D07/D14/D15; F01/F04/F08/F09/F10/F11/F23 | Один START, полный ledger/snapshot/источники, правильные поколения и обе очередности гонок |
| R046–R048/R053–R060 | K01–K07, D09–D11, J10; F12/F13 | Текущий actor/login/grant, целое evidence/audit и отсутствие раскрытия закрытых групп |
| R049–R052 | D13; F14/F15/F16 | Точный event/consumer scope, отсутствие второго эффекта, lease/token и пятая попытка |
| R008/R061/R063–R068 | D12/D16, J09/J10; F17–F24 | Техническая недоступность при порче, полный scan/внешнее evidence и доказанный барьер восстановления |

Ссылки: [все синтетические примеры](database-synthetic-examples.md), [24 карточки сбоев](database-fault-reconciliation.md). Номера S/N/K/E/D/J/F — идентификаторы документов; новый код продукта или автоматический тест этим не создаётся. Проверка наличия ссылки/покрытия A не доказывает работоспособность ограничения.

## 8. Что закрыто и что осталось

**Закрыто документально по поручению:** единый реестр 71 группы ограничений/гарантий, указатель всех 34 таблиц и полная двусторонняя связь с A01–A112; способы обеспечения и их границы разделены. Принятые решения, строгая полнота C06, C04/last_input_receipt_id, ERR и история ADR сохранены.

**Не выполнено:** DDL/миграции/кодек/функции/процедуры/реальные роли и ограничения, DB/API/Auth/concurrency/DST/restore испытания, проверка query plans или совместимости кандидатов. Нельзя считать столбец «способ обеспечения» существующим SQL или пройденной проверкой.

**Оставшиеся зависимости:** остальные полные DTO и защищённые H01-протоколы (включая guest proof/claim/logout unknown); конкретные publisher/DB privileges и библиотечная совместимость; изолированные стендовые состояния/механизмы M02–M03; формат/хранилище/права evidence M05. M04 первого стенда — отсутствие архива, без новой разработки. Полный M01 не закрыт одной картой ограничений.

Следующий возможный документальный блок по отдельному поручению — точный состав изолированных наборов M02–M03 с исходными строками, допустимой контролируемой порчей, ожидаемыми дельтами и условиями изоляции; затем протокол будущей приёмки. Этот реестр не начинает эти блоки или реализацию автоматически.

## 9. Документальные состояния для проверки механизмов M02–M03

30.10.2026 · [Спецификация изолированных состояний](database-isolated-test-states.md) связывает I01–I22 с существующими R/A/F. BASE сохраняет обычные ограничения; PUB публикует целый snapshot/current state; NEG должен доказывать отказ нужного ограничения, а не случайного более раннего барьера; BAD/READ-FAULT проверяют чтение повреждения на разных уровнях. Корректный BASE не содержит новых lifecycle-кодов или торговых таблиц.

Реестр R001–R071 и его исходные связи не изменены. Документальный состав M02–M03 подготовлен; физические future-state представления, конкретные инструменты/roles и все испытания остаются. Наличие карточки не доказывает работу D/FK/guards/Auth или выполнение A.

## 10. Применение ограничений в транзакциях C04/C05/C06/claim

30.10.2026 · [Карта транзакций](database-transaction-boundaries.md) связывает существующие R001–R071 с защищёнными чтениями, неделимыми наборами записи, полнотой до commit и восстановлением исхода. Ранний отказ, durable rejected, подтверждённый rollback и unknown разделены; циклические ссылки не становятся nullable ради вставки. Карта не меняет строки правил, принятый общий порядок или строгую полноту C06. Конкретные режимы блокировок и парные гонки остаются следующим блоком. Механизмы не реализованы и не испытаны.
