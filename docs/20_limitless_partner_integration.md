# Limitless: партнёрская интеграция и порядок доступа

Дата проверки: 25 сентября 2026 года. Статус: рабочий источник требований к первой execution-интеграции.

## 1. Решение проекта

Limitless становится первой площадкой для интеграционных проверок и кандидатом на первый execution adapter. Причина — подтверждённая основателем готовность команды Limitless поддерживать проект и наличие отдельного Programmatic API для платформ, которые создают sub-accounts и торгуют от имени пользователей.

Polymarket остаётся важным контрольным сравнением и кандидатом на второй адаптер. Решение не разрешает MVP или реальные пользовательские сделки: сначала должны пройти GEO, trust, fee и execution spikes.

## 2. Обязательная регистрация

Партнёрский аккаунт проекта нужно создавать только через ссылку:

https://limitless.exchange/?r=FutureHaus

По сообщению основателя, регистрация через `FutureHaus` даёт будущие партнёрские преимущества и скидку 10% на комиссии. Публичная документация Limitless подтверждает постоянную атрибуцию первого referrer и реферальные выплаты с taker fees, но не описывает скидку 10% для приведённого аккаунта. До включения скидки в экономическую модель нужно письменно зафиксировать:

- к каким комиссиям применяется 10%;
- является ли это относительной скидкой (`fee × 0,90`) или уменьшением на 10 процентных пунктов;
- срок действия и список подходящих аккаунтов/рынков;
- распространяется ли она на sub-accounts;
- как скидка отражается в `effectiveFeeBps`, `usdFee` и `contractsFee`;
- можно ли одновременно получать стандартные referral rewards.

До ответа расчёты показывают два сценария: без скидки и с условной относительной скидкой 10%. Скидка не считается гарантированной выручкой проекта.

## 3. Что даёт Programmatic API

Официальный партнёрский API поддерживает:

- HMAC-SHA256 токены с отдельными scopes;
- создание и восстановление связанных с партнёром sub-accounts;
- EOA-режим с пользовательской EIP-712 подписью каждого ордера;
- server-wallet режим с `delegated_signing`, где Limitless/Privy подписывает ордер;
- GTC, FAK и FOK ордера;
- чтение позиций, истории и статусов принадлежащих партнёру sub-accounts через `x-on-behalf-of`;
- отдельные операции redeem и withdrawal;
- официальные TypeScript, Python, Go и Rust SDK.

HMAC `tokenId` и `secret` хранятся только в backend/BFF. Публичные market reads могут выполняться из frontend. Secret возвращается один раз при выпуске токена.

## 4. Какие scopes нужны

Минимальный набор для автоматического copy trading в server-wallet модели:

| Scope | Назначение | Решение |
|---|---|---|
| `trading` | создать и отменить ордер | требуется |
| `account_creation` | создать/list/recover sub-account | требуется |
| `delegated_signing` | подписывать ордера server wallet от имени sub-account | требуется для полной автоматизации |
| `withdrawal` | выводить ERC20 с managed sub-account | не выдавать execution worker; отдельное решение после trust spike |

Scope `admin` не является self-service. Токен с торговыми scopes и токен для будущих операций вывода должны быть разными секретами, процессами и журналами.

## 5. Порядок получения доступа

1. Открыть `FutureHaus` referral link и создать стандартный Limitless-аккаунт кошельком проекта.
2. Сохранить wallet address и полученный `profileId` в закрытом реестре доступов, не в Git.
3. Подать официальную заявку на Programmatic API: https://docs.google.com/forms/d/e/1FAIpQLSd1P4UB1yDcdcxJzRrM7EiwuJKTFpKtqgFGA_ftYbNOLg7lsQ/viewform
4. В заявке описать продукт как контролируемое копирование сделок с лимитами, журналом, kill switch и без обещаний доходности.
5. Попросить scopes `trading`, `account_creation`, `delegated_signing`; `withdrawal` не запрашивать для первого spike.
6. После активации проверить capabilities через `GET /auth/api-tokens/capabilities`.
7. Через UI или `POST /auth/api-tokens/derive` выпустить scoped token. Secret сразу сохранить в secrets manager.
8. Создать отдельный тестовый sub-account без пользовательских средств.
9. Проверить allowance readiness, lifecycle GTC/FAK/FOK, `clientOrderId`, `x-request-id`, отмену, статусы, reconciliation и отзыв токена.
10. Только после trust/security review провести минимальный личный live-тест отдельным решением основателя.

