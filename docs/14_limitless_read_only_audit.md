# Limitless — read-only аудит пригодности для copy trading

Дата: 24.09.2026. Режим: официальная документация, публичная OpenAPI-схема и публичные GET-запросы. Аккаунт, ключи и реальные сделки не создавались.

## Решение

Limitless технически подходит для публичного рейтинга трейдеров, исторического анализа и paper-trading spike. После этого read-only аудита команда Limitless подтвердила готовность поддерживать проект, и ADR-0007 выбрал площадку первой интеграционной проверкой. Автоматическое копирование всё ещё не разрешено до проверки trust, GEO и economics gates.

Три блокера до разрешения автоматического исполнения на Limitless:

1. Нет публичного потока сделок произвольного лидера. Публичная история показывает уже финализированные on-chain операции, а WebSocket событий ордеров доступен только владельцу аутентифицированного аккаунта.
2. Без участия пользователя автоматическая подпись работает через партнёрский server wallet и `delegated_signing`. Это другая граница доверия, чем отдельный ограниченный signer при основном пользовательском кошельке.
3. Terms дают доступ к Platform Content для личного некоммерческого использования. Допустимость коммерческого индексирования публичных профилей и истории для нашего рейтинга нужно письменно подтвердить у Limitless.

## Карта результата

| Область | Статус | Вывод |
|---|---|---|
| Публичная история и позиции | Условно готово | Данных достаточно для рейтинга, backfill и paper trading |
| Стабильные идентификаторы | Условно готово | Есть `transactionHash`, `tradeEventId`, `orderId`, market slug и outcome index |
| События лидера в реальном времени | Блокер | Публичного user-trade WebSocket нет; REST показывает mined/finalized события |
| Автоматическая подпись | Блокер | EOA требует подпись каждого ордера; delegated flow использует managed server wallet |
| Отсутствие права вывода | Требует spike | `withdrawal` отделён от `trading`, но lifecycle, отзыв и recovery не проверены |
| Сомали и Таиланд | Не подтверждено | Их нет в опубликованном списке запретов, но это не является подтверждением доступности |
| Малые бюджеты $10–200 | Риск | Комиссии taker и market-specific minimum size могут сделать $10 непригодными |
| Коммерческое использование данных | Блокер | Требуется письменное разрешение или отдельное партнёрское условие |

Статусы «блокер» означают необходимость подтверждения, а не окончательный отказ от площадки.

## 1. GEO и eligibility

