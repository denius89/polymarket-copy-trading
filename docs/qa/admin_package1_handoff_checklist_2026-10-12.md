# Админка: черновой handoff и приёмка первого дизайн-пакета

Дата подготовки: **12.10.2026**. Область: оболочка, UI kit, ADM-01 «Обзор», ADM-02 «Пользователи», ADM-03 «Сессии», RU/EN.

Это шаблон реестров и проверок, а не отчёт о завершённом дизайне. Фактические file/page/node IDs, ссылки, результаты и принятая ревизия заполняются корневым агентом после создания и проверки соответствующих узлов. Поля ниже намеренно пустые; выполненные проверки этим документом не заявляются.

Источники: [115 — техническая спецификация, §§3–6, 8, 17](../115_admin_console_technical_specification_2026-10-09.md), [118 — задание на дизайн, ADM-01/02/03, §§9.1–9.3](../118_admin_console_figma_design_brief_2026-10-09.md), [116 — связь с пользовательским UI](../116_admin_user_interface_consistency_2026-10-09.md). Принятые ADR имеют приоритет над иллюстративными данными и текстом макета.

## 1. Предложенная структура постоянного реестра

При первом сохранении фактического пакета разместить handoff в `docs/design/admin/`. Названия ниже — предложение; новых каталогов/файлов оно само по себе не создаёт.

| Путь | Содержание |
| --- | --- |
| `README.md` | Текущий baseline, пакет и статус вычитки; ссылки на спецификации, kit и реестры |
| `package-01/README.md` | Scope ADM-01/02/03, ревизия, начало прототипов, состав, ограничения, история изменений |
| `package-01/screens.md` | Все фактические фреймы RU/EN и состояния, точные IDs, ссылки, статус вычитки |
| `package-01/actions.md` | Контракты кнопок/форм/таблиц и связанные endpoints как предложения из 115 |
| `package-01/prototype.md` | Переходы, роль/язык, покрытие P-ID, фактические Present start nodes |
| `package-01/qa.md` | Проверки точной ревизии, evidence, дефекты, исправления и повторная проверка |
| `ui-kit/components.md` | Общий для всех пакетов реестр компонентов, variants/properties, bindings и зависимостей |
| `ui-kit/tokens.md` | Общий реестр переменных/стилей, semantic aliases, существующих тем, значений и назначения |
| `ui-kit/migration.md` | Сопоставление admin/client kit, reuse/deprecation, миграция instances; слияние позднее |

UI kit не дублируется внутри каждого пакета: пакет ссылается на точную ревизию общего реестра и перечисляет добавленные/изменённые элементы. Сохранённые screenshots или структурные snapshots можно разместить в отдельном evidence-каталоге с ссылкой из `qa.md`.

## 2. Паспорт пакета — заполнить по факту

| Поле | Значение |
| --- | --- |
| Package revision / дата среза | |
| Figma file ID / URL | |
| Page IDs: kit, RU, EN, review | |
| Статус пакета и вычитки | |
| GitHub baseline commit / ссылки на реестры | |
| Источники: версии 115/116/118 и применённых ADR | |
| Автор / проверяющий | |
| Синтетические fixtures: описание и scope | |
| Owner prototype RU/EN start nodes | |
| Operations prototype RU/EN start nodes | |
| Restricted-role prototype start nodes, если создан | |
| Не создано / не проверено / synchronization_pending | |

Статус каждого отсутствующего фрейма — `planned`, существующего непроверенного — `draft`. `reviewed` и `accepted` возможны только с конкретным evidence/решением; дата создания и screenshot не означают принятие основателем. Пакет с расхождением Figma/GitHub получает `synchronization_pending` с точным перечнем недостающего.

## 3. Поля реестра экранов

Одна строка = конкретный фрейм, locale и состояние; имя фрейма не заменяет node ID.

`screen_key | ADM-ID | title | locale | state | role/scope | environment/mode/venue | Figma file/page/node | frame URL | spec section | component refs | P-ID/route ID | revision | review status | evidence | replaces/archived node`

Начальная карта покрытия (фактические nodes и ссылки не заполнены):

| Screen key | Покрытие | RU node | EN node | Состояния для реестра |
| --- | --- | --- | --- | --- |
| SHELL | Меню, контекст, профиль/язык, поиск, хлебные крошки | | | Default, no access, revoked/expired, exact-ID found/not-found |
| ADM-01/Overview | Счётчики, обе площадки, очередь внимания | | | Ready, empty, disconnected, stale/partial, unknown |
| ADM-02/List | Пользователи, сортировка, фильтры, пагинация | | | Ready, loading, empty, filter-empty, error, restricted |
| ADM-02/Detail | Пользователь, подключения, сессии, обращения, условия, история | | | Ready, disconnected, partial/stale, restricted |
| ADM-02/VIP | Назначение/изменение/завершение, preview, результат | | | Owner form, field error, conflict, accepted, applied; future/active/ended |
| ADM-03/List | Сессии, контекст, независимые причины ограничений | | | Ready, loading, empty, filter-empty, error, restricted |
| ADM-03/Detail | Настройки/версия, бюджет, позиции, ордера, активность/сигналы | | | Fresh empty demo, active demo, user pause, risk pause, venue restriction, stop |
| ADM-03/Command | Pause/resume-demo/disconnect-demo, scope и результат | | | Confirmation, accepted, running, applied, blocked, unknown, conflict |

