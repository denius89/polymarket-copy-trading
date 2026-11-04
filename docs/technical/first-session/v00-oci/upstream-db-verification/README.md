# V00 upstream Auth: границы БД и ожидаемые доказательства

04.11.2026 · **Продолжение реализации по V00-06:** после прямого поручения
`01a1a6f3-387b-7cf0-82a2-66936cd8a3be` создан [исполняемый кандидат](../../../../../scripts/v00-upstream-db/manifest.md):
core/admission, provider generation hooks, SQL TOTP, атомарный completion и wrappers,
safe snapshot, bound fixture loader и Oracle harness. Шесть локальных групп
RFC/encoding/window oracle прошли; это ещё не SQL/provider/HTTP PASS. Сервер
подтвердил минимальные actual metadata, отдельный base32-looking synthetic factor,
доступность pgcrypto1.3 и подготовил свежий dependency. Новый bridge ожидает
установки и адресного прогона серверным оператором. Ниже — история PR239;
её «SQL/verifier не создан» относится к предыдущему документальному блоку.

04.11.2026, исходный baseline `41123ec`, повторная сверка main `373bf2a` / PR238.
Прямое «вперед» владельца в административном чате
`01a1a6a7-d0fc-7f00-8fda-baf79ebc3d93` относится к реальной цепочке тестовая почта →
email OTP → подключённый TOTP → исходный Shadow login → recovery/logout, внешней
копии/restore и конечному списку условий V01. Серверный чат — ведущий и единственный
оператор Oracle; дополнительные расходы — 0, синтетические данные, прежние стенды сохранены.

БД ведёт `scripts/v00-upstream-db/` и этот каталог документов, новый test namespace
`v00_upstream`. Бэкенд — `tools/v00-upstream-auth/`. Согласовано использовать проверенный
`v00_session` как dependency в новой отдельной копии БД. Новый service executor не
получает прямой plan/complete и синтетический endpoint завершения входа.
Это не замена принятого каталога 78 таблиц и не допуск V01.

**Результат текущего документального блока:** БД и бэкенд согласовали узкий профиль
local-adapter TOTP над действующим provider factor и поколение email-токена как
private instrumentation. Подготовлены [ожидаемый provider manifest PC01–PC12](provider-manifest.md),
[private signatures и транзакции](private-contract.md),
[18 ожидаемых UB-сценариев](verification-plan.md). Исполняемый SQL/verifier не создан;
actual preflight и все новые UB — NOT RUN. Автоматическая проверка разрешений
отклонила серверную read-only SQL-инспекцию; её не обходили через другой инструмент.
Проект контракта вычитан бэкендом; пять замечаний исправлены и повторно закрыты
им в документальном охвате. Это не свидетельство реализации.
Компонентный provider preflight и загрузка шифротекста уже отражены сервером в
[общем остатке V00](../v00-exit-checklist.md). Они не подтверждают новый bridge,
прочитанный actual SQL catalog или восстановление объекта из внешнего хранилища.

| Замечание повторной вычитки | Отражённое исправление | Статус |
| --- | --- | --- |
| UB-R01 | ReadRef сохраняет command action, проверка также для unresolved/recovery | Закрыто в документах; runtime NOT RUN |
| UB-R02 | Immutable ingress capture/admission, отдельная роль, AdmissionRef и исходный бюджет | Закрыто в документах; procedures/grants ещё не реализованы |
| UB-R03 | Полная таблица lock paths, provider user перед generation/seal, граница actor serialization | Expected порядок согласован; deadlock safety не испытана |
| UB-R04 | Закрытые private variants, точные dependency refs, COMMIT/ROLLBACK для401/409/crypto | Закрыто в документах; новый bridge NOT RUN |
| UB-R05 | Непокрытый email negative остаётся unresolved, без ложного wrong-code/result/counter | Закрыто в документах; полный classifier NOT IMPLEMENTED |

