---
name: cct-deployment-data-ops
description: Review deployment, migration, backup restore and financial reconciliation runbooks for safe project operations. Not a production deployment or permission to replay external side effects.
---

# S19 · Выпуск, восстановление и данные

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Зафиксируй release/artifact/schema/config versions, environment и scope; раздели deploy, migration, restart, feature enable и live gate.
2. Подготовь staging/rollout/preflight и compatibility window; destructive schema rollback не универсально обратим. Forward repair может быть безопаснее, но требует основания.
3. Для backup проверь capture consistency, encryption/access, retention, dependency credentials и restore drill в изоляции. Файл backup не подтверждает восстановление.
4. После restore запусти сначала read-only reconciliation внешних операций, controls и funds; старый outbox не основание повторно отправить submitted/unknown.
5. Определи cutover/rollback/abort критерии, RPO/RTO evidence и ответственных; не восстанавливай/деплой на реальной системе по просьбе написать план.

## Знания и проверка

Для предметной работы: [пакет S19](../../../docs/ai-system/learning/S19.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/operations.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Не признавать restore по скачанному файлу.
- Сначала изолированный drill и сверка, без повторной отправки unknown.

Смежные процедуры: S07, S09, S18, S23. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
