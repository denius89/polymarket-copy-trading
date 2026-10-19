# Независимый review forward shadow · 18.10.2026

Объект — новый сбор наблюдений без аккаунтов, средств и отправки заявок. Применены S11 (происхождение/полнота), S12 (временная допустимость replay), S22 (API capabilities). Прочитаны текущий инженерный эталон `copy-reference-single-v1`, связанные ограничения ADR-0024/25/26 и официальные страницы ниже. Это review исследовательского вертикального среза, не приёмка эксплуатации или числового скора.

## Что можно доказать сбором

Публичный GET/stream даёт собственный receipt time и исходный ответ. При сохранённом запросе, статусе, endpoint/schema, UTC+monotonic receipt, connection/run ID, clock status и SHA можно воспроизводимо сказать: «этот процесс получил эти сведения тогда». Timestamp API — отдельное поле; нельзя подставлять его вместо observedAt. Полученная позже историческая строка не становится доступной до её первого собственного наблюдения. Обнаруженный после рестарта разрыв остаётся разрывом; backfill восстанавливает историю источника, но не историческую доступность процессу.

Свежая полная книга подтверждает отображённую ёмкость в момент получения. Это **не подтверждение собственного исполнения**, очереди, расходов или результата FOK. Даже непрерывный публичный stream не является частным order/fill подтверждением вымышленной заявки. Денежный shadow требует отдельно объявленного paper fill model и только условных labels; настоящие подтверждения собственного исполнения появятся лишь в другом, отдельно разрешённом эксперименте. Не импортировать искусственные $0.10/$0.05 fees эталона в forward.

## Проверенные документированные возможности (не свежие endpoint experiments)

