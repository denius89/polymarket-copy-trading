# БД первого сценария — сводная передача будущему бэкенду

29.10.2026 · **Сводная передача и заключительный блок 4 приняты целиком. Согласование физической схемы завершено.** [ADR-0064 §33](../../decisions/0064_first_session_database_contract.md). Все четыре блока приняты; baseline финального принятия: main `77bcba67547bd6448799d792a36757c180e41395` после PR №164. H01–H06 сохраняются как инженерные зависимости будущего бэкенда. Код, SQL, миграции, работающий API/БД и развёртывание отсутствуют в рамках этой работы. Другому чату сообщения не отправлялись.

## 1. Что передаётся и что имеет приоритет

Путь первого сценария: полный вход → выбор трейдера → настройки → сохранённая проверка → явный запуск пустой демо-сессии → чтение **этой же** сессии в админке с актуальными правами. Бэкенд будет разрабатываться отдельно по [его заданию](backend-chat-brief.md). Общие источники: [README](README.md), [ADR-0064](../../decisions/0064_first_session_database_contract.md), [логическая модель](data-model.md), [команды](commands.md), [приёмка A01–A112](acceptance.md), [auth-policy](auth-policy.md). Исторические проектные HTTP-пути и открытые форматы не считать уже работающим API.

Принятые продуктовые решения имеют приоритет над удобством схемы/библиотеки. Эти документы детализируют их физически, не разрешают менять диапазоны, сроки, права или финансы. Имена snake_case относятся к БД, не обязывают менять DTO. Любой конфликт будущей реализации с принятым смыслом требует явного решения; технические названия/проверяемая реализация внутри смысла не требуют новой серии продуктовых согласований.

## 2. Реестр таблиц и границы

| Блок | Статус | Таблицы shadow |
| --- | --- | --- |
| [1 — пользователь и черновик](database-physical-design.md) | Принят | users, user_auth_identities, setup_drafts, draft_ownerships |
| [2 — каталог и проверка](database-physical-catalog-review.md) | Принят | venues, catalog_sources, traders, trader_revisions, paper_policy_versions, paper_controls, setup_reviews |
| [3 — сессия и деньги](database-physical-session-ledger.md) | Принят | user_session_slots, paper_sessions, settings_revisions, funding_flows, journals, journal_entries, session_snapshots |
| [4 — служебные записи](database-physical-operations-access.md) | Принят | command_keys, command_receipts, command_receipt_details, draft_claim_receipts, audit_events, audit_authorizations, outbox_events, consumer_event_receipts |
| [4 — доступ и вход](database-physical-operations-access.md) | Принят | staff_principals, staff_auth_identities, staff_assignments, staff_assignment_grants, login_policy_versions, login_policy_controls, auth_sessions, staff_login_slots |

Итого 34 прикладные таблицы в документальном проекте; количество не означает 34 реализованных компонента или расширение пользовательского сценария. Провайдерские OTP/TOTP/WebAuthn credentials/challenges, ключи, recovery-секреты и внутренние таблицы Auth сюда не копируются. Их проверенная интеграция — H01, а не право обойти согласованное восстановление. Рыночные ордера/позиции/резервы/signals/score, treasury и настоящие платежи не добавлены. Начальный состав сотрудников: владелец 1 и владелец 2, два личных равноправных Owner.

## 3. Общий контракт полей

