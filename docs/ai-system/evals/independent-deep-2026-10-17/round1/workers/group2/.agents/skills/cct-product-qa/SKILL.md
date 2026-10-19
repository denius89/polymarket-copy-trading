---
name: cct-product-qa
description: Design risk-based acceptance and fault/concurrency tests for user/admin and financial scenarios. Use for product QA planning or authorized review, not writing product features or treating coverage as correctness.
---

# S23 · Сквозная стратегия качества

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Назови пользовательский результат и критические инварианты, роли/локали/venue/mode; выбери boundary cases по риску, не полный декартов продукт без пользы.
2. Выбери unit/property/integration/E2E/visual/accessibility/exploratory уровни и независимый oracle. Проверка, повторяющая ту же формулу, не независимый контроль.
3. Включи duplicate/out-of-order/late/cancel/partial/unknown, гонки бюджета, stale controls и failure/recovery; проверь деньги/лоты/trace, а не одну зелёную кнопку.
4. Отдели synthetic/recorded/staging от real venue/account, предусмотри изоляцию и запрет неожиданных side effects. Нагрузочные/денежные тесты требуют своего scope.
5. Выдай acceptance matrix и минимальные воспроизводимые примеры/ожидаемые свойства с доказанным охватом. Green coverage и screenshot не полная приёмка; не начинай реализацию tests/app вне поручения.

## Знания и проверка

Для предметной работы: [пакет S23](../../../docs/ai-system/learning/S23.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Обнаружить круговой oracle и ограниченность coverage.
- Предложить независимые денежные инварианты и сбойные сценарии без кода продукта.

Смежные процедуры: S06, S07, S08. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
