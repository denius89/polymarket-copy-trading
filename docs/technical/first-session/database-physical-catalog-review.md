# Физическая схема БД — блок 2: каталог, правила и проверка настроек

02.11.2026 · **Текущий документальный состав —36 таблиц:** приняты q02_read_scopes и q02_read_scope_sources, [физический каталог §16](database-physical-catalog-review.md), [Q02 §§16–17](database-q02-catalog-design.md). Упоминания34 ниже — прежняя базовая схема/история; её связи и полнота сохранены. Реальная БД, SQL, код, миграции и испытания не создавались.

02.11.2026 · **Блоки 1–2 DB-API-10 приняты:** два read_visible отражены в §§3–4/13; единый снимок/общий отпечаток — [проект Q02 §§6–8](database-q02-catalog-design.md). DB-API-09 закрыт документально; DB-API-10 ещё требует cursor/H01. Старые статусы ниже исторические. Только документы, без SQL/кода/миграций/испытаний.

02.11.2026 · Блок 2: [карта API-полей DB-API-01–08/11](database-api-field-map.md) отражена в этой физической спецификации; подробности — в заключительном разделе. Baseline main `6a4e2fe04f8b4bb11dcbe09812724ffec84cb0c0` (PR №185). Прежние пометки о невыбранных внешних формах уточнены; C04/карта ошибок и строгий C06 сохранены. Только документы, без кода, SQL, миграций и испытаний. DB-API-09/10 и компонентные зависимости остаются открытыми.

30.10.2026 · [Реестр физических ограничений](database-constraint-register.md) связывает принятые таблицы/поля с механизмами обеспечения и A01–A112. Это свод существующих гарантий и границ БД/бэкенда; новые правила, SQL и испытания не добавлены.

29.10.2026 · По поручению владельца после PR №177 завершена [точная карта ошибок API ↔ БД](database-error-field-map.md): контейнеры reasons/fieldErrors, закрытые params и источник ошибок Q03. Это уточнение документов в рамках T01–T17, без пересогласования C04. Прежние пометки о незавершённости именно этой карты ниже исторические; полные DTO/Auth/компоненты и испытания остаются отдельно.

29.10.2026 · Заключительный блок принят после PR №176 и отражён; [итог дополнения §§4–5](database-c04-addendum.md), [ADR-0064 §37](../../decisions/0064_first_session_database_contract.md). Реестры H02/H03, параметры H04–H06 и T01–T17 действуют вместе с физическими полями ниже. Исторические пометки «ещё выбрать код/бюджет» не отменяют последующее принятие. Полевая карта JSON/DTO, компоненты и предметные испытания остаются отдельно; только документы.

29.10.2026 · **Блок 2 принят целиком 29.10.2026 после PR №162.** [Фиксация — ADR-0064 §31](../../decisions/0064_first_session_database_contract.md). [Блок 1](database-physical-design.md) принят; общие соглашения и зависимости сохраняются. Baseline: main `8c1719f8d9aecf1a4ee11b050ab27c4da3dcbc4a`. Семантика — [ADR-0064](../../decisions/0064_first_session_database_contract.md), числовые правила — [ADR-0058](../../decisions/0058_paper_mvp_numeric_settings_policy.md) и [paper-mvp-settings-v1](../../policies/paper-mvp-settings-v1.json). Только документ, без SQL, кода и интеграций.

## 1. Состав и общий принцип

Девять таблиц: venues, catalog_sources, traders, trader_revisions, paper_policy_versions, paper_controls, setup_reviews и принятые02.11.2026 q02_read_scopes, q02_read_scope_sources (§16). Они раскрывают уже принятые Venue/Trader/TraderRevision/PolicyVersion/SetupReview и их текущие pointers/controls. У всех собственных строк PK `(environment, id)`, UUID v4; ссылки включают environment. Ниже общие поля перечислены явно или вынесены в общую строку: это отдельные колонки, не объект JSON.

Неизменяемы trader_revisions, опубликованные paper_policy_versions и setup_reviews. Текущая доступность/указатели/версии guards меняются отдельно. Исторический review не проверяется FK на изменяемый текущий номер версии: он сохраняет номер как факт, а C06 сравнивает его с актуальным состоянием под блокировками.

## 2. `shadow.venues` — площадки

| Колонка | Тип | Обязательна | Правило |
| --- | --- | --- | --- |
| environment, id | text, uuid | Да | Составной PK |
| code | text | Да | Стабильный код `polymarket` либо `limitless`; unique(environment, code) |
| display_name | text | Да | Название площадки для каталога, не идентификатор доступа |
| version | bigint | Да | Версия изменяемых сведений, от 1 |
| created_at, updated_at | timestamptz | Да | Серверные моменты |

Наличие площадки в справочнике не означает, что её реальные данные или торговое исполнение доступны. Записи обеих площадок сохраняют принятую venue-neutral модель. Здесь нет ключей кошелька, endpoint credentials, подключения live или настроек рыночного профиля. Изменение отображаемого имени не меняет code/ID.

## 3. `shadow.catalog_sources` — источник каталога и его guard

| Колонка | Тип | Обязательна | Правило |
| --- | --- | --- | --- |
| environment, id | text, uuid | Да | PK |
| venue_id | uuid | Да | FK → venues той же среды |
| source_environment | text | Да | Непустая серверная область источника; отличается от среды самого приложения |
| data_origin | text | Да | synthetic для первого стенда; реальный источник/fallback этим не разрешён |
| source_ref | text | Да | Безопасная ссылка/идентификатор набора данных, без bearer-ссылок и secrets |
| read_visible | boolean | Да | Публикация источника для Q02; false скрывает все его карточки, не заменяя start_enabled; принято DB-API-10 блок 1 |
| start_enabled | boolean | Да | Текущий допуск использования этого источника для первого paper-запуска |
| unavailable_reason_code | text | Условно | Обязателен при start_enabled=false; при true NULL |
| version | bigint | Да | Текущая catalog/control version, от 1; guard изменений этого каталога |
| created_at, updated_at | timestamptz | Да | Серверные моменты |