| Источник | Документировано 18 октября | Практический предел |
|---|---|---|
| [Polymarket activity](https://docs.polymarket.com/api-reference/core/get-user-activity) | Public user activity; bounded time windows, pagination; v2 counterpart указан | Transaction hash не economic signal ID; объединение/дедуп multi-fill требует отдельного identity evidence. `excludeDepositsWithdrawals=false` обязателен для получения этих потоков. Полный ledger не следует из страницы TRADE |
| [Polymarket positions](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user) | Public per-user positions, дополнительные поля fee basis | Для начального inventory нужны `sizeThreshold=0`, `includeArchived=true`, вся пагинация и account/token scope. Optional fee field missing не означает 0. Снимок не атомарен с историей trades |
| [Polymarket real-time](https://docs.polymarket.com/market-data/realtime-data) | Full books, price changes, tick/lifecycle; outcome ID зависит от CTF/V2 | В прочитанной схеме нет доказательства contiguous exchange sequence. Сохранять raw frames и локальный порядок, отмечать разрывы; version/hash не выдумывать как sequence. Last trade не задаёт адрес лидера |
| [Polymarket fees](https://docs.polymarket.com/trading/fees) | Market-dependent taker fees, market detail binding | Нужны применимые на decision time параметры конкретного рынка и проверенная fee unit/rounding; общая категория не достаточный binding |
| [Limitless public history](https://docs.limitless.exchange/api-reference/public-portfolio/history) | `/portfolio/{account}/history` для произвольного адреса без HMAC, opaque nextCursor; market-bound cursors | Это отдельный endpoint от private `/portfolio/history`. Нельзя заявлять, что arbitrary-user history отсутствует. Схема sparse: cursor/account/event identity и completeness нужно проверить фактическими ответами |
| [Limitless public positions](https://docs.limitless.exchange/api-reference/public-portfolio/positions) | Public AMM/CLOB/group inventory | Resolution в API не означает settled/redeemable on-chain. Проверять raw token balances/units, правильный venue, полный scope |
| [Limitless market events](https://docs.limitless.exchange/api-reference/trading/market-events) | Final MINED taker trades exact market/group slug; cache 30 s плюс stale window | Публичный профиль не полная wallet binding. Нет placements/cancellations; поздний cached сигнал может быть старше frozen 30 s. Не обходить freshness ради появления fills |
| [Limitless WS market data](https://docs.limitless.exchange/developers/websocket/market-data) | Coalesced full books; size в raw 6 decimals; publisher version | Coalescing не список сделок. Version не contiguous, может сброситься после failover; fallback version 0 только до live frame. Не выводить trade count/leader из frame count |
| [Limitless WS overview](https://docs.limitless.exchange/developers/websocket/overview) | Public market subscriptions; private own-order updates; reconnect через 24 h | Новый connection ID и повторная подписка, snapshot после ack; authenticated scope отдельно. Public book доступ не даёт private lifecycle |

Проектный navigator указывает отдельные Draft PR #14 (Polymarket) и #15 (Limitless); они не считаются merged main или новой endpoint-проверкой. Прочитаны локальный `docs/19_polymarket_api_access.md` (проверка 25 сентября) и `design/qa-2026-10-02/api-comparison/README.md` (кеш перенесён в /tmp, не гарантированно доступен/актуален). Отдельные актуальные branch/head этих Draft PR в данном scoped review не проверялись. Старый 403 — наблюдение прежнего запуска; он не опровергает существование документированного public API. Новый запуск должен отдельно сохранить свою доступность. Официальная общая authentication-страница Limitless говорит о HMAC для programmatic access, но конкретные public endpoints и WS market subscriptions явно допускают no-auth; использовать конкретный контракт capability и проверять фактический ответ, а не добавлять торговые credentials в public collector.

## Обязательные границы приёмки

1. **Сигналы:** receipt provenance, expected account+venue+token binding; ключ строки и экономический сигнал разделены. txHash или content hash может быть observation key, не уникальный leader instruction. Изменение строки при том же надёжном ID — correction/conflict, не повторная покупка.
2. **Времена:** first observedAt immutable; paginated historical pages не копируются с source time как arrival. Поздний backfill не создаёт ретро-решение. Wall-clock backwards и monotonic restart различаются.
3. **Книги:** depth payload parsed Decimal, missing/malformed≠empty; identity/side/age/gaps/duplicate conflict. Последний невалидный известный snapshot не заменяется предыдущим удобным. Между REST poll существует ненаблюдённый интервал.
4. **Leader inventory:** before-SELL balance не восстанавливается из позднего current position минус «что нашли». Требуются opening snapshot плюс доказанная полнота token events/transfers/split/merge/redeem и сверка. При unknown proportional exit unknown.
5. **Стоимость:** price/fee binding известны до решения и versioned. Нет applicable binding → наблюдение сохраняется, денежного fill/PnL нет. Минимум/tick/collateral/native decimals берутся из фактов venue, не fixture constants.
6. **Полнота:** HTTP error/429/timeout/schema change/невыполненная пагинация вызывают incident или coverage flag; пустой payload после ошибки не «0 событий». Bounded retries, total request/duration/bytes budgets, no infinite loop cursor.
7. **Защита:** collector не читает env secrets, не принимает auth/signing config и не содержит execution endpoints; redirect/domain/path scoped. Файлы неизменяемых запусков, raw bodies и manifests; прерывание не считается complete.
8. **Исследование:** первая небольшая когорта — pilot. Каждый forecast фиксируется до outcome, включая abstention/missingness. Нельзя выбрать удобных surviving leaders или удалить failed sessions после результата. H30+declared independent groups нужны до сравнения моделей; инженерный smoke не statistical win.

## Режимы результата

- `observation_pilot`: можно собирать raw публичные сведения и coverage.
- `conditional_paper`: только после явного fill model, applicable costs/precision, согласованных signal identities и inventory, полного lineage; результаты помечены model-dependent.
- `confirmatory_score_comparison`: отдельный замороженный период и протокол, согласованные risk parameters/минимальный effect; не достигается просто истечением 30 дней.

Первый режим разрешён текущим поручением. Последующие не следует включать автоматически из успеха HTTP. Оценка текущего collector и независимые fault tests будут записаны ниже после появления его исходников.

## Независимая проверка реализации

Проверены текущие `collector.py`, `run_shadow.py`, `compare_models.py` и протокол. Два замечания supervisor исправлены автором: ограничение срока теперь использует monotonic clock, задержки между chunks учитывают конец срока; проверено наличие `capture` subcommand. Проверены исправления gate: изменённая timezone не наследует frozen target, malformed requirement mapping/session ID получает отказ или диагностическую причину.

**16 независимых тестов прошли**: 11 capture-evidence и 5 process-lifecycle. Capture: отказ config secrets/endpoints/execution paths, явные account/window/deposit/inventory фильтры, no redirect, malformed/conflicting pagination, невозможно заменить unknown пустой историей, tampering/deletion детектируются, byte limit сохраняет предыдущие записи, существующий run не перезаписывается, verified bytes не означают continuity/signals. Supervisor: настоящий отдельный локальный процесс с искусственным collector проверяет lock duplicate, STOP до запуска и во время child, monotonic deadline завершает child, конфиг launch остаётся исходным после изменения файла. Сетевые запросы в этих тестах не выполняются.

Команды из каталога пакета:

```bash
python3 -m unittest test_independent_capture.py -v
python3 -m unittest test_forward_supervisor.py -v
```

Это не проверка падения диска, suspend/resume ОС, recovery после power loss, полного real-time покрытия, endpoint drift или статистического качества. Supervisor локальный; stop/crash/sleep и границы chunks остаются разрывами. Collector хранит raw unqualified observations, поэтому текущая достаточная готовность — **ограниченный observation pilot**. Обещания финансового H30 или готового сравнения моделей из этих тестов не следуют. Конкретный live run и его endpoint результаты фиксирует автор запуска отдельно; данный review не приписывает себе сетевой эксперимент.

### Проверка последнего изменения архива

Дополнительно проверены SIGTERM/frozen-source/gzip изменения collector и архивация supervisor. Собственный `Recorder` без сети создал завершённый run; после gzip raw удаляется только при совпавшем декодированном SHA, `verify_run` принимает исходные записи из архива. Изменённый raw вызывает отказ и сохраняется; незавершённый run остаётся raw; существующий архив не перезаписывается; изменённый gzip отвергается. Отдельный реальный процесс fake collector завершает chunk и supervisor создаёт gzip + archive metadata. Это lossless container conversion, не доказательство полноты рынка.

Проверенные SHA: collector `f876035330a99a8f0385a3ee5c878711537f9923e24c3cbfbd13b6fe26181d90`; supervisor перед последним уточнением статуса архива `08a4b75ddaf31da4dd689f6b99b692a574986ab953315c75d7417dd81c479a79`. При изменении исходников запуск фиксирует собственный новый hash; тест не переносится на него автоматически.
