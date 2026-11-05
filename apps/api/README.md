# Закрытый synthetic paper API · polygon-paper-v1

Кандидат TypeScript API для POLYGON-SYNTH-01. Это отдельный ограниченный тестовый
профиль, не готовность всех 78 продуктовых таблиц, staff Auth, Q06, claim или P04.
Формы следуют [принятым API](../../docs/technical/first-session/backend-api-forms-addendum.md),
[карте ошибок](../../docs/technical/first-session/database-error-field-map.md) и
[контракту Q02](../../docs/technical/first-session/database-q02-catalog-design.md).
DB RPC описан в отдельном пакете `scripts/polygon-paper-db/README.md`.
Наличие пакета не означает его установки или прохождения испытаний.

## Состав

- Q02: закрытые запросы/карточки, полный разрешённый snapshot, Manifest/JCS/SHA-256,
  XChaCha20-Poly1305 cursor, постоянный reader, scope revision, CATALOG_CHANGED.
  Нет TTL, усечения каталога или неподписанного fallback.
- C04/C05/C06 и Q03/Q04/Q05: строгие DTO/декодеры, private UTF-8/base64 raw с
  сохранением NUL/Unicode/NULL/empty; численный разбор и policy остаются в БД.
- Один pg client/Serializable на операцию; параметризованный allowlist RPC;
  5 секунд от начала HTTP-обработки, включая тело, pool wait, locks, CPU и паузы.
  У writes до трёх попыток только после подтверждённого serialization/deadlock
  rollback; чтения не повторяются. COMMIT ACK обязателен до успешного ответа.
  Unknown →503 с прежним commandRef, без нового намерения или выдуманного receipt.
- C06 prepare/calendar/finish в одной T; [календарный компонент](src/time/README.md).
  START имеет отдельный выключатель.
- Внутренний HTTP listener проверяет Host, Origin/защитный заголовок, выбранный
  login/cookie, диагностику, размеры, Unicode и дубли. V00 HMAC совместим с
  существующим user credential; текущие права проверяются RPC в той же T.

## HTTPS gateway

Публичный HTTPS origin обслуживает существующий Python launcher. Он проксирует
только `/api/traders`, `/api/traders/:venue/:id`, `/api/demo/drafts`,
`/api/demo/drafts/:id`, `/api/demo/validate`, `/api/sessions`,
`/api/sessions/current`, `/api/sessions/:id`, `/api/commands/:id` с разрешёнными
методами. Auth и статические `/`, `/app/`, `/admin/` остаются у launcher.
Никакие X-Forwarded-* или caller actor ID не становятся полномочиями.

`GET /__polygon__/identity?requestSchemaVersion=v1` — **только внутренний** bridge,
результат `{userId}` после текущего доказанного user-входа. Публичный gateway
обязан возвращать404 на `/__polygon__/…`. При включённом paper gate launcher
сначала выполняет настоящий Q01, затем получает product user mapping этим bridge
и заменяет только `user.userId`. Ошибка mapping даёт технический отказ, без fallback
к V00 actor UUID. Уже выполненное закрытие окна Q01 этим не откатывается.
При выключенном paper baseline Auth не меняется. Node не имитирует Q01.

## Запуск оператором после допуска совместимого пакета

`npm ci --prefix apps/api --workspaces=false --ignore-scripts --omit=dev`
использует отдельный pinned lock. Запуск: `node apps/api/src/runtime.ts` с
POLYGON_API_CONFIG — абсолютным путём к приватному JSON-файлу без symlink,
доступным только сервисной учётной записи. Ключи/пароли не идут в репозиторий.

Конфигурация закрытая, все поля обязательны:

| Поле | Значение |
| --- | --- |
| profile | polygon-paper-v1 |
| origin | точный HTTPS origin браузера: https://localhost:18443 |
| databaseUrl | существующая приватная БД, выделенный LOGIN только с polygon_executor |
| credentialKeyFile | приватный V00 key file, purpose credential/id credential-1 |
| cursorKeyFile | отдельный приватный ключевой набор Q02 ниже |
| calendarProfile | node, icu, tzdb, temporalPolyfill: измеренные и допущенные версии |
| startEnabled | false до совместной проверки и активации согласованного профиля |
| bindHost | 127.0.0.1; 0.0.0.0 только в изолированной сети контейнеров без публичного порта |
| port | внутренний порт1024–65535 |
| ingress | `{mode:"gateway-monotonic-v1",keyFile:"/private/path"}` для gateway; `{mode:"direct-test"}` только явный disposable HTTP-тест |