| Семейство | Хранение и обмен | Проверка |
| --- | --- | --- |
| Scope/ID | environment + серверный UUID v4; clientCommandId — UUID v4 клиента до отправки | Environment доверенный серверный; все FK в своей среде; ID не право доступа |
| Деньги | Нормализованные целые n/d в numeric без scale; в API строки целых | Конечность, d>0, gcd=1, zero=0/1, до 64 цифр без знака на компонент первого пустого запуска; без округления |
| Проценты | Integer сотых процентного пункта | 3%→300, /10000; общий DTO сохраняет явно выбранную внешнюю единицу; шаги ADR-0058 |
| Version/sequence/generation | Bigint, всегда строки API | Разные счётчики; положительные, транзакционные, без сброса при переполнении |
| Время | Timestamptz, UTC с Z, миллисекунды | Серверные часы; при now=expiry уже недействительно; deadline + IANA + версия алгоритма/tzdb сохраняются |
| Формат записи | Text recordSchemaVersion=v1 отдельно для review/settings/snapshot/receipt | Общий реестр декодеров, неизвестное не приводить к известному и не повторять эффект |
| Ввод | Raw text ≤64 Unicode code points на числовое поле | NULL/пустая строка различимы, не обрезать; неактивный ввод не effective settings |
| Дополнительный JSON | Типизированные безопасные поля ≤16 КиБ компактного UTF-8 каждое | Деньги/owner/обязательные связи вне JSON; диагностике не отдавать полную запись |
| C04/C06 запрос | 64 КиБ исходного UTF-8, глубина 8 (корень 1), без сжатия и повторных ключей | Отказ без обрезания/частичного изменения; canonical hash не подменяет транспортную проверку |

Policy чисел остаётся [paper-mvp-settings-v1](../../policies/paper-mvp-settings-v1.json). Deadline — 14 календарных дней в закреплённой IANA-зоне, gap→первый существующий момент, overlap→первое вхождение. Draft — 7 дней после настоящего изменения, review — 10 минут. User login — 30 суток/7 без активности; staff — 8 часов/30 минут и один рабочий вход. Изменение срока входа применяется к новым полным входам по действующей политике, не переписывает историю.

## 4. Сводная матрица связей и ограничений

Ниже `env` означает environment; записи полных ключей/nullable-вариантов даны в таблицах блоков. Исторические номера guards — значения, не FK на изменяемый текущий номер.

| Связь / инвариант | Ключ или проверка | Когда |
| --- | --- | --- |
| User/staff identity → один постоянный principal | Unique env/realm/provider/subject + FK principal | При связывании; никакого email-merge/переназначения |
| Draft ↔ current ownership своего draft | Composite env/draft/ownership, максимум одна guest и одна user ownership в первом сценарии | Deferred FK до commit создания/claim |
| Claim receipt ↔ claimed ownership | Unique env/draft; составные ссылки и сравнение previous/user/current | Одна транзакция claim, закрытие guest handle |
| Draft → trader своей venue | FK env/venue/trader | При выборе/сохранении; недоступный trader не удаляется |
| Trader ↔ current revision своего source/venue | Unique source/external ID, полный composite scope | Начальная пара и смена revision атомарны с guards |
| Review → draft/исторический ownership/точная revision/policy | Composite IDs + immutable copies; версия draft историческая | C05; C06 заново сравнивает текущие версии/сроки |
| Slot → current session того же user/paper/slot | Unique env/user/mode, FK env/session/slot/user/mode | C06; generation=1 у первой сохранённой строки, последующие изменения pointer +1 |
| Session → исходные draft/review | Unique env/draft и env/review **по всей истории**, composite review/draft/ownership | До commit C06; used draft ссылается обратно |
| Session ↔ current settings / initial funding / current snapshot / ledger sequence | Обязательные same-session FK и проверка полноты | Создание/публикация атомарно; нельзя ссылаться на чужую version |
| Settings revisions | Unique env/session/sequence и env/session/command receipt; previous своей session | Первая 1, затем полные immutable revisions; редактирование активной session сейчас не реализуется |
| Initial funding ↔ journal | Unique env/session/initial-kind, flow↔journal, тот же receipt/session | До commit, сумма=B settings1, не второе зачисление поверх ledger |
| Journal → ровно две entries | Unique journal/line и journal/account; same-unit/session FK, точные противоположные n/d | Deferred полнота/баланс; добавление третьей/изменение опубликованной запрещены |
| Snapshot → settings/ledger своей session | Unique env/session/version; current pointer монотонен; current state совпадает | Публикация, а не чтение; нет автоматического ремонта |
| Key ↔ receipt | Unique env/user-realm/actor/type/clientCommandId, обязательные двусторонние FK | Резервирование и финальный результат одной транзакцией; никаких committed pending |
| Receipt ↔ C06 session/settings/funding/journal/snapshot | Успех со своими result IDs, составные ссылки и совпадающий actor | Deferred полнота; отказ не содержит создаваемой session |
| Receipt → details/start audit/outbox | Наличие обязательных детей при создании успешного результата | До commit; ключ и receipt сохраняются при будущем разрешённом архиве деталей |
| Q06 audit → authorization evidence → assignment/grant | Обязательная достаточная evidence, неизменяемые grants и историческая assignment version | В одной транзакции с текущими правами и выбранным snapshot |
| Outbox → consumer receipt | Unique env/consumer/event, совпадающие consumer/resource/result | Локальный эффект и receipt атомарны; processed без доказательства запрещён |
| Staff assignment → current grant set | Полный набор одной версии, current pointer/guard и principal guard | Нет частичной публикации/смешивания action/venue разных grants |
| Login → policy/identity/principal своего realm | Условно полные composite FK; скопированные пределы своей policy | Только после full-auth, затем текущая проверка срока/отзыва |
| Staff slot → единственный рабочий login своего principal | Unique env/staff + composite login/realm/principal | Новый полный вход и отзыв прежнего атомарно |

