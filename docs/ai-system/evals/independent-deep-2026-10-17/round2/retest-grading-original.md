# Independent retest grading

Scope: six frozen retest answers and their raw fixtures; author/errata.json applied before grading. No answer or skill changed. Additional improvement checks are separate from the four frozen criteria.

## S06-B

- **1: pass**. Evidence: «при disconnect нужен статус „Соединение потеряно“; после восстановления транспорта — „Синхронизация“»; «Кэш сохраняет lastConfirmedAt и подпись „Данные устарели“». Reason: Обе ошибки banner и optimistic money найдены; конкретные состояния согласованы с fixture requirements.

- **2: pass**. Evidence: «один активный цикл reconnect, последовательный timeout с exponential backoff и full jitter»; «Отменять timer/request ... при unmount». Reason: Нулевой interval определён как ошибка; bounded strategy и controlled disconnect measurements предложены, численные границы помечены предложением.

- **3: pass**. Evidence: «переход должен учитывать prefers-reduced-motion; проверить объявление статусов ... сохранение фокуса»; «на одинаковых build, route, устройстве, сети и cold/warm cache». Reason: Покрыты preferences, focus/status и воспроизводимые условия. Численный INP не выдуман.

- **4: pass**. Evidence: «screenshot подтверждает только кадр после первого подключения, регрессию reconnect он не покрывает»; «Код и приложение не изменялись». Reason: Дан содержательный ограниченный review, без ложного runtime pass и реализации.

## S09-A

- **1: pass**. Evidence: «знаменатель ... 970 + 20 + 10 = 1000 admitted intents»; «SLI = 970/1000 = 97%». Reason: 100 duplicate requests исключены; HTTP200 dashboard не подменяет correct terminal within 2s.

- **2: pass**. Evidence: «Условно ... допустимы ... 10 bad outcomes. Фактически 30 ... превышение на 20, расход 300%»; «Target пока не принят». Reason: Условный budget рассчитан явно; нарушения принятого SLO не заявлено.

- **3: pass**. Evidence: «Показывать stale с lastConfirmedAt либо unknown; перед повтором выполнять сверку по operationId»; «Соединить traces, operationId, lastConfirmedAt и результаты reconciliation». Reason: Запрещён денежный success по кэшу; сохраняется неопределённость до сверки, резервы не предлагается снимать.

- **4: pass**. Evidence: «назначить ответственного за инцидент, escalation и проверку восстановления»; «В synthetic drill воспроизвести late/unknown/duplicate»; «Удалить raw wallet address из alert labels». Reason: Есть три конкретных runbook изменения, bounded labels и изолированный drill; реальная настройка не заявлена.

- Additional **explicit_conditional_error_budget: pass**. Evidence: «условный остаток бюджета −20 intents, превышение на 20, расход 300%». Reason: Условность и расчёт изложены прямо; target не объявлен принятым.

## S12-A

- **1: pass**. Evidence: «Decision ... = 12:00:03»; «Доступна первая книга: observedAt 12:00:02»; «Вторая ... 12:00:04 и исключается». Reason: Выбрана последняя доступная по observedAt книга, без lookahead и leader-price substitution.

- **2: pass**. Evidence: «5.18 notional; средняя цена 0.518; fee ... 0.0518; общая стоимость 5.2318»; «cash ... 14.7682». Reason: Full target depth 10 при limit 0.54 подтверждён fixture; арифметика верна.

- **3: pass**. Evidence: «максимальный резерв ... 5.454»; «Освобождение этого остатка не задано ... Только условно после разрешённого release»; «Прибыль неизвестна». Reason: С учётом errata S12-A-3: reserve и excess 0.2222 верны; unconditional release не требуется, прибыль не заявлена.

- **4: pass**. Evidence: «Расчёт realizable лишь внутри synthetic допущений книги; реальный fill не установлен». Reason: Результат ограничен immutable fixture snapshot, default latency и реальные исполнения не выдуманы.

- Additional **release_confirmed_rule_or_conditional: pass**. Evidence: «Только условно после разрешённого release available стало бы 14.7682; это не подтверждённый переход». Reason: Release явно условный; отсутствие правила в fixture не замещено новым правилом.

## S15-A

- **1: pass**. Evidence: «новым draft release r9, сохранив r7, ошибочный r8 и evidence инцидента»; «Предлагаемый источник восстановления — сохранённый r7/d20; его пригодность на новом cutoff требуется проверить». Reason: Версионированное восстановление с review+approval; ручные A72/B0 и удаление r8 отвергнуты.