Общие состояния из 118 §4 покрываются экраном или переиспользуемым компонентом с записанным примером. Не требуется создавать дубликаты всех экранов только ради каждого состояния, но точный способ покрытия фиксируется.

## 4. Поля UI kit registry

### Компоненты

`stable name | kind: shared/admin/client composition | Figma file/node ID | main-component URL | existing/reused/new | variants/properties | state coverage | instance swaps | variable/style bindings | Auto Layout/resizing | typography/icons/assets | example screen refs | dependent user/admin screens | revision | evidence | status | replacement mapping`

Минимальные группы первого пакета: shell/navigation, Button, Input/Search/Select, Tabs, Status, Filter/Chip, DataTable/Pagination, EntityCard, VenueHealthCard, Empty/Error/Loading/Stale, Timeline, Dialog, Toast, FormField, VIP preview, SessionCommand result. Названия уточняются по фактической библиотеке, не создают новое обязательное API компонентов.

### Токены и стили

`stable name | semantic purpose | Figma collection/variable/style ID | alias target | value by existing mode | used components/screens | client correspondence | future code name (proposed) | revision | status | evidence`

Записывать colors/semantic aliases, typography, spacing, radii, borders/effects, icons. Фактические bindings проверять, не выводить из похожего цвета. Новые темы и detached-копии shared элементов без причины не добавлять. Объединение клиентского/admin kit в этот пакет не включено.

## 5. Поля action contract

`action_key | screen/node | RU/EN label | actor/permission | context scope | preconditions | inputs/validation | confirmation/re-auth if applicable | proposed API/event refs | accepted/pending | success evidence | blocked/error/unknown/conflict | destination | return/context preservation | Figma reaction | limitation | spec refs`

Обязательные действия первого пакета:

- Из сводного счётчика открыть соответствующий список с тем же environment/mode/venue/period.
- Точный поиск и открытие разрешённой сущности, без утечки через результаты/подсказки.
- Сортировка/фильтры/сброс/пагинация/строка списка; возврат сохраняет фильтры и позицию.
- Пользователь → сессия; сессия → пользователь; related ticket/incident — только если реальный целевой фрейм создан. Иначе ссылка явно вне пакета.
- Owner: VIP create/edit/end с временем, причиной и preview до/после; остальные роли не получают action.
- Разрешённые pause/resume-demo/disconnect-demo с явной областью и независимыми блокировками. Запрос не равен результату.
- Отмена формы, несохранённые изменения, обновление после конфликта, безопасный следующий шаг unknown.

## 6. Прототип и evidence

Реестр маршрутов:

`route ID | canonical P-ID | role | locale | start file/page/node | Present URL | sequence (source/action/destination) | state branch | expected outcome | actual result | timestamp | package revision | evidence | defect ID | retest`

| Маршрут первого пакета | Связь с общим заданием | Граница покрытия |
| --- | --- | --- |
| Обзор → отфильтрованные сессии → карточка → пользователь → возврат | Фрагмент P-01 | Без ADM-04/05 нельзя считать весь P-01 пройденным |
| Пользователи → карточка → VIP preview → применение/будущий/завершённый | P-06 | Полное покрытие только при фактическом создании и проверке всей ветки |
| Operations → сессия → pause → accepted → applied → resume при другом ограничении | Операционный контракт ADM-03 | Blocked не изображается как восстановленный active |
| Сессия → disconnect-demo → processing → завершено | Контракт ADM-03 | Workflow иллюстративный; отсутствие backend явно отмечено |
| Restricted role → обзор/пользователь/сессия → недоступная информация/действие | Фрагмент P-11 / общие права | Без журнала и экспорта не считается полной проверкой P-11 |
| Обе площадки: disconnected/unknown → диагностика | Фрагмент P-12 | Без ADM-06/15 не считать весь P-12 пройденным |

Для каждой ветки проверить RU и EN, click targets, overlay dismissal, назад/отмена, отсутствие неожиданной потери контекста. Структурная проверка reactions — отдельный вид evidence; Present, визуальная проверка и проверка сервера не взаимозаменяемы.

## 7. Приёмочные checks — все пока не отмечены выполненными

### Состав и фактические ссылки