Обычные FK/unique/NOT NULL/локальные CHECK дополняются отложенными constraint triggers для полноты/согласованности и отдельной защитой неизменяемости/монотонных переходов. Проверки покрывают **все** пути изменения, в том числе родителя без детей. Прикладные роли не отключают ограничения и не имеют DDL-прав. Не требуется и не допускается превращать межстрочный баланс в CHECK, читающий другие таблицы. Конкретные процедуры и испытания — H05.

## 5. Индексы: минимум и кандидаты под запросы

PK и все перечисленные unique обязательны как целостность, включая составные target keys для FK. Одинаковые индексы поверх них не создаются. Составные «избыточные» target keys, включающие ID и scope, нужны для принадлежности, а не для произвольного ускорения. Реальная стоимость/планы проверяются на выбранной версии БД.

| Обращение | Уже поддерживает ключ | Дополнительный кандидат, только после плана |
| --- | --- | --- |
| Q03 draft по ID / его reviews | PK draft/review | env/draft/created_at/id у reviews только для списка; env/owner_user/draft у ownership для перечисления своих draft |
| Q02 каталог | Trader/source uniques | env/catalog_source/start_allowed/id для выдачи разрешённого списка |
| Q04/Q06 current session | Unique slot env/user/paper, PK session, unique snapshot env/session/version | История env/user/started_at/id только если запрос действительно нужен |
| Settings/ledger/entries | Unique session/sequence и journal/line | Не индексировать все суммы или account code отдельно без запроса |
| Q05 / повтор C06 | Unique полного ключа и receipt/key | Для поиска по client ID обязательна вся область actor/type, не глобальный ID |
| Claim retry | Unique claim env/draft | Отдельный индекс по секрету/сырому guest handle запрещён |
| Q06 назначения | PK principal/assignment | env/staff_principal/status для выборки назначений; grants по assignment/current set поддерживает unique prefix |
| Текущий staff login / отзыв user logins | Unique staff slot; auth_session PK | env/user_id и env/staff_principal_id для списков/отзыва, по реальным запросам |
| Очередь worker | Outbox PK, unique consumer/event receipt | Раздельные частичные индексы по env/consumer/next_attempt_at/id для pending/retry_wait и env/consumer/lease_until/id для processing |
| Журнал выдачи | Audit PK и request/command uniques | env/session/occurred_at/id либо env/actor/time при разрешённом запросе истории |

Служебные индексы на referencing FK выбираются по фактическим join/lock/delete-планам; PostgreSQL не создаёт их все автоматически. Реальные EXPLAIN/нагрузка ещё не выполнены. Историю синтетического стенда пока не удалять, индексы под автоочистку не являются разрешением включить её.

## 6. Границы транзакций и восстановления

Общий порядок: активные policy/catalog/control → principal/identity/access guards, login/assignments → command/claim key → user/staff slot → draft/ownership → session/финансовые дети/audit/outbox. Стабильный полный ключ внутри группы. Несовместимые изменения доступа используют те же guards; добавление дочерних прав повышает guard родителя. Предварительное чтение не обходит проверки после ожидания.