- **2: pass**. Evidence: «Для B ... „Недостаточно данных для рейтинга“, а не 0»; «rating-ineligible не session control»; «receipts сохраняют связь с S9». Reason: Rating eligibility отделена от session control; S9 и operation history не переписаны.

- **3: pass**. Evidence: «r7 → method m3, code c17, data d20, config k5, cutoff 10:00Z, venue P»; «Стандарт копировщика ... неизвестен: sizing, fees, latency и exits». Reason: Полный известный lineage перечислен, непрозрачный config не выдан за доказательство; актуальность r7 на новом cutoff не заявлена.

- **4: fail**. Evidence: «A95 r8 пометить недостоверным ... A72 r7 ... только как исторический»; «draft с причиной и сравнением A/B; независимый review ... явное approval ... затем ... publication». Reason: Affected/historical отображение, comparison и approval есть, публикации и обещания нового A72 нет. Но в ответе отсутствует требуемый oracle план monitoring после восстановления: что наблюдать и когда реагировать на повтор identity/coverage проблемы. Минимальное исправление: добавить наблюдение join/coverage и переходов affected/stale после r9 с ответственным и условием остановки/разбора.

## S22-B

- **1: pass**. Evidence: «прошло 120 секунд ... выходит за документированное окно»; «позиции 102–104 не объяснены»; «Сопоставить восстановленные события с WS». Reason: Окно 60s превышено; seq105 не доказывает полноту, proposed pagination/reconciliation не выдан за выполненное восстановление.

- **2: pass**. Evidence: «доступ к произвольным лидерам — не подтверждён ... authenticated permissions — unknown»; «Idempotency key ... documented, но фактическая дедупликация и fee precision не проверены». Reason: Own account, account authorization, documented и observed execution разделены корректно.

- **3: pass**. Evidence: «SDK не запускать: по docs startup вызывает createOrder». Reason: Read-only утверждение команды отвергнуто; запуск и credentials не предложены.

- **4: fail**. Evidence: «На записанных REST-страницах проверить все cursors, завершение, перекрытие страниц и дедупликацию»; «timeout, ошибки и 429»; «boundary cases price/size precision». Reason: Gap/window/pagination/duplicates/errors/precision проверки конкретны, но требуемый oracle identity contract check отсутствует: unknown account scope назван ограничением, без проверки, что WS и REST события относятся одному нужному account и не смешиваются с чужим/leader. Минимальное исправление: добавить synthetic account identity/binding case с ожидаемым rejection mismatch и исключением чужих событий.

## S23-B

- **1: pass**. Evidence: «screenshot ... только build b7; 100% unit coverage относится к formatters»; «Recorded fixture охватывает venue P и одного tenant». Reason: Полезные узкие результаты сохранены и не перенесены на новый release/всю систему.

- **2: pass**. Evidence: «запросы к B отклоняются без выдачи данных и побочных изменений. Support получает только чтение. Проверить прямые запросы ... revoke»; «unknown ... duplicate ... recovery»; «ожидаемые суммы брать из независимого ledger». Reason: Permission boundary включая direct requests и поддержку проверяется отдельно; retry/recovery инварианты receipt/деньги/резервы независимы от formatter/mock.

- **3: pass**. Evidence: «Реальный withdrawal на $1 исключён условиями задачи»; «recorded/synthetic timeout после отправки»; «изолированный пользовательский путь». Reason: Real account action исключён, предлагаются изолированные synthetic/recorded сценарии, немедленный completed mock признан недостаточным.

- **4: pass**. Evidence: «EN не проверена; mobile runtime и desktop неизвестны»; «вторая venue не проверена»; «admin/support путь с отказами полномочий». Reason: Конкретные gaps локалей/venues/admin/negative scenarios и targeted checks есть; readiness обеих venues не заявлена.

- Additional **current_client_admin_e2e_separate: pass**. Evidence: «Сейчас client runtime E2E не подтверждён, admin E2E явно не запускался; новый план не повышает эти статусы». Reason: Текущее evidence client/admin E2E разделено явно, будущая проверка не подменяет текущий статус.

Summary (24 frozen criteria only): {"pass": 22, "fail": 2, "not_verified": 0}.

Remaining defects: S15-A omits post-restoration monitoring; S22-B omits an identity/account-binding contract check. These are omissions of specified oracle subproperties, not evidence of executed unsafe actions.
