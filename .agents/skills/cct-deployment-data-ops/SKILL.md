---
name: cct-deployment-data-ops
description: Review deployment, migration, backup restore and financial reconciliation runbooks for safe project operations. Not a production deployment or permission to replay external side effects.
---

# S19 · Выпуск, восстановление и данные

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Зафиксируй release/artifact/schema/config versions, environment и scope; раздели deploy, migration, restart, feature enable и live gate.
2. Подготовь staging/rollout/preflight и compatibility window; destructive schema rollback не универсально обратим. Forward repair может быть безопаснее, но требует основания.
3. Для backup проверь capture consistency, encryption/access, retention, dependency credentials и restore drill в изоляции. Файл backup не подтверждает восстановление.
4. После restore запусти сначала read-only reconciliation внешних операций, controls и funds; старый outbox не основание повторно отправить submitted/unknown.
5. Определи cutover/rollback/abort критерии, RPO/RTO evidence и ответственных; не восстанавливай/деплой на реальной системе по просьбе написать план.

## Дополнительные материалы

[пакет S19](../../../docs/ai-system/learning/S19.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/operations.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
