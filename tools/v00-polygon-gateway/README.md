# Python paper gateway · подготовительный кандидат

Это исходный кандидат, а не установленный сервис или разрешение на 008.

- `gateway_core.py`: allowlist, HMAC framing, deadline-bounded body/upstream, Q01 runtime cap, strict product identity.
- `gateway_handler.py`: opt-in subclass существующего `polygon_handler`; `GatewayServerMixin` фиксирует время до scheduling; absolute header reader, реальные Auth Q01 и его последующий mapping.
- `gateway_serve.py`: явная точка запуска на основе существующего `polygon_serve` и его SPA overlay. С выключенным `V00_POLYGON_PAPER_ENABLED` вызывает исходный `serve()` без paper config. С включённым флагом не применяет SQL, не создаёт ключи или пользователей, не меняет DB gate.
- `test_gateway_core.py`: 26 компонентных/transport проверки. Socketpair не создаёт слушающих портов. Legacy app и upstream в этих тестах явно заменены stub; это не real Auth/SQL/browser evidence.

## Сборка исходников для изолированного демо

[GIT-DEMO-LOCK.json](GIT-DEMO-LOCK.json) закрепляет исходники клиента, API,
SQL и Auth, корневой npm lock, образы Node и PostgreSQL по digest и SHA-256
31 Python-файла. Исторические архивы для этой сборки не нужны.

Из корня репозитория, имея Python 3.11+ и Git, выполните:

```sh
python3 tools/v00-polygon-gateway/assemble_git_demo.py HEAD /tmp/polygon-demo
```

Сборка читает Git-объекты указанной версии и проверяет их до записи.
В новом каталоге `src/` содержит npm workspaces, `sql/scripts/` содержит
закреплённые миграции, `tools/` содержит Python runtime с подготовленной
раскладкой импортов, а lock фиксирует идентификатор собранного Git-дерева.

В закреплённом образе Node выполните из `src/` `npm ci --ignore-scripts`
и `VITE_PUBLIC_BASE=/app/ npm run build:web`. Разместите `apps/web/dist` в
`/app/distributions/app` среды шлюза. Дайте непривилегированному процессу шлюза доступ на чтение
файлов и проход по каталогам. Используйте PostgreSQL 17.11 из lock
и порядок миграций из [инструкции БД](../../scripts/polygon-paper-db/README.md).
Для изолированного прогона с готовой синтетической сессией используйте
[HTTP fixtures](../../scripts/polygon-http-db/README.md). Python gateway
использует версии Python, `psql` и libsodium из раздела `ubuntuPackages`. TLS, раздельные DB-роли и ключи
создаются в тестовой среде. Запустите `node apps/api/src/runtime.ts` из
`src/` и `python3 tools/v00-polygon/gateway_serve.py` из корня сборки.
Перед запуском загрузите приватные настройки соответствующей среды;
сборка не создаёт и не читает рабочие секреты.

Новая конфигурация читается существующим `private_json` по `POLYGON_API_GATEWAY_CONFIG`: ровно `format=polygon-gateway-v1`, `upstreamHost` (явный приватный IP), `upstreamPort` (1024–65535), `ingressKeyFile` (приватный путь). Origin берётся из `V00_ORIGIN`; Node должен получить тот же origin. Ключ ingress — отдельный файл ровно `{format:"polygon-ingress-hmac-v1",hex:<64lowercasehex>}`, не credential key. В репозиторий попадают только формы без реальных значений. Ошибки ключа в запросе дают503.

Компонентные тесты не заменяют проверку реальных SQL, API и шлюза
на одноразовом стенде. Состав этой сборки рассчитан на синтетического
пользователя и отдельный браузерный сценарий закрытого демо.

Конкретные ограничения: host-порты не изолируют cookies, нужен отдельный browser profile. На внешнем `/__polygon__/`404. Auth POST10s не меняется, для Q01 и paper сохраняется общий5s. Неизвестный результат commit не превращается в успех. Реальные деньги/площадки/staff/P04 не входят в этот кандидат.

Дополнительно проверен фактический `http.client.HTTPResponse` через socketpair: медленные заголовки upstream не получают новый idle-бюджет. Каждый raw read и send используют остаток исходного deadline. Это transport-test без настоящего Node/SQL, TLS и браузера.

Путь сохранения в Git: `tools/v00-polygon-gateway/`; для него команда проверки `python3 -m unittest discover -s tools/v00-polygon-gateway -v`. Общий E2E-пакет в Git: `docs/technical/first-session/polygon-browser-e2e-package-2026-11-05.md`. Исходный локальный кандидат сохранён отдельно; перед запуском сверять manifest, а не только имя папки.

GW05: выдача headers/body клиенту также использует остаток исходного deadline. После начала ответа ошибка закрывает соединение без второй HTTP response. При уже истёкшем бюджете соединение может закрыться без503; это технический отказ транспорта, а не успешная команда. Socketpair/backpressure проверяет этот случай.
