---
name: cct-wallet-security
description: Review wallet, signer, user/admin authorization and abuse risks against project trust boundaries. Use for threat modeling or changes to authorization/signing boundaries; a role label or layout change alone does not require a security audit.
---

# S08 · Кошельки, права и безопасность админки

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Определи активы, actors, entry points, trust boundaries и фактические внешние полномочия signer/account/roles; название non-custodial не доказательство.
2. Прочитай действующие денежные/security ADR с заменами. Раздели торговлю, funding, withdrawal и service treasury; secret не вставлять в чат, fixtures, logs или KB.
3. Проверь server/executor/signer enforcement, tenant isolation, sessions/revoke, signing domain/nonce/replay/allowance и admin separation. Скрытая кнопка не RBAC.
4. Разбери stolen identity/key, prompt injection, support/social abuse, прямую DB modification, recipient change и lost Owners. Local block не равен внешнему revoke.
5. Выдай threat→control→evidence→residual risk и план независимой проверки. Не исправляй security обходом подтверждения; exploit/сканирование живой цели не следуют из документального review.

## Дополнительные материалы

[пакет S08](../../../docs/ai-system/learning/S08.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
