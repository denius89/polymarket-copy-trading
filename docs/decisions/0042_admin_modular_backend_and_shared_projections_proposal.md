# ADR-0042: Предлагаемая техническая основа админки

Дата: 09.10.2026. Статус: **предложено для реализации после согласования технического документа**.

## Контекст

Основатель поручил полный технический документ админки и последующую сверку с пользовательским интерфейсом. Продуктовые правила закреплены ADR-0029–0041; создание спецификации не является запуском frontend/backend или live.

## Предлагаемое решение

- TypeScript-модули с общим domain core и contracts; user/admin APIs читают общие проекции sessions, operations, reserves и effective policies.
- Модульный backend, PostgreSQL, durable outbox/inbox и отдельные API/worker процессы без обязательного broker/microservices в V1.
- Emergency control endpoint/process отдельно от пользовательского frontend; fail-closed для новых side effects при недоступности актуального состояния. Общая БД сама по себе не гарантирует независимость от DB outage.
- Сервисный payout executor и signer authority изолированы от пользовательского trading/funding, работают только по frozen Owner-confirmed intents.
- Published policy/content immutable, ledger append-only; no manual success/unknown resend; operations сохраняют provenance и versioned evidence.
- Полная спецификация — [115](../115_admin_console_technical_specification_2026-10-09.md), проверка пользовательских связей — [116](../116_admin_user_interface_consistency_2026-10-09.md).

## Последствия

Конкретный identity provider, deployment topology, libraries/versions, signer custody, source routes и численные SLO проверяются до соответствующего gate. Принятые продуктовые решения не требуют повторного утверждения; технические предложения этого ADR пока не выдаются за реализованную или окончательно принятую инфраструктуру.

## Проверка

Shared projection parity; RBAC/revoke; outbox replay без внешнего resend; constrained payout signer; emergency DB/control outage; backup restore с read-only reconciliation; независимость venue/environment и paper/live.
