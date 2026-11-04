# V00: ожидаемая форма provider и границы наблюдателя

04.11.2026. Source review: Supabase Auth `v2.197.0`; Shadow baseline `41123ec`.
Это manifest для единственного серверного оператора. Он не подтверждает чтение
живого каталога и не является разрешением обойти отказ автоматической проверки.
Сервер сообщил, что запрос read-only SQL introspection был отклонён; actual
attestation ниже остаётся **NOT RUN** до разрешённого выполнения.

Обновление main `373bf2a` / PR238: сервер опубликовал успешный компонентный путь
Mailpit →6-digit OTP → Supabase Auth2.197.0 → enroll/verify TOTP. Это источник
наблюдения этих примитивов, не повторённое БД испытание и не actual PC01–PC12.
Точные catalog/permissions/secret-form и связь с Shadow completion ещё не доказаны.
Ссылка на [серверный срез](../v00-exit-checklist.md).

## 1. Минимальный безопасный preflight

Отчёт содержит версии, имена/типы/ограничения, boolean capabilities и counts.
Никаких значений email/OTP/seed/refresh/access token, cookies, ключей, hash токенов,
сырых SQL-параметров и дампов provider rows. Проверка формы secret возвращает
только `plain_base32`, `encrypted`, `unsupported` или `unavailable`, без образца.
Любое несовпадение закрывает зависимый маршрут, а не вызывает исправление provider.

| ID | Что необходимо подтвердить на отдельном стенде | Ожидаемый источник / значение | Безопасный actual |
| --- | --- | --- | --- |
| PC01 | Образ Auth и применённые migrations соответствуют изученному источнику | `v2.197.0`, закреплённый image digest и миграционный набор | NOT RUN: version/digest/migrations-match |
| PC02 | Поля user для двух семейств кода | `auth.users`: `id`, `email_confirmed_at`, `confirmation_token`, `confirmation_sent_at`, `recovery_token`, `recovery_sent_at` | NOT RUN: names/types/nullability; без значений |
| PC03 | Создание provider session | `auth.sessions`: `id`, `user_id`, `created_at`, `aal`, `factor_id`; точные FK/uniqueness по факту | NOT RUN: metadata и разрешённый синтетический trace |
| PC04 | Действующий TOTP factor | `auth.mfa_factors`: `id`, `user_id`, `factor_type`, `status`, `secret`, `created_at`, `updated_at`; type `totp`, status `verified` | NOT RUN: shape, counts и состояние только synthetic factor |
| PC05 | Форма активного seed и шифрование provider | `Factor.SetSecret/GetSecret` допускает plain и encrypted; выбор зависит от config | NOT RUN: только классификация, key ID допустим лишь если несекретный и разрешённый |
| PC06 | Криптографическая функция для предложенного SQL verifier | Доступный `pgcrypto.hmac(bytea,bytea,text)`, установленная schema/version; SHA1 | NOT RUN: capability; отсутствие не повод ставить extension автоматически |
| PC07 | Действительный OTP profile | Email6/expiry10min; user TOTP SHA1/6/30/±1; trusted server time | NOT RUN: config/profile/clock evidence, не client time |
| PC08 | Права и закрытость стенда | Runtime не владелец/superuser; нет public provider bypass; observer не читает secret; executor без synthetic completion | NOT RUN: role membership/function privileges и отрицательные вызовы |
| PC09 | Порядок реального provider email effect | Точный token transition и ровно новая session одного user в той же provider transaction | NOT RUN: сначала existing-user recovery, отдельно initial confirmation |
| PC10 | Срок жизни witnesses | Исторический outcome не удаляется вместе с provider session/factor | NOT RUN: FK/delete behavior; не выполнять удаление вне отдельной synthetic fixture |
| PC11 | Наблюдатель видит все изменения token family | Hooks установлены до тестовой выдачи; reset/replacement/consume различимы, initial unknown закрыт | NOT RUN: generation trace без token bytes/digest |
| PC12 | Штатные audit/log settings не сохраняют секретный ввод | Trusted verifier не пишет raw payload; server query/error logging и tracing проверены | NOT RUN: config/classification и redaction test, не печатать сырой журнал |

Если PC05=`encrypted`, SQL verifier не получает provider key в таблице/функции.
Нужен отдельно проверенный transient decrypt/verifier в доверенном адаптере с
привязкой результата к живой транзакции, текущему factor и времени. Нельзя молча
выключить encryption, скопировать seed или принять caller-supplied success/steps.
Если PC05=`plain_base32` и PC06 подтверждён, узкий SECURITY DEFINER verifier может
вычислять весь набор совпадений внутри БД, не возвращая seed исполнителю.
Ни один из этих runtime вариантов пока не подтверждён этим manifest.

## 2. Выбранная по контракту граница TOTP