[Terms of Service](https://docs.limitless.exchange/user-guide/terms-of-service) в редакции от 15.09.2026 запрещают весь доступ из России, Беларуси, Кубы, Ирана, Северной Кореи, Сирии, Крыма, Донецкой и Луганской областей. Торговля дополнительно недоступна пользователям из США, Китая, Онтарио и Альберты.

Сомали, Бангладеш, Марокко, Египет и Таиланд в этом явном списке не указаны. Это позволяет продолжить исследование всех пяти GEO, но не доказывает разрешённость продукта: Terms возлагают на пользователя проверку местного права и позволяют площадке запросить подтверждение возраста, личности и eligibility в любой момент.

Выводы:

- не закладывать KYC со своей стороны, но в onboarding честно предусмотреть возможную проверку со стороны execution-площадки;
- не обещать доступность Limitless в конкретной стране до runtime-проверки и письменного ответа площадки;
- не проектировать обход геоблокировки;
- отдельно запросить подтверждение по Сомали и Таиланду.

## 2. Публичные данные лидера

Публичная OpenAPI-схема подтверждает GET-эндпоинты:

- `/portfolio/{account}/history` — история адреса с cursor pagination;
- `/portfolio/{account}/positions` — открытые позиции;
- `/portfolio/{account}/realized-pnl` и PnL chart;
- `/portfolio/{account}/traded-volume`;
- `/markets/{slug}/events` — публичные финализированные `MINED` CLOB trades;
- `/markets/{slug}/orderbook` — текущая книга CLOB.

Проверка реального публичного адреса вернула для торговой операции:

- `blockTimestamp`;
- `collateralAmount` и `outcomeTokenAmount`;
- market slug, `conditionId`, collateral и expiration;
- `outcomeIndex` и фактическую цену;
- стратегию `Market Buy`, `Market Sell`, `Limit Buy` или `Limit Sell`;
- `orderId`, `tradeEventId` и `transactionHash`.

История также содержит неторговые действия вроде `Merge`. Ingestion обязан классифицировать тип события и не превращать split/merge/redeem в обычную покупку или продажу.

Предварительный ключ источника:

```text
venue = limitless
source_event_key = tradeEventId
fallback = transactionHash + account + market.conditionId + outcomeIndex + strategy
```

`orderId` нельзя использовать как единственный ключ: один ордер способен иметь несколько частичных исполнений. Выбор `tradeEventId` нужно подтвердить replay-тестом на нескольких адресах.

## 3. Задержка и полнота событий

[WebSocket overview](https://docs.limitless.exchange/developers/websocket/overview) разделяет каналы:

- публичные: цены, orderbook, lifecycle рынка и invalidation PnL leaderboard;
- аутентифицированные: позиции и события **своих** CLOB-ордеров.

Публичного WebSocket для подписки на сделки произвольного адреса документация не описывает. Следовательно, discovery сделки лидера должен опрашивать `/portfolio/{account}/history` либо собирать `/markets/{slug}/events`. Второй путь неудобен для большого набора лидеров и всё равно отдаёт только finalized `MINED` trades.

Разовая проверка из текущего окружения показала:

| Запрос | Время ответа |
|---|---:|
| `/markets/active` | 0,25 с |
| `/markets/{slug}/events?limit=5` | 0,18 с |
| `/portfolio/{account}/history?limit=5` | 2,03 с |

Это проверка доступности, а не SLA. В 40-секундном окне наблюдения на выбранном рынке новая сделка не появилась, поэтому фактическая задержка от исполнения лидера до видимости через REST не измерена. Документация гарантирует лишь то, что market events уже mined/finalized. Для копировщика это означает неизбежное исполнение после лидера и риск ухудшения цены.

До live-решения нужен recorded-data spike на 3–5 активных адресах минимум 72 часа:

1. polling 1–2 секунды с backoff и cursor backfill;
2. параллельная фиксация on-chain времени, market events и public history;
3. доля пропусков, перестановок и дублей;
4. p50/p95/p99 задержки;
5. изменение достижимой цены и глубины за это время.

## 4. Аутентификация и граница доверия

[Authentication](https://docs.limitless.exchange/developers/authentication) использует scoped HMAC tokens. HMAC secret аутентифицирует API-запрос, но сам по себе не является ключом кошелька. Для обычного EOA order всё равно нужен EIP-712 signature приватным ключом пользователя.

Есть два рабочих режима.

### EOA пользователя

Пользователь хранит свой ключ и подписывает каждый ордер. Backend хранит partner HMAC secret и отправляет уже подписанный ордер. Режим хорошо соответствует non-custodial границе, но не даёт полностью автоматическое копирование без нового ограниченного signing policy, которого публичная документация Limitless не описывает.

Передача приватного ключа EOA нашему backend запрещается архитектурой проекта.

### Partner server wallet

[Programmatic API](https://docs.limitless.exchange/developers/programmatic-api) позволяет партнёру создать sub-account с managed Privy wallet. Scope `delegated_signing` вместе с `trading` разрешает серверу подписывать ордера за sub-account. Scope `withdrawal` выделен отдельно, поэтому токен для торгового сервиса можно выпускать без права вывода.

Оставшиеся риски:

- кошелёк управляется через инфраструктуру Limitless/Privy, а не через ограниченный signer при основном кошельке пользователя;
- `trading` также нужен для redeem resolved positions;
- отзыв токена, отзыв delegated authority, emergency recovery и судьба live orders интеграционно не проверены;
- существующий Limitless profile нельзя позднее прикрепить к партнёру через опубликованный flow;
- Terms запрещают создавать аккаунт «от имени другого лица», тогда как partner API описывает sub-accounts. Для коммерческой интеграции требуется письменное толкование этого расхождения.

Архитектурный вывод: EOA подходит для подтверждаемого пользователем режима, server wallet — кандидат для автоматического режима только после партнёрского согласования и отдельного permission/recovery spike.

## 5. Сети, ордера, комиссии и минимум

[Migration guide](https://docs.limitless.exchange/developers/migrate-from-polymarket) подтверждает Base `8453`, USDC с 6 decimals, единый REST host и market-specific venue addresses. Поддерживаются GTC, FAK и FOK. Для NegRisk может потребоваться дополнительный approval адаптеру.

[Fees](https://docs.limitless.exchange/user-guide/fees):

| Рынок/исполнение | Комиссия Limitless |
|---|---:|
| AMM | 0,40% со сделки |
| CLOB maker | 0% |
| CLOB taker buy | 0,40–3,00% |
| CLOB taker sell | 0,42–1,50% |

Фактическая комиссия площадки приходит в execution response как `effectiveFeeBps`, `usdFee` и `contractsFee`. Наша сервисная maker/taker комиссия является дополнительной. В неблагоприятном CLOB-примере при двух taker-исполнениях подтверждённого тарифа совокупная номинальная нагрузка может приблизиться к 6,0% до спреда и проскальзывания: 3% + 0,75% на входе и 1,5% + 0,75% на выходе. VIP-максимум 1% taker дал бы 6,5%, но это не стандартный тариф. Точный расчёт использует фактическую базу и тип каждого fill.

Minimum size задаётся рынком. В read-only выборке 20 активных CLOB-рынков `settings.minSize` составлял 50–200 контрактов, медиана — 150. Это снимок, а не характеристика всей площадки. При цене $0,50 даже 50 контрактов требуют около $25 до комиссий, поэтому обещанный диапазон клиента $10–200 не совместим со всеми рынками.

Следствия для продукта:

- рейтинг должен учитывать `copyable at $10/$50/$200`, а не только P&L лидера;
- до сделки проверяются min size, глубина, fee curve и наша комиссия;
- maker-only способен снизить fee, но создаёт tracking error и риск неисполнения;
- FAK/FOK ближе к копированию фактической позиции, но чаще платят taker fee;
- USDT из агентского канала сначала должен быть самостоятельно преобразован пользователем в USDC on Base; Limitless не является нашей платёжной интеграцией.

## 6. Место Limitless в архитектуре

Limitless следует сохранить как отдельный venue adapter с capability flags:

```text
public_wallet_history = true
public_wallet_positions = true
public_leader_trade_stream = false
user_order_stream = authenticated_only
eoa_per_order_signature = true
delegated_server_signing = partner_only
withdrawal_scope_separable = true
collateral = USDC_BASE
order_types = GTC, FAK, FOK
```

Нормализованный copy engine не должен считать рынки Polymarket и Limitless одинаковыми по совпадению заголовка. Копирование между площадками разрешается только при явном проверенном mapping resolution rules, oracle, expiration, outcomes и settlement contract. Для первой версии cross-venue copy исключается.

## 7. Что нужно получить от Limitless

Обновление 25.09.2026: общий интерес и поддержка со стороны Limitless подтверждены основателем. Партнёрский аккаунт должен создаваться через FutureHaus. Ниже остаются вопросы, которые нужно закрепить письменно или доказать интеграционным тестом.

До решения go нужны письменные ответы:

1. Разрешена ли торговля и партнёрская интеграция для резидентов и пользователей, находящихся в Сомали и Таиланде?
2. Разрешено ли коммерчески индексировать публичные профили, PnL, позиции и историю в собственном рейтинге?
3. Допускается ли copy-trading продукт в partner program?
4. Как пользователь отзывает delegated signing и восстанавливает доступ к server wallet без работоспособности нашего backend?
5. Что происходит с live orders после отзыва HMAC token или partner relationship?
6. Можно ли гарантировать токен без `withdrawal` и отдельно запретить изменение withdrawal allowlist?
7. Каковы rate limits и ожидаемая задержка `/portfolio/{account}/history`?
8. Есть ли поддерживаемый поток публичных user fills или webhook партнёра, отсутствующий в общей документации?
9. Как трактуется запрет создания аккаунта от имени другого лица применительно к partner sub-accounts?

## 8. Рекомендация

Limitless становится первой интеграционной проверкой для всех пяти GEO и особенно для Сомали и Таиланда. Ближайший этап — обязательная регистрация через FutureHaus, partner application, 72-часовой read-only ingestion/latency spike и изолированный sub-account lifecycle без пользовательских средств.

Limitless теперь первый технический кандидат благодаря Programmatic API и прямой поддержке. Решение считается подтверждённым только после сравнения с Polymarket по четырём измеримым критериям: p95 задержки, доля копируемых сделок на $10/$50/$200, полная комиссия round trip и качество recovery/revocation. Условия обещанной 10% скидки фиксируются отдельно по документу 20.

## Официальные источники

- [Terms of Service](https://docs.limitless.exchange/user-guide/terms-of-service)
- [Fees](https://docs.limitless.exchange/user-guide/fees)
- [Wallet Types](https://docs.limitless.exchange/user-guide/wallet-types)
- [Authentication](https://docs.limitless.exchange/developers/authentication)
- [Programmatic API](https://docs.limitless.exchange/developers/programmatic-api)
- [WebSocket Overview](https://docs.limitless.exchange/developers/websocket/overview)
- [Migrate from Polymarket](https://docs.limitless.exchange/developers/migrate-from-polymarket)
- [Public OpenAPI schema](https://docs.limitless.exchange/openapi.json)
- [Official TypeScript SDK](https://github.com/limitless-labs-group/limitless-exchange-ts-sdk)
