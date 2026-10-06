# Limitless → общий адаптер документа 23

Проверка 06.10.2026. Эта карта поясняет предложенный [контракт 23](../../23_dual_venue_adapter_contract.md), не меняя интерфейсы, sizing, бизнес-правила и live-gates. D/R/U/P определены в [README](README.md). Runtime capabilities нашего партнёрского аккаунта **U/P**: аккаунт не создавался.

## Read adapter и показатели

| Контракт / задача | Источник Limitless | Нормализация и ограничение |
|---|---|---|
| `listMarkets`, `getMarket` | Active markets, exact market detail, navigation, stable-slug resolver | `venue=LIMITLESS`; сохранять original slug/id/conditionId/outcomes/tradeType/venue. Exact market закрепляется до intent; stable alias не идентичность раунда |
| `getOrderBook` | REST orderbook, `orderbookUpdate` | YES-side книга; size/minSize raw scale6, price не scaled. Сторону NO преобразовывать по документированным правилам, не копировать YES asks под другим названием |
| `backfillLeaderEvents` | Public address history; public MINED market events как дополнительная сверка | Cursor opaque, перекрытие страниц и дедупликация; action-type filter. AMM/CLOB trades, split/merge/convert/redeem не становятся одинаковым BUY/SELL. Порядок newest-first не гарантирует отсутствие поздней записи |
| `streamLeaderEvents?` | Универсальный address-based поток произвольного лидера не подтверждён | Capability false/U. WS цены/книга, feed за24h, leaderboard invalidation и own orderEvent не дают полноту чужого account stream |
| `listPositions` | Public address positions; own/delegated private positions | Снимок внешнего владения без происхождения virtual lots. Не считать весь остаток адреса принадлежащим одной copy policy |
| PnL/rating/accuracy | Public realized-pnl и user-stats accuracy, private positions/history | Realized/unrealized отдельно. Coverage, период, backend methodology, money scale и lastUpdated сохранять. Наш рейтинг, ROI, drawdown и closed-trade win rate требуют собственной утверждённой методики |
| Источник доступных денег | On-chain balance и подтверждённые расходы/резервы, private orders/positions | PnL, position value и traded volume не заменяют spendable USDC. Публичного капитала лидера для sizing эти endpoints не доказывают |

