# QA первого дизайн-пакета

12.10.2026, v0.1. Проверки относятся к текущим узлам, перечисленным в screens.md. Документы агентов в docs/qa — предварительные чеклисты, не доказательство выполненной приёмки; этот файл содержит фактический результат.

| Проверка | Результат |
| --- | --- |
| Нативные frames / роли / размеры | 34 RU + 34 EN; 1440×1000; Owner и Operations |
| Шрифты | Inter на всех проверенных текстах |
| Image-filled nodes | 0: экраны редактируемые, не растровые картинки |
| Выход текста за root bounds | 0; это не полная проверка каждого локального перекрытия |
| Реакции | 198 на язык; invalid/self NODE destinations = 0 |
| UI kit | 5 новых admin compositions; свойства/styles/bindings сняты в registry.json |
| Visual QA | RU обзор и VIP form: исправлены ширины контейнеров/перекрытие и ширина вложенных select; после исправления повторный рендер |
| Present | Представительные маршруты перечислены в prototype.md; backend не участвовал |
| Viewport | Present проверен со scaled view в том числе 1280×900; responsive layout не подтверждён |

Evidence: [RU structure](evidence/ru-structure.json), [EN structure](evidence/en-structure.json), [RU edges](evidence/ru-reactions.json), [EN edges](evidence/en-reactions.json), [Overview PNG](evidence/overview-ru.png), [VIP PNG](evidence/vip-form-ru.png).

Остаются: совместная вычитка; динамический ввод, поиск/фильтры/сортировка/pagination; loading/network/permission/auth states; future/end VIP; долгие локализованные строки; responsive; полная проверка accessibility/contrast/focus/keyboard; полная сквозная Present приёмка и остальные разделы. UI kit merge с клиентским ещё не выполнен. Код/backend/API/live тесты этим пакетом не заявляются.
