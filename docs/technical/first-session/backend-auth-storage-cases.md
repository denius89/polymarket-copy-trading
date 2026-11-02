# Проверка точной карты Auth-хранения

02.11.2026 · Дополнение к [D01-A](backend-auth-storage-map.md). ASC01–ASC18 — документальные сценарии проверки карты, не новые продуктовые A-критерии, не runtime-коды. **Все испытания: не выполнялось.** Это план для БД/API/Auth, а не код, SQL или созданные данные.

Источники: [DA01–DA12](database-auth-handoff-review.md), [E01–E17](database-evidence-plan.md), [G1–G6/CC](database-concurrency-locks.md), [принятый Auth](backend-auth-contracts-addendum.md). В будущих данных только синтетические refs и секреты отдельного изолированного тестового окружения; реальные cookie/OTP/provider evidence в документацию не помещаются.

## 1. Обязательные ограничения и способ обеспечения

| Правило | Механизм карты | Что отдельно сверить |
| --- | --- | --- |
| Один scoped Auth intent | UNIQUE operations(environment,context,action,operation_id), immutable canonical/HMAC comparison | Другой payload не расходует код/не вызывает provider; сырой email различается даже при равной нормализации |
| Один окончательный результат | UNIQUE operation_results(operation_row_id), обратный result FK/phase и immutable result | Ни resolved без result, ни результат без совместимых stage/challenge/subject |
| Полный login только после результата | Unique context/operation/login в completion, typed realm/principal refs, deferred полнота | Отдельная строка auth_sessions не проходит конец транзакции без обязательных completion/credential/window |
| Cookie только исходная | Credential digest + completion/window FK + AEAD AAD; X window | Перестановка ciphertext между login/средами не выдаёт secret; закрытие не создаёт новый login |
| История отдельно от секрета | Erasure только nullable cipher/digest + erased_at; отсутствие cascade | Backup не возвращает право на выдачу; исчезнувший до deadline cipher не CLOSED/пустой secret |
| Согласие не результат/ключ | Typed consent, immutable actor/login/draft/previous ownership; прежний unique receipt | Новый consent не создаёт новую область однократности и не отменяет неизвестный старый запрос |
| Поздний writer исключён явно | Captured epoch/permit, журнал attempts, closed source, fence/drain/reconciliation | Пустой receipt и свободный G3 без этих фактов не разрешают новый effect |
| Auth и Shadow коммитятся локально вместе | Auth control и Shadow одной выбранной локальной транзакции; provider отдельно | Одинаковый кластер не делает внешний HTTP частью этой транзакции |

## 2. Минимальные сценарии

