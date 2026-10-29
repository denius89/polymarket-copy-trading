# Физическая схема БД — блок 2: каталог, правила и проверка настроек

29.10.2026 · Заключительный блок принят после PR №176 и отражён; [итог дополнения §§4–5](database-c04-addendum.md), [ADR-0064 §37](../../decisions/0064_first_session_database_contract.md). Реестры H02/H03, параметры H04–H06 и T01–T17 действуют вместе с физическими полями ниже. Исторические пометки «ещё выбрать код/бюджет» не отменяют последующее принятие. Полевая карта JSON/DTO, компоненты и предметные испытания остаются отдельно; только документы.

29.10.2026 · **Блок 2 принят целиком 29.10.2026 после PR №162.** [Фиксация — ADR-0064 §31](../../decisions/0064_first_session_database_contract.md). [Блок 1](database-physical-design.md) принят; общие соглашения и зависимости сохраняются. Baseline: main `8c1719f8d9aecf1a4ee11b050ab27c4da3dcbc4a`. Семантика — [ADR-0064](../../decisions/0064_first_session_database_contract.md), числовые правила — [ADR-0058](../../decisions/0058_paper_mvp_numeric_settings_policy.md) и [paper-mvp-settings-v1](../../policies/paper-mvp-settings-v1.json). Только документ, без SQL, кода и интеграций.

## 1. Состав и общий принцип

Семь таблиц: venues, catalog_sources, traders, trader_revisions, paper_policy_versions, paper_controls, setup_reviews. Они раскрывают уже принятые Venue/Trader/TraderRevision/PolicyVersion/SetupReview и их текущие pointers/controls. У всех собственных строк PK `(environment, id)`, UUID v4; ссылки включают environment. Ниже общие поля перечислены явно или вынесены в общую строку: это отдельные колонки, не объект JSON.

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
| start_allowed | boolean | Да | Текущая допустимость выбора этого трейдера для запуска |
| unavailable_reason_code | text | Условно | При start_allowed=false обязателен; иначе NULL |
| version | bigint | Да | Trader control version; повышается при смене текущей revision/допуска |
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

Одна строка хранит показанные значения и контекст проверки C05. Физический проект предусматривает и предметно отклонённую проверку: неверный ввод сохраняется как raw-копия, а отсутствующие нормализованные параметры явно отличимы от нулей. Это не превращает техническую ошибку БД, отсутствие доверенного источника политики или неполный вход в успешную проверку. Ошибка формы запроса до обработки C05 может не создавать review; точное отображение ответов — B2-D3.

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
| reason_details, warnings | jsonb | Да; типизированные по контракту безопасные дополнительные данные, пустые структуры при отсутствии, до 16 КиБ каждое. Обязательные настройки/владелец не переносятся сюда |
| checked_at, expires_at, created_at | timestamptz | Да; expiry через 10 минут после checked_at; запись неизменяема |

### 8.1. Полнота и исторические связи

- При normalization_valid=true заполнены B, p, d, точные P/D и ровно один действующий F/q. Все дроби — конечные целые n/d, d>0, gcd=1, zero=0/1, до 64 цифр на компонент. Данные соответствуют raw выбранного режима и указанной policy; проверяется без округления. Это условие числовой валидности, не вся авторизация запуска.
- При normalization_valid=false все нормализованные поля NULL, allowed_to_start=false и причина обязательна. Raw-копия остаётся для объяснения. Не создаётся частичный набор «действующих» настроек из части успешно разобранных полей.
- allowed_to_start=true требует полного пользовательского ownership, normalization_valid=true, определённых трейдера/revision/зоны, проверенного слота, пригодных controls и отсутствия препятствий. Гость всегда requires_authentication=true; любое true требует allowed_to_start=false. Для разрешённого C05 от user требуется подтверждённый доступ и requires_authentication=false. Недействующий вход не обходится созданием review от имени user; текущая авторизация проверяется при каждом запросе.
- Согласованность owner_kind/owner_user_id с историческим ownership проверяется до commit. При claim старый guest review остаётся связан с guest ownership; current_ownership_id draft меняется отдельно. C06 требует соответствие именно текущему владельцу.
- Не ставить FK от draft_version к текущему setup_drafts.version, catalog_version к catalog_sources.version или control versions к текущим guards: иначе обычная правка разрушит историю. FK защищает постоянные IDs, а актуальность сравнивает транзакция C06.
- Для следующих таблиц нужен уникальный ключ `(environment, id, draft_id, ownership_id)`; он позволит связать будущую session с точной исходной проверкой. Историческое поле checked_at не меняется при просмотре; expiry и старый отказ не исправляются «на месте».

### 8.2. Пустой слот и неполная проверка

Различение absent/present/not_applicable не создаёт новую бизнес-сущность. Если слота действительно нет, C05 фиксирует absent; при C06 отсутствие перепроверяется под защитой уникального ключа/владельца до создания слота. Если чужая операция уже создала или заняла слот, отсутствие из review не считается актуальным. Конкретный стартовый generation и отображение этого варианта в общем DTO завершаются с блоком 3; нельзя подставить NULL вместо неизвестного ответа БД.

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

