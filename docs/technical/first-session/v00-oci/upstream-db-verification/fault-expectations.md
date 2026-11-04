# UB07/04/10/15: независимая проверка следующего блока V00

04.11.2026 · baseline main `9de48a0`, runtime DB `2747516`, backend runtime
`210044b`; backend A/B harness `f7973ae`. Продолжение разрешённого V00-05/06,
серверный чат — ведущий и единственный оператор Oracle. Здесь только инструменты
проверки и ожидаемые результаты; **новые actual NOT RUN**. Новая реализация
production Auth, U03/global drain и допуск V01 этим блоком не заявляются.

Область БД: [audit_fault.py](../../../../../scripts/v00-upstream-db/audit_fault.py),
[audit_locks.py](../../../../../scripts/v00-upstream-db/audit_locks.py),
[read-only наблюдение](../../../../../scripts/v00-upstream-db/observe_fault_locks.sql).
Runtime SQL/functions/grants не меняются. 10 новых локальных тестовых групп
(7 storage, 3 locks) используют вымышленные состояния; вместе с прежними14 —24.
Это не 24 новых серверных испытания.

## Раздельные доказательства

| Сценарий | БД до/после | Что обязательно наблюдать вне этих snapshots |
| --- | --- | --- |
| UB07 | Два context одного actor/current factor, исходные C02 stages; один полный TOTP result/plan/login и один владелец всего matching set; loser401 даёт один rejection/audit/failure, loser503 не даёт ложного отказа/счётчика | Два реальных waiter с blocking graph к держателю actor row; независимый actor успел завершиться до release; один свежий код отправлен обоим, обе попытки перекрылись; нет cookie у loser |
| UB04 | Один исходный admission и seal; generation issued; нет consumption/outcome/result/plan/login/steps; исходные executor/epoch/deadline не изменены | Подтверждение **seal COMMIT** действительно потеряно перед dispatch; provider/network запросов0 до и после exact repeat/new-key negative probe; public503, GET202, без cookie |
| UB10 | Один исходный C02 full bundle; exact provider consume/session witness; no duplicate login/steps | Реальный full COMMIT состоялся, tag не дошёл до controller; direct503 без cookie; GET возвращает исходный result, explicit recovery тот же login/credential/deadline, новых provider calls0 |
| UB15 — только expired budget | После исходного10s admission deadline появился same-T consume/session witness; result/plan/login/steps0, counter/stage прежние | Originally accepted provider dispatch и поздний effect; не новая ручная отправка; исходный deadline действительно истёк; повтор/чтение не выдают cookie или новое право |
| UNKNOWN_NO_FORWARD — дополнительный B | Один admission/seal и issued generation, никакого outcome/полного результата/счётчика; новые запрещённые ключи не создали admissions | Изолированный no-forward proxy принял ровно1request, forward0, второйrequest0; routing/isolation и время сняты отдельно; timeout не объявлен окончательным not-sent |

Публикация исходных runtime JSON следующего прогона не разрешается автоматически
адресным согласием на 13 файлов PR245. Этот кодовый пакет содержит только ожидаемые
условия и вымышленные тесты. Новые actual собираются приватно; публикация производного
пакета идёт по применимому разрешению через административный чат. Не отправлять
отклонённые материалы другим инструментом или через другой чат.

## UB07: реальное ожидание, а не только два HTTP запроса

В `v00_session.lock_context` actor `FOR UPDATE` берётся перед context. Upstream
держит global gate в `FOR SHARE`; отдельные actors не требуют global X. Оператор
перед запуском держит **только выбранную** строку actor в отдельной T. Служебные
соединения этой выделенной проверки получают `PGAPPNAME=v00-ub07-holder`,
`v00-ub07-ingress`, `v00-ub07-executor`. Не менять активный чужой стенд.