Unique(environment, venue_id, source_environment). Для составных FK добавить unique(environment, id, venue_id). Идентифицирующие venue/source_environment и тип происхождения не переписываются под другим источником; новый источник получает отдельную строку. Изменения каталога, влияющие на проверку/выбор, повышают version той же строки в транзакции: добавление/замена используемой revision, изменение допустимости трейдера и controls. Guard меняется и при добавлении дочерней записи, чтобы устаревший Serializable-снимок не счёл каталог неизменным.

Для первого стенда источник явно синтетический. Сбой реального источника не переключает пользователя на fixture. Свежесть каталога и version не являются обещанием свежей цены/книги заявок. Это технический ресурс допуска, не новый экран управления или разрешение подключить площадку.

## 4. `shadow.traders` — постоянная идентичность и текущий допуск

| Колонка | Тип | Обязательна | Правило |
| --- | --- | --- | --- |
| environment, id | text, uuid | Да | PK |
| venue_id | uuid | Да | Площадка трейдера |
| catalog_source_id | uuid | Да | FK `(environment, catalog_source_id, venue_id)` → catalog_sources |
| external_trader_id | text | Да | Непустой ID в источнике; нормализация только по проверенному контракту этой площадки |
| current_revision_id | uuid | Да | Текущая revision именно этого трейдера; обязательная циклическая ссылка до commit |
| read_visible | boolean | Да | Публикация карточки для Q02 только при видимом разрешённом source; обязательное значение, без NULL/default при чтении |
| start_allowed | boolean | Да | Текущая допустимость выбора этого трейдера для запуска |
| unavailable_reason_code | text | Условно | При start_allowed=false обязателен; иначе NULL |
| version | bigint | Да | Trader control version; повышается при смене текущей revision/допуска/read_visible |
| created_at, updated_at | timestamptz | Да | Серверные моменты |

Unique(environment, catalog_source_id, external_trader_id). Вместе с уникальностью source это эквивалент области venue/sourceEnvironment/externalTraderId. Один адрес на разных площадках не объединяется. Дополнительные ключи `(environment, venue_id, id)` и `(environment, id, venue_id, catalog_source_id)` нужны для FK draft/review/revision, а не как произвольные ускоряющие индексы.

Связь setup_drafts `(environment, venue_id, trader_id)` из блока 1 замыкается на traders `(environment, venue_id, id)`. Если трейдер не выбран, trader_id NULL; если выбран, venue_id обязателен. Недоступность не удаляет строку и не разрушает прежний draft/review. Изменение допуска сериализуется с запуском по общему порядку, включая catalog guard.

## 5. `shadow.trader_revisions` — использованные сведения о трейдере

| Колонка | Тип | Обязательна | Правило |
| --- | --- | --- | --- |
| environment, id | text, uuid | Да | PK неизменяемой записи |
| trader_id, venue_id, catalog_source_id | uuid | Да | Составной FK на ту же идентичность traders |
| revision | bigint | Да | Номер версии этого трейдера, от 1; unique(environment, trader_id, revision) |
| displayed_name | text | Да | Имя, которое показывали; не user ID и не допуск |
| data_origin | text | Да | Сохранённое происхождение использованных сведений |
| source_ref | text | Да | Безопасное доказательство/ссылка на исходный набор |
| catalog_version_at_creation | bigint | Да | Номер каталога при публикации этой revision; историческое значение, не FK на текущую version |
| observed_at | timestamptz | Да | Момент получения/подготовки исходных сведений; для fixture не изображает live-наблюдение |
| created_at | timestamptz | Да | Момент сохранения revision |

Unique(environment, trader_id, id) обеспечивает current_revision_id → revision того же трейдера. Для review предлагается дополнительный ключ `(environment, id, trader_id, venue_id, catalog_source_id)`. При первом создании trader и revision сохраняются вместе с заполненной current-ссылкой и отложенной проверкой цикла. При новой revision создаётся новая строка, затем атомарно меняются current pointer, trader version и catalog guard. Исторические ссылки не переписываются.

Полная торговая статистика, score и денежные показатели сюда не дублируются. Поля происхождения — часть неизменяемого факта; соответствие источнику проверяется при записи. Новая revision не переводит test fixture в реальные данные.

## 6. `shadow.paper_policy_versions` — опубликованная числовая политика

Одна строка — опубликованная неизменяемая версия правил paper-настройки. Редактор черновиков политики и публикация как административная функция не добавляются. Неопубликованные параметры не становятся активными через эту таблицу. Ниже `*_n` и `*_d` — две отдельные numeric-колонки без округляющего scale: конечные целые, d>0, нормализованная дробь, до 64 цифр на компонент. Поля percent — integer в сотых процентного пункта, не доли и не проценты интерфейса.

| Колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| environment, id | text, uuid | Да; PK |
| policy_version_code | text | Да; unique(environment, policy_version_code), первая версия `paper-mvp-settings-v1` |
| source_ref, source_hash, calculation_version | text | Да; ссылка на принятое решение/версионированный источник, проверяемый отпечаток его точного содержимого, версия правил расчёта; source_hash = sha256: + 64 строчные hex-цифры точных байтов источника; calculation_version = paper-settings-calculation-v1 |
| currency_unit | text | Да; `virtual_USD` для денежных параметров первого paper-среза |
| budget_min_n, budget_min_d; budget_max_n, budget_max_d | numeric | Да; B min=100/1, max=1000/1 |
| budget_step_n, budget_step_d; budget_origin_n, budget_origin_d; budget_default_n, budget_default_d | numeric | Да; шаг=10/1, начало сетки=100/1, default=200/1 |
| fixed_min_n, fixed_min_d; fixed_max_n, fixed_max_d | numeric | Да; F min=5/1, абсолютный max=200/1 |
| fixed_step_n, fixed_step_d; fixed_origin_n, fixed_origin_d; fixed_default_n, fixed_default_d | numeric | Да; шаг=1/1, начало сетки=5/1, default=20/1 |
| fixed_selection_limit_rule | text | Да; `floor_min_session_position_and_day_usd` по действующей версии |
| retain_unchanged_fixed_on_cap_reduction | boolean | Да; true по ADR-0058/0056; не создаёт команду изменения активной сессии в первом срезе |
| copy_percent_min, copy_percent_max, copy_percent_step, copy_percent_origin, copy_percent_default | integer | Да; q: 100, 2000, 50, 100, 300 соответственно |
| market_percent_min, market_percent_max, market_percent_step, market_percent_origin, market_percent_default | integer | Да; p: 500, 2000, 100, 500, 1000 |
| loss_percent_min, loss_percent_max, loss_percent_step, loss_percent_origin, loss_percent_default | integer | Да; d: 1000, 3000, 100, 1000, 1500 |
| copy_percent_basis | text | Да; `confirmed_individual_trader_buy_notional` |
| budget_limit_basis | text | Да; `session_budget_usd` для p/d |
| percent_product_min_n, percent_product_min_d | numeric | Оба NULL у v1: у процентного результата нет продуктового минимума $5. Это не отменяет минимум инструмента будущего торгового этапа |
| signal_max_age_seconds | integer | Да; 30 |
| signal_max_age_editable | boolean | Да; false |
| signal_max_age_applies_to | text | Да; `signal`, не свежесть книги |
| published_at, created_at | timestamptz | Да; серверные моменты публикации/сохранения |

Наличие min/max/default не разрешает исправлять ввод автоматически. При новом fixed-выборе сохраняется ограничение F ≤ floorUSD(min(P,D)), где P=B×p/100 и D=B×d/100; проверяется точной арифметикой. p>d допустимо. Конкретные числа выше только переносят принятую policy v1 в колонки. Проценты пересчитаны в сотые процентного пункта, смысл не изменён.

Не хранить одновременно редактируемый JSON с теми же обязательными числами. При загрузке опубликованной policy проверяются содержимое, hash и согласованность колонок с версионированным источником; hash сам по себе не доказывает корректность. Изменение принятой политики — новая строка/код, без изменения старых review/settings. Неизвестные calculation/rule codes не исполняются как знакомые.

## 7. `shadow.paper_controls` — активная политика и текущий допуск среды

| Колонка | Тип | Обязательна | Правило |
| --- | --- | --- | --- |
| environment, id | text, uuid | Да | PK |
| mode | text | Да | Только `paper`; unique(environment, mode) |
| active_policy_version_id | uuid | Да | FK на опубликованную paper_policy_versions той же среды |
| start_enabled | boolean | Да | Явный серверный допуск первого сценария; не клиентский флаг |
| unavailable_reason_code | text | Условно | При start_enabled=false обязателен, иначе NULL |
| version | bigint | Да | Guard активной policy и системного допуска, от 1 |
| created_at, updated_at | timestamptz | Да | Серверные моменты |

Отсутствие controls или пригодной опубликованной policy закрывает проверку/новый запуск, не создаёт default «на лету». Переключение активной версии и повышение guard сохраняются атомарно. Чтение старого успешного receipt не требует повторно проходить новые правила запуска: оно требует текущего права читать результат. Эта таблица не является механизмом live или новым набором глобальных финансовых лимитов.

## 8. `shadow.setup_reviews` — неизменяемый результат проверки

Одна строка хранит показанные значения и контекст проверки C05. Физический проект предусматривает и предметно отклонённую проверку: неверный ввод сохраняется как raw-копия, а отсутствующие нормализованные параметры явно отличимы от нулей. Это не превращает техническую ошибку БД, отсутствие доверенного источника политики или неполный вход в успешную проверку. Ошибка формы запроса до обработки C05 может не создавать review; точные формы ответов приняты и отражены [картой §6](database-api-field-map.md); реализация/проверка B2-D3 остаётся.

