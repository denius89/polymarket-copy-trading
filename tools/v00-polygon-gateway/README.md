# Python paper gateway · подготовительный кандидат

Это исходный кандидат, а не установленный сервис или разрешение на 008.

- `gateway_core.py`: allowlist, HMAC framing, deadline-bounded body/upstream, Q01 runtime cap, strict product identity.
- `gateway_handler.py`: opt-in subclass существующего `polygon_handler`; `GatewayServerMixin` фиксирует время до scheduling; absolute header reader, реальные Auth Q01 и его последующий mapping.
- `gateway_serve.py`: явная точка запуска на основе существующего `polygon_serve` и его SPA overlay. С выключенным `V00_POLYGON_PAPER_ENABLED` вызывает исходный `serve()` без paper config. С включённым флагом не применяет SQL, не создаёт ключи или пользователей, не меняет DB gate.
- `test_gateway_core.py`: 26 компонентных/transport проверки. Socketpair не создаёт слушающих портов. Legacy app и upstream в этих тестах явно заменены stub; это не real Auth/SQL/browser evidence.

Требуется совместимый исходный launcher из `local-data/polygon-operator/frontend-overlay.tar` и его runtime dependencies. При сборке оператор должен закрепить SHA archive и каждого используемого файла, включая `polygon_serve.py`/`spa_mount.py`, и поместить три runtime .py рядом с launcher. Тесты в runtime не монтировать. Окончательный Compose, TLS/DSN/ACL и fresh-copy operator здесь ещё не собраны.

Новая конфигурация читается существующим `private_json` по `POLYGON_API_GATEWAY_CONFIG`: ровно `format=polygon-gateway-v1`, `upstreamHost` (явный приватный IP), `upstreamPort` (1024–65535), `ingressKeyFile` (приватный путь). Origin берётся из `V00_ORIGIN`; Node должен получить тот же origin. Ключ ingress — отдельный файл ровно `{format:"polygon-ingress-hmac-v1",hex:<64lowercasehex>}`, не credential key. В репозиторий попадают только формы без реальных значений. Ошибки ключа в запросе дают503.

Проверка: `python3 -m unittest discover -s polygon-gateway-candidate -v` из родительского каталога. Пройдено на Mac Python3.11. Это не ARM64, не настоящий provider и не доказательство работы всей композиции. После независимой вычитки нужны фактическая сборка на Oracle, негативные end-to-end проверки шлюза и браузерный маршрут из `shadow-polygon-browser-e2e-package-local.md`.

Конкретные ограничения: host-порты не изолируют cookies, нужен отдельный browser profile. На внешнем `/__polygon__/`404. Auth POST10s не меняется, для Q01 и paper сохраняется общий5s. Неизвестный результат commit не превращается в успех. Реальные деньги/площадки/staff/P04 не входят в этот кандидат.

Дополнительно проверен фактический `http.client.HTTPResponse` через socketpair: медленные заголовки upstream не получают новый idle-бюджет. Каждый raw read и send используют остаток исходного deadline. Это transport-test без настоящего Node/SQL, TLS и браузера.

Путь сохранения в Git: `tools/v00-polygon-gateway/`; для него команда проверки `python3 -m unittest discover -s tools/v00-polygon-gateway -v`. Общий E2E-пакет в Git: `docs/technical/first-session/polygon-browser-e2e-package-2026-11-05.md`. Исходный локальный кандидат сохранён отдельно; перед запуском сверять manifest, а не только имя папки.

GW05: выдача headers/body клиенту также использует остаток исходного deadline. После начала ответа ошибка закрывает соединение без второй HTTP response. При уже истёкшем бюджете соединение может закрыться без503; это технический отказ транспорта, а не успешная команда. Socketpair/backpressure проверяет этот случай.
