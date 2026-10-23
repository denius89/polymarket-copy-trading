---
name: cct-score-governance
description: Plan score versioning, data lineage, monitoring, stale handling and rollback under project admin rules. Not a manual score editor or production publishing authority.
---

# S15 · Версии и управление скором

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Свяжи method/code/data/config versions, standard copier settings, cutoff и scope venue; один номер без lineage недостаточен. В выдаваемом lineage перечисли каждую из этих связей явно: непрозрачный config ID сам по себе не доказывает стандарт копировщика (sizing, fees, latency, exits). Если состава нет, пометь неизвестное и требуемое подтверждение, не придумывай параметры.
2. Раздели identity, data eligibility, ranking eligibility и active copying. Изменение rating eligibility не останавливает сессию автоматически.
3. Определи draft/review/comparison/approval/publication и роль; no manual metric fixing или назначения баллов. Demo controls не production authority.
4. Планируй data/model drift, coverage/freshness и incident thresholds как proposals до проверки; stale/unknown не превращай в нулевой score.
5. Для rollback восстанови правила новой версией, сохрани old outputs и evidence; не пересчитывай совершённые сделки. В governance package явно включи post-restore monitoring: что сверять в identity/coverage/freshness и outputs, ответственную роль, условия остановки/повторного review; неизвестные thresholds остаются предложениями. Выход — governance package, не публикация/изменение рейтинга.

## Дополнительные материалы

[пакет S15](../../../docs/ai-system/learning/S15.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/score.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
