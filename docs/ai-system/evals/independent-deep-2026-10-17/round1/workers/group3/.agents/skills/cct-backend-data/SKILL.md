---
name: cct-backend-data
description: Review backend and database boundaries, concurrency, transactions, idempotency and migrations for Controlled Copy Trading. Not an authorization to create production schemas or integrations.
---

# S07 · Backend, БД и целостность

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Отдели предложенный стек ADR-0042 от принятого/реализованного; установи предметные инварианты и trust boundaries.
2. Проследи API validation/auth/tenant scope, money precision, keys/constraints и lifecycle сущностей; межплощадочные IDs сохраняют venue.
3. Разбери конкурентные handlers, duplicate/late events, crash между commit и external side effect, timeout и повтор. Outbox даёт устойчивую запись намерения, не магический exactly-once внешнего действия.
4. Оцени transactions/isolation/locks/unique keys и обоснованную стратегию retry; проверяй query plans до добавления индексов и лимиты pooling.
5. Для изменения данных подготовь план совместимости миграций, backfill/retention, restore/reconciliation и независимые проверки. Выход — review/варианты и доказательства, не новая схема продукта без поручения.

## Знания и проверка

Для предметной работы: [пакет S07](../../../docs/ai-system/learning/S07.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Обнаружить гонку и нарушение совокупного лимита.
- Предложить атомарную/транзакционную проверку с meaningful concurrency test, без миграции.

Смежные процедуры: S03, S08, S22. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
