---
name: cct-backend-data
description: Review backend and database boundaries, concurrency, transactions, idempotency and migrations for Controlled Copy Trading. Not an authorization to create production schemas or integrations.
---

# S07 · Backend, БД и целостность

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Отдели предложенный стек ADR-0042 от принятого/реализованного; установи предметные инварианты и trust boundaries.
2. Проследи API validation/auth/tenant scope, money precision, keys/constraints и lifecycle сущностей; межплощадочные IDs сохраняют venue.
3. Разбери конкурентные handlers, duplicate/late events, crash между commit и external side effect, timeout и повтор. Outbox даёт устойчивую запись намерения, не магический exactly-once внешнего действия.
4. Оцени transactions/isolation/locks/unique keys и обоснованную стратегию retry; проверяй query plans до добавления индексов и лимиты pooling.
5. Для изменения данных подготовь план совместимости миграций, backfill/retention, restore/reconciliation и независимые проверки. Выход — review/варианты и доказательства, не новая схема продукта без поручения.

## Дополнительные материалы

[пакет S07](../../../docs/ai-system/learning/S07.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