PK/unique выше обеспечивают целостность; не дублировать их одинаковыми индексами. Кандидат чтения каталога `(environment, catalog_source_id, start_allowed, id)` и поиска reviews по `(environment, draft_id, created_at, id)` добавляется только при соответствующем запросе и проверенном плане. Q02/Q03/C06 и чтение review по ID не требуют заранее индексировать все display names, JSON warnings или сроки. Набор FK-проверок и плана удаления сводится после всех блоков; физического удаления используемых источников/policy/revisions/reviews сейчас нет.

## 10. Зависимости и проверка документа

| ID | Что ещё детализируется | Граница |
| --- | --- | --- |
| B2-D1 | Коды data_origin/source_environment, external ID normalization и безопасные source refs | Бэкенд/будущие адаптеры подтверждают реальные значения; fixture не выдаётся за live |
| B2-D2 | Формат отпечатка policy, calculation/rule code registry и сохранение опубликованного источника | Версии и числа ADR-0058 уже приняты; ни новый алгоритм, ни новые лимиты не выбираются |
| B2-D3 | Полная машинная схема review v1, безопасные reason/warning codes и отображение validation errors в DTO | Физический проект отличает raw/нормализованный набор и отказ; API не реализуется этим чатом |
| B2-D4 | Начальный generation и точные составные связи slot/session/settings | Блок 3 замкнёт ссылки и вариант отсутствующего слота, без нового запуска/сброса истории |

Документально сверено с ADR-0058 и policy JSON: B/F/q/p/d, шаги/origins/defaults, предел fixed, отсутствие $5-минимума процента, p>d и сигнал 30 секунд сохранены. Предметные проверки будущей реализации: чужая площадка/источник, новая revision при C06, смена active policy, guest claim со старым review, невалидный raw, занятый/отсутствующий слот, точные P/D и fixed-граница. Это план проверки, не выполненные DB/API-тесты.

Технические источники прочитаны 29.10.2026: [PostgreSQL Numeric Types](https://www.postgresql.org/docs/current/datatype-numeric.html), [Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html). Numeric без объявленного scale не подменяет проверки конечности/целочисленности; межстрочную согласованность нельзя считать обеспеченной одним CHECK строки.

**Блок 2 принят целиком**, включая явно указанные технические зависимости. Блоки 3–4 также приняты; [сводная передача](database-backend-handoff.md) фиксирует завершение согласования и инженерные зависимости. SQL, миграции и код по-прежнему не начинать.

## 11. Отражённые реестры, review v1 и приоритеты

Источники — first-session-registry-v1 и backend-contracts §§3–9/18–19. Source refs/environment/external ID normalization остаются проверяемыми ссылками/контрактом адаптера, не произвольным enum. Policy paper-mvp-settings-v1 и calculation paper-settings-calculation-v1 неизменяемы. Source_hash хеширует точные байты закреплённого источника; это не канонизация command-jcs-v1.

Review v1 имеет свой полный формат, отдельный от version draft и current policy. raw_loss_limit_percent → rawDailyBuyLimitPercent; loss_limit_percent → dailyBuyLimitPercent; effective_loss_limit_n/d → effectiveDailyBuyLimit. Сотые процентного пункта БД → decimal-строка API, n/d → сокращённые целочисленные строки. При normalization_valid=false нормализованный набор весь NULL; допустимая неполнота raw не превращается в частично действующие настройки.

По одному fieldError на активное поле: REQUIRED→INVALID_DECIMAL→OUT_OF_RANGE→INVALID_STEP→FIXED_LIMIT_EXCEEDED. Порядок массива: бюджет, размер выбранного режима, рынок, дневной лимит. Зависимый fixed-предел вычисляется только при корректных B/p/d; собственные проверки F независимы. Неактивный raw не даёт ошибки настройки, но обязан пройти структуру/длину. Смысл params принят T04, точные имена и физическое размещение fieldErrors внутри review.reason_details требуют полевой карты; новая колонка/обёртка не придумана.

Для разрешённого отрицательного review приоритет: AUTH_REQUIRED guest → SESSION_NOT_SETTLED → CURRENT_SESSION_EXISTS → CAPABILITY_UNAVAILABLE → VENUE_REQUIRED → TRADER_REQUIRED → SIZING_MODE_REQUIRED → TIMEZONE_REQUIRED → NUMERIC_SETTINGS_INVALID. В capability: PAPER_START_DISABLED → CATALOG_SOURCE_DISABLED → TRADER_START_DISABLED; только применимые достоверно установленные причины. Сначала проверяется законность создания review из доступного актуального draft; техническая недоступность не отрицательный review. Warnings SYNTHETIC_DATA/COPYING_NOT_CONNECTED запуск не запрещают.

C05:5s/до 3 подтверждённых rollback-попыток; unknown прекращает автоматические повторы, возможен явный новый review, прежний возможный результат сохраняется. C05 не получает CommandReceipt/Q05. Успешное создание любого review — HTTP 200, allowedToStart=false не техническая ошибка. Точный DTO/JSON-map, публикация источников и испытания остаются; B2-D2 и кодовая часть B2-D3 отражены, полевые/компонентные части не объявлены закрытыми.