- [ ] Все фактические фреймы пакета и состояния внесены в реестр с точными IDs/locale/revision.
- [ ] Прямые frame/Present ссылки открывают нужный фрейм/роль/язык.
- [ ] В документации явно отделены planned, draft, reviewed, accepted и архив; принятие не приписано основателю.
- [ ] Старые admin/client узлы не удалены без mapping; внепакетные destination не объявлены созданными.

### Контекст, данные, права

- [ ] Среда, demo/live и площадка явно видны; Polymarket и Limitless различимы и независимы.
- [ ] В сводке и карточках есть актуальность/источник/причина ограничения; unknown не зелёный успех.
- [ ] Ноль отличается от отсутствия данных; disconnected/stale/partial не маскируются полноценной сводкой.
- [ ] Operations не получает финансовую информацию через counts, поисковые результаты, nested cards или подсказки без отдельного разрешения.
- [ ] Минимальный и расширенный пользовательский контекст разделены; нет impersonation и раскрытия секретов.
- [ ] Роль/площадка/среда в прототипе иллюстративны, не заявлены серверной защитой.

### ADM-01/02/03 и общая бизнес-логика

- [ ] Counters → list сохраняют фильтры; назад сохраняет позицию и контекст.
- [ ] Fresh demo не имеет истории/сделок синтетической active fixture.
- [ ] Пользовательские available/reserved/executed/P&L не смешиваются и не выдаются за сервисную выручку.
- [ ] Карточка сессии связывает настройки/версию, сигналы, причины skip, позиции/ордера и историю.
- [ ] Partial order fill допустим и не назван частичной партнёрской выплатой.
- [ ] User pause, risk pause, venue restriction и system stop различаются; resume не снимает чужую причину.
- [ ] Pause/disconnect: принято → обработка → доказанный результат; unknown не даёт опасного повторения.
- [ ] Нет ручного редактирования исполненных сделок/балансов или незаявленного live submit за пользователя.
- [ ] VIP create/edit/end только Owner; время/срок/причина/preview/history присутствуют.
- [ ] Будущий VIP не выглядит уже действующим; ended не переписывает прошлые комиссии.
- [ ] Alpha fee 0 сохранена; синтетический VIP preview не объявлен принятой новой тарифной политикой.
- [ ] User VIP отделён от partner VIP и не обходит risk/emergency/capability gates.

### UI kit и визуальная проверка

- [ ] Existing foundations/components проверены до добавления аналогов; reused IDs сохранены.
- [ ] Экранные shared элементы — instances, новые admin compositions используют общую основу.
- [ ] Auto Layout/resizing, variants/properties/swaps, text styles и variables фактически проверены.
- [ ] Default/focus/disabled/loading/error и используемые success состояния включены в kit registry.
- [ ] Текстовые причины сопровождают цвет/иконку; disabled-action объясняет состояние, когда это уместно.
- [ ] RU/EN проверены визуально, включая длинные строки, таблицы, модальные формы, даты и суммы.
- [ ] Фокус/клавиатурное поведение описано для реализации; прототип не выдаётся за полную accessibility-проверку.
- [ ] Assets/fonts/icons и зависимости admin/client записаны; общая библиотека ещё не объявлена слитой.

### Клики и синхронизация

- [ ] Выполненные маршруты проверены в Present; результаты/дефекты и точная ревизия записаны.
- [ ] Иллюстративный ввод/сортировка/реальные вычисления/асинхронность/серверные права явно ограничены.
- [ ] Невыполненные P-01–P-18 не отмечены принятыми из-за проверки небольшого фрагмента.
- [ ] Все изменённые screens/actions/components/tokens/prototype/evidence сохранены в GitHub одной связанной ревизией.
- [ ] Корневой агент обновил PROJECT_STATE/ROADMAP/навигацию по фактическому результату; npm check и diff check отражены только после выполнения.

## 8. Открытые ограничения и журнал замечаний

Каждое ограничение записывается отдельно: `ID | screen/route | limitation | user impact | implementation requirement | owner | status | evidence`. Минимально явно указать отсутствие backend/live execution, реального enforcement permissions, настоящих финансовых данных и неохваченные ADM/P. Доступные API routes из 115 — проектные контракты, не доказательство реализованного API.

Журнал замечаний: `ID | revision | screen/component/node | problem | proposed correction | source rule | severity | reviewer | decision | retest evidence`. Открытые численные/API вопросы не закрываются иллюстративным текстом. Слияние UI kit, полный P-01/P-11/P-12 и оставшиеся разделы админки — будущие пакеты, если не созданы и не проверены фактически.

Перед реализацией нового среза разработчик получает конкретный accepted baseline с RU/EN nodes, kit revision, action contracts, выполненной приёмкой и открытыми вопросами. До этого статусы остаются достоверными: черновой или проверенный дизайн не означает разрешение production/live.
