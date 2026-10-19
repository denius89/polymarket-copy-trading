---
name: cct-wallet-security
description: Review wallet, signer, user/admin authorization and abuse risks against project trust boundaries. Use for threat modeling and security evidence, not certification or live key operations.
---

# S08 · Кошельки, права и безопасность админки

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Определи активы, actors, entry points, trust boundaries и фактические внешние полномочия signer/account/roles; название non-custodial не доказательство.
2. Прочитай действующие денежные/security ADR с заменами. Раздели торговлю, funding, withdrawal и service treasury; secret не вставлять в чат, fixtures, logs или KB.
3. Проверь server/executor/signer enforcement, tenant isolation, sessions/revoke, signing domain/nonce/replay/allowance и admin separation. Скрытая кнопка не RBAC.
4. Разбери stolen identity/key, prompt injection, support/social abuse, прямую DB modification, recipient change и lost Owners. Local block не равен внешнему revoke.
5. Выдай threat→control→evidence→residual risk и план независимой проверки. Не исправляй security обходом подтверждения; exploit/сканирование живой цели не следуют из документального review.

## Знания и проверка

Для предметной работы: [пакет S08](../../../docs/ai-system/learning/S08.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Скрытый UI не ограничивает signer scope; секрет в пример не сохранять.
- Найти least-privilege/trust-boundary проблему без live revoke/переводов.

Смежные процедуры: S01, S03. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