## 6. Архитектурный выбор, который ещё надо доказать

### EOA

Пользователь хранит ключ и подписывает каждый ордер. Это сильнее соответствует прямому контролю пользователя, но не даёт бесшовное автоматическое копирование.

### Server wallet и delegated signing

Пользователь не подписывает каждую копию; Limitless/Privy подписывает ордер managed wallet по партнёрскому запросу. Это лучше соответствует UX продукта, но требует доказать:

- как пользователь самостоятельно получает и выводит средства при недоступности нашего сервиса;
- как отзывается автоматическая торговля;
- что торговый backend не имеет права вывода;
- что происходит с открытыми GTC-ордерами при отзыве токена или остановке сервиса;
- можно ли ограничить delegated signing бюджетом, рынками и сроком на стороне площадки;
- как восстанавливается server wallet и кому доступна операция recovery.

До ответа продукт нельзя называть строго non-custodial без пояснения границ Limitless/Privy.

## 7. Обязательные runtime controls

- перед торговым действием проверять `GET /maintenance/status?target=trading`;
- обрабатывать режимы `post_only`, `cancel_only`, `disabled` и ответ `425` без tight retry;
- отправлять уникальный `clientOrderId` и `x-request-id`;
- включить per-order, daily notional, per-trader, per-market и portfolio limits до SDK call;
- задавать self-trade prevention policy;
- иметь kill switch, который сначала отменяет resting orders, затем останавливает новые;
- учитывать `429` и использовать backoff;
- сверять terminal order events и on-chain settlement;
- не считать API attribution заменой нашего event journal.

## 8. Комиссии и экономика

Публичные комиссии Limitless на дату проверки:

- AMM: обычно 0,40% на сделки;
- CLOB maker: 0%;
- CLOB taker buy: примерно 0,40–3,00% в зависимости от цены;
- CLOB taker sell: примерно 0,42–1,50% в зависимости от цены.

Точный fill возвращает `effectiveFeeBps`, `usdFee` и `contractsFee`; именно их нужно использовать в ledger и показе чистого результата. Наша сервисная комиссия добавляется отдельно. Даже при обещанной скидке 10% нельзя рассчитывать экономику по одной средней ставке: backtest и shadow mode должны воспроизводить fee curve по фактическим fills.

Стандартная реферальная программа Limitless и наша агентская программа — разные уровни:

- `FutureHaus` атрибутирует партнёрский аккаунт проекта внутри Limitless;
- наши агенты атрибутируют конечных пользователей внутри продукта;
- выплаты Limitless нельзя автоматически обещать нашим агентам;
- любое решение передавать upstream referral revenue агентам требует отдельной версии экономики.

## 9. Gate перед разработкой MVP

Доступ считается технически подтверждённым, когда:

- partner capabilities реально включены на аккаунте проекта;
- scopes и token rotation проверены;
- создан тестовый sub-account;
- доказан ордерный цикл и recovery после неизвестного состояния;
- подтверждён безопасный вывод без права execution worker направить деньги произвольно;
- получен письменный ответ по GEO и коммерческому использованию данных;
- условия скидки FutureHaus записаны однозначно;
- измерены задержка, ликвидность и полный round-trip cost для бюджетов $10/$50/$200.

## 10. Источники

- [Programmatic API](https://docs.limitless.exchange/developers/programmatic-api)
- [Authentication](https://docs.limitless.exchange/developers/authentication)
- [Fees](https://docs.limitless.exchange/user-guide/fees)
- [Referral Program](https://docs.limitless.exchange/user-guide/referral-program)
- [Maintenance Mode](https://docs.limitless.exchange/developers/maintenance-mode)
- [Responsible Trading Agents](https://docs.limitless.exchange/developers/responsible-agents)
- [Migrate from Polymarket](https://docs.limitless.exchange/developers/migrate-from-polymarket)

