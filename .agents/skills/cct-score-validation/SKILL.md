---
name: cct-score-validation
description: Challenge score and replay claims with temporal/group splits, leakage checks, uncertainty and stress tests. Use for methodological validation, not fitting on the holdout or certifying profit.
---

# S14 · Независимая валидация Copy Score

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Проверь заранее заданный target, universe и baseline; отдели разработку метода, eligibility gates и финальную оценку.
2. Проверь train/validation/holdout по времени и общим событиям/связанным адресам. Preprocessing/feature selection должны обучаться без будущей выборки.
3. Исследуй lookahead, survivorship, missingness, много попыток, clustered dependence и смену режима. Random fill split не независимость трейдеров/событий.
4. Сравни net copier outcomes, uncertainty/calibration/coverage и stability, sensitivity к latency/fees/depth; выигрыш на узком отобранном классе не обобщай на весь рынок.
5. Зафиксируй rejected/unsupported claims и воспроизводимые проверки. Не меняй формулу ради пройти holdout; итог limited pass/fail/not_verified методологического утверждения.

## Дополнительные материалы

[пакет S14](../../../docs/ai-system/learning/S14.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/score.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
