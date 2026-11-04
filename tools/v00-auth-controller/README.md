# V00: узкий контроллер TOTP и сверка Auth-эффекта

04.11.2026. Основа `74fc31f` / PR224. Новое поручение владельца разрешает проверочный код и испытания трёх пунктов V00. Серверный чат — единственный оператор Oracle; этот пакет не разворачивает стенд самостоятельно.

## Граница

Это **проверочный адаптер**, не реализация V01, всех D02 HTTP-контрактов или каталога78. `/v00/*`, `totp_consumed`, `confirmed_effect` и диагностические `reason` — только тестовый transport. Он не выдаёт Shadow login/cookie, JWT или provider token. Полный D03-05 (enroll/disable/reset/reenroll, security transition, audit/notification), остальные provider actions BR08 и D03-07 остаются отдельными испытаниями. Нативное повторное принятие TOTP само по себе не объявляется взломом: проверяется совместимость с более строгим принятым профилем Shadow.

Правила: [Auth §6/7](../../docs/technical/first-session/backend-auth-contracts-addendum.md), [D02 §6/8](../../docs/technical/first-session/backend-auth-d02-contracts.md), [D03-04/05](../../docs/technical/first-session/backend-auth-d03-validation-passport.md). SQL/независимые наблюдения — `scripts/v00-db/`, владелец участка — чат БД.

## Состав

- `totp.py`: SHA1/6digits/30s/T0=0/±1; полный matching set; HMAC fingerprint с отдельным закрытым ключом (код не сохраняется и не хешируется открытым SHA).
- `controller.py`: закрытые fixture principal/context bindings, replay до часов/новой проверки; атомарные функции БД; однократное разрешение отправки provider запроса и отдельное чтение witness.
- `test_*.py`: RFC4226/6238, коллизия, границы, строгий ввод, scoped replay, clock failure, запрет повторного dispatch. Это локальные проверки логики, не реальные PG/network tests.
- `prepare_email.py`: операторские синтетические signup и чтение внутренней почты. Создаёт новый private файл, никогда не подтверждает email. Рабочий пароль/URL/token не выводятся.
- `prepare_client.py`: из private fixture manifest БД создаёт отдельные private configs контроллера и клиента. Клиент получает только свои искусственные proof/коды, без factor secret/DB credentials.
- `client_probe.py`: запускается только из изолированной клиентской сети, проверяет отсутствие TCP к реальным Auth/DB адресам, HTTP ответы, повторы, одновременный старт и потерю клиентского ответа.

## TOTP и доказательства

`verify_totp` связывает context/challenge/factor version/operation/fingerprint и расходует все matching steps вместе с результатом. Пересечение хотя бы одного ранее использованного шага отвергает весь набор. Один actor lock защищает счётчик между контекстами/устройствами. Точный replay не расходует код повторно, изменение payload конфликтует. Смена 30-секундного окна во время ожидания DB lock даёт технический отказ без расхода/счётчика, автоматического retry нет.

Публичный RFC-secret `12345678901234567890` имеет код `468457` на шагах153567 и153569; при центре153568 совпадают оба. На границе до центра — только153567, после — только153569. Это **фиксированные тестовые часы**, заданные только администратором БД, а не возможность клиента передавать время. Отдельный wall-clock случай использует закрытый случайный seed и время БД. Доверенность времени берётся из read-only операторского Chrony sample; срок sample — условие конкретного прогона, не новый продуктовый TTL. При недоступном/просроченном sample —503 без вызова verify/counter. В evidence fixed/wall никогда не смешиваются.

Реальную конкуренцию с двумя соединениями и наблюдаемым lock barrier проверяет БД. Одновременный старт двух HTTP-запросов сам по себе не доказывает столкновение транзакций. Дополнительный fresh fixture `lost_client_reply` проверяет обрыв клиентского соединения до заголовков TOTP-ответа и восстановление только через чтение исходного результата; БД отдельно сверяет один result и два consumed steps.

## Корреляция потерянного ответа

Проверяется конкретный signup/email-verification путь Auth2.197.0. До HTTP сохраняется immutable seal `operation_id → synthetic user → digest исходного confirmation_token`. Только первый успешно получивший durable `dispatch_allowed=true` вызов отправляет запрос. Потеря ответа seal, повтор/новый ключ при занятом user и unknown не разрешают повторную отправку.

