# Доступ к API Polymarket

Проверено по официальной документации 25.09.2026. По ADR-0008 Polymarket является обязательной площадкой целевого продукта и исследуется параллельно с Limitless. Этот документ разделяет доступ к публичным данным, торговые credentials пользователя и Builder-доступ проекта. Это разные уровни, и один ключ не заменяет остальные.

## Короткий вывод

Для чтения рынков, цен, книги ордеров и части публичной аналитики отдельное одобрение Polymarket не требуется. Для торговли конкретный signer создаёт или восстанавливает собственные CLOB credentials через подпись кошелька. Для нашего продукта дополнительно нужен Builder profile: он даёт builder code, ключи для relayer, attribution и builder fees.

Непрерывное копирование без использования основного ключа пользователя предполагает Polymarket Session Key. Этот механизм находится в beta, работает только с Deposit Wallet и сейчас требует, чтобы Polymarket отдельно разрешил Builder API key для session-key management.

## Три разных вида доступа

| Уровень | Для чего | Что требуется |
|---|---|---|
| Публичные API | рынки, метаданные, цены, order book, публичная активность | API key не нужен; применяются обычные rate limits |
| Пользовательский CLOB L1/L2 | приватные ордера, сделки и управление ордерами конкретного signer | EIP-712 подпись кошелька для создания/derive credentials; затем `apiKey`, `secret`, `passphrase` и HMAC-подпись запросов |
| Builder Program | attribution, builder fees, gasless relayer, создание Deposit Wallet и управление session keys | Builder profile, builder code и Builder API credentials; повышенные tiers требуют отдельного согласования |

## Что можно получить сразу

Новый builder начинает на уровне Unverified без ручного одобрения:

1. войти в Polymarket своим проектным аккаунтом;
2. открыть `Settings → Builders`;
3. создать Builder profile;
4. нажать `Create New` и выпустить Builder API credentials;
5. скопировать `bytes32` builder code;
6. хранить `key`, `secret` и `passphrase` только в серверном secrets manager.

Текущий Unverified tier включает до 100 relayer-транзакций в день, стандартные API limits, gasless operations, attribution и builder fees. Лимит относится к relayer-транзакциям; фактические CLOB/Gamma limits нужно измерить отдельно на используемых endpoints.

## Что требует обращения в Polymarket

### Session Keys

Session Key — отдельный EOA signer с ограниченными торговыми правами и сроком до 180 дней. Он не может выводить средства из Deposit Wallet. Для авторизации и отзыва session keys нужен Builder API key, который Polymarket должен разрешить для этой функции во время beta rollout.

Канал запроса: `builder@polymarket.com` или Builders Telegram, если доступ уже выдан.

В запросе нужно описать:

- продукт: контролируемое копирование сделок с бюджетами и risk limits;
- модель владения: пользователь контролирует owner wallet, сервис не получает право вывода;
- зачем нужен Session Key: автоматические CLOB-ордера без хранения owner key;
- scopes: только необходимые торговые площадки, для первого spike — `CLOB`;
- отзыв и аварийная остановка;
- ожидаемый тестовый объём и число кошельков;
- ссылку на репозиторий, краткую презентацию и контакт проекта.

### Verified tier

Verified нужен при превышении 100 relayer-транзакций в день или когда понадобятся leaderboard visibility, стандартная инженерная поддержка и повышенный throughput. В письме Polymarket просит Builder API Key, описание use case, ожидаемый объём и дополнительные материалы. Документация указывает ориентир ответа в несколько рабочих дней, но это не SLA.

Partner tier имеет смысл только после работающей интеграции и устойчивого объёма: он даёт unlimited relayer transactions, повышенные API limits и расширенную поддержку.

## Техническая последовательность для нашего проекта

1. **Read-only spike.** Проверить Gamma, CLOB market data, Data API и WebSocket без ключей; измерить полноту, задержку и rate limits.
2. **Builder bootstrap.** Создать проектный Builder profile и ключи на отдельном аккаунте, не связанном с личным рабочим кошельком.
3. **Собственный тестовый wallet.** На разрешённом GEO создать или подключить Deposit Wallet и проверить CLOB L1/L2 credentials на кошельке основателя.
4. **Session-key request.** Отправить Polymarket описание use case и попросить разрешить наш Builder key для session-key management.
5. **Безопасный spike.** Авторизовать session signer только для CLOB, проверить expiry, revoke, повторное получение состояния и поведение открытых ордеров после отзыва.
6. **Builder attribution.** Приложить builder code к тестовым ордерам и проверить attribution, maker/taker классификацию и начисление builder fee.
7. **Нагрузочная оценка.** Посчитать relayer transactions на onboarding, approve, order lifecycle и revoke; определить момент, когда потребуется Verified.

Реальные пользовательские средства и production credentials в этих проверках не используются.

## Обязательные ограничения

- Перед размещением ордера вызывается официальный geoblock endpoint. Заблокированные и close-only GEO обрабатываются согласно ответу площадки; обход ограничений запрещён.
- Builder fee добавляется к platform fee и не заменяет её. Пользователь должен видеть полную стоимость до включения копирования.
- Максимумы Builder Fees сейчас: taker 100 bps (1%), maker 50 bps (0,50%). Изменение ставки разрешено не чаще одного раза в 7 дней и вступает в силу через 3 дня.
- Builder code и ставки публичны. Нельзя строить модель на скрытой комиссии.
- User CLOB credentials, Builder credentials и session private keys хранятся раздельно и имеют отдельные процедуры ротации и отзыва.
- Session Keys пока beta и работают только с Deposit Wallet. Safe/Proxy нельзя считать совместимыми без отдельной проверки или миграции.

## Что потребуется от основателя

Не сейчас, а перед Builder bootstrap:

- отдельный аккаунт Polymarket для проекта;
- разрешённое местоположение для собственного технического теста;
- проектное имя и контактный email;
- короткое описание use case и ожидаемого пилота;
- адрес будущего сайта или GitHub и актуальная презентация;
- решение, кто контролирует проектный Builder profile и recovery.

Приватные ключи, API secrets и session keys не передаются в чат и не коммитятся в Git.

## Открытые проверки

- Подходит ли текущая beta Session Keys для нашей модели автоматического копирования и количества пользователей.
- Какие реальные CLOB/Gamma/Data rate limits получит Unverified builder.
- Какие операции расходуют relayer quota в выбранном onboarding flow.
- Можно ли надёжно связать builder attribution, наш fee ledger и фактическую выплату.
- Как ведут себя session keys, открытые ордера и reconciliation при expiry, revoke и сетевом сбое.
- Какая execution-площадка допустима в каждом исследуемом GEO.

Подробный порядок регистрации, готовый запрос на Session Keys, программа 72-часового наблюдения и критерии `GO / CONSTRAIN / STOP` вынесены в [исполняемый план доступа и spikes](21_polymarket_access_and_spike_plan.md).

## Официальные источники

- API и уровни аутентификации: https://docs.polymarket.com/getting-started/api
- Wallets and Authentication: https://docs.polymarket.com/trading/wallets-auth
- Session Keys Beta: https://docs.polymarket.com/trading/session-keys
- Builder Program: https://docs.polymarket.com/programs/builders/overview
- Builder tiers и процедура upgrade: https://docs.polymarket.com/programs/builders/tiers
- Builder Fees: https://docs.polymarket.com/programs/builders/fees
- Geographic Restrictions: https://docs.polymarket.com/api-reference/geoblock
