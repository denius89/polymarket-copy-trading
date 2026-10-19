# Review reconnect и контракт адаптера

Вывод ограничен snapshot VenueQ в `fixture/docs.md` и четырьмя строками `fixture/log.csv`. Дата проверки, environment, pinned API/SDK version и полный request shape не предоставлены. Последний seq 105 не доказывает непрерывность fills: между получением 101 в 10:00:01 и reconnect в 10:02:01 прошло 120 секунд, тогда как документированное окно resumeFrom — 60 секунд. Значения 102–104 не наблюдались; являются ли они fills и как именно работает seq, неизвестно.

| Возможность | Основание и предел |
|---|---|
| WS account feed, seq, resumeFrom ≤60 с | Documented snapshot; observed только 100, 101, 105 и попытка resumeFrom 101 |
| REST fills с пагинацией | Documented для собственного аккаунта; полнота ledger, retention и доступ всех лидеров не установлены |
| Order idempotency key | Documented; неизвестны TTL, scope и поведение повторов |
| Account authorization / partner access | Evidence отсутствует; публичный успех также не проверялся |
| Precision, fees, limits, lifecycle | Fee precision не дана; остальные ограничения требуют контракта |

Минимальные подготовленные проверки, исключительно на локальных fixtures/mocks:

1. Replay внутри окна, на границе и после 60 секунд: обнаружение разрыва, явный статус incomplete, отсутствие вывода «история полная». Смоделировать REST backfill всех страниц с overlap, дубликатами, пустой страницей и повторным cursor; неполный backfill сохраняет unknown.
2. Проверить venue/account binding каждого WS event и REST page. Чужой account либо venue отклоняется; одинаковые event IDs разных scopes не объединяются. События вне порядка и повторы не удваивают fill.
3. Смоделировать ошибки, timeout и 429: bounded retries, backoff и лимит попыток; неизвестный результат запроса сохраняется как unknown. Для order timeout подготовить reconciliation и повтор с тем же ключом лишь при подтверждённом контракте, без слепого создания нового заказа.
4. Проверить price/size precision, tick, minimum, rounding и fee units/precision. До получения значений ожидать явный отказ либо not_verified; чисел не выдумывать.

SDK не устанавливать и не запускать: пример при старте вызывает createOrder. Ни SDK, ни authenticated проверки этим review не разрешены. Тезисы команды о полном ledger и всех лидерах доказательств не имеют.
