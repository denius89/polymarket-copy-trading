# Проверка рыночных профилей · 19.10.2026

Объект: ADR-0059, контракт 136 и `docs/policies/paper-clob-market-profiles-v1.json`. [Первичные источники и версии средств наблюдения](sources.json). Baseline main: `1f75a84df923c3ae16e66408b24939e42df629fc`.

## Наблюдения без аккаунтов

- [GET manifest](evidence/public-get-manifest.json): 8 ограниченных последовательных публичных GET, время/длительность и безопасные заголовки. По одному выбранному рынку каждой площадки; никакой полной выборки или торгового запроса. Отдельные SHA исходного HTTP body и преобразованного artifact; исходные тела не архивированы. Market artifacts сокращены до публичных параметров; у чисел сохранены исходные десятичные значения строками.
- [Stream manifest](evidence/stream-manifest.json): Python websockets и python-socketio, одновременно по одной публичной подписке каждой venue, 8 секунд на подключение, затем отключение и новая подписка ещё на 8 секунд; никакой приватной auth. Polymarket `assets_ids` из book; Limitless `marketSlugs` точного CLOB slug. Сохранены первые 6 relevant кадров на подключение, счётчик включает все полученные relevant кадры. Это bounded smoke, не случайная выборка задержки.
- Polymarket: 2 подключения, 9 кадров; среди сохранённых необработанная разница receive−source 48,765–5660,013 мс. REST book: 7477 мс при 190 мс длительности запроса. Эти разницы **без доказанной clock correction**, не достоверная метрика задержки/SLA.
- Limitless: 2 подключения, 51 кадр, 12 сохранены; необработанная разница 24,506–148,881 мс. REST timestamp отсутствует. Подтверждены форма полных book snapshots и version после повторной подписки, не поведение при реальном backend failover.
- Polymarket выбранный Gamma v1 содержит и token, и position IDs, rate=0.04/exponent=1; fee-rate вернул base_fee=1000. Дополнительный compact CLOB market GET дал fd.r=0.04/e=1 и mbf/tbf=1000; pinned official SDK берёт нужный feeInfo из fd. Нормализацию missing→zero и auto-shrink BUY из SDK проект принимать не должен. Limitless выбранный рынок — legacy fee-enabled с takerDelayMs=500, не COLLATERAL venue. Актуальную формулу legacy и будущую delayed execution эти чтения не подтверждают.

Даты/ID/полные сохранённые кадры и SHA доступны в evidence. GET `/time` с секундной гранулярностью не доказывает clock uncertainty ≤250 мс. Ни baseline NTP, ни fee trades, ни V2/collateral-venue сбор не выполнены. Время системы во время наблюдения — UTC в manifest, решение владельца датировано 19.10 по проектному календарю.

## Изолированная модель

Запуск: `python3 docs/qa/venue-profiles-2026-10-19/reference_test.py`.

Результат: 22/22 проверок. Exact Fraction: freshness boundary с clock uncertainty/elapsed time, acquisition и invalid generation; BUY floor/SELL ceil на шести tick grids и 99 ценах; full depth без уменьшения BUY; raw collateral equation и side-specific maker floor; YES→NO; fee official example, aggregation и half-up, резерв с доказанным числом списаний, gross/net без двойного списания, version-based asset selection, strict raw fee presence/source, полный BUY при нехватке fee reserve, hashes saved evidence, AMM unsupported и runtime disabled.

Модель синтетическая. Она не является adapter, не сертифицирует все значения JSON, parser/clock implementation, DB/concurrency, произвольные fee curves, реальные начисления/газ или полный stream replay. Отдельный gate: пригодные часовые доказательства, непрерывная запись используемых кадров, reorder/duplicates/loss/failover/fallback fixtures, точная схема amount/fee по каждому семейству и независимые raw totals. Нельзя включить профиль по одному успешному snapshot или этим 22 тестам. См. конкретные blockers в JSON и раздел 7 контракта 136.