Официальные контракты и детализация endpoints: [public data](public-data.md), [orderbook](https://docs.limitless.exchange/api-reference/trading/orderbook), [public history](https://docs.limitless.exchange/api-reference/public-portfolio/history), [public realized PnL](https://docs.limitless.exchange/api-reference/public-portfolio/realized-pnl).

## Trading и reconciliation

| Метод / модель | Отображение | Условие перед будущей реализацией |
|---|---|---|
| `capabilities` | Runtime partner capabilities + документация + результат конкретного spike | D не даёт автоматически enabled capability. Разделять public reader, EOA, partner owner, delegated child и maintenance mode |
| `permissionSnapshot` | HMAC scopes, partner ownership, срок/revoke, trading wallet mode | Private profile owner route не становится child route только из-за `x-on-behalf-of`. `withdrawalAllowed=false` для execution credential требуется доказать отдельным доступом |
| `operationalMode` | Maintenance status target trading | `post_only`, `cancel_only`, `disabled`, 425; stale snapshot не даёт разрешение новых операций |
| `eligibility` | ToS и письменный account/GEO contract | Официальный универсальный per-user eligibility endpoint не подтверждён; вернуть UNKNOWN, не ALLOW по успешному market GET |
| `validateOrder` | Market tradeType/venue, decimals, tick/min-size, effective fees, balance/allowance | Уровень биржевых проверок не заменяет core budgets, stale signal/slippage и reservations |
| CLOB `submit` | Signed EIP-712 EOA или partner unsigned delegated POST /orders | Trade GTC/FAK/FOK, clientOrderId/requestId, venue contract и actual profile. Timeout → SubmitUnknown. SDK retry для торговой команды не должен обходить поиск результата |
| AMM `submit` | Отдельные /amm/buy и /amm/sell server-wallet операции | Не выдавать AMM за CLOB order. Sell задаёт exact collateral return, а не exact shares. Mapping будущего share-based sell требует отдельного согласования, U/P |
| `findSubmission`, `getOrder` | Status batch по orderId/clientOrderId, exact market user-orders | `x-on-behalf-of` для owned child. Пустой ответ не доказывает ProvenAbsent: retention/indexing scope должен быть проверен |
| `listOrders`, `listFills` | User-orders, status batch, private history (CLOB/AMM), trades (AMM-only); settlement events для owner | Открытые по умолчанию LIVE orders не полный журнал. Не выдумывать универсальный account-wide order listing или бесконечный backfill |
| `cancel`, `cancelAll` | Combined ID/client-ID, batch, market-scoped all | Request ≠ final cancellation. Partial results независимо; all/{slug} не global kill switch |
| Cancel-replace | Связанная cancel + create операция и отдельные результаты | Не atomic amendment; старая отменена/новая отклонена и unknown — допустимые разные исходы. Не использовать same intent как новое без связи old/new |
| `incremental`, `full` | REST snapshots/backfill + own events + chain evidence | Delegated CLOB order events REST-only. После reconnect/revoke/maintenance сохранить checkpoint и выполнить сверку |
| `settlementEvidence` | Документированные MINED/FAILED/RETRYING/reorg + Base receipt/позиции | Matching не финальные деньги; конкретный RPC/provider и depth finality здесь не проверялись |

Источники: [Programmatic API](https://docs.limitless.exchange/developers/programmatic-api), [Order events](https://docs.limitless.exchange/developers/websocket/order-events), [Cancel-replace](https://docs.limitless.exchange/api-reference/trading/cancel-replace), [AMM](https://docs.limitless.exchange/developers/amm-trading), [Maintenance](https://docs.limitless.exchange/developers/maintenance-mode). Полные площадочные семантики — [execution](execution.md), полномочия — [authorization-partner](authorization-partner.md).

## Snapshot capabilities: документировано ≠ доступно проекту

| Поле документа 23 | Что записать по этому исследованию |
|---|---|
| publicMarkets/publicOrderBook | D; конкретные R только в отчёте проверки. Live полнота и freshness U |
| publicWalletHistory/publicWalletPositions/historicalBackfill | D; проверенный адрес и число страниц не гарантия всех аккаунтов/времён |
| publicLeaderRealtimeStream | false/U: universal leader stream не подтверждён |
| authenticatedUserOrderStream | D для владельца профиля, U runtime; false для delegated children согласно D |
| clientOrderId | D native CLOB uniqueness/correlation, duplicate409 без replay; scope/retention/timeout absence proof U/P, не exactly-once обещание |
| orderTypes/partialFills/cancelSingle/cancelAll | D по endpoint-specific условиям. POST_ONLY semantics не отдельный универсальный order type; cancelAll ограничен market/group slug |
| fillFeeBreakdown | D по documented fills; реальная reconciliation fees U/P |
| authModes | D EOA signing/PARTNER_HMAC/DELEGATED_SIGNING. Privy bearer/UI session не заявляется session-key execution capability |
| tradingPermissionRevocable/withdrawalPermissionSeparable | D scoped token/revoke; фактический credential boundary проекта U/P |
| permissionExpiryObservable | Token expiry упомянут общим auth guide, но lifetime/expiresAt DTO не определён; наблюдаемость U/P, lastUsedAt не expiry |
| maintenanceStatus | D; реальные maintenance переходы U |
| geoEligibilityCheck | UNKNOWN/account policy: нет подтверждённого автоматического per-user endpoint |
| onchainSettlementObservable | D Base и settlement tx evidence; независимая chain сверка U |
| platformFeeAttribution/serviceFeeAttribution | D площадочный fee payload/referral, U project access. Наш service fee ledger считается core отдельно; платформа не ведёт его автоматически |

## Пригодность paper и будущего copy trading

Наблюдаемый public history Cache-Control=max-age60/s-maxage60 означает, что частый опрос может возвращать кешированную страницу; это не измеренная60-секундная latency SLA. В raw evidence history не содержит totalCount.

Для paper публичные рынки, книга, история и позиции дают основу recorded fixtures и наблюдения. Реальный public read не доказывает simulator readiness: ещё нужны snapshots с source time, fee curve, exact units, sample partial/cancel/unknown, cursor overlap, поздние записи, изменения рынка и 72-часовые измерения на3–5 лидерах по документу23. Локальный paper не должен обращаться к mutation production endpoints.

Для будущего live Limitless документирует partner-managed accounts и delegated execution. Нужны фактическое включение capabilities, экономические/legal/data-use условия, security/recovery и отдельное разрешение. В настоящем исследовании отсутствуют live credentials, end-to-end submit/cancel/redeem/withdrawal, WS handshake и фактические latency/SLA. Обязательное наличие обеих площадок не даёт права запускать любую из них.

Утверждённые partial-fill правила [ADR-0026](../../decisions/0026_keep_confirmed_partial_fill_and_cancel_remainder.md) и [ADR-0027](../../decisions/0027_reconcile_fills_while_remainder_cancellation_is_pending.md) сохраняются: исполненную часть удержать, остаток отменять, дополнительные исполнения во время отмены учесть. Публичная история не доказывает исполнение именно нашей копии; provenance virtual lots остаётся во внутреннем ledger.

## Конкретные вопросы партнёру

1. Для нашего use case доступны ли trading/account_creation/delegated_signing без withdrawal; есть ли ограничения по пользователям, GEO, рынкам, budget/time и delegated wallet recovery?
2. Как пользователю получить контроль и деньги при недоступности сервиса? Что происходит с resting orders после revoke и как отменить их при отозванном execution token?
3. Можно ли расширить order event stream на owned children; если нет, какой REST polling budget/SLA, retention statuses и account-wide reconciliation путь рекомендованы?
4. Как доказать отсутствие заявки после lost response? Уточнить clientOrderId uniqueness scope/retention, indexing lag, cancellation retry и cancel-replace частичные/неопределённые исходы.
5. Есть ли адресный публичный/partner поток сделок лидеров, replay/backfill checkpoint, корректировки/reorg и SLA? Можно ли использовать данные коммерчески и хранить исторические snapshots?
6. Как определить funding/balance readiness, maker/taker fee classification, USDC/share precision и окончательные расходы delegated fills? Как получить quote для share-target AMM exit?
7. Как получать GEO/eligibility конкретного пользователя, включая точный смысл `Republic of China` в ToS? Нельзя заменить ответ собственным предположением о стране.
8. Кто и как может добавлять withdrawal allowlist; можно ли execution credential технически лишить всех путей transfer/recovery и доказать это на нашем доступе?
9. Как начисляется FutureHaus attribution, распространяется ли на subaccounts, и существует ли обещанная проекту10% скидка? Подтвердить базу/срок/fee fields письменно; публичная upstream referral programme не означает нашу сервисную программу.
10. Как устранять обнаруженные schema/prose расхождения; какую версию pin, как получать breaking changes, и есть ли уведомления до deprecation? Сроки «within weeks» не календарный deadline.

Исторические списки вопросов: [20](../../20_limitless_partner_integration.md), [22](../../22_limitless_access_and_spike_plan.md), [81](../../81_full_figma_business_api_and_ui_audit_2026-10-04.md), [API-аудит](../../../design/qa-2026-10-04/api-mapping-audit-agent.md). Ответов партнёра в этом цикле не запрашивали; продукты и правила не изменяли.
