# Контракт дизайна ADM-16

Источники: [115 §14](../../../115_admin_console_technical_specification_2026-10-09.md), [118 ADM-16/P-08](../../../118_admin_console_figma_design_brief_2026-10-09.md), ADR-0031 и ADR-0034. Не заменяет API/production контракт.

## Права

content.view — каталог и разрешённые namespace/usage references, история и read-only просмотр. content.edit — черновик и его проверка. content.publish — публикация и откат. locale.manage — определения языков. Права проверяются отдельно, включая момент применения; потеря права не обходится сохранённой кнопкой. Обязательного Owner approval нет, включая финансовые и критические тексты. Пример edit-only не ведёт к публикации.

## Данные и границы

Catalog item: immutable key, usage/surface, locale coverage, draft state, published/draft version, author, updated_at. Editor: base version/revision, RU/EN values, typed placeholders, length/markup/link constraints, comment, validation result, usage reference. Publication: id, operation id, immutable bundle/manifest version, complete locale set, diff, validation evidence, actor, time, current confirmed version. Locale: stable code/name, direction, coverage, inactive/active definition and declared fallback.

Keys зарегистрированы контрактом, не создаются произвольно через замену текста. В примере funds.withdraw.confirmation.body требует amount/asset/address. Числа и адрес передаются typed data и форматируются отдельно; full address сохраняется. Текст не меняет комиссию, риск, permission, действие кнопки или state enum. Максимум 180 знаков — ограничение fixture, не утверждённый универсальный лимит.

## Переходы

Draft → save → validate → preview → publication request → confirmed publication. Пропущенный обязательный перевод/placeholder или нарушенное ограничение блокирует публикацию. Конфликт revision сохраняет пользовательский вариант для сравнения и не перезаписывает актуальный. Публикация переключает согласованный bundle; нельзя смешивать RU/EN разных версий или строки старого cache.

Accepted/pending не равен published. При unknown доступны только проверка/сверка; отправить повторно нельзя. После подтверждённого failure черновик сохраняется, повтор начинается с новой проверки. Server-side idempotency/dispatch/status остаются реализацией, не функцией Figma.

Rollback использует прошлые значения и создаёт новую publication. B-13 → B-14 based on B-12; до подтверждения восстановления последняя подтверждённая версия B-13. История B-12/B-13 не удаляется. Автор черновика и автор публикации различаются; обе записи должны сохраняться.

Missing/unavailable content не означает нулевой каталог/удалённую историю. Продукт использует последний валидный bundle/registry fallback и baseline согласно ADR-0034; реальный fallback contract и cache transport проверяются при реализации. Arabic draft не активируется и не меняет личный выбор языка сотрудника. Управление языками продукта отделено от настроек своего аккаунта.

## Приёмка

Проверить основной P-08, missing/length/conflict/error/unknown, view/edit-only/no-access и language draft. Сверить scope changes, audit before/after, атомарность bundle и используемую version в confirmation evidence с backend перед реализацией. Native preview — ограниченная композиция текста, не конструктор страницы и не обновление клиентских финансовых экранов.