| Колонки | Тип | Обязательность / смысл |
| --- | --- | --- |
| environment, id | text, uuid | Да; PK |
| record_schema_version | text | Да; `v1`, соответствует логическому recordSchemaVersion |
| draft_id | uuid | Да; FK на setup_drafts той же среды |
| draft_version | bigint | Да; проверенный номер ввода, не FK на изменяемую текущую version |
| ownership_id | uuid | Да; FK `(environment, draft_id, ownership_id)` → draft_ownerships |
| owner_kind | text | Да; guest/user, совпадает с указанной неизменяемой ownership |
| owner_user_id | uuid | Для user обязателен и совпадает с ownership; для guest NULL |
| venue_id | uuid | Выбранная площадка, FK на venues; NULL только если выбор ещё не определён и allowed_to_start=false |
| catalog_source_id, trader_id, trader_revision_id | uuid | Для выбранного известного трейдера все заполнены вместе с venue_id и связаны составным FK на одну trader_revisions; иначе все три NULL в предметном отказе. Частично заполненная тройка не допускается |
| catalog_version, trader_control_version | bigint | Обязательны вместе с выбранной trader revision; исторические версии guards, не FK на текущие номера |
| policy_version_id, paper_control_id | uuid | Да; ссылки на использованные опубликованные правила и controls той же среды |
| paper_control_version | bigint | Да; номер guard на момент проверки |
| selected_mode | text | fixed/percent либо NULL, если ещё не выбран; копия выбора, не переключатель после создания review |
| raw_budget, raw_fixed_amount, raw_copy_percent, raw_market_limit_percent, raw_loss_limit_percent | text | Копия исходных строк draft, включая NULL/пустую строку; до 64 code points каждая. Неактивный ввод не становится действующим |
| proposed_timezone | text | Копия выбранной IANA-зоны либо NULL, если ещё не определена |
| normalization_valid | boolean | Да; удалось ли получить полный валидный набор числовых настроек по указанной policy |
| budget_n, budget_d | numeric | Обязательная нормализованная пара при normalization_valid=true; иначе оба NULL |
| fixed_amount_n, fixed_amount_d | numeric | Только при валидном fixed; иначе оба NULL |
| copy_percent | integer | Только при валидном percent; иначе NULL |
| market_limit_percent, loss_limit_percent | integer | При normalization_valid=true обязательны; иначе NULL |
| effective_market_limit_n, effective_market_limit_d; effective_loss_limit_n, effective_loss_limit_d | numeric | При normalization_valid=true обязательны: точные P/D; иначе NULL |
| slot_observation | text | `not_applicable` для guest; `absent` либо `present` для user, только после серверной проверки слота |
| expected_slot_generation | bigint | Только при slot_observation=present; иначе NULL с явным смыслом, не невыясненное состояние |
| allowed_to_start | boolean | Да; результат проверки на тот момент, не разрешение обойти проверки C06 |
| requires_authentication | boolean | Да; у guest всегда true и allowed_to_start=false |
| primary_reason_code | text | Обязательная безопасная основная причина при allowed_to_start=false; при true NULL |
| reason_details | jsonb | Да; объект ровно reasons/fieldErrors, оба массива обязательны; при разрешённом review оба []. Primary_reason_code согласован с первым reason. Полная форма — [карта §2–4](database-error-field-map.md), до 16 КиБ на весь объект |
| warnings | jsonb | Да; массив закрытых объектов ровно code/params: SYNTHETIC_DATA, COPYING_NOT_CONNECTED, params={}, без повторов и в этом порядке, только применимые установленные предупреждения. Отсутствие — []; NULL/{} не массив. ≤16 384 байта компактного UTF-8 на всё поле. Отдельно от reasons/fieldErrors; точные правила §12 |
| checked_at, expires_at, created_at | timestamptz | Да; expiry через 10 минут после checked_at; запись неизменяема |

### 8.1. Полнота и исторические связи

- При normalization_valid=true заполнены B, p, d, точные P/D и ровно один действующий F/q. Все дроби — конечные целые n/d, d>0, gcd=1, zero=0/1, до 64 цифр на компонент. Данные соответствуют raw выбранного режима и указанной policy; проверяется без округления. Это условие числовой валидности, не вся авторизация запуска.
- При normalization_valid=false все нормализованные поля NULL, allowed_to_start=false и причина обязательна. Raw-копия остаётся для объяснения. Не создаётся частичный набор «действующих» настроек из части успешно разобранных полей.
- allowed_to_start=true требует полного пользовательского ownership, normalization_valid=true, определённых трейдера/revision/зоны, проверенного слота, пригодных controls и отсутствия препятствий. Гость всегда requires_authentication=true; любое true требует allowed_to_start=false. Для разрешённого C05 от user требуется подтверждённый доступ и requires_authentication=false. Недействующий вход не обходится созданием review от имени user; текущая авторизация проверяется при каждом запросе.
- Согласованность owner_kind/owner_user_id с историческим ownership проверяется до commit. При claim старый guest review остаётся связан с guest ownership; current_ownership_id draft меняется отдельно. C06 требует соответствие именно текущему владельцу.
- Не ставить FK от draft_version к текущему setup_drafts.version, catalog_version к catalog_sources.version или control versions к текущим guards: иначе обычная правка разрушит историю. FK защищает постоянные IDs, а актуальность сравнивает транзакция C06.
- Для следующих таблиц нужен уникальный ключ `(environment, id, draft_id, ownership_id)`; он позволит связать будущую session с точной исходной проверкой. Историческое поле checked_at не меняется при просмотре; expiry и старый отказ не исправляются «на месте».

### 8.2. Пустой слот и неполная проверка

Различение absent/present/not_applicable не создаёт новую бизнес-сущность. Если слота действительно нет, C05 фиксирует absent; при C06 отсутствие перепроверяется под защитой уникального ключа/владельца до создания слота. Если чужая операция уже создала или заняла слот, отсутствие из review не считается актуальным. Generation=1 первого сохранённого слота задан [блоком 3](database-physical-session-ledger.md); API expectedSlot.state/generation принят и отражён в §12. Нельзя подставить NULL вместо неизвестного ответа БД.

Если числовой ввод валиден, но трейдер недоступен, слот занят или нужен вход, review сохраняет валидные показанные параметры и отказ. Если трейдер вообще не выбран, тройка catalog_source_id/trader_id/trader_revision_id NULL и отказ явный; выбранная venue_id сохраняется независимо, чтобы не терять показанный выбор площадки. Дополнительное безопасное пояснение не заменяет типизированную ссылку и не изображает полный trader reference. Неподдерживаемый формат/непрочитанные controls/ошибка хранилища — техническая недоступность, не ложный business review.

### 8.3. Граница записи C05 и запуска C06

В одной согласованной транзакции C05 читаются draft/current ownership, опубликованная policy, текущие guards и слот, создаётся собственная копия review. Новые права/трейдеры/политика во время ожидания не заменяются молча. C05 не создаёт session, настройки активной сессии, funding или денежный snapshot.

