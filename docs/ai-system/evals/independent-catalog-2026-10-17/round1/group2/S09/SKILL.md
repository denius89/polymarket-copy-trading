---
name: cct-reliability-operations
description: Assess SLOs, capacity, observability, DDoS resilience and incident response for this project. Use for operational planning and review, not enabling live mitigations without a scoped task.
---

# S09 · Надёжность и эксплуатация

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Определи критические пользовательские/денежные пути, dependencies и failure domains. Назначь измеримые SLI, предложенный SLO/window и допустимые последствия отказа отдельно от измерений.
2. Раздели edge/CDN/WAF и доступный origin, application quotas, expensive endpoints, WS/backpressure, reconnect storms и бюджеты поставщиков. Один per-IP limit не полная защита.
3. Свяжи logs/metrics/traces с operation IDs, freshness и ledger/reconciliation, без keys/PII и неограниченной cardinality. Alert должен иметь actionable owner/runbook.
4. Разбери dependency outage, DB saturation, stale controls, retry storm и unknown operations; safe degradation не должна рисовать финансовый успех.
5. Подготовь incident/restore/drill и capacity/cost plan, recovery criteria и support escalation. Не включай настройки или рассылку алертов без соответствующего поручения.

## Знания и проверка

Для предметной работы: [пакет S09](../../../docs/ai-system/learning/S09.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/operations.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Отметить origin bypass и reconnect amplification.
- Предложить проверяемые controls/SLI с ограниченным выводом, не заявить защиту.

Смежные процедуры: S17, S23. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
