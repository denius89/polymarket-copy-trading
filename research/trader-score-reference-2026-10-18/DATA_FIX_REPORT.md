# Исправления данных и новый recorded-прогон · 18.10.2026

Исправлены DR-02/03/04 из [перепроверки](../trader-score-review-2026-10-18/data-replay.md). DR-01 исследован с сохранением точности JSON, но семантика часов/полнота исторического replay не объявлены доказанными. Это исследовательский инструмент проверки данных, не продуктовый адаптер и не свидетельство исполнения ордеров.

## Что изменилось

- [market_data.py](market_data.py): Decimal parsing, явное различие отсутствующей стороны и наблюдаемого пустого массива. Malformed/nonfinite/negative/duplicate/crossed уровни дают invalid; из invalid книги не вычисляются ёмкость и цена. Больше нет второго небезопасного парсинга после ошибки validator.
- ASOF выбирает последнюю группу снимков одного token. Любая invalid строка делает группу unknown независимо от порядка; разные валидные книги дают conflict. Точное равенство arrival, invalid latest, conflict и stale не подменяются старой хорошей книгой.
- Проверка файлов требует независимо заданного точного списка, уникальных путей, размещения внутри источника, bytes/SHA; recorded reader дополнительно проверяет Parquet schema, количества строк, asset/time/condition scope. Успешный новый bundle создаётся только после завершения проверок/расчётов, в новом каталоге. Старые источники/результаты не могут быть output-dir.
- [analyze_recorded.py](analyze_recorded.py) безопасен при импорте; явный CLI запускает локальную квалификацию сохранённых данных. Dependencies, hashes кода/входов, правила выбора и исходный target manifest фиксируются в новом run manifest.
- В hindsight diagnostic больше нет утверждения «первая сделка» на основании сортировки цены. Сохраняется первый наблюдаемый секундный bucket; multiple-row buckets исключаются из строгой таблицы, помечаются и получают отдельные bounds. Эти bounds — возможные значения внутри bucket, не доверительные интервалы, прибыль или оценка скора.

Старые небезопасные точки запуска `source-audit/analyze_pmxt_target.py` и `trader-score-real-2026-10-16/analyze_public.py` заменены import-safe guards: явный запуск завершается кодом 2 с адресом нового runner. Их точный исходный код сохранён рядом как `.2026-10-16.py.txt`, контрольные суммы — [retirement manifest](legacy-entrypoint-retirement.json). Старые исследовательские отчёты/цифры не переписаны. Для проверки исходной реализации нужно читать этот архивный исходник; прежний путь теперь намеренно не запускает её молча.

## API для инженерного эталона

```python
from decimal import Decimal
from market_data import parse_book, displayed_buy_capacity, Snapshot, select_snapshot
book = parse_book({"bids": [["0.4", "10"]], "asks": [["0.5", "10"]]})
capacity = displayed_buy_capacity(book, Decimal("5"), max_price=Decimal("0.6"))
selection = select_snapshot(
    [Snapshot("fixture-token", Decimal("10"), book)],
    arrival=Decimal("10.5"), max_age=Decimal("1"),
)
```

`CapacityEvidence.status` — `covered / insufficient / unknown`, `gross_spent / quantity / vwap` — Decimal либо None. `covered` означает лишь покрытие gross суммы наблюдаемыми уровнями **снимка**. Это не fill. Fee calculation, округление допустимого количества площадкой, expense reserve, очередь, position/daily caps, signal observedAt и terminal confirmations остаются задачей отдельного профиля/движка. При insufficient найденный объём не превращается в частичную покупку до допуска (ADR-0025).

`Selection.status` — `eligible / unknown`. Даже eligible снимок требует проверки intervening changes и достаточности источника в recorded qualification. Ledger эталон использует контролируемые fixture-доказательства и подтверждения отдельно; нельзя перенести их на историческую выборку.

## Что получилось на реальных сохранённых файлах

Новый результат: [recorded-qualification-v2](recorded-qualification-v2/recorded-qualification.json), [run manifest](recorded-qualification-v2/run-manifest.json), [output hashes](recorded-qualification-v2/output-manifest.json).

- Проверены target parquet, четыре aligned trade файла и 64 файла исходного real-data пакета; исходники не загружались заново.
- PMXT: **369 362 события**, включая **8 766 snapshots**. Decimal-порядок по sub-ms JSON timestamp — диагностическая sensitivity, а не доказанный exchange sequence.
- Next snapshot comparisons: **8 764**, совпадений глубины **8 691**, лучших цен **8 734**. Остались **73/30** расхождения: 32 с изменившимся набором ценовых уровней, 41 только по объёму. Неисправленной исторической книге не присваивается статус достоверного replay.
- В интервале совпали 10 450 trade rows; 1 284 BUY. При условном delay 2s/max-age 1s: **857 свежих однозначных снимков**, **347 conflict**, **1 exact arrival tie**, **79 stale**. Во всех 857 есть price_change в включительном интервале snapshot availability→arrival. Строгая категория без известных промежуточных/совпадающих изменений — **0**, что означает unknown at arrival, а не нулевую реальную исполнимость.
- На самих 857 снимках наблюдаемой глубины хватает на gross $5. `copier_fill_claim=false`, `copier_pnl=null`, `model_verdict=not_validated` сохранены явно.
- [First-bucket diagnostic](recorded-qualification-v2/first-bucket-diagnostic.json): **9 385 групп**, 1 246 multiple-row buckets, 1 221 с разными экономическими значениями, 953 с разными ценами. Строгая новая таблица содержит **8 139 single-row buckets**. [Построчные flags/bounds](recorded-qualification-v2/first-bucket-bounds.json) позволяют проверить каждое исключение; адреса в выходе псевдонимизированы.

## Проверки и их предел

21 целевой тест в [tests/test_market_data.py](tests/test_market_data.py) прошёл. Покрыты Decimal exact boundaries, независимый пример $2+$3 на двух уровнях, price cap/full amount, empty vs missing, malformed/nonnumeric/nonfinite/negative/duplicate/crossed, invalid/conflict permutation, exact tie/invalid latest no fallback, stale/future/mixed-token, file list/hash/size/path escape, schema, import safety, запрет старого output, неоднозначный first bucket и его bounds при перестановке входов. Оба legacy guard отдельно проверены: import без побочных эффектов, CLI exit 2, архивный source hash совпал.

Это проверки механики нового data-layer и записанного среза. Они не проверяют runtime приложения, UI, площадочные API/account permissions, ликвидность всей площадки, комиссии конкретного исполнения или надёжность скора. Неизвестные fees/signal observedAt/leader inventory не заменены нулём. Для принятого стандарта с пропорциональными продажами эти слои и собственный денежный ledger ещё необходимы.

## Повторение

Из корня репозитория, с уже доступным DuckDB 1.4.1:

```bash
PYTHONPATH=/tmp/trader-score-python-deps python3 -m unittest discover -s research/trader-score-reference-2026-10-18/tests -p 'test_market_data.py' -v
PYTHONPATH=/tmp/trader-score-python-deps python3 research/trader-score-reference-2026-10-18/analyze_recorded.py --output-dir research/trader-score-reference-2026-10-18/NEW_RECORDED_RUN
```

Каталог output должен отсутствовать. Повтор в существующий каталог намеренно запрещён. Результаты 16 октября остаются датированными доказательствами прежнего анализа; новый runner не переписывает их и не объявляет записанный replay исполнением.
