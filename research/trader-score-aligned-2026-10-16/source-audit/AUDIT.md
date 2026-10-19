# Аудит архивов для общего периода — 16.10.2026

Первый этап: проверить пригодность TimeSeventeen и OpenMarket и выбрать совпадающие даты по каталогам и открытому коду. Это аудит источников, не проверенный полный финансовый ledger.

**Дополнение:** затем найден и ограниченно скачан реальный исторический PMXT L2 с пересечением по токенам и времени. Итог и точные размеры — в [PMXT_RESULT.md](PMXT_RESULT.md). Ограничения OpenMarket ниже относятся только к OpenMarket и не означают отсутствия полного L2 в других архивах.

## Конкретный срез

Версии: [TimeSeventeen/Polymarket-v1](https://huggingface.co/datasets/TimeSeventeen/Polymarket-v1/tree/5aa1b9d52316a8b2e789e81c8ae42c7ed532e8aa) и [OpenMarket](https://huggingface.co/datasets/gregyoung14/openmarket-btc-polymarket/tree/74502466d1a7cef56395bfd8d0b465fbebc849cf). Полные полученные каталоги: `daily-partitions-complete.json` (1248 файлов), `quote-partitions.json` (54 файла котировок).

Пересечение **имён дат** — 51 дата между 2026-02-12 и 2026-04-21. Не непрерывный период: quote collector имеет пропуски. У OpenMarket после 21 апреля до 12 мая заявлен пробел; TimeSeventeen заканчивается 28 апреля. Разные часовые зоны разделов требуют фильтра по timestamp, а не join по имени файла.

| Дата имени файла | `daily_aligned/YYYY_MM_DD.parquet`, bytes | `unified/polymarket_ticks_ms/date=YYYY-MM-DD/part-000001.parquet`, bytes |
|---|---:|---:|
| 2026-03-01 | 135448359 | 2974212 |
| 2026-03-02 | 133243360 | 6813914 |
| 2026-03-03 | 145406743 | 5675495 |
| 2026-03-04 | 146908576 | 9143826 |

Первые три quote файла суммарно 15 463 621 bytes; `unified/market_meta/unpartitioned/part-000001.parquet` — 427173 bytes. Каждый trade file превышает 20 MB, поэтому для bounded pilot нужен range-read нужных колонок/row groups либо отдельный согласованный объём. Raw `OrderFilled/2026_03.parquet` — 7614987040 bytes.

**Timezone:** TimeSeventeen README объявляет разделение UTC+8. Файл 2026_03_01 соответствует предполагаемому окну 28 февраля 16:00 UTC — 1 марта 16:00 UTC; это необходимо проверить фактическими min/max. Чтобы покрыть UTC 1–3 марта, понадобятся имена trade files 1–4 марта. README и exporter объявляют UTC partition от `source_ts_ms`, но эмпирическая проверка родительского агента это опровергла для загруженных файлов: файл Mar1 содержит Mar1 05:41:42Z–Mar2 04:32:10Z, Mar2 — Mar2 05:57Z–Mar3 04:46Z, Mar3 — Mar3 06:13Z–Mar4 02:02Z. Использовать фактические timestamp, захватывать соседние файлы (включая Feb28 для начала UTC Mar1); имя файла не доказывает UTC coverage. `block_timestamp` trade — секунды, quote — миллисекунды.

## Подтверждённая семантика OpenMarket

Прочитан публичный код тега `v0.5.2`; локальные копии и SHA256 перечислены в `source-code-manifest.json`. Это доказательство поведения данной версии кода; не независимое доказательство того, что именно она обслуживала каждую архивную запись.

- [`normalize.rs` строки 65–98](https://github.com/gregyoung14/openmarket/blob/v0.5.2/crates/recorder/src/normalize.rs#L65): для `price_change` поля `price` и `size` берутся из изменённого уровня. **Это не mid и не гарантированный объём лучшего ask.** Описание README о mid/depth at top нельзя применять буквально.
- Там же `best_bid` при отсутствии поля заменяется `price`. Исторический fallback нельзя отличить от настоящего bid, если исходный JSON отсутствует.
- [`normalize.rs` строки 101–143](https://github.com/gregyoung14/openmarket/blob/v0.5.2/crates/recorder/src/normalize.rs#L101): `book` сворачивается в best bid/ask, `price=None`, `size=None`; полные массивы уровней остаются лишь в `raw_json`.
- [`export_snapshot_to_parquet.py` строки 152–157](https://github.com/gregyoung14/openmarket/blob/v0.5.2/scripts/datasets/export_snapshot_to_parquet.py#L152): default exporter исключает `raw_json`. BUY/SELL side изменённого уровня также не отдельная колонка таблицы. Поэтому из default parquet **нельзя восстановить L2, проверить достаточную глубину для $5 или очередь лимитного ордера**.
- [`ingest.rs` строки 109–180](https://github.com/gregyoung14/openmarket/blob/v0.5.2/crates/recorder/src/ingest.rs#L109): direct recorder сохраняет timestamp сообщения биржи; `ingest_ts_ms` ставится локально при нормализации.
- В отдельном [`exchange-polymarket/src/polymarket.rs` строки 479–532](https://github.com/gregyoung14/openmarket/blob/v0.5.2/crates/exchange-polymarket/src/polymarket.rs#L479) intermediary overwrites timestamp локальным SystemTime перед broadcast. Текущий recorder имеет direct route; наличие альтернативного route само по себе не доказывает смешение timestamp в архиве. Но без deployment provenance для старых снимков нельзя автоматически приравнять каждый `source_ts_ms` к чистому exchange clock.

Правило пилота: использовать quote `ingest_ts_ms` как observed time этого сборщика, отдельно анализировать задержку source→ingest и отрицательные значения; trade block time не равен моменту появления исполнимого сигнала копировщика. Исполнение по best ask/bid при неизвестном размере — **непроверенная capacity assumption**, не доказанный fill.

## Почему CTF — ещё не полный денежный ledger

Каталог TimeSeventeen содержит:

| Файл | Bytes |
|---|---:|
| CTF/preparations.parquet | 101009561 |
| CTF/resolutions.parquet | 92752280 |
| CTF/merges.parquet | 592059273 |
| CTF/redemptions.parquet | 2792374236 |
| CTF/splits.parquet | 4957001014 |

Схема CTF имеет `id=chainId_blockNumber_logIndex`, но **не block_timestamp**; для общего времени нужна verified block-number→timestamp mapping. Splits/merges/redemptions отражают финансовые действия CTF, но dataset не содержит полных ERC20 USDC/USDC.e transfers, произвольных ERC1155 transfers, initial/end balances и прочих действий кошелька. Trading-only cash flow не равен всей доходности кошелька. Нельзя автоматически помечать расхождение как убыток или нулевой баланс.

Для полного ledger надо добавить нужные transfer logs и balance snapshots с одного архива Polygon за фиксированные начальный/конечный блоки, связывая chain/contract/transaction/log IDs. Доступность такого архива в данной подзадаче не подтверждалась.

## Практическая граница

Доступный bounded срез позволяет реальный audit trade-to-quote join, задержек, spreads, quote coverage, условную оценку capacity-unverified returns. Он не позволяет объявить подтверждённую торговую исполнимость, полный PnL кошелька или готовый надёжный публичный скор. Следующий источник для снятия этой границы: raw snapshots/price-change JSON + reconnect/gap provenance, и полный on-chain ledger за те же UTC/блоки.