cursorKeyFile содержит ровно format=q02-cursor-keyset-v1, enabled=true,
issuerKeyId (32 lowercase hex), keys (массив keyId/hex,16-byte ID и32-byte key),
revoked (массив отозванных ID). Источник перечитывается для каждой страницы;
недоступность/повреждение —503. Ротация сохраняет прежние проверочные ключи;
revoked отвергается400. TTL/автоматическое удаление не добавлены. Отдельный
ключ создаёт оператор один раз, сохраняет при restart, не копирует тестовые ключи.
Это локальный synthetic key store, не новый общий протокол восстановления.

Startup не создаёт БД/учёток/ключей, не применяет SQL и не выполняет скрытый Q01.
Открытие listener не readiness. Оператор отдельно проверяет DB pin, effective ACL,
profile gate/tzdb, отсутствие публичного Node/DB/Auth/Mailpit, ключи, HTTPS proxy и
реальные сценарии. Runtime монтирует только src/package/lock и приватные
конфигурации, без test fixtures.

## Проверки и пределы

### Исходный бюджет HTTPS-запроса

Gateway фиксирует `time.monotonic_ns()+5000000000` при первом входе запроса,
до чтения тела и очереди. Q01 и его последующий identity bridge используют тот
же deadline. После истечения gateway не отправляет внутренний запрос.
Node сравнивает deadline с `process.hrtime.bigint()` и переносит только остаток
в свой performance clock, затем тот же бюджет действует до COMMIT. Новый5s
на внутреннем запросе не начинается.

Закрытые заголовки: `X-Shadow-Internal-Deadline-Ns` — каноническая положительная
десятичная строка; `X-Shadow-Internal-Body-Sha256` —64 lowercase hex точного тела;
`X-Shadow-Internal-Proof` — canonical base64url32 bytes без padding. HMAC-SHA256
вычисляется отдельным32-byte ключом: ASCII `shadow.polygon.ingress.v1` + NUL,
затем method, raw request-target, body hash, deadline; каждое UTF-8 поле предваряет
uint32 big-endian длина. Порядок именно такой. Proof проверяется до body-read,
тело затем сверяется с подписанным hash. Отсутствие/дубли/подмена/невалидный
ключ/истёкший deadline/остаток больше5s →503, без обращения к БД.

Gateway отбрасывает клиентские internal заголовки и формирует свои; Host/Origin
не заменяют этот proof. Файл ключа ровно `{format:"polygon-ingress-hmac-v1",hex}`,
64 lowercase hex, приватные права как у прочих ключей. V00 key не переиспользуется.
Direct-test режим отвергает любой internal proof и не предназначен для gateway.
Gateway и Node работают на одном Linux kernel с проверенными нулевыми
`/proc/self/timens_offsets`; Node проверяет это при запуске. Оператор отдельно
проверяет сопоставимость Python/Node clocks в фактических образах. Проверка
компонента не заменяет slow-body/queue испытания всего gateway.

`node --test apps/api/test/*.test.mjs` проверяет DTO/crypto/HTTP boundary и
контролируемые отказные ответы pg. Фальшивые клиенты unit tests не доказывают
поведение PostgreSQL, атомарность, конкурентность, реальный login или E2E.
`tsc -p apps/api/tsconfig.json` выполняется закреплённым TypeScript проекта.
Корневой workspace lock ведёт фронтенд; локальные установки его не меняют.

Локальный calendar profile Node24.9.0/ICU77.1/tz2025a проверен; серверный чат
отдельно передал16PASS на ARM64 Node24.22.2/ICU78.3/tz2026e. Следующие прогоны
используют CCT_CALENDAR_PROFILE_FILE, не автоматически принимают текущую среду.
Golden даты проверены независимо Python zoneinfo2026e-rearguard.

