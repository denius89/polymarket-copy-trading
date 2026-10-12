# Admin UI kit v0.4.5

После [упорядочивания дизайн-системы](../../design-system-consolidation-2026-10-12.md) текущая страница — **08 · Admin UI kit** (`1981:2`). Секция `2152:1084` хранит ранние Admin masters (`113:203`), используемые действующими RU/EN экранами. Они перенесены без замены и отсоединения экземпляров; исходный UI kit v0.4.5 остаётся на той же странице.

12.10.2026: `Admin/Sidebar` (1981:16) обновлён на месте до утверждённой навигации с иконками. Первые три старых client nav instances заменены на Admin/Navigation item с сохранением ID. Служебный Later скрыт; property оставлен для совместимости старых overrides. Подписи RU/EN и активные пункты проверены на 68 связанных instances. [Изменения исходника](fixes/sidebar-source.json).

## Основа дизайна админки

Все новые и обновляемые экраны админки собираем из этого UI kit: используем instances, общие цвета, типографику, иконки и состояния. Недостающий элемент сначала добавляем в кит, затем применяем в экранах. Изменения делаем на существующих страницах, сохраняя связи компонентов.

[Основы и сетка в Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2099-16977): 12 растягиваемых колонок, промежуток 16 px, поля 24 px; sidebar 248 px вне сетки. При desktop 1440 px основной контейнер 1192 px. Раскладки: 4 + 4 + 4, 6 + 6 и 12. Общий стиль `Admin/Grid/Desktop · 12 columns` переиспользуется без дублирования. Auto Layout управляет содержимым. Мобильная компоновка согласуется отдельно. [Точные ID и параметры](grid-and-usage.json).

12.10.2026: добавлена витрина **Apps Components** — 15 семей и 104 варианта компонентов на существующей странице. [Открыть Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2082-125), [правила применения](APPS_COMPONENTS.md), [актуальные ID и properties](apps-components.json). Состояния являются дизайн-спецификацией; интерактивность и миграция всех экранов не заявляются.

12.10.2026: текущая админка пересобрана на месте в едином стиле по Monty с палитрой Shadow. 184 состояния на двух страницах RU/EN, общий UI kit, иконки и сохранённый прототип. Новые итерации ведём в существующих экранах. Работа только над дизайном. [Актуальный дизайн и правила работы](../STYLE_GUIDE.md).

Пакет 02 добавил `Admin/Finance row/v0.1` (2002:5) и `Admin/Form field/v0.1` (2019:16; Input 2019:5 / Select 2019:10). [Точные properties и token usage](../package-02/evidence/ui-kit-additions.json). Существующие пять compositions сохранены, новые коллекции не созданы. Старые Select/Shared Field с узким value не используются в формах пакета 02; client masters не менялись. Focus/error/disabled добавлены в v0.4; объединение kit остаётся следующим этапом.

12.10.2026, draft_for_review. Figma page `1981:2`. [Точные компоненты, properties, style IDs и variable bindings](registry.json). Это локальные masters в текущем файле; опубликованная объединённая библиотека не заявляется.

| Composition | Node | Properties |
| --- | --- | --- |
| Admin/Metric/v0.1 | 1981:3 | Title, Value, Hint |
| Admin/Entity panel/v0.1 | 1981:7 | Title, Body |
| Admin/Data row/v0.1 | 1981:10 | Title, Body |
| Admin/Notice/v0.1 | 1981:13 | Title, Body; amber notice |
| Admin/Sidebar | 1981:16 | Brand, Subtitle, Later; nested client nav |

Переиспользованы старые button masters Primary 113:207, Secondary 113:209, Quiet 113:211 и status masters 113:214/216/218/220; клиентские Nav default/selected 1978:1003/1005, Select 1978:874 и Textarea 1978:921. Width overrides вложенного Control применены к admin instances, оригинальные клиентские masters не изменены.

Shared foundations: Color `VariableCollectionId:2:3`, Dark `2:1`, Light `7:0`; Spacing `2:4`, Radius `2:5`, Inter text styles. Новые коллекции-дубликаты не созданы. Registry сохраняет alias IDs; полные примитивы/клиентские основы — [client UI kit](../../../../design/client-ui-kit/README.md). Экранный пакет проверен только в Dark.

Будущее объединение с client kit 121: сопоставить назначения и состояния, выбрать shared masters, сохранить admin compositions для domain content, заменить instances с сохранением props/overrides/reactions, проверить RU/EN рендеры и Present, зафиксировать old→new ID mapping и QA в Git. Совпадение внешнего вида не доказывает совместимость. Entity panel/Data row/Notice проверить на дублирование клиентских patterns; старые masters не удалять до подтверждения миграции. Merge ещё не выполнен.

12.10.2026: страница UI kit очищена и сгруппирована на месте: витрина, исходные компоненты, используемые композиции экранов и иконки. Удалён устаревший `UI kit passport` (1981:26); название страницы — `13 · Admin UI kit`. Сохранены ID всех 15 семейств / 104 вариантов, 6 композиционных masters и 17 иконок. Границы исходных Checkbox и Segmented расширены под текущие варианты. [Журнал структуры](cleanup-ledger.json).

12.10.2026 · пакет 03: исходный Sidebar расширен на месте до 13 пунктов. Исправлены 84 отсутствующие текстовые привязки Form field, итого 90 на 30 вариантах. Полные адреса в витрине проверены. Семейств 15, вариантов 104; новые дубли masters не создавались. [Журнал QA и изменённых ID](../package-03/qa.json).


12.10.2026 · пакет 04: добавлен исходник Admin/Metadata row (2137:26727) с Title/Detail/Meta, шириной 1144, минимумом 64 и переносами. Колонки используют общие Inter/styles/tokens; денежные действия не скрываются в строке. 15 component sets / 104 variants сохранены; composition masters теперь 7. Alert Title/Body обновлены до Fill/HEIGHT для корректного переноса при 560 px форме входа. [Пакет и проверка](../package-04/README.md).
