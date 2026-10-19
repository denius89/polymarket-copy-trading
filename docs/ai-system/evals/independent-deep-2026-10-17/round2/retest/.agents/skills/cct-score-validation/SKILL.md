---
name: cct-score-validation
description: Challenge score and replay claims with temporal/group splits, leakage checks, uncertainty and stress tests. Use for methodological validation, not fitting on the holdout or certifying profit.
---

# S14 · Независимая валидация Copy Score

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Проверь заранее заданный target, universe и baseline; отдели разработку метода, eligibility gates и финальную оценку.
2. Проверь train/validation/holdout по времени и общим событиям/связанным адресам. Preprocessing/feature selection должны обучаться без будущей выборки.
3. Исследуй lookahead, survivorship, missingness, много попыток, clustered dependence и смену режима. Random fill split не независимость трейдеров/событий.
4. Сравни net copier outcomes, uncertainty/calibration/coverage и stability, sensitivity к latency/fees/depth; выигрыш на узком отобранном классе не обобщай на весь рынок.
5. Зафиксируй rejected/unsupported claims и воспроизводимые проверки. Не меняй формулу ради пройти holdout; итог limited pass/fail/not_verified методологического утверждения.

## Знания и проверка

Для предметной работы: [пакет S14](../../../docs/ai-system/learning/S14.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/score.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Обнаружить temporal/group leakage и зависимость.
- Не сертифицировать результат; предложить корректное разбиение и повтор без tuning holdout.

Смежные процедуры: S10, S12, S13. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