Наблюдатель БД связывает переход `email_confirmed_at` из NULL с digest **OLD** token; сессию принимает только в той же provider transaction по user+txid. В [verify.go v2.197.0](https://github.com/supabase/auth/blob/v2.197.0/internal/api/verify.go) подтверждение и выдача сессии выполняются в одной транзакции; [User.Confirm](https://github.com/supabase/auth/blob/v2.197.0/internal/models/user.go) очищает token вместе с установкой времени. До испытания эти исходники — основание конструкции, не доказательство фактического прогона.

Faults задаёт только операторский fixture, HTTP клиент не выбирает их:

| Случай | Ожидание |
| --- | --- |
| `before_send` | Seal есть, HTTP не отправлен. Сохранённая неизвестность без эффекта; это **не** реализация `closed_without_dispatch`. Replay не отправляет запрос |
| `before_headers` | Реальный socket shutdown сразу после отправки HTTP, до чтения любых заголовков. Commit/rollback заранее не угадываются: только witness подтверждает эффект, иначе uncertain |
| `after_effect_before_result` | Ответ провайдера получен и отброшен, до локального чтения результата искусственный503. Следующий lookup восстанавливает только доказанный witness, без нового HTTP |
| `none`, клиент отбрасывает ответ | Клиент закрывает сокет до заголовков контроллера. Последующие чтения восстанавливают результат, исходная команда не отправляется повторно |

Witness на том же primary — транзакционный источник provider outcome этого теста, **не внешний backup/witness для восстановления после потери сервера**. Из подтверждённого email-эффекта не выводится разрешение полного Shadow login. Отсутствие witness, таймаут или303 не означают rollback/отказ/успех. Прочие actions и поздние effects при закрытом допуске требуют своих проверок; этот пакет не закрывает BR08 целиком.

## Порядок запуска единственным оператором

1. Сверить точные commits бэкенда/БД, установленную provider schema и image BOM. Поставить SQL БД один раз в V00. Создать отдельный LOGIN, которому выдан только `v00_db_executor`; credentials/passfile вне Git. Runtime не имеет owner/admin/Docker socket. БД запускает свои независимые expected/actual проверки.
2. Контейнер контроллера: Python≥3.11 stdlib + `psql`; версии/образ фиксирует оператор. Две сети: внутренняя Auth/DB и отдельная client-only. В client-only нет Auth/DB, порт контроллера наружу не публикуется. Клиентский контейнер не имеет host network, privileged, Docker socket или второй сети.
3. Оператор выполняет `scripts/v00-db/seed_controller.py --output <new-private-seed-file>` под admin runner. Это отдельные synthetic fixtures, не reset существующих данных. `V00_PSQL_COMMAND_JSON` — argv psql runner без shell; для controller обычный `["psql"]` и dedicated login.
4. При проверке email создать private fixtures через `prepare_email.py`: env `V00_PROVIDER_ORIGIN`, `V00_MAIL_ORIGIN`, `V00_TEST_PRINCIPAL` (из seed), `V00_EMAIL_OUTPUT`; `V00_EMAIL_FAULTS` выбирает только перечисленные варианты. Подготовка не обходит rate-limit провайдера. Если разрешённый лимит исчерпан, отмечается blocked/setup, не pass.
5. Непосредственно перед запуском выполнить `prepare_client.py`: env `V00_SEED_CONFIG`, `V00_CONTROLLER_ORIGIN`, `V00_FORBIDDEN_TCP_JSON` (два реальных IP/port Auth9999/DB5432 с label), `V00_CONTROLLER_OUTPUT`, `V00_CLIENT_OUTPUT`; для email дополнительно `V00_EMAIL_FIXTURES`/`V00_PROVIDER_ORIGIN`. Выходные файлы новые0600; wall-code действует только в принятом окне.
6. Контроллер запускается `python3 controller.py` с env `V00_FIXTURE_CONFIG`, `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSFILE`, `V00_CLOCK_ATTESTATION`, `V00_PORT=8080`. Clock-file read-only: `trusted`, `checked_at` и `valid_until` (Unix seconds), после фактической проверки Chrony. Права fixture/passfile0400/0600. При ошибке clock не подставлять trusted=true.
7. В клиентской сети `V00_CLIENT_CONFIG=<private-client-file> python3 client_probe.py`; сохраняется только очищенный JSON. Полные private manifests/почта/URL/пароли/коды/ключи в Git не попадают. БД отдельно читает used steps/results/counters и provider witness по IDs из закрытого manifest.
8. Для отдельной добавочной проверки потери TOTP-ответа использовать новый неприменённый `lost_client_reply` fixture и `V00_ONLY_LOST_TOTP=1` при `prepare_client.py`. Клиент выполнит только сетевые отрицательные контроли и этот один case, без повторения email/остальных команд. Контроллер должен быть запущен с соответствующим private output config, чтобы bindings совпали.
9. Для повторного прогона — новый fixture scope. Не чистить историю/used steps для зелёного результата. Проверка ошибок/restore не меняет старые результаты. Общее evidence и допуск собирает серверный ведущий.

## Статус

18 локальных unit-проверок пройдены, включая отдельный генератор targeted manifest и отсутствие fallback к полному прогону. На Oracle оператор сообщил успешный прогон27 HTTP/network случаев для commit `111c85e`: all-matching/reuse/collision/replay/conflict/5–15/guards, два HTTP contenders, четыре варианта потери Auth-ответа, запрет прямого Auth/DB из client-only сети. После выявленного RLS-препятствия применён узкий test-only allowlist БД; первый отказ не скрывается, успешный прогон использует свежие fixtures. Отдельно выполнены12 storage и8 RLS проверок БД. Очищенный actual и независимую сверку хранит [общий пакет V00](../../docs/technical/first-session/v00-oci/README.md).

Дополнительный lost-client-reply TOTP оператор выполнил отдельно на неизрасходованном fixture: тот же frozen controller/client_probe `111c85e`, вручную собранный минимальный private config. Клиент не прочитал заголовки исходного ответа, только `/v00/totp/result` вернул200/resolved; по exact context+operation сохранён1 result и steps153567/153569. После физического restore отдельной копии записи и права сохранились. Автоматический генератор из последующего commit в этом серверном прогоне **не участвовал**; он проверен отдельными offline unit tests, а не объявлен испытанным на Oracle.

`before_headers` email остался uncertain: это положительная проверка безопасной неизвестности, а не подтверждение эффекта/отката. Полный Shadow login не выдавался. V01 закрыт до применимых результатов D03; этот узкий успех не закрывает весь V00/D03/BR08, факторные изменения или внешнее защищённое восстановление после потери сервера.
