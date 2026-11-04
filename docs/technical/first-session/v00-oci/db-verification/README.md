# V00: независимая проверка хранения и восстановления

04.11.2026. Baseline `74fc31f5fd7096882703134a50c22133b4c6c66c` / PR224, D02/v6.
Новое прямое поручение владельца в административном чате разрешило необходимые код,
тестовое хранение и испытания трёх пунктов V00; повторный прямой ответ
«давай, теперь даю разрешение на код и все что потребуется» подтвердил этот объём.
Это не V01–V07 и не создание всей схемы78. Серверный чат — единственный оператор
Oracle; бэкенд ведёт контроллер, БД — этот пакет и независимые ожидаемые результаты.
Расходы0, синтетические аккаунты, закрытые порты, ключи вне Git сохраняются.

## Статус и область доказательства

**DB01–DB12 исполнены оператором и прошли независимую сверку expected/actual БД.**
[Очищенные actual и хеши](storage-actual.json) получены напрямую от серверного чата;
файлы001/002/runner совпадают по SHA256. Среда — отдельный `shadow-v00-integrated`,
исходный стенд не изменён. DB05 наблюдал двух реальных lock waiters перед release
барьера. Это12 pass в указанном фиксированном профиле; полный Auth не испытан.
Чтение SQL,
проверка синтаксиса Python и файлов репозитория не заменяют PostgreSQL/HTTP/restore.
История BDR01–BDR08 в [листе вычитки](../../database-auth-d02-review-2026-11-03.md)
сохранена; принятие D02 не открывает автоматически исполнительные gates.

Источники обязательств: [D03-04/05/13](../../backend-auth-d03-validation-passport.md),
[Auth §6](../../backend-auth-contracts-addendum.md), [AC04/05/09–12/39](../../auth-storage-unified.md),
[E07–09/11/14/15/17](../../database-evidence-plan.md),
[AS03–06/15–16/26–27](../../database-auth-synthetic-states.md),
[HR/HE](../../database-auth-history-erasure.md), [операции §§4–5](../../backend-operations.md).
Они задают смысл; имена `v00_db.*` — изолированная проверочная модель, а не новые
продуктовые таблицы, DTO или изменение A01–A112/R001–R071.

Два разных уровня времени: фиксированный администратором clock для известной
коллизии RFC-ключа и настоящие серверные часы для сетевого пути. Нельзя объявлять
fixed fixture проверкой Chrony/реальной границы шага. Runtime executor не меняет
clock, bindings, seed, factor version или fixtures. Код/совпавшие шаги поступают
в БД от доверенного закрытого контроллера, не от пользовательского API.

## Файлы и интерфейс

- `scripts/v00-db/001-storage.sql`: actor/factor/context/challenge, immutable result,
  used steps; роли owner/executor/observer. Установка однократная в отдельном namespace.
- `002-provider-observer.sql`: test-only seal и два witness trigger на реальных
  `auth.users` / `auth.sessions` версии2.197.0. Не универсальный provider adapter.
- `003-snapshot.sql`: безопасный read-only срез синтетических строк и проверки связей.
- `verify_storage.py`: независимый SQL-runner; создаёт новые UUID, не сбрасывает историю.
- `seed_controller.py`: отдельные fixtures для сетевого контроллера; новый приватный
  файл0600 с ключами вне Git. В stdout только несекретная сводка.
- `compare_snapshots.py`: сравнение исходного и восстановленного срезов при одной
  остановленной точке записи; ни целостность WAL, ни свежесть внешнего witness из
  совпадения строк не выводятся.

Все runtime-функции принимают **один jsonb**: `lookup_totp`, `read_totp_clock`,
`verify_totp`, `seal_email`, `read_email_outcome`. Lookup выполняется до расчёта
TOTP/нового времени; NULL означает отсутствие видимого результата, не откат.
Результат `totp_consumed` — только примитив проверки, без login/cookie/полного AC05.
Replay возвращает неизменяемый JSON; текущие guard failures не сохраняются как
`verification_rejected`. `fingerprint` — keyed HMAC контроллера, не хеш шести цифр.
Новый ключ не разрешается после технической неопределённости.