Отдельно подтверждено: неразличимая issuance с теми же token+issued-at закрывает
корреляцию. Бэкенд повторно прочитал исправления и связанные UB-сценарии04.11.2026.
Открыты реальные capabilities, конкретные capture/admission процедуры/права,
versioned safe snapshot, negative classifier, реализация и все18 UB. Эти зависимости
не означают повторного открытия закрытых пяти замечаний.

## Что уже есть и что ещё не следует из прежних pass

| Имеющийся пакет | Подтверждённый узкий смысл | Разрыв реальной цепочки |
| --- | --- | --- |
| `v00_db` all-matching | Атомарные полный set used steps, scoped immutable result, счётчик/пауза; наблюдаемые locks | Нет привязки этого результата к provider MFA outcome и полному Shadow completion |
| `v00_db` email witness | Первый signup: точный предшествующий token digest, user confirmation и session в одной provider T | Не доказывает автоматически login OTP для уже существующей identity; поле и переход provider требуют фактической проверки |
| `v00_session` | Полный completion bundle, исходная history, отдельный verifier/recovery cipher/window, Q01 и target logout | Прежний completion вызывался после подготовленного synthetic upstream, а не после реального email/TOTP |
| [Независимая сверка runtime](../session-db-verification/runtime-review.md) | Один сохранённый bundle после потери подтверждения COMMIT, точные source refs/time | Не доказывает provider dispatch и внешний исход до этого bundle |

Проверки старых пакетов остаются их историческими фактами. Ни соседние HTTP 200, ни два
отдельных корректных результата не являются доказанной атомарной цепочкой.

## Условия нового стыка

1. Определить фактический endpoint/provider transaction и точный доверенный witness
   email login OTP; нельзя заменить код magic-link или переиспользовать signup witness
   без доказанного совпадения пути.
2. Привязать context/action/client operation, identity, challenge и factor version
   **до сети**. Durable seal выдаёт разрешение только исходному исполнителю; потеря
   ответа seal/dispatch не разрешает вторую отправку или новый operation key.
3. All-matching set/однократность проверяются вместе с фактором/временем/общими guards.
   Не допустить прямого provider verify в обход этого контроля. Для выбранного
   local-adapter профиля отдельный внешний MFA consume на каждом login не нужен:
   полная проверка, used steps и login сохраняются одной локальной T. Форма provider
   seed и криптографические возможности ещё требуют actual preflight; старый
   `totp_consumed` не выдаётся за полный login или provider AAL2.
4. Подтверждённый внешний эффект и право выдать login — разные факты. Finalizer
   заново проверяет исходную epoch/current guards/срок; late effect не оживляет
   старое право. Применяются принятые U03 и закрытые DTO, не «неверный OTP» вместо
   доказанного эффекта.
5. Общий fence/epoch и reconcile-only остаются по принятой Auth-карте. Нельзя
   незаметно сузить global fence до одного actor или открыть старый permit после
   нового epoch. Сеть не выполняется под удерживаемым DB gate X.
6. Finalizer сохраняет исходный result и весь local login/credential/window/secret/
   context/audit комплект в одной подтверждённой T. До доказанного COMMIT cookie
   не выдаётся; неизвестность читается по исходному scope, не пересоздаёт login.

Источники: [Auth-карта §§5–6](../../auth-storage-unified.md),
[D03-04/05/07/12](../../backend-auth-d03-validation-passport.md),
[D02 API/late result](../../backend-auth-d02-contracts.md).
Provider code path изучен по pinned source; private calls представлены проектом
для вычитки. Фактические capabilities, SQL и новый runtime actual не подтверждены.
Полные C01/C03, resend/mail uncertainty, persistent quotas и MFA lifecycle в этот
узкий bridge не включены; они остаются открытой работой Auth/V00. Новый пакет
не закрывает весь upstream Auth и не переносит зависимости автоматически в V01.

## Backup и границы допуска

Адресная сверка требований — [backup-gates.md](backup-gates.md). Она различает
обязательное текущее поручение внешнего restore, применимые зависимости V01,
безопасное открытие после restore и более позднюю сквозную приёмку V07.
