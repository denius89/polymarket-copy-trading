# Limitless: план доступа и интеграционных spikes

Дата: 25.09.2026. Статус: исполнимый рабочий план до решения о live-интеграции.

## 1. Цель и границы

Цель этого этапа — получить партнёрский доступ Limitless и доказать на измерениях, что площадку можно подключить к общему copy-trading core без пользовательских средств и без права торгового сервиса выводить деньги.

По ADR-0008 Limitless и Polymarket являются обязательными площадками целевого продукта. Работа по ним идёт параллельно, но разрешение live-режима выдаётся каждой площадке отдельно. Успешный Limitless spike не разрешает live-торговлю на Polymarket, и наоборот.

На этом этапе запрещены:

- пользовательские депозиты и реальные пользовательские сделки;
- хранение seed phrase, приватных ключей и HMAC secrets в Git, документах, чатах и клиентском приложении;
- выдача scope `withdrawal` execution worker;
- обещания доступности продукта в конкретном GEO до письменного ответа площадки;
- учёт обещанной скидки 10% как подтверждённой части экономики;
- автоматическое сопоставление и копирование рынков между Limitless и Polymarket.

## 2. Ожидаемый результат

Этап завершён, когда команда получила:

1. партнёрский аккаунт, созданный только через FutureHaus;
2. одобренную заявку на Programmatic API и фактический список capabilities;
3. письменные ответы Limitless по скидке, GEO, коммерческому использованию данных, recovery и withdrawal;
4. 72-часовой отчёт о задержке и полноте публичных данных;
5. журнал изолированного lifecycle-теста partner sub-account и delegated orders;
6. отдельное решение `GO`, `CONDITIONAL GO` или `NO-GO` для Limitless live adapter.

## 3. Регистрация и partner application

### Шаг 1. Создать проектный аккаунт

Регистрацию выполнить только по ссылке:

https://limitless.exchange/?r=FutureHaus

Использовать отдельный проектный кошелёк. Не использовать личный основной кошелёк основателя, кошелёк агента или будущего клиента.

После регистрации сохранить в закрытом реестре доступов:

- публичный wallet address;
- `profileId`, если он доступен;
- дату и время регистрации;
- подтверждение, что переход и регистрация выполнены через FutureHaus;
- рабочий email и контакт Limitless;
- владельца аккаунта и способ восстановления доступа.

Секретные данные в репозиторий не добавлять.

### Шаг 2. Подать заявку

