# Admin UI kit v0.4

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
| Admin/Sidebar/v0.1 | 1981:16 | Brand, Subtitle, Later; nested client nav |

Переиспользованы старые button masters Primary 113:207, Secondary 113:209, Quiet 113:211 и status masters 113:214/216/218/220; клиентские Nav default/selected 1978:1003/1005, Select 1978:874 и Textarea 1978:921. Width overrides вложенного Control применены к admin instances, оригинальные клиентские masters не изменены.

Shared foundations: Color `VariableCollectionId:2:3`, Dark `2:1`, Light `7:0`; Spacing `2:4`, Radius `2:5`, Inter text styles. Новые коллекции-дубликаты не созданы. Registry сохраняет alias IDs; полные примитивы/клиентские основы — [client UI kit](../../../../design/client-ui-kit/README.md). Экранный пакет проверен только в Dark.

Будущее объединение с client kit 121: сопоставить назначения и состояния, выбрать shared masters, сохранить admin compositions для domain content, заменить instances с сохранением props/overrides/reactions, проверить RU/EN рендеры и Present, зафиксировать old→new ID mapping и QA в Git. Совпадение внешнего вида не доказывает совместимость. Entity panel/Data row/Notice проверить на дублирование клиентских patterns; старые masters не удалять до подтверждения миграции. Merge ещё не выполнен.