`seal_email` допускает отправку (`dispatch_allowed=true`) только первому успешно
зафиксированному seal. При потере ответа seal отправки нет; при повторе false.
Уникальность synthetic user не позволяет второму operation переотправить тот же
effect. Наблюдатель связывает **старый** confirmation token digest, конкретного user,
переход unconfirmed→confirmed, txid и вставку session **в той же provider T**.
Одного HTTP303, user ID или количества строк недостаточно. Digest не попадает в
snapshot/evidence. Нет полного witness → uncertain, без login и повторной отправки.
Отдельного доказательства `confirmed_not_sent` этот probe не создаёт.

Provider source2.197.0 и live колонки сверены профильными чатами; оператор сообщил:
users.id UUID PK, confirmation_token varchar nullable, email_confirmed_at timestamptz;
sessions.id UUID PK, user_id UUID NOT NULL FK users; обе таблицы owner=v00_auth.
Observer расширяет наблюдаемость provider транзакции; такой instrumentation ещё
не означает пригодность управляемого сервиса без этих trigger.

## Независимые ожидаемые результаты до прогона

| ID | Исходное состояние / действие | Ожидается |
| --- | --- | --- |
| DB01 | Public RFC seed, eval153568, code468457; совпадают153567 и153569 | success200, ровно2 steps,1 result,0 failures; оба шага в одном commit |
| DB02 | После DB01 фактор отключён и время сдвинуто | lookup/replay дают byte-equivalent JSON исходного результата; нет повторного расхода |
| DB03 | Тот же context+operation, другой fingerprint |409, прежний result единственный |
| DB04 |153567 уже использован; новый context и совпадение[153567,153569] |401,153569 не расходуется;1 increment, повтор не increment |
| DB05 | Два context одной factor version, один step; admin barrier удерживает actor lock | Наблюдаются2 ожидающих lock; ответы200/401,1 step,2 results,1 failure |
| DB06 |5 разных operations с неверным кодом; затем правильный |5×401, затем429;5 results,5 failures,0 steps |
| DB07 | Ровно15min после паузы, новый текущий challenge |200, серия сброшена, pause снята |
| DB08 | Недоверенное время, сменившийся шаг, чужой challenge |503/503/404; steps/results/counters неизменны |
| DB09 | Внешняя локальная T откатывает successful verify |0 steps/result/failure; lookup NULL; это специально доказанный rollback, не timeout |
| DB10 | Повтор после доказанного DB09 rollback |200 и один новый комплект |
| DB11 | Другая factor version того же actor, прежний номер шага |200, version-scoped step не конфликтует |
| DB12 | Executor меняет rows; observer вызывает verify; owner переписывает history | Все4 попытки отклонены |
| NET | Контроллер вычисляет полный set из seed/code; client не задаёт steps/clock/factor | Сопоставление с DB01/04/05 и denied bypass; отдельные реальные HTTP actual бэкенда |
| OUT | Потеря ответа до headers/после effect; повтор original operation | Exact witness либо uncertain; не новое HTTP/provider effect, не full login |

DB01 использует заранее заданный полный set и отдельно проверяет его атомарное
хранение. Криптографическое получение set доказывается собственным golden vector
бэкенда и NET; SQL не умеет проверить seed и не выдаёт свой успех за криптографию.
DB12 не доказывает защищённость superuser/владельца provider таблиц: оператор
доверенный, executor не их член; эти роли нельзя выдавать пользовательскому пути.

## Порядок операторского прогона

1. Зафиксировать commit/hash трёх SQL, Python, controller, образы/версии/схему/роли.
   Не запускать одновременно другие изменения stand. Не хранить пароль в argv.
2. Оператор устанавливает001→002→003 в `shadow_v00` через psql с ON_ERROR_STOP.
   Не применять повторно и не удалять namespace при ошибке; сначала сверить commit.
3. `V00_PSQL_COMMAND_JSON` задаёт trusted admin psql argv (может быть container exec
   с stdin). Runner добавляет свои psql flags; код функции передаётся stdin.
   SQL-runner использует owner только для fixture/barrier, executor для verify.
4. Для контроллера выделить отдельный LOGIN, член только executor; observer отдельно.
   Проверить отсутствие membership owner/provider/superuser и прямого SELECT/UPDATE.
   Secrets/passfile и clock sample — private, без docker socket в контроллере.
5. Сохранить stdout JSON и завершение процесса; при failure не повторять вслепую.
   Оператор передаёт очищенные actual БД, которая сверяет ожидания и границы вывода.

## Восстановление: ожидаемые проверки

