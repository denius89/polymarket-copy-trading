---
name: cct-infrastructure-plan
description: Compare infrastructure options, environments, capacity, residency, recovery and total cost for this project. Not provisioning resources or selecting a provider by habit.
---

# S17 · План инфраструктуры

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Собери нагрузку, latency/freshness, dependencies, region/residency, privacy, SLO/RPO/RTO и бюджет; неизвестное обозначай допущением.
2. Сравни managed services/VPS, failure domains и operational skills без автоматического Kubernetes/microservices; предлагаемый PostgreSQL не deployed fact.
3. Раздели dev/staging/prod и paper/live credentials/data, control-plane/worker/signer trust boundaries; common DB создаёт общий failure domain.
4. Оцени CPU/RAM/IO/connections, archival/backups/egress/monitoring/support и API quotas. Сравнение цен требует актуальной даты/region/tariff; при отсутствии цен дай модель стоимости.
5. Выдай alternatives/tradeoffs, минимальный план проверки и обратимость/exit. Не арендуй сервер, не меняй DNS или IaC по запросу сравнения.

## Дополнительные материалы

[пакет S17](../../../docs/ai-system/learning/S17.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/operations.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
