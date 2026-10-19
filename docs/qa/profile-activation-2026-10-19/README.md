# Предметная проверка активации · 19.10.2026

[Вывод по каждому семейству — 137](../../137_profile_activation_audit_2026-10-19.md). Baseline `e6642caef80bcb2eafcb75d9e10fbfa3e73a77d4`. Проверка существующего ADR-0059, без новых product decisions, private auth, SDK install, trade/approval или изменения часов.

## Воспроизведение и границы

- `python3 docs/qa/profile-activation-2026-10-19/replay_test.py` — офлайн, 18 проверок. Анализ записей детерминированно обновляет `evidence/analysis.json`; реальные network-запросы этим запуском не выполняются.
- [collect_public.py](collect_public.py) и [discover_alternates.py](discover_alternates.py) — исходный bounded read-only сбор: public GET, 8 time reads, по два controlled market-stream подключения в окнах 25/15 с. Повторный запуск намеренно отказывается затирать run/alternate evidence; для новой проверки нужен отдельный каталог. Никакие keys/env credentials не читаются. Для записанной среды использовались Python websockets 15.0.1 и установленный python-socketio; версии зависимостей первого сбора — [предыдущий реестр](../venue-profiles-2026-10-19/sources.json). Сеть для offline replay не нужна.
- [manifest](evidence/manifest.json) содержит SHA256/размеры evidence, [run](evidence/run.json) — URL/времена/HTTP результаты; response hashes относятся к исходным HTTP телам, JSON artifacts нормализованы с сохранением decimal lexemes строками. Полные discovery тела не сохранены; [проекция](evidence/discovery-projection.json) содержит только публичные параметры. [Дополнительная выборка](evidence/alternate-discovery.json) — newest Polymarket + страницы 2/3 Limitless. Итог: 50 уникальных Polymarket /75 Limitless IDs, V2/COLLATERAL не наблюдены. Это bounded sample, не inventory всех рынков.
- SNTP: `sntp -t 3 -n 1 time.apple.com`, затем `time.cloudflare.com`, без clock-changing флагов. Сохранены диагностические ответы; точное время этих двух отдельных команд не записано, они выполнены перед stream run в этой задаче. Host service configuration недоступна без администратора, обход не выполнялся. SNTP не доказывает publisher clock.

## Результаты

18/18 passed: полные записи и новый seed после reconnect; Polymarket nested asset binding/absolute size replacement и фильтрация чужого outcome; synthetic duplicate/out-of-order/version jump/conflict/restart/fallback/identity/generation loss; официальные fee examples Polymarket; COLLATERAL Limitless raw/rounding; несовпадение legacy whitepaper/table; rank/effective-rate и API/SDK grid counterexamples; условный time interval, SHA и запрет включения профилей.

12 Polymarket и 118 Limitless payloads кадров сохранены полностью в нормализованном JSONL (decimal lexemes строками, не byte-for-byte wire archive), ни один session cap не достигнут. Fault cases **синтетические**, не утверждение о реально случившихся сбоях. Replay Polymarket проверяет state reconstruction, но не криптографический book hash algorithm/идеальную полноту publisher; Limitless full snapshots не превращаются в event ledger. Первое исправление диагностического parser после failed fixture учло `price_changes[].asset_id`; оно не является исправлением приложения.

[Точные наблюдения](evidence/analysis.json), [первичные источники и pinned SDK](sources.json). SDK package.json=1.2.0 на inspected commit; исходники прочитаны, чужой код не запускался. Формулы проверены на официальных опубликованных примерах и exact counterexamples, без независимого settlement receipt/deployed bytecode proof. Clock intersection — условное вычисление при дополнительных непроверенных предпосылках, не сертифицированная погрешность.

Итог eligibility: **ни один execution профиль не включать**. Public observation/fixtures можно использовать при последующей реализации. Полный набор activation доказательств и адресные blockers — в 137 и JSON-политике, runtimeEnabled=false. App/Figma/live untouched.
