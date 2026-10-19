---
name: cct-figma-handoff
description: Reconcile Figma components, versions, tokens and project handoff evidence. Use for design collaboration and scoped handoff, not automatic design implementation or library publication.
---

# S05 · Работа с Figma и передача

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Определи read/review/edit/handoff цель и затронутые file/node IDs; перед Figma инструментом загрузи обязательный подходящий Figma skill. Если инструмента/ссылки нет, продолжай локальную часть с ограничением.
2. Читай bounded nodes и версии; при timeout сужай запрос, не повторяй полное дерево. Фиксируй дату/охват чтения и реальные screenshots.
3. Раздели master, variant, variable/token, instance override, экран и prototype reaction. Publication библиотеки не равна обновлению всех instances.
4. Сверь действующие kit/HANDOFF/117 или admin 118, RU/EN и responsive состояния; не меняй принятые бизнес-правила и не отрывай компоненты ради удобства.
5. Для разрешённого изменения подготовь mapping изменённых IDs/версий/токенов и связанных документов/evidence; publish/migration/implementation имеют отдельный scope. Construction script не точный backup, prototype не runtime.

## Знания и проверка

Для предметной работы: [пакет S05](../../../docs/ai-system/learning/S05.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/collaboration.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Publication не доказывает миграцию экземпляров.
- Назвать нужный bounded inspection и ограничения screenshot, без publish/edit.

Смежные процедуры: S01, S10. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
