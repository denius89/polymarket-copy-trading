---
name: cct-product-qa
description: Design risk-based acceptance and fault/concurrency tests for user/admin and financial scenarios. Use for acceptance strategy or cross-layer fault testing; a bounded prototype click-through does not require a full product QA programme.
---

# S23 · Сквозная стратегия качества

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Назови пользовательский результат и критические инварианты, роли/локали/venue/mode; выбери boundary cases по риску, не полный декартов продукт без пользы.
2. Выбери unit/property/integration/E2E/visual/accessibility/exploratory уровни и независимый oracle. Проверка, повторяющая ту же формулу, не независимый контроль.
3. Включи duplicate/out-of-order/late/cancel/partial/unknown, гонки бюджета, stale controls и failure/recovery; проверь деньги/лоты/trace, а не одну зелёную кнопку.
4. Отдели synthetic/recorded/staging от real venue/account, предусмотри изоляцию и запрет неожиданных side effects. Нагрузочные/денежные тесты требуют своего scope.
5. Выдай acceptance matrix и минимальные воспроизводимые примеры/ожидаемые свойства с доказанным охватом. Отдельно пометь текущий evidence/status для client и admin E2E, tenant/permission boundaries, локалей и venues: план сценария не выполненная проверка. Green coverage и screenshot не полная приёмка; не начинай реализацию tests/app вне поручения.

## Дополнительные материалы

[пакет S23](../../../docs/ai-system/learning/S23.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