C06: максимум 3 попытки всего, только подтверждённые serialization/deadlock rollback, общий бюджет 5 секунд по монотонным часам, паузы 50–150 мс. Unique conflict/бизнес-отказ/unknown commit не объявляются автоматически этим классом повтора. При неизвестном исходе сначала исходный key из основного согласованного хранилища; непонятный receipt не исполняется заново. Старый успешный receipt требует текущего доступа, но не повторного прохождения новых правил запуска.

Worker: 5 захватов всего; паузы 1/5/30/120 секунд, bounded lease/token, consumer dedup в транзакции эффекта; после исчерпания/неизвестного формата needs_review. Сбой доставки не отменяет успешную session. Позднее событие не строит заднюю версию snapshot и не выполняет повторное финансирование. Внешние эффекты не разрешены этим пакетом.

Q06: актуальная авторизация, один snapshot и audit «Данные разрешены к выдаче» с evidence в одной транзакции; ошибка аудита закрывает выдачу. Аудит не доказывает получение ответа человеком. Read не повышает snapshot/version/asOf и не продлевает пользовательский login. Проверка доступа предшествует раскрытию существования/сумм; запрещённые значения не заменяются нулями.

Backup/restore: ежедневно, последние 7 успешных зашифрованных копий вне сервера; изолированный restore, рабочие входы/worker закрыты. Сверить историю, дедуп, эффекты и изменения прав/команд после точки backup. Если доказательств недостаточно, доступ/повторы остаются закрыты. Полный обход **всех** записей review/settings/snapshot/receipt по независимым v1 и другим реально найденным форматам; неизвестный формат блокирует, пустой тип — «Нет данных для проверки». Неизменяемый отчёт каждого прогона хранит сервер/схему/копию/форматы/результаты. Где хранить сам отчёт и доказательства — H06; поддельный «пройденный отчёт» или рабочая копия сейчас не создаются.

## 7. Сводные зависимости — инженерная работа, не новые продуктовые вопросы

| ID | Что передать/закрыть бэкенду | Прежние зависимости | Что уже определено |
| --- | --- | --- | --- |
| H01 Auth и доверенная привязка | Совместимость конкретного пользовательского/staff-компонента; guest proof/digest; full-auth/MFA/passkey; session refs, cookies/CSRF/rotation/revoke; foreground; bootstrap и принятый recovery | B1-D1/D2, auth-policy | Отдельные realms, постоянные principals, сроки, один staff login, без автоназначения/обхода восстановления |
| H02 Общие форматы/канонизация | Полные DTO и 4 декодера v1, hash/canonical registry, policy/source/calculation codes, event schemas, безопасные причины/ошибки | B1-D3, B2-D1/D2/D3, B3-D1 | Точные единицы/лимиты/NULL, immutable history, typed scope, explicit absent/present; новый код не меняет смысл |
| H03 Действующие назначения | Закрытый реестр role/action/section/data scope/status, проверяемая публикация grants/источника, отзыв/guards, выбор evidence для Q06 | B1-D1, B3-D1, контракт админки | Два равноправных Owner; read отдельно от остальных действий; полная область каждого grant; текущие права |
| H04 Доставка | Конкретные lease/renewal/timeouts, registry локального consumer, crash/reconciliation на 5-й попытке | Data-model §23 | Пять попыток, паузы, receipt dedup, no-repeat funding, needs_review, без внешних эффектов |
| H05 Схема и интеграционные доказательства | После отдельного поручения: выбранная PostgreSQL/driver, точная арифметика, constraint triggers, DB-роли/процедуры, планы запросов, fault/concurrency-тесты | B3-D4 и сводные механизмы | Полные документальные таблицы/связи/инварианты, единый atomic start и Serializable |
| H06 Срок/restore/совместимость | Проверенная библиотека времени/tzdb и DST; политика форматов/совместимые изменения; отчёт/хранилище restore evidence, сверка после backup | B3-D3, data-model §16–23 | 14 календарных дней, сохранённый deadline, 7 копий, закрытый restore, отсутствие автоочистки/авторемонта |