`observe_fault_locks.sql` читает только `pg_stat_activity`/`pg_locks` для текущей
БД и данного application prefix; query text и значения параметров не выводятся.
Holder должен быть idle in transaction, с relation RowShareLock на actors.
У двух разных waiters должны наблюдаться `wait_event_type=Lock`, transactionid/
tuple wait и негрантованная соответствующая lock. `pg_blocking_pids` может указывать
не прямо на holder, а через первого waiter — verifier проверяет всю цепочку.
Одна relation lock не доказывает точный actor: сохраняется независимая запись
operator holder setup с фактически заблокированной строкой.

Снимок независимого actor с уже завершённым входом снять **пока holder ещё держит
строку**; рядом снять blocking graph и затем отметить release. Не считать успех
independent actor после release доказательством независимого прогресса. Все шаги
должны уложиться в runtime lock_timeout3s; при недостаточном overlap отпустить
блокировку и сохранить недостаточность наблюдения, не объявлять PASS. Не держать
до таймаута ради искусственного «конкурентного отказа».

Capture может увидеть незавершённый admission первого запроса и вернуть503 до
создания второго. Это допустимая отдельная ветвь, не saved used-step rejection.
Один явный точный POST loser допустим в harness только после независимого
наблюдения **отсутствия его admission** и уже завершённого winner, с тем же op/body/
code и действующим кодом. Нет automatic retry и нового ключа. Если admission уже
есть — executor не переиздаётся. Статусы первого запроса и последующего контроля
записываются раздельно; известный401 exact repeat не добавляет failure/result.

## Минимальный формат offline verifier

`audit_fault.py` читает локальный JSON с точными ключами:

- `schema`: `v00-upstream-fault-storage-v1`.
- `case`: один из пяти идентификаторов таблицы выше.
- `before`, `after`: `v00-upstream-snapshot-v1` одного и того же actor.
- `operations`: список `{context_id, operation_id, action}` исходных команд;
  две AUTH_TOTP_VERIFY для UB07, одна C02 для остальных.

Before берётся после fixture issuance (и двух C02 stages для UB07), до оригинального
запроса. After — после ответов и адресных проверок повтора. Чужих операций/issuance
на этом actor в промежутке нет. Для отдельной проверки неизвестного exact repeat
можно взять before сразу после первого unknown и after после repeats: исходные
admission/executor/deadline и отсутствие результата должны сохраниться. Для
проверки стабильности уже завершённого результата сравниваются отдельные snapshots
до и после exact repeat; первоначальный verifier envelope не переименовывается
в такой сценарий. Q01/erasure могут менять recovery state законно и отмечаются явно.

Команда offline: `python3 -B scripts/v00-upstream-db/audit_fault.py /private/case.json`.
Результат содержит только case, постоянные labels, counts и границы. Нет идентификаторов,
таймстампов, исходных исключений, тела запроса или секретов. Verifier не подключается
к БД/сети. Он проверяет связи полного bundle через существующий auditor **новой
fixture**, не повторяет семь прошлых цепочек/812 сравнений ради нового числа PASS.

`audit_locks.py` получает `{observation, holder_pid, waiter_pids}` с двумя waiters;
observation — точный результат read-only файла. Выход `observed_wait_verdict` не
доказывает точный actor binding, сетевые отправки или независимый actor progress.
Операторские данные отдельно передаются БД для адресной независимой сверки.

## Окончательная граница

UB15 в этом срезе закрывает только **невыдачу доступа при позднем effect**. Нет
реализованного U03 finalizer, глобального drain/reopening или доказанного closure;
`auth_completion_not_issued` не фабрикуется. Original history остаётся202/unresolved
при разрешённом чтении; POST/recovery503 без cookie. Это остаток, а не скрытый PASS.
Для UB04/10 нужен настоящий lost COMMIT acknowledgement, а не обычный exception
до SQL или потеря HTTP после уже известного controller COMMIT. Ошибка в harness
фиксируется отдельно от ошибки runtime, повтор требует свежей безопасной fixture.
