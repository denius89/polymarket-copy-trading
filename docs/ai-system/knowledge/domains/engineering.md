# Домен, API, frontend/backend, безопасность и QA

Опоры: KB07–KB09; P06 ADR-0028, P07/P08 security/treasury; D01/D02 venues; D03/D04 web quality; D05 transactions; D06 threat modeling; D11 testing. Перед финансовым выводом читать действующие ADR и заменяющие их части. Для собственного скора отдельно использовать score.md.

## Деньги и данные

- Order intent, accepted/submitted order, fill, settlement и wallet transfer различны. Unknown означает незавершённое знание, не разрешение повторной отправки. Резерв не освобождается по желанию UI.
- Лоты сохраняют provenance и связь с лидером/ручным действием. Увеличение/уменьшение и новая покупка/выход требуют своих принятых правил. Одинаковый рынок разных venues не тождество автоматически.
- Отдельно проверять pre-admission недостаточную ликвидность и post-admission partial fill. Цену определяет наблюдаемая подходящая книга, расходы/округление/актив требуют основания. Last/mid/leader fill не универсально исполнимы.
- У идентификаторов важны venue, сеть, event position и asset; precision денег не обеспечивается форматированием числа в UI. Event time и observed time сохраняются для воспроизводимости.

## Архитектура и целостность

- SELECT перед INSERT не делает «проверить и зарезервировать» атомарным. Проверять инвариант под конкурентным исполнением, выбранным isolation/lock/constraint и реальным failure mode.
- Durable outbox/inbox решают сохранение/дедупликацию внутри границы; внешнее exactly-once требует доказанной семантики API и reconciliation. Не все ошибки безопасно retry.
- У API нужны validation, auth/tenant scope, timeout/retry/backpressure, версия ошибок и документированная capability, отдельно account authorization. Schema совпала — не значит данные полны или endpoint актуален.
- Schema migration, backfill, retention, audit и restore рассматриваются вместе. ORM не отменяет constraints/query plans; shared DB не гарантирует аварийную независимость.

## Безопасность и UI

- User/admin/signer authorization должна действовать на сервере/исполнителе; скрытая кнопка не control. Local revoke не доказывает отзыв внешнего credential.
- Signer scope, spending/withdrawal authority, replay domain/nonce, key rotation, segregation и trust assumptions — разные свойства. Non-custodial название не доказывает контроль средств пользователем.
- Frontend state может быть optimistic для удобства, но финансовые факты должны иметь подтверждённое основание. Performance выводы зависят от build/device/network/cache и field/lab охвата.

## Проверка

Выбирать независимые oracle: сохранение денег/лотов/резервов, допустимые переходы и внешняя подтверждённость, а не повтор той же функции расчёта. Coverage полезен для охвата кода, но не доказывает все инварианты. Нагрузочные, security и денежные тесты не запускаются на живой системе из общего QA-плана.