C06 под тем же общим порядком проверяет current ownership/draft version, guards, выбранную trader revision, slot observation/generation, вход и сроки. Старое allowed_to_start=true само по себе не разрешает запуск. Значимые изменения требуют нового review и отдельного подтверждения; неизменяемая история сохраняется. Зафиксированный прежний successful receipt обрабатывается как прежний результат, а не как новый C06.

## 9. Связи, ограничения и индексы этого блока

| Инвариант | Механизм в проекте |
| --- | --- |
| Один код площадки в среде | Unique(environment, venues.code) |
| Источник принадлежит конкретной площадке | FK и unique(environment, venue_id, source_environment) |
| Внешний trader ID не смешивается между источниками | Unique(environment, catalog_source_id, external_trader_id) |
| Current revision принадлежит своему trader | Составной FK environment/trader/revision; начальный цикл проверяется до commit |
| Draft выбирает trader своей venue | FK environment/venue/trader из блока 1 |
| Review не ссылается на чужую revision/ownership | Составные FK для полного trader scope и draft/ownership; проверка owner-варианта |
| Старые review живут после изменения текущих записей | Исторические версии — значения; ссылки на IDs и неизменяемые revisions, без FK на текущий номер |
| Неопубликованные/неизвестные правила не становятся активными | Active pointer только на опубликованную policy; проверка поддерживаемых rule/calculation codes |
| Невалидное число не попадает в effective settings | Условная полнота по normalization_valid/selected_mode; точные проверки и отказ без округления |
| Изменение каталога/допуска не теряется для запуска | Повышение соответствующих guards в той же транзакции, Serializable и общий порядок locks |

PK/unique выше обеспечивают целостность; не дублировать их одинаковыми индексами. Кандидат чтения каталога `(environment, catalog_source_id, read_visible, id)` и поиска reviews по `(environment, draft_id, created_at, id)` добавляется только при соответствующем запросе и проверенном плане. Start_allowed не фильтр видимости Q02; разрешённые start-disabled остаются в списке. Q02/Q03/C06 и чтение review по ID не требуют заранее индексировать все display names, JSON warnings или сроки. Набор FK-проверок и плана удаления сводится после всех блоков; физического удаления используемых источников/policy/revisions/reviews сейчас нет.

## 10. Зависимости и проверка документа

| ID | Что ещё детализируется | Граница |
| --- | --- | --- |
| B2-D1 | Коды data_origin/source_environment, external ID normalization и безопасные source refs | Бэкенд/будущие адаптеры подтверждают реальные значения; fixture не выдаётся за live |
| B2-D2 | Формат отпечатка policy, calculation/rule code registry и сохранение опубликованного источника | Версии и числа ADR-0058 уже приняты; ни новый алгоритм, ни новые лимиты не выбираются |
| B2-D3 | Документальные формы review v1, reasons/fieldErrors и warnings определены [картой ошибок](database-error-field-map.md), [картой API §6](database-api-field-map.md) и §12; остаются исполняемые codecs/проверки | Физический проект отличает raw/нормализованный набор и отказ; API не реализуется этим чатом |
| B2-D4 | Начальный generation и точные составные связи slot/session/settings | Блок 3 замкнёт ссылки и вариант отсутствующего слота, без нового запуска/сброса истории |

Документально сверено с ADR-0058 и policy JSON: B/F/q/p/d, шаги/origins/defaults, предел fixed, отсутствие $5-минимума процента, p>d и сигнал 30 секунд сохранены. Предметные проверки будущей реализации: чужая площадка/источник, новая revision при C06, смена active policy, guest claim со старым review, невалидный raw, занятый/отсутствующий слот, точные P/D и fixed-граница. Это план проверки, не выполненные DB/API-тесты.

