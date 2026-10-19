---
name: cct-score-data-audit
description: Audit provenance, temporal availability, identity and ledger completeness for trader-score datasets. Not a score formula design or permission to fill missing cashflows with assumptions.
---

# S11 · Данные собственного Copy Score

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Зафиксируй snapshot/version/license, universe, time interval/timezone, venue и реальный охват загрузки. Имена файлов не доказывают UTC-границы.
2. Проверь event IDs/dedup/entity identity, maker/taker overlap, missingness и corrections; похожие строки не автоматически экономические дубли.
3. Раздели eventTime, observedAt, resolution-known time и quote-arrival; на cutoff допустимы только реально доступные сведения.
4. Сверь opening cash/positions, deposits/withdrawals/transfers, fees/fills/reserves и mark/settlement; fills archive без этих слоёв не полный ledger.
5. Выдай пригодность конкретных метрик и когорты, интервалы/пробелы и план устранения. Не назначай неизвестному score 0/50, не заявляй результат копировщика по лидерскому win rate.

## Знания и проверка

Для предметной работы: [пакет S11](../../../docs/ai-system/learning/S11.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/score.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Обнаружить неполный ledger и зависимость наблюдений.
- Ограничить допустимые метрики и не назначать числовой score.

Смежные процедуры: S03, S22. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
