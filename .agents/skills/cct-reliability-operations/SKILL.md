---
name: cct-reliability-operations
description: Assess SLOs, capacity, observability, DDoS resilience and incident response for this project. Use for operational planning and review, not enabling live mitigations without a scoped task.
---

# S09 · Надёжность и эксплуатация

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Определи критические пользовательские/денежные пути, dependencies и failure domains. Назначь измеримые SLI, предложенный SLO/window и допустимые последствия отказа отдельно от измерений.
2. Если даны счётчики и target, покажи числитель/знаменатель SLI и на том же окне рассчитай допустимые bad outcomes = denominator × (1 − target), фактические bad и остаток/превышение бюджета. Для proposed target весь расчёт условный; не объявляй нарушение принятого SLO и не смешивай окна/единицы.
3. Раздели edge/CDN/WAF и доступный origin, application quotas, expensive endpoints, WS/backpressure, reconnect storms и бюджеты поставщиков. Один per-IP limit не полная защита.
4. Свяжи logs/metrics/traces с operation IDs, freshness и ledger/reconciliation, без keys/PII и неограниченной cardinality. Alert должен иметь actionable owner/runbook.
5. Разбери dependency outage, DB saturation, stale controls, retry storm и unknown operations; safe degradation не должна рисовать финансовый успех.
6. Подготовь incident/restore/drill и capacity/cost plan, recovery criteria и support escalation. Не включай настройки или рассылку алертов без соответствующего поручения.

## Дополнительные материалы

[пакет S09](../../../docs/ai-system/learning/S09.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/operations.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
