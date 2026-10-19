---
name: cct-infrastructure-plan
description: Compare infrastructure options, environments, capacity, residency, recovery and total cost for this project. Not provisioning resources or selecting a provider by habit.
---

# S17 · План инфраструктуры

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Собери нагрузку, latency/freshness, dependencies, region/residency, privacy, SLO/RPO/RTO и бюджет; неизвестное обозначай допущением.
2. Сравни managed services/VPS, failure domains и operational skills без автоматического Kubernetes/microservices; предлагаемый PostgreSQL не deployed fact.
3. Раздели dev/staging/prod и paper/live credentials/data, control-plane/worker/signer trust boundaries; common DB создаёт общий failure domain.
4. Оцени CPU/RAM/IO/connections, archival/backups/egress/monitoring/support и API quotas. Сравнение цен требует актуальной даты/region/tariff; при отсутствии цен дай модель стоимости.
5. Выдай alternatives/tradeoffs, минимальный план проверки и обратимость/exit. Не арендуй сервер, не меняй DNS или IaC по запросу сравнения.

## Знания и проверка

Для предметной работы: [пакет S17](../../../docs/ai-system/learning/S17.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/operations.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Не выбирать топологию/цену без предпосылок; отметить trust/failure domain.
- Сравнить варианты и полный cost model без покупки/настройки.

Смежные процедуры: S07, S08. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
