# Примеры чтения и схемы запросов

Дата:06.10.2026. Публичные URL относятся к production. Ниже нет credentials; private пример является **схемой**, не выполненным запросом. Публичные результаты подтверждаются только [evidence](public-request-evidence.json), а не примерным JSON.

## Public discovery без auth

```http
GET /markets/active?limit=1&page=1 HTTP/1.1
Host: api.limitless.exchange
Accept: application/json
User-Agent: curl/8.7.1
```

В выполненном GET получен HTTP200 и JSON с `data[]`. Это проверяет одну страницу на один момент, а не полноту всех markets или downstream history. Из ответа закрепить exact `slug` и `tradeType`; затем read-only `GET /markets/<exact-slug>` и для CLOB `GET /markets/<exact-slug>/orderbook`. Не строить exact-market path из stable alias без resolve. Источники: [Browse](https://docs.limitless.exchange/api-reference/markets/browse-active), [Details](https://docs.limitless.exchange/api-reference/markets/get-market), [Book](https://docs.limitless.exchange/api-reference/trading/orderbook).

## Delegated status: иллюстрация, не executed request

```http
POST /orders/status/batch HTTP/1.1
Host: api.limitless.exchange
Content-Type: application/json
lmts-api-key: <token-id>
lmts-timestamp: <fresh-ISO-8601>
lmts-signature: <computed-base64-HMAC>
x-on-behalf-of: <owned-child-profileId>

{"items":[{"clientOrderId":"paper-illustration-only-001"}]}
```

Это read operation через POST, не submit order. Каждый item содержит ровно один internal orderId или clientOrderId; отсутствующий ID даёт result not_found и сам по себе не доказывает, что предыдущая submission не исполнялась. Partner token требует delegated_signing и ownership. Для своего профиля header убрать. HMAC рассчитывается по точным отправляемым body bytes, method/path/query/timestamp; placeholder нельзя использовать как подпись. Источники: [Status batch](https://docs.limitless.exchange/api-reference/trading/order-status-batch), [Authentication](https://docs.limitless.exchange/developers/authentication).

## Нормализация единиц: синтетические значения

REST/WS book level `size="50000000"` в raw scale6 означает50 shares. Цена0.53 остаётся0.53, её не делят на1e6. Это **синтетическая иллюстрация**, не сохранённый уровень рынка. OME lifecycle `remainingSize=50` (JSON number shares) и OME terminal `remainingSize="50000000"` (raw) требуют разных parsers. В ledger использовать Decimal/BigInt, price/quantity scale и raw representation. Источники: [Orderbook](https://docs.limitless.exchange/api-reference/trading/orderbook), [Order events](https://docs.limitless.exchange/developers/websocket/order-events), [Changelog 02.10](https://docs.limitless.exchange/changelog).

Схемы mutations и неатомарных результатов находятся в [execution](execution.md) и [authorization-partner](authorization-partner.md). Это reference для будущей реализации; production mutation примеры не выполнялись.