B1-D4 замыкается блоками 2–4 по venue/trader/session/claim receipt. B2-D4 замкнут **принятым блоком 3** по generation/слоту/session/settings; DTO spelling остаётся H02. B3-D2 замкнут принятым блоком 4 по документальным связям command key/receipt/actor/audit/outbox; реализация/испытания относятся к H05. Не писать в статусе «все зависимости решены»: компонентные контракты H01–H06 ещё требуют проверки. Их работа входит в отдельное техническое проектирование/реализацию после поручения, не в самовольную смену продукта.

## 8. Порядок продолжения и критерии приёмки

29.10.2026 · Подготовлены [24 сценария сбоев и сверки](database-fault-reconciliation.md), блок 3 проверочного пакета. У каждой карточки есть A-ID, синтетический исходный набор, точка сбоя, ожидаемые записи и порядок установления исхода. Особо отделены rollback/unknown commit, effect receipt/пятая попытка worker и непокрытый backup период. H01–H06/M01–M05 не закрыты документом; реальные испытания, SQL, код и миграции не выполнялись.

29.10.2026 · Подготовлены [синтетические примеры](database-synthetic-examples.md): 16 допустимых наборов обеих площадок/fixed/percent, 22 случая неверного ввода и 7 контекстов связей/повторов/чтения. Для будущих испытаний зафиксированы точные P/D, две проводки, пустой snapshot, дельты и A-ID; отдельные примеры не объявлены полным покрытием приёмки. H01–H06 и M01–M05 остаются открытыми зависимостями; fixtures/SQL/код не создавались.

29.10.2026 · Дополнительно подготовлена [матрица целостности A01–A112](database-integrity-matrix.md): ожидаемые дельты операций, обратная карта 34 таблиц и стыки M01–M05. Она не меняет принятую схему/критерии и не означает выполненные испытания. Особо требуется закрыть в H02/H05 хранение/чтение результата точного повтора C04 (A54–A57): согласованный command_keys сейчас описывает C06, поэтому готовая защита C04 из него автоматически не следует. Остальные стыки — тестовые состояния последующих этапов, контролируемая публикация/повреждение snapshots, будущий архив и отчёты совместимости — остаются в соответствующих H01–H06.

1. **Выполнено 29.10.2026:** все четыре физических блока и сводная передача приняты целиком; итог зафиксирован в ADR-0064 §33. Согласование в этом чате завершено.
2. Отдельный чат бэкенда читает этот пакет и подтверждает совместимость H01–H06: DTO/форматы, Auth/права, операции/неизменяемость и выбранные компоненты. Не создавать параллельные сущности/денежные правила по одному макету. Автоматическая отправка сообщения туда не поручена.
3. Только после отдельного поручения на код — минимальная схема и API вместе, совместимые миграции и изолированный стенд. Принятие схемы не является разрешением deploy или изменения реальных доступов.
4. Реальная приёмка по A01–A112: оба допустимых способа размера и обе площадки на явно синтетическом источнике; точное выбранное B; одинаковая session/settings/snapshot у клиента/админки; гонки/дубли/отзыв/unknown outcome; worker crash; DST и restore. Проверки других этапов не заменяются фиктивными успешными заглушками.

Предметная вычитка этого пакета: ключ C06 не зависит от login; обязательные дети и обратные ссылки имеют механизм до commit; guest claim не переиспользует guest review; финансирование не удваивает cash; staff-read не даёт write/export; scope grants не смешивается; receipt/consumer защита сохраняется после потери ответа/копии. Это **документальная сверка**, не выполненные тесты БД/API/Auth/restore.

Проверки репозитория выполняются отдельно: структура/ссылки, политика файлов, тесты обслуживающих скриптов и чистота diff. Даже их успешное прохождение не означает готовый первый сценарий.

Технические основания индексов/ограничений: [PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html), прочитано 29.10.2026. Выбор конкретной серверной версии и испытания остаются H05.
