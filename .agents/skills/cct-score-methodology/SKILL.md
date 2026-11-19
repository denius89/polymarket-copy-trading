---
name: cct-score-methodology
description: Research trader-score targets, baselines, uncertainty and candidate methodology using audited copier evidence. Not automatic acceptance or publication of new formulas or weights.
---

# S13 · Исследование методики Copy Score

[Общие правила навыков](../../../docs/ai-system/OPERATING_RULES.md) открывай по вопросу, если нужного правила ещё нет в контексте или оно изменилось.

## Процедура

1. Сформулируй estimand: чьё будущее копирование, на каком стандартном счёте и горизонте; лидерский PnL и копируемая полезность различаются.
2. Проверь prerequisites данных/replay до выбора сложной формулы; существующие принятые веса не меняй из research draft.
3. Определи простой baseline, eligibility отдельно от ranking, расходы/риск/неопределённость; короткая история требует осторожности, не произвольной награды.
4. Обоснуй кандидатов и первичные научные источники под гипотезу; calibration, shrinkage/LCB/CE — альтернативы, а не доказанный победитель по названию.
5. До просмотра holdout зафиксируй protocol/splits/metrics, sensitivity и отказ от вывода при insufficient evidence. Выход — research proposal, не принятие/publication/recalculation.

## Дополнительные материалы

[пакет S13](../../../docs/ai-system/learning/S13.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/score.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