Перед backup остановить пишущие runners/controller/provider либо выбрать и доказать
одну консистентную точку; snapshot всех синтетических таблиц и provider связей
снять **одной read-only repeatable-read T** через observer. `snapshot('{}')` не
содержит токены/seed/cookie. Сам backup всё равно секретный: шифрование до внешней
передачи, ключ вне сервера и внешнего файла копии, отдельное подтверждение чтения.

| ID | Независимое требование | Признак отказа / предел |
| --- | --- | --- |
| REST01 | Приёмщик подтверждает объект/hash, чтение и расшифрование вне исходного диска; проверены реальные uploader/verifier ACL | Локальный архив или самоотчёт uploader не внешняя резервная копия |
| REST02 | Consistent base + system ID/timeline/полный требуемый WAL до целевой точки, контрольные markers до/после backup | Пропущенный сегмент/другая timeline → fail, не fallback к старому состоянию |
| REST03 | Отдельный restore target; provider/controller/workers остаются выключенными | Не восстанавливать поверх исходника; не выдавать старые credentials/повторять dispatch |
| REST04 | Сравнить source/restored JSON; все10 групп и5 checks, точные IDs/results/steps/txid | Счётчики без состава/потерянный outcome/лишний step → fail; пустая группа no-data |
| REST05 | Роли, privileges, trigger enable, immutable guards восстановлены; отрицательные runtime probes подexecutor/observer | Restore одной data dump без ролей/trigger недостаточен |
| REST06 | Разрыв WAL намеренно только в отдельной копии; restore не заявляет целевой marker и остаётся закрытым | «Старый snapshot читается» не pass, отсутствие marker не доказанный no-effect |
| REST07 | После source snapshot создать отдельный sealed/uncertain или confirmed external effect; восстановление старой копии сверить с независимым свежим журналом | Старый DB copy не свидетель свежести самого себя; missing result не разрешает resend |
| REST08 | Измерить UTC+monotonic: момент последнего защищённого восстановления commit, исходный последний commit, начало restore и готовность проверенного состояния | RPO=непокрытый интервал; RTO=время до проверенной готовности, не распаковки. Численные SLO здесь не выдуманы |

REST07 требует внешнего witness/checkpoint и фактических прав/назначений,
не создаваемых ролью независимого проверяющего БД. Владелец1/владелец2 не
приравниваются к реальным infra custodians автоматически. Оператор отмечает
каждую строку pass/fail/not_run/inconclusive с артефактами; оставшийся разрыв
не скрывается общим «backup успешен». Реальное reopening только по принятому H06.

Даже успешные DB/NET/OUT/REST не закрывают полный D03: proof/secret handling,
browser cookie, grants/recovery, бюджеты, полноценные witness/fencing/AC outcomes,
все изменения факторов и полный manifest78 проверяются своим охватом.
V01 закрыт до достаточных D03-04–10/12; BR08 не закрывается одним signup probe.

## Независимая сверка сообщения оператора

БД сравнила все12 actual с ожиданиями выше, отдельно проверила состав partial-overlap,
число результатов/счётчиков, отсутствие записи после rollback и совпадение исходного
result после смены factor/time. Два адресных замечания бэкенда исправлены **до**
испытанного hash: NULL current challenge закрывается через `IS DISTINCT FROM`,
изменение actor/factor binding при ожидании lock возвращает503 без мутации.
Это подтверждение narrow primitive, не выдуманное исполнение всей AC-схемы.

Оператор также сообщил локальный WAL rehearsal на **другом синтетическом наборе**:
pg_verifybackup/SHA256 passed; recovery paused/read-only; reader без UPDATE.
Точка `0/40001E8` дала `active|seed,start|f|on` за3.426s, точка `0/50001F8` —
`revoked|seed,start,revoke|f|on` за1.836s. Без второго WAL сегмента целевая точка
не достигнута. Интервал до симулированного инцидента1.439s. Это сообщение оператора
поддерживает узкий положительный/отрицательный REST02/06, но **не** REST04 полного
Auth/наш namespace и не RPO/RTO продукта. Внешний объект, IAM/custody, доверенная
подпись/свежесть и приёмка восстановленного входа пока `not_run`/зависимость.
Следующий шаг передан оператору напрямую: установить003, захватить один безопасный
source snapshot после остановки writers, восстановить весь integrated namespace и
Auth на отдельной цели, сопоставить снимки; затем связать с внешней копией/журналом.