Подать [официальную заявку Programmatic API](https://docs.google.com/forms/d/e/1FAIpQLSd1P4UB1yDcdcxJzRrM7EiwuJKTFpKtqgFGA_ftYbNOLg7lsQ/viewform).

Краткое описание use case для заявки:

> Multilingual controlled copy-trading product for prediction markets. Users select a trader and configure explicit per-order, daily, per-trader and portfolio limits. The product maintains an execution journal, shows platform and service fees, supports immediate pause and kill switch, and makes no return guarantees. Limitless and Polymarket are separate venue integrations; no cross-venue market matching is planned for the first release.

Запросить:

| Capability / scope | Для чего нужен | Решение первого этапа |
|---|---|---|
| partner sub-accounts | отдельный связанный аккаунт пользователя | запросить |
| `account_creation` | create/list/recover sub-account | запросить |
| `trading` | создание и отмена ордеров, redeem | запросить |
| `delegated_signing` | автоматическая подпись server-wallet orders | запросить |
| `withdrawal` | вывод средств managed sub-account | не запрашивать для execution token |
| публичные market/portfolio reads | рейтинг, backfill и shadow copy | проверить без секрета |

Если Limitless требует `withdrawal` для recovery или пользовательского вывода, запросить отдельный процесс и отдельный токен. Execution worker не должен иметь такой scope.

### Шаг 3. Проверить фактические capabilities

После активации:

1. запросить `GET /auth/api-tokens/capabilities`;
2. сохранить ответ без секретов в отчёте spike;
3. выпустить минимальный scoped token через UI или `POST /auth/api-tokens/derive`;
4. записать token ID, scopes, дату создания, владельца и процедуру отзыва в закрытом реестре;
5. сохранить secret сразу в secrets manager — он возвращается один раз;
6. проверить отказ для операции вне выданных scopes;
7. проверить отзыв и ротацию токена до создания тестового sub-account.

Критерий успеха: capabilities включают `account_creation`, `trading` и `delegated_signing`, а запрос без нужного scope предсказуемо отклоняется. Отсутствие одной из трёх возможностей означает `CONDITIONAL GO` либо изменение режима на подтверждаемую пользователем EOA-модель.

## 4. Письменные вопросы Limitless

Ответы сохранить как датированное приложение к решению о live-интеграции.

### FutureHaus и скидка 10%

1. Подтвердите, что проектный аккаунт атрибутирован рефереру `FutureHaus`.
2. К каким комиссиям применяется обещанная скидка 10%: AMM, CLOB taker, maker, сервисные или иные комиссии?
3. Это относительное снижение комиссии (`fee × 0,90`) или снижение на 10 процентных пунктов?
4. Каков срок действия скидки и может ли он быть изменён?
5. Применяется ли скидка к partner sub-accounts и всем рынкам?
6. Как скидка отражается в `effectiveFeeBps`, `usdFee` и `contractsFee`?
7. Совместима ли скидка со стандартными referral rewards и партнёрскими условиями?

### GEO и eligibility

8. Допускаются ли partner sub-accounts, торговля и продвижение продукта пользователям, находящимся в Сомали, Бангладеш, Марокко, Египте и Таиланде?
9. Есть ли дополнительные требования к резидентству, возрасту, KYC или геолокации для этих GEO?
10. Какой endpoint или поддерживаемый механизм нужно использовать для runtime eligibility/geoblock check?
11. Может ли партнёр хранить результат проверки и каков допустимый срок его актуальности?

### Коммерческое использование данных

12. Разрешено ли коммерчески индексировать публичные профили, историю, позиции, объём и PnL для рейтинга трейдеров, backtest и shadow copy?
13. Разрешено ли хранить нормализованную историю и производные метрики после удаления или изменения публичного профиля?
14. Есть ли обязательные attribution, retention, rate-limit или redistribution условия?
15. Есть ли партнёрский поток публичных user fills или webhook, которого нет в общей документации?

### Delegated signing, recovery и withdrawal

16. Как пользователь самостоятельно отзывает delegated signing без доступности нашего backend?
17. Как пользователь восстанавливает доступ к managed Privy wallet и кто может инициировать recovery?
18. Что происходит с открытыми GTC-ордерами после отзыва HMAC token, delegated authority или partner relationship?
19. Можно ли ограничить delegated signing бюджетом, рынками, типами ордеров и сроком на стороне Limitless?
20. Можно ли гарантированно выпустить execution token без `withdrawal` и запретить ему изменение withdrawal destination/allowlist?
21. Как пользователь выводит средства при недоступности нашего сервиса и какие действия требуют участия Limitless/Privy?
22. Как partner sub-accounts соотносятся с условием Terms о запрете создавать аккаунт от имени другого лица?

## 5. Spike A: read-only ingestion и latency

### Цель

Проверить, достаточно ли быстро и полно публичная история показывает исполненные сделки выбранных лидеров для backtest, shadow copy и последующего копирования.

### Входные данные

- 3–5 активных публичных адресов Limitless;
- не менее 72 часов непрерывного наблюдения;
- `/portfolio/{account}/history`, `/portfolio/{account}/positions`;
- `/markets/{slug}/events` и orderbook для затронутых рынков;
- on-chain block timestamp как опорное время.

### Выполнение

1. Опросить историю каждого адреса раз в 1–2 секунды с backoff после `429` и ошибок.
2. Использовать cursor backfill после рестарта и хранить raw response с временем получения.
3. Классифицировать trade, split, merge, redeem и остальные действия; копируемыми считать только подтверждённые fills.
4. Дедуплицировать сначала по `tradeEventId`, fallback — `transactionHash + account + conditionId + outcomeIndex + strategy`.
5. Для каждого события сопоставить первое появление в wallet history, market events и on-chain timestamp.
6. Зафиксировать цену и доступную глубину при первом обнаружении; рассчитать достижимое исполнение для бюджетов $10, $50 и $200.
7. Выполнить controlled restart и доказать, что backfill не теряет и не дублирует события.

### Измерения

- p50, p95 и p99 задержки обнаружения;
- доля событий, появившихся позднее 30, 60 и 120 секунд;
- пропуски, дубли и изменения порядка;
- доля однозначно классифицированных событий;
- ухудшение цены и доступной глубины к моменту обнаружения;
- доля копируемых fills для $10/$50/$200 с учётом min size;
- полный ожидаемый round-trip cost: venue fee, сервисная комиссия, spread и slippage.

### Критерии успеха

- 72 часа данных собраны без необъяснимых разрывов;
- после replay/backfill нет подтверждённых потерь и двойного учёта событий;
- не менее 99,9% записей имеют устойчивый source event key либо задокументированный fallback;
- p50/p95/p99 и доля stale events рассчитаны по фактическим событиям, а не предположениям;
- для каждого бюджета рассчитана копируемость и причины пропуска;
- команда может установить измеримый venue-specific stale threshold.

Spike считается неуспешным, если публичный источник систематически пропускает события, не позволяет устойчиво дедуплицировать их или задержка делает копирование непредсказуемым. Paper/backtest могут остаться допустимыми даже при `NO-GO` для live copying.

## 6. Spike B: sub-account и delegated-order lifecycle

### Предусловия

- Programmatic API одобрен;
- capabilities проверены;
- письменное разрешение на тест partner sub-account получено;
- используется отдельный тестовый аккаунт без пользовательских средств;
- `withdrawal` отсутствует у execution token;
- установлен малый личный тестовый лимит основателя, если Limitless не предоставляет sandbox/testnet.

Любая реальная минимальная сделка требует отдельного решения основателя после dry run. До этого используются только безопасные read/create/cancel операции, которые не перемещают средства.

### Выполнение

1. Создать partner sub-account и проверить идемпотентное повторение запроса.
2. Получить профиль и адрес; проверить list/recover flow без раскрытия секретов.
3. Проверить allowance readiness и корректный отказ при недостаточном allowance/балансе.
4. Сформировать ордер с уникальными `clientOrderId` и `x-request-id`.
5. Проверить dry run или отклоняемый ордер без достаточного баланса, затем — только после отдельного разрешения — минимальные GTC, FAK и FOK сценарии.
6. Для GTC проверить partial fill, отмену остатка и kill switch: сначала cancel resting orders, затем запрет новых.
7. Для FAK/FOK проверить terminal states, partial/no-fill поведение и фактические комиссии.
8. Искусственно воспроизвести timeout/unknown response и восстановить итог через reconciliation без повторного ордера.
9. Проверить `post_only`, `cancel_only`, `disabled`, ответ `425`, `429` и backoff без tight retry.
10. Сверить API order/fill states с on-chain settlement и внутренним append-only журналом.
11. Отозвать токен и delegated authority; проверить невозможность новых ордеров и судьбу уже открытых.
12. Проверить documented recovery и независимый withdrawal path без предоставления execution worker права вывода.

### Обязательные артефакты

- capability matrix и redacted token inventory;
- sequence log всех запросов со временем, `clientOrderId`, `x-request-id` и результатом;
- таблица переходов состояний GTC/FAK/FOK;
- доказательство idempotency и reconciliation после unknown state;
- результаты token revoke, delegated revoke, recovery и kill switch;
- фактические `effectiveFeeBps`, `usdFee`, `contractsFee` и settlement identifiers;
- список расхождений документации и наблюдаемого поведения.

### Критерии успеха

- sub-account создаётся и восстанавливается поддерживаемым способом;
- execution token торгует, но не может вывести средства или изменить withdrawal destination;
- повтор запроса и unknown response не создают неконтролируемый duplicate order;
- все order states сводятся к внутренней state machine и подтверждаются reconciliation;
- kill switch прекращает новые заявки и отменяет resting orders;
- пользовательский revoke/recovery/withdrawal path описан и проверен без зависимости от работоспособности нашего backend;
- фактическая комиссия каждого fill воспроизводится внутренним ledger;
- ни одно секретное значение не попало в логи или репозиторий.

Любой недоказанный withdrawal boundary, неустранимое двойное исполнение или невозможность восстановить unknown state означает `NO-GO` для Limitless live execution.

## 7. Безопасные ограничения тестов

- отдельные проектные и тестовые аккаунты;
- нулевые пользовательские средства;
- минимальные scopes и разные токены для разных процессов;
- secret только в secrets manager, redaction в логах включён до первого запроса;
- лимиты до вызова SDK: per-order, daily notional, per-trader, per-market и portfolio;
- один тестовый рынок за раз, без cross-venue действий;
- stop-on-anomaly: неожиданный permission, unknown state или расхождение баланса немедленно останавливает новые запросы;
- maintenance status проверяется перед торговым действием;
- результаты скидки 10% считаются экспериментальным сценарием до письменного подтверждения;
- production token не создаётся в рамках этих spikes.

## 8. Что требуется от основателя

| Когда | Действие основателя | Передаваемый результат |
|---|---|---|
| До заявки | зарегистрировать проектный аккаунт только через FutureHaus | публичный wallet address, `profileId`, дата регистрации; без seed phrase |
| Для заявки | указать юридическое/рабочее имя проекта, контактный email, сайт или GitHub и ожидаемый объём | данные для partner application |
| Для переписки | представить контакт со стороны Limitless или отправить подготовленный список вопросов | письменные ответы либо доступ команды к переписке |
| После одобрения | создать token по инструкции и самостоятельно поместить secret в secrets manager | подтверждение token ID и scopes; не secret в чате |
| Перед lifecycle spike | подтвердить допустимость создания тестового sub-account | письменное подтверждение Limitless |
| Перед любой реальной сделкой | отдельно утвердить максимальную личную тестовую сумму и рынок | явное разовое разрешение; пользовательские средства запрещены |
| После отчётов | принять решение по Limitless live gate | `GO`, `CONDITIONAL GO` или `NO-GO` с условиями |

## 9. Порядок выполнения и решение

| Порядок | Работа | Можно выполнять параллельно |
|---:|---|---|
| 1 | регистрация через FutureHaus | подготовка partner application и письма |
| 2 | partner application и письменные вопросы | read-only spike A |
| 3 | получение capabilities и token hygiene check | завершение spike A |
| 4 | sub-account/delegated lifecycle spike B | Polymarket Builder/Session Keys spike по отдельному плану |
| 5 | сравнение Limitless и Polymarket по одинаковым метрикам | экономика и product gate review |
| 6 | отдельное решение Limitless live gate | отдельное решение Polymarket live gate |

### GO

Все критерии spikes выполнены, коммерческое использование данных и GEO письменно подтверждены, withdrawal/recovery boundary доказан, а стоимость исполнения приемлема для целевых бюджетов.

### CONDITIONAL GO

Paper/shadow mode разрешён, но live ограничен конкретным GEO, бюджетом, режимом подписи, типом ордера или дополнительным ручным подтверждением. Все ограничения становятся capability flags адаптера и видимыми правилами продукта.

### NO-GO

Live execution на Limitless остаётся выключенным. Публичные данные могут использоваться только в письменно разрешённых пределах для рейтинга, backtest или research. Обязательность Limitless в целевом scope пересматривается отдельным ADR, а не молча удаляется из проекта.

## 10. Источники проекта

- [Read-only аудит Limitless](14_limitless_read_only_audit.md)
- [Партнёрская интеграция Limitless](20_limitless_partner_integration.md)
- [ADR-0008: две обязательные площадки](decisions/0008_dual_venue_product_scope.md)
- [Programmatic API](https://docs.limitless.exchange/developers/programmatic-api)
- [Authentication](https://docs.limitless.exchange/developers/authentication)
- [Maintenance Mode](https://docs.limitless.exchange/developers/maintenance-mode)
- [Responsible Trading Agents](https://docs.limitless.exchange/developers/responsible-agents)