Для native/WASM interop оператор генерирует публичный вектор командой
`node apps/api/test/cursor-interop-vector.mjs`, передаёт stdout на stdin
`python3 apps/api/test/verify-cursor-native.py` в имеющемся native libsodium
контейнере. Оба контейнера network=none, без runtime keys/DB mounts. Этот probe
прошёл 05.11.2026 у серверного оператора: native libsodium1.0.18 и WASM дали
одинаковый ciphertext, корректную расшифровку и отказ при изменённом теге.
Проверенный wire483 bytes/plaintext426 bytes; тестовые key/nonce общедоступны
и запрещены в runtime. На том же ARM64 Node24.22.2/ICU78.3/tz2026e прошли все
72 компонентных теста (0 failed/skipped). Пакет исходников b5d4708,
SHA256 архива4645ad21be323af125228e24fbc6cb935803575c14e92d4f369f0b3702617e17.
Оба прогона выполнялись network=none без DB и runtime keys; безопасный вывод
сохранён оператором в `oracle-component-safe.txt`, рабочая копия
`/private/tmp/shadow-paper-api-check.2UTezM/`. Эти результаты не проверяют
выдачу реальной cookie, SQL RPC, gateway или конкурентность PostgreSQL.

Совместимый DB pin, реальные HTTP/конкурентные испытания и постоянная активация
не подтверждены локальным пакетом. Нельзя запускать миграции или обходить
отклонённый SQL-прогон из процесса API.

## Отдельный disposable HTTP → SQL пакет

`test/offline-http.mjs` не входит в unit test glob и никогда не запускается при
startup. Только оператор на свежей изолированной копии Oracle с
`POLYGON_DISPOSABLE_HTTP=offline-http-clone`:

1. `node apps/api/test/offline-http.mjs prepare /private/new-fixture-dir` создаёт
   новые случайные ключи/cookies и закрытые файлы0600. Каталог обязан отсутствовать.
   В SQL передаётся только `fixture-input.json` с двумя loginId/cookieDigest;
   keys/raw cookies не входят в SQL, журнал или экспорт на Mac.
2. БД применяет отдельный проверенный `polygon-http-db/setup-fixture.sql` на
   candidate5 e7a85671, с marker `offline-http-clone` и отдельным LOGIN, состоящим
   только в polygon_executor. Setup включает профиль только в копии, создаёт
   помеченные synthetic Auth fixtures и возвращает descriptor JSON. Их opaque
   cipher не доказывает recovery/provider/WebAuthn.
3. Оператор готовит приватный runtime JSON: measured calendar, startEnabled=true,
   bindHost=127.0.0.1, ingress={mode:direct-test}, только runtime LOGIN через
   shared Unix socket. Node container network=none, без DB admin/Docker socket,
   с read-only source/keys/config и единственным приватным output-каталогом.
4. `node apps/api/test/offline-http.mjs run /private/fixture-dir /private/config.json /private/descriptor.json`
   выполняет реальные loopback HTTP запросы. Создаются2 черновика,8 keys/receipts,
   3 reviews и2 сессии с полным финансовым комплектом и суммой400 virtual_USD.
   Проверяются NUL/errors/source, historical replay, stale/key conflict, курсор,
   изоляция пользователей, два одновременных запроса одного C06 и Q04/Q05.
5. После запросов harness записывает `HTTP_COMPLETE`, удерживает соединение
   runtime до60 секунд. Оператор запускает независимый `observe-effects.sql`;
   только после его PASS пишет файл `OPERATOR_OBSERVED` с единственной строкой
   `pass`. Harness проверяет acknowledgement, печатает safe labels/counts и
   закрывает listener/pool. Нет acknowledgement — прогон не PASS.
6. Оператор сохраняет безопасное свидетельство и удаляет только проверенную
   временную копию/тестовые ключи. 008 и постоянная активация не выполняются.

Ни один итог этого этапа не доказывает реальный provider/browser login,
HTTPS gateway, достоверный lock wait, lost COMMIT, restart или restore. Для них
нужны отдельные адресные наблюдения. Даже успешные параллельные HTTP ответы не
доказывают, что PostgreSQL успел заблокировать вторую транзакцию.