[AC09–AC11](../../auth-storage-unified.md#32-подтверждения-лимиты-продолжение-и-окно) допускают
`issuer_source=local_adapter`, оставляют активный seed у provider и требуют
атомарного полного набора использованных steps. [BR08 / механизмы §3](../../backend-review-mechanisms.md)
требуют доказанной совместимости адаптера; provider success сам по себе недостаточен.
[User Auth §6](../../backend-auth-contracts-addendum.md#6-проверка-totp-при-входе-и-обновление-challenge)
задаёт результат и one-use, не требование provider MFA HTTP на каждом login.

Рабочий выбор БД: реальное provider email подтверждение и реально активированный
provider factor; затем trusted local-adapter TOTP и полный Shadow login одной T.
Provider enroll/challenge/verify используется для начальной synthetic fixture.
Это не подтверждение provider AAL2 каждого Shadow login, не завершение MFA lifecycle
и не разрешение доступа к сервисам провайдера по Shadow cookie.

Для варианта обязательного provider MFA на каждом login отдельной проработки требуют
durable reservation всех steps, точный challenge/session/AMR witness и продолжение
после утраты email bearer. `auth.mfa_challenges` не содержит session ID; AMR может
обновляться через upsert. Одного AAL2 или количества session недостаточно.
Refresh/mint JWT не подменяет восстановление исходной операции.

## 3. Точная email-корреляция без копии короткого секрета

Согласованный БД и бэкендом проект private instrumentation; runtime PC09/11 ещё нужны:

1. Hook наблюдает изменение каждой token family у user. При выпуске ненулевого
   токена назначается случайный generation ID. Сравнение OLD/NEW происходит только
   в памяти trigger; raw token и дополнительный обычный hash не сохраняются.
   Доказанное изменение времени выдачи при тех же bytes тоже создаёт новую generation.
   Если повторная issuance имеет те же token bytes **и** issued-at и её write path
   не позволяет различить события, корреляция закрывается как недоказанная. Нельзя
   предположить, что timestamp всегда изменится, или назначить успех старому seal.
2. Все замены/очистки/удаления меняют закрытое состояние этой generation. Hook нельзя
   включить после выдачи и объявить неизвестную старую generation доказанной.
3. До verify-вызова короткая admission/seal T связывает исходные context/action/op,
   user, family, generation, epoch и единственного executor. Только подтверждённый
   commit этого seal даёт этому исполнителю один permit; повтор никогда не выдаёт его.
4. Consume наблюдается по точному OLD current generation → token cleared в provider
   T. Ровно session того же user и той же provider T завершает immutable witness.
   Произвольная очистка без session не success. Несколько подходящих session —
   неоднозначность, не выбор «первой». Порядок hooks доказывается PC09, не угадывается.
5. Пока seal unknown, нельзя новый verify key/новый context/resend для обхода того же
   невыясненного эффекта. Неизвестность фиксации самого seal тоже не даёт повторить
   network. Без доказательства witness результат остаётся unresolved.
6. Запрещён прямой provider bypass и конкурирующий неучтённый caller для этого
   synthetic user/generation. Иначе trigger доказывает факт provider effect, но
   не его принадлежность именно исходному HTTP-вызову. Это явное trust assumption.

Исторические provider witnesses не FK с каскадным удалением на `auth.sessions`.
Email comparison для exact replay — отдельный purpose-bound keyed HMAC по AC08;
generation ID не заменяет сравнение введённых bytes. Generation не раскрывается
клиенту и не становится продуктовым challenge ID автоматически.
Этот witness на primary ещё не внешний доверенный checkpoint после restore.

## 4. Первичные источники

- [OTP → MagicLink](https://github.com/supabase/auth/blob/v2.197.0/internal/api/otp.go) и
  [MagicLink](https://github.com/supabase/auth/blob/v2.197.0/internal/api/magic_link.go):
  existing confirmed user использует recovery family.
- [verify.go](https://github.com/supabase/auth/blob/v2.197.0/internal/api/verify.go):
  проверка email token, consume и выдача новой session.
- [factor.go](https://github.com/supabase/auth/blob/v2.197.0/internal/models/factor.go):
  поля фактора и два варианта хранения secret.
- [mfa.go](https://github.com/supabase/auth/blob/v2.197.0/internal/api/mfa.go),
  [challenge.go](https://github.com/supabase/auth/blob/v2.197.0/internal/models/challenge.go),
  [amr.go](https://github.com/supabase/auth/blob/v2.197.0/internal/models/amr.go),
  [token.go](https://github.com/supabase/auth/blob/v2.197.0/internal/api/token.go):
  provider MFA меняет challenge, AMR/session/refresh state; это отдельные эффекты.

Исходники доступны и прочитаны. Их описание не заменяет actual catalog/config и
наблюдение конкретного работающего образа. Названия полей здесь expected, не PASS.
