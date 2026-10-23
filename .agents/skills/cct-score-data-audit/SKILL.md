---
name: cct-score-data-audit
description: Audit provenance, temporal availability, identity and ledger completeness for trader-score datasets. Not a score formula design or permission to fill missing cashflows with assumptions.
---

# S11 · Данные собственного Copy Score

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Зафиксируй snapshot/version/license, universe, time interval/timezone, venue и реальный охват загрузки. Имена файлов не доказывают UTC-границы.
2. Проверь event IDs/dedup/entity identity, maker/taker overlap, missingness и corrections; похожие строки не автоматически экономические дубли.
3. Раздели eventTime, observedAt, resolution-known time и quote-arrival; на cutoff допустимы только реально доступные сведения.
4. Сверь opening cash/positions, deposits/withdrawals/transfers, fees/fills/reserves и mark/settlement; fills archive без этих слоёв не полный ledger.
5. Выдай пригодность конкретных метрик и когорты, интервалы/пробелы и план устранения. Не назначай неизвестному score 0/50, не заявляй результат копировщика по лидерскому win rate.

## Дополнительные материалы

[пакет S11](../../../docs/ai-system/learning/S11.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/score.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