| ID / связь | События, включая отрицательный вариант | Ожидаемые факты и результат |
| --- | --- | --- |
| ASC01 · DA01/E08/E12 | Два C01 с одним context/action/ID: одинаковые bytes; затем иной raw email при равной нормализации; затем иной locale | Одна operation/email binding; повтор исходный результат; различие409, второго dispatch нет. HMAC/key недоступен —503, не совпадение |
| ASC02 · DA01 | Crash до seal; после seal до сети; после внешнего эффекта до local finalizer | Первый допускает только доказанный безопасный путь; два последних не означают rollback. Dispatch/outcome сохраняется, новый permit без confirmed_not_sent не выдан |
| ASC03 · DA01/DA04 | C02 и C03/renew конкурируют по старому challenge; оба порядка; unknown первого | Один согласованный stage/current/result, второй stale либо technical unknown; ни второй login, ни два подтверждённых новых current. Resend не сбрасывает counters |
| ASC04 · DA01/E02 | Прервать local finalizer после любой из result/completion/login/credential/window/secret; попытаться commit parent без child | Полный комплект либо никакого локального успешного комплекта; проверка должна достигнуть целевой completeness, а не упасть раньше по другой FK |
| ASC05 · DA02 | Q01 берёт X window первой; параллельный recovery ждёт; Q01 commit подтверждён | First_confirmed/closed/erasure сохранены вместе, recovery409 CLOSED, исходный deadline/credential/login неизменны; idle не продлён |
| ASC06 · DA02/DA03 | Recovery первой разрешает исходный secret; Q01 закрывает; задержать delivery recovery HTTP до после Q01 | Допустим поздний тот же secret; новая recovery запрещена. Не обещается отзыв уже подготовленного HTTP. Повторная cookie не создаёт новую server session |
| ASC07 · DA03/DA12 | Revoke/смена staff slot перед/после разрешения recovery, обе очередности; поздний cookie response | Текущий guard/slot сильнее cookie, отозванный login не оживает. Нельзя читать stale snapshot после ожидания как актуальный допуск |
| ASC08 · DA02/E11 | Now до/ровно/после deadline; eraser задержан; Q01 впервые после expiry с сохранённой действующей cookie | На границе recovery закрыта независимо от ciphertext; Q01 может подтвердить действующий login, deadline/reason истории не переписываются; erased_at отражает реальную очистку |
| ASC09 · DA02/E08 | Q01 commit response потерян; repeat Q01; reader не может установить состояние window | Не обещать успешный200 при неустановленной обязательной фиксации. Повтор идемпотентен; повреждённая строка не достоверное «окно закрыто» |
| ASC10 · DA05 | Logout A; продолжение через новый полный login B того же user; late result/clear cookie A | Target immutable=A; B не отозван, старый исход не переписан новым C07; GET/204 различены. Чужой realm/principal не проходит typed связь |
| ASC11 · DA06 | Два identical/different continuation POST; access revoked перед GET; ошибка чтения binding | Один immutable binding; identical200/different409; denied не default, storage failure не NULL; claim не происходит автоматически |
| ASC12 · DA07/DA08 | Consent истёк/secret утрачен до GET результата; новый login того же user; чужой user; corrupt consent | Свой доказанный historical scope даёт200 receipt либо202 unresolved, но не execution. Чужой скрыт; unreadable503/RECORD_UNAVAILABLE по контракту, не202 |
| ASC13 · DA09/CC11 | Два consent одного draft, в том числе разных пользователей; конкурентные admission/effect и обе очередности | Один полный claim receipt максимум; чужой результат скрыт; неопределённый конкурент блокирует новое действие. Нет unique active execution как новой постоянной guard-таблицы |
| ASC14 · DA09 | Старый handler допущен, задержан до G3. Другой видит пустой receipt и свободный guard; затем fence/новый epoch; старый возобновляется | До доказанной сверки новый claim не разрешён. После fence старый captured epoch/закрытый consent не обновляются, effect запрещён; fresh snapshot после drain доказывает допустимое отсутствие |
| ASC15 · DA09/E09 | Serialization/deadlock rollback; сохранить/потерять подтверждение rollback; третья попытка/исчерпание5s; commit-loss | До3 только доказанных разрешённых попыток внутри общего срока. Lost proof остаётся unknown, не4-я/новый ключ. При commit-loss receipt и committed attempt/execution согласованы в одном commit |
| ASC16 · E15/DA09 | Fence crash до/после gate-close; executor неизвестен; один item unresolved; попытка reopen по локальному старому witness head | Gate остаётся закрытым до полного доказательства. Задержанный/неучтённый executor не исчезает из inventory; opened epoch не уменьшается |
| ASC17 · E15/DA03 | Restore старого backup с открытым cookie-window, старым consent/credential и отозванными внешними ключами | Нет выдачи cookie/claim только по старой БД. Независимая сверка/epoch/отзывы обязательны; новые full proofs только по отдельному доверенному пути |
| ASC18 · DA01/DA11 | Provider full-auth подтвердился, local completion ещё не был commit; тем временем context expiry/security revoke | Нет нового login с искусственно свежим временем и нет ложного verification_rejected. Provider fact сохранён, публичная окончательная классификация — явный стык D02; не объявлять маршрут готовым до него |

## 3. Что требуется от физической сверки БД

Для каждого обязательного FK/UNIQUE/conditional/deferred правила указать физический механизм и охват всех writers, включая late finalizer, eraser и reconciler. Проверить вставку обеих сторон циклических completion/result/window refs, update/delete immutable фактов, NULL-варианты, полноту rollback и неявные FK locks. Нельзя ограничиться «валидация в API» при доступном другом writer.

Для claim отдельно проверить две admission-транзакции и delayed-before-G3, а не только две уже вошедшие SQL-попытки. Наличие журналов не доказывает, что runtime не возобновит старый permit. Для Q01 проверить служебный commit/неизменность idle и прежней JSON-формы. Для secrets различать логическое закрытие, реальное стирание текущего ciphertext и сохранность старых backup/WAL.

При будущих прогонах каждый ASC получает отдельные expected до запуска, trace разных участников/барьеров, fresh read полных записей, независимый verifier и ограниченный verdict по существующему evidence-формату. Ни одной новой фактической pass-записи сейчас нет.

## 4. Документальная проверка

02.11.2026 выполнены npm run check (структура/Markdown-ссылки/политика хранения), npm run test:repository (10 проверок хранилища и5 проверок уборки веток), git diff --check. Содержательно сверены immutable/nullable варианты, полнота login/result/window, два порядка Q01/recovery, общие бюджеты от начала запроса и delayed claim до G3. Изменены только Markdown-документы; ASC и поведенческие DB/API/Auth/restore проверки не запускались. Физическая вычитка БД ещё требуется.