Технические источники прочитаны 29.10.2026: [PostgreSQL Numeric Types](https://www.postgresql.org/docs/current/datatype-numeric.html), [Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html). Numeric без объявленного scale не подменяет проверки конечности/целочисленности; межстрочную согласованность нельзя считать обеспеченной одним CHECK строки.

**Блок 2 принят целиком**, включая явно указанные технические зависимости. Блоки 3–4 также приняты; [сводная передача](database-backend-handoff.md) фиксирует завершение согласования и инженерные зависимости. SQL, миграции и код по-прежнему не начинать.

## 11. Отражённые реестры, review v1 и приоритеты

Источники — актуальный first-session-registry-v2 и backend-contracts §§3–9/18–19; прежние коды review/политики из v1 сохранены, новое значение Q02 не включается в причины review. Source refs/environment/external ID normalization остаются проверяемыми ссылками/контрактом адаптера, не произвольным enum. Policy paper-mvp-settings-v1 и calculation paper-settings-calculation-v1 неизменяемы. Source_hash хеширует точные байты закреплённого источника; это не канонизация command-jcs-v1.

Review v1 имеет свой полный формат, отдельный от version draft и current policy. raw_loss_limit_percent → rawDailyBuyLimitPercent; loss_limit_percent → dailyBuyLimitPercent; effective_loss_limit_n/d → effectiveDailyBuyLimit. Сотые процентного пункта БД → decimal-строка API, n/d → сокращённые целочисленные строки. При normalization_valid=false нормализованный набор весь NULL; допустимая неполнота raw не превращается в частично действующие настройки.

По одному fieldError на активное поле: REQUIRED→INVALID_DECIMAL→OUT_OF_RANGE→INVALID_STEP→FIXED_LIMIT_EXCEEDED. Порядок массива: бюджет, размер выбранного режима, рынок, дневной лимит. Зависимый fixed-предел вычисляется только при корректных B/p/d; собственные проверки F независимы. Неактивный raw не даёт ошибки настройки, но обязан пройти структуру/длину. Смысл params принят T04; точные имена и физическое размещение fieldErrors внутри review.reason_details определены [картой ошибок](database-error-field-map.md). Новая колонка не добавляется.

Для разрешённого отрицательного review приоритет: AUTH_REQUIRED guest → SESSION_NOT_SETTLED → CURRENT_SESSION_EXISTS → CAPABILITY_UNAVAILABLE → VENUE_REQUIRED → TRADER_REQUIRED → SIZING_MODE_REQUIRED → TIMEZONE_REQUIRED → NUMERIC_SETTINGS_INVALID. В capability: PAPER_START_DISABLED → CATALOG_SOURCE_DISABLED → TRADER_START_DISABLED; только применимые достоверно установленные причины. Сначала проверяется законность создания review из доступного актуального draft; техническая недоступность не отрицательный review. Warnings SYNTHETIC_DATA/COPYING_NOT_CONNECTED запуск не запрещают.

C05:5s/до 3 подтверждённых rollback-попыток; unknown прекращает автоматические повторы, возможен явный новый review, прежний возможный результат сохраняется. C05 не получает CommandReceipt/Q05. Успешное создание любого review — HTTP 200, allowedToStart=false не техническая ошибка. Точные DTO/JSON-map отражены в [карте API §6](database-api-field-map.md), карте ошибок и §12; публикация источников, исполняемые codecs/компонентная совместимость и испытания остаются. Документальные формы не доказывают готовность B2-D2/B2-D3 в реализации.

## 12. Отражение полного review и warnings

02.11.2026 · [Карта §§3.2/6](database-api-field-map.md) фиксирует все поля API без новых колонок. Review выбирается по своему id и выдаёт собственные raw/owner/guards/policy/числа/сроки; текущие draft/ownership/policy/catalog не подменяют исторический результат. При claim гостевой review не становится пользовательским. Для C06 нужен новый user C05 и принятые проверки актуальности.

| Колонки / вариант | Требование к форме и источнику |
| --- | --- |
| draft_id/draft_version/proposed_timezone | C05 проверяет указанную версию и совпадение зоны с сохранённым draft; другая зона той же версии — INVALID_REQUEST без review, старая версия — VERSION_CONFLICT. Изменение зоны сначала C04; null может дать предметный TIMEZONE_REQUIRED |
| *_n/*_d нормализованного набора | Конкретные пары §8 → Money.n/d как канонические целочисленные строки; при normalization_valid=false все семь числовых полей API null, не частичные Money и не нули |
| copy_percent/market_limit_percent/loss_limit_percent | Сотые п.п. → Percent с ровно двумя десятичными знаками: 50 → «0.50». При валидных числах выбран только F либо q; неактивное нормализованное поле null |
| raw_loss_limit_percent/loss_limit_percent/effective_loss_limit_n,d | Внешние rawDailyBuyLimitPercent/dailyBuyLimitPercent/effectiveDailyBuyLimit; дневной лимит новых покупок, не stop-loss |
| slot_observation/expected_slot_generation | expectedSlot: guest только not_applicable без generation; user absent без generation либо present с положительной строкой generation. Существующий свободный слот — present. Неизвестное чтение не absent |
| warnings | Отдельный неизменяемый массив §8; code/params по принятой API-форме, не пересчёт по текущему источнику, не новая блокирующая причина |
| reason_details/primary_reason_code | Прежняя [карта ошибок](database-error-field-map.md); warnings не добавляются в reasons/fieldErrors и не меняют их порядок |

В warnings каждый объект имеет ровно code и params, params ровно {}; code только из указанных двух, без дублей и с сохранённым относительным порядком. Пустой массив допустим при установленном отсутствии предупреждений; NULL, {}, пропущенный ключ, лишнее поле или неизвестный code не заменяются []. Лимит 16 384 байта относится к целому компактному UTF-8 warnings отдельно от reason_details, по прежнему правилу измерения [карты ошибок §7](database-error-field-map.md). Превышение при подготовке — техническая ошибка до commit без усечения массива; найденная порча/неподдерживаемый формат при чтении — RECORD_UNAVAILABLE/503, без частичного review.

Способ обеспечения остаётся [R008/R026](database-constraint-register.md): закрытый формат/полнота/размер и неизменяемость, доверенный C05 устанавливает применимость предупреждений, API проверяет формат выдачи. Это спецификация проверки, не созданный CHECK/decoder или проведённое испытание. Запрет повторов относится к code; смена порядка свойств JSON-объекта не меняет смысл, порядок элементов массива значим. Record_schema_version=v1 родителя задаёт формат; отдельной версии внутри warnings нет. Ранее реально сохранённый иной JSON не объявляется совместимым без отдельной сверки.

Контекст реестра — актуальное издание first-session-registry-v2; его новый CATALOG_CHANGED относится только к Q02, не к review/warnings. Четыре сохранённых формата остаются v1. Коды первого сценария/числовая policy не меняются. DB-API-10 (наблюдение каталога/курсор/guards) не закрывается источниками review.

## 13. Принятые блоки 1–2 Q02: видимость и согласованное состояние

02.11.2026 · [DB-API-10 §§6–8](database-q02-catalog-design.md) согласованы. Добавлены только проектируемые catalog_sources.read_visible и traders.read_visible, boolean NOT NULL. Доверенная подготовка явно задаёт false, true публикуется лишь с полным валидным current-циклом. Новых таблиц/истории страниц/сохраняемого отпечатка нет.

Изменение S.read_visible атомарно с S.version; изменение T.read_visible атомарно с T.version и S.version. Положительные guards без сброса/ABA/переполнения; скрытие не разрушает FK/историю. Уже опубликованный synthetic-набор при будущей подготовке имеет явно подтверждённые true и фактические версии после публикации. Start-disabled и hidden различны, прежние unavailable_reason_code относятся к start-флагам и не получают нового значения для скрытия.

Q02 берёт одну Serializable-картину основного хранилища для всех источников/guards/карточек и продолжения. Внутренний fingerprint включает весь серверно разрешённый набор до read_visible-фильтра, свои paper/source/trader guards/current pointers и доверенную область чтения; формат/криптография — следующий блок. H01 ещё должен дать источник/защиту/версию области. Один снимок сам по себе не решает внешнюю авторизацию.

Карта всех 17 полей — §2 документа Q02. Current Q02 не заменяет историческую revision review/session. C05/C06 используют прежние проверки актуальности guards, C04/его повтор/карта ошибок и strict C06 не пересматриваются; новые бизнес-причины не добавлены. QCAT01–QCAT20 — будущие примеры, испытания не выполнялись.

## 14. Принят точный cursor Q02 — без новых колонок

02.11.2026 · [DB-API-10 §§9–10/12–13](database-q02-catalog-design.md) принят владельцем целиком; [ADR-0064 §52](../../decisions/0064_first_session_database_contract.md). Восемь полей cursor формируются из разрешённого текущего контекста, позиции страницы и fingerprint полного состояния §13. Manifest берёт P/S/T/current R; JCS/SHA-256/AEAD — обязанности доверенного слоя выдачи, не новые хранимые JSON/hash/key-поля.

read_visible/версии/current-цикл и все34 таблицы сохраняются. Ключевой набор вне Shadow; история страниц/таблица cursor не создаются. Q02 не пишет CMD/review/session/финансы/audit Q06 и не выполняет внутренний retry. Текущий H01 обязателен; его readContextId/scopeRevision и привязка ещё зависимость. Принятие codec не доказывает производительность/изоляцию/права writer. QCAT01–QCAT36 не выполнялись; SQL/код/миграции не начинались.

## 15. Q02 reader identity — существующие источники, без новых полей

02.11.2026 · [Q02 §14](database-q02-catalog-design.md) принят: readContextId user использует постоянный users.id, guest — уже согласованный постоянный Auth guest UUID. Физические колонки/34 таблицы остаются прежними. Исторический actor_guest_context_id/ownership не самостоятельное доказательство текущего гостевого чтения; вымышленный FK на внутреннюю Auth-таблицу не вводится.

Точная передача [QH01–QH08 §15](database-q02-catalog-design.md) отделяет этот источник от незавершённых proof/guest bootstrap/scopeRevision и атомарной привязки к catalog snapshot. Codec/состав Manifest/guards/C04/строгий C06 не изменены. QID01–QID08 — будущие проверки, не созданные данные/испытания.

## 16. Принятое расширение Q02: область чтения и разрешённые источники

02.11.2026 · Владелец явно принял две таблицы **в документальном проекте**, с расширением34→36. [Q02 §§16–17](database-q02-catalog-design.md), [ADR-0064 §54](../../decisions/0064_first_session_database_contract.md). В каталожном блоке теперь9 таблиц: прежние7 и две ниже. Это не созданная БД, DDL, SQL, миграция или новая система ролей.

### 16.1. shadow.q02_read_scopes — текущая разрешённая область

Одна строка описывает текущий серверный набор источников одной площадки и guard его публикации. H01 выбирает конкретную строку по текущему доказанному допуску. Само существование строки, её ID/source_ref или состав не назначают право пользователю/гостю. Колонок user_id/login_id/role и автоматического правила «все читают всё» нет.

| Колонка | Тип | Обязательна | Правило |
| --- | --- | --- | --- |
| environment, id | text, uuid | Да | PK(environment,id), постоянный серверный UUID v4; общие правила среды/identity |
| venue_id | uuid | Да | FK(environment,venue_id)→venues(environment,id); venue неизменна |
| version | bigint | Да | От1; монотонный guard состава/версии доверенного основания. Не сбрасывается/не переполняется |
| source_ref | text | Да | Непустая безопасная ссылка на конкретное версионированное основание публикации, без secrets/bearer. Не самостоятельное доказательство доступа и не исполняемая ссылка |
| created_at, updated_at | timestamptz | Да | Серверные времена; created_at неизменно, updated_at меняется только с действительной публикацией |

Дополнительный target unique(environment,id,venue_id) нужен дочернему scoped FK. Unique только по venue не вводится: число/назначение областей задаёт доверенная конфигурация H01, не новое продуктовое разграничение. Для запросов по ID/составу дополнительных индексов без измерений не выбирают.

ScopeRevision вычисляется как строка **q02-read-scope-v1:<scopeId>:<version>**, где scopeId — канонический строчный UUID из id, version — положительная десятичная строка без ведущих нулей. Префикс — внутренний формат значения, не новый API reasonCode/record_schema_version. Это детерминированное представление двух колонок, а не дублируемая сохраняемая колонка. Environment уже отдельно связана в Manifest/environmentBinding. При выборе другой области её id отличает токен даже при тех же version/источниках.

### 16.2. shadow.q02_read_scope_sources — текущий состав области

| Колонка | Тип | Обязательна | Правило |
| --- | --- | --- | --- |
| environment, id | text, uuid | Да | PK(environment,id), серверный UUID v4 записи членства |
| read_scope_id | uuid | Да | FK(environment,read_scope_id,venue_id)→q02_read_scopes(environment,id,venue_id) |
| venue_id | uuid | Да | Та же площадка scope и source |
| catalog_source_id | uuid | Да | FK(environment,catalog_source_id,venue_id)→catalog_sources(environment,id,venue_id) |
| created_at | timestamptz | Да | Серверный момент включения записи в текущий состав |

Unique(environment,read_scope_id,catalog_source_id) запрещает дубли. Площадку/источник/родителя существующей записи не переназначают; исключение source удаляет только эту запись текущего членства, повторное включение создаёт новую запись с новым id. Это явно изменяемый состав конфигурации, **не immutable история**. Удаление членства не удаляет catalog_sources/traders/revisions/другие scopes/draft/review/session. Каскадное удаление этих объектов не добавляется; scope/venue/source нельзя удалить «заодно» с членством.

Допустима область с нулём источников: это достоверный пустой разрешённый набор, только если H01 разрешил сам запрос. Нет обязательного фиктивного source. Отсутствующая обязательная строка scope или сломанный FK не пустой набор; после надлежащего допуска — техническая недоступность. Эта разрешённая пустота не ослабляет mandatory children/полноту C06, command receipts или Q06 audit.

### 16.3. Неделимая публикация и версия

Создание scope и всего исходного состава — одна транзакция, version=1 после полной подготовки; при пустом составе родитель также создаётся явно. Trusted writer проверяет основание source_ref и весь итоговый набор, scope/venue/source связи. Набор не принимается от клиента Q02.

Изменяющий writer защищает родительский scope до чтения/изменения детей. Под X он сверяет текущую version с исходной версией доверенного плана публикации. Устаревший план не применяется поверх новой публикации и не сливается автоматически; это внутренний протокол publisher, не новое поле/отказ C04 или публичная команда. В одной транзакции применяет все включения/исключения, новое версионированное основание source_ref при его изменении, version=прежняя+1 и updated_at. Несколько membership-изменений одной публикации дают одно повышение guard. Повтор того же состава **и того же основания** без иных значимых изменений не увеличивает version и не меняет updated_at. Новое основание политики даже при прежнем составе требует новой версии. Нельзя менять смысл ранее опубликованного source_ref на внешнем сервисе без новой локальной публикации.

Каждый путь записи детей обязан изменить/защитить parent guard; отдельный FK/unique/NOT NULL этого не обеспечивает. Проект требует транзакционного writer и ограничения обходных DB-привилегий; конкретные процедуры/проверки межстрочной публикации ещё предстоит спроектировать и доказать до реализации. Не объявлять прикладной UPDATE достаточным физическим enforcement.

Возврат прежнего набора A→B→A даёт новую version. Новая catalog revision/read_visible/start-флаг source/trader меняют прежние S/T guards, а не автоматически scope.version. Членство не фильтруется по read_visible/start_enabled: эти признаки сохраняют отдельный смысл. Смена состава области не переписывает S/T версии только ради нового scope guard. При общей транзакции с каталогом оба соответствующих набора guards изменяются вместе по единому порядку.

### 16.4. Чтение, блокировки и остаток H01

Q02 читает родителя/его состав и полный Manifest в одной прежней короткой Serializable-транзакции primary. Для уже выбранного scope берёт S-защиту родителя; writer — X до изменения состава. В G1 scope идёт **до paper_controls → catalog_sources → traders**; внутри вида — полный ключ environment/id. Профили, которым scope не нужен, его пропускают: C04/C05/C06/claim автоматически не получают новых чтений/locks/причин отказа. Если операция совмещает изменение scope и source, сначала защищает scope, а не добавляет его после source.

Под защитой сверяются scopeId/venue/version/состав и текущий H01. Предварительно найденный readScopeId не право. Если защищённая проверка H01 требует другой ещё не защищённый scope после G2, нельзя захватывать G1 задним числом: завершить попытку техническим исходом без внутреннего повтора, либо установленным access-ответом при доказанном отказе. Если ожидание встретило уже изменённую строку вне снимка, нельзя считать snapshot освежённым; конфликт — технический исход Q02 без внутреннего retry. Проверяются также сроки после ожиданий. Reader не держит locks между HTTP-запросами. Транзакция может требовать режима, допускающего row locks, но Q02 не пишет предметные строки/аудит/финансы; это не новая изменяющая команда.

S-защита scope покрывает согласованность **локального состава** против соответствующего writer. Она не блокирует внешние изменения Auth или самовольную смену серверного выбора области. H01 ещё должен доказать защищённый readScopeId, актуальные права и их связь с локальной транзакцией/guards; никакой client/cursor ID не выбирает scope. Неверный/утраченный допуск даёт прежний access/hidden ответ, неизвестность503, установленное изменение допустимого scopeRevision/fingerprint409.

### 16.5. История, restore и граница проекта

Новые таблицы хранят текущую область, не историю страниц/каталога и не key store. Прежние34 таблицы и их обязательная история сохраняются. Публикации опираются на версионированный доверенный источник; конкретная сохранность его manifest/evidence/права остаётся H01/M05. Полноценный новый журнал публикаций/новые audit-kind не добавлены молча.

В обычной работе version не уменьшается, ID области не переиспользуется. Restore старой БД способен вернуть старую пару id/version, поэтому **одной локальной монотонности недостаточно**. До открытия H06 должен исключить повторное использование прежних scopeRevision: например, новой идентичностью восстановленных областей с доказанным переключением H01 либо иным отдельно доказанным барьером. Точный recovery-протокол ещё зависимость, не выполненная операция и не скрытая переустановка версии в0. Отзыв/свежесть ключей проверяются отдельно.

Новая пара таблиц и контракт записи согласованы документально; реальные типы/FK/privileges/процедуры/locks/планы/restore не созданы и не испытаны. Исторические упоминания34 таблиц отражают прежний состав; текущая полная схема —36.
