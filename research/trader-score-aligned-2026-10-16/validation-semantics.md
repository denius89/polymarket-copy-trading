# Независимая проверка семантики trade → quote

16.10.2026. Проверяется разрешённость диагностического signed price displacement; это не chain verification и не расчёт полного PnL кошелька. Frozen protocol не изменён.

## Вывод для текущего расчёта

**Да, price и taker_direction допустимо использовать как поля, нормализованные поставщиком, для явно условной диагностики котировок. Нельзя объявлять их независимо подтверждёнными реальными действиями конкретного кошелька.** Итоговое название: `provider-side-aligned quote displacement`. Для основного причинного вывода о копировании требуются receipts/transaction context и проверка decoder.

| Поле daily_aligned | Документированная семантика поставщика | Допустимое использование |
|---|---|---|
| asset_id | Outcome-token данной строки | Exact join с quote asset_id, с проверкой venue |
| price | USDC.e за одну долю именно этого outcome-token | Сопоставление с bid/ask этого токена; НЕ подставлять p_event |
| taker_direction | Raw taker BUY/SELL; заявлено derivation из settlement | BUY: ask−price, SELL: price−bid; сохранить attribution provider |
| p_event, D | Приведение противоположных токенов к reference event axis | Не смешивать с raw token BBO; нельзя дополнительно перевернуть направление NO-token |
| block_timestamp | Unix seconds времени onchain блока | UTC filter; не CLOB match timestamp, не observedAt и не точное время пользовательского исполнения |
| maker/taker | Адреса и роли в нормализованной записи | Не восстанавливать изменения maker/его позицию одним переворотом taker_direction |

Источник: сохранённый [README поставщика](../trader-score-real-2026-10-16/polymarket/trade_archive/README.md), разделы Data format / Field notes / Known limitations; опубликованный [dataset](https://huggingface.co/datasets/TimeSeventeen/Polymarket-v1). Локальный trade manifest фиксирует revision `5aa1b9d52316a8b2e789e81c8ae42c7ed532e8aa`. Исходники преобразования raw→daily_aligned в проверенном материале **не найдены**; документированное утверждение не заменяет независимого воспроизведения decoder.

## Почему нельзя вывести maker или движения денег автоматически

В официальном [Trading.sol](https://github.com/Polymarket/ctf-exchange/blob/main/src/exchange/mixins/Trading.sol) `_fillMakerOrder` эмитирует данные активов maker-order. `_deriveMatchType` допускает BUY/BUY через MINT и SELL/SELL через MERGE; это не только обмен BUY против SELL одного токена. `_deriveAssetIds` описывает отдаваемый/получаемый актив самого order. Следовательно, противоположное maker/taker направление и одинаковый token для обоих участников нельзя считать универсальной физической проводкой.

Это проверка публичного исходного кода на main, **не** доказательство соответствия конкретному deployed bytecode и историческому receipt. Для конкретной строки нужны тип сопоставления, asset IDs/amounts, все релевантные logs и transfer/split/merge context. До этого разрешён только provider-normalized diagnostic.

Статья поставщика [Polymarket-v1 Database, §3.4–3.5](https://arxiv.org/html/2606.04217v1) заявляет settlement-derived aggressor и описывает нормализацию бинарных ног. Она не даёт в просмотренном тексте достаточного decoder trace для независимой проверки каждой нашей строки. Более того, статья описывает tx_hash/log_index, тогда как cleaned schema не сохраняет эти event IDs: нельзя приписывать очищенной строке уникальность первичного onchain события.

## Ограничения для labels, fees и времени

- Метаданные архивом заморожены. Fee rate и resolution fields не являются автоматически point-in-time справочником на timestamp fill. Не использовать их как известные тогда значения без dated provenance.
- `fee_usdc` — нормализация поставщика, не доказательство валюты/плательщика каждой исторической fee. В данном displacement расчёте fees вообще не включаются; результат gross quote diagnostic.
- `usdc_amount/price` — implied quantity при положительной цене, а не независимо подтверждённый integer token transfer. Не выдавать равенство, построенное этой формулой, за ledger reconciliation.
- README содержит разночтение: введение и field guidance называют UTC+8, одна фраза methodology — UTC day. Фактический block_timestamp имеет приоритет; соседние календарные файлы должны быть включены до UTC-фильтра.
- Block timestamp может значительно отставать от offchain matching. Lag 0.5/2/5 секунды от него измеряет условное смещение относительно settlement clock, не реальную задержку копировщика от первоначального решения трейдера.
- Нет direct onchain ID в cleaned rows: exact duplicates нельзя уверенно удалять как повторную загрузку без provenance. Допустим sensitivity по совпавшим строкам с отдельной пометкой; не primary «исправление» реальных fills.

## Минимум для технического review анализатора

1. Не используется `p_event`, `D`, `winning_outcome_label` или future resolution в quote metric.
2. Matching exact token и causal as-of; price units и BUY/SELL semantics не угадываются из quote movement.
3. Никакой maker inverse ledger, `cash = ±usdc_amount` не выдаётся за полную history денег кошелька.
4. Timestamp ties/конфликтующие BBO сохраняются как ambiguity; gap/unknown не становится skip.
5. Вывод прямо сообщает provider normalization, gross metric, settlement-clock scenario, unknown size/depth, отсутствие scorer validation.

## Независимый review первоначального analyze_alignment.py

Код прочитан после фиксации протокола; окончательный расчёт ещё не запускался/не оценивался этим reviewer на момент замечаний. Проверено по реализации:

- ASOF направлен в прошлое: `arrival_ms >= quote_ms`, exact asset_id; quote age 0…1000 мс.
- Последняя плохая BBO не удаляется перед ASOF, поэтому нет скрытого fallback на более раннюю хорошую цену.
- Совпадающие значения в одной миллисекунде схлопываются, разные пары bid/ask маркируются конфликтом; exact arrival ties исключаются.
- Common-cohort требует eligibility одной строки на всех трёх lags, а per-lag результаты выводятся отдельно.
- BUY/SELL знак, cents и bps соответствуют объявленной формуле; outcomes/resolution не загружаются в аналитическую таблицу.
- Переводы/кошелёк не реконструируются; gross notional не называется PnL; model verdict явно blocked.

Переданы координатору следующие замечания; статус исправления определяется последующей проверкой файла:

1. **NULL в audit counts:** `WHERE NOT predicate` не считает SQL NULL. Нужны `coalesce(predicate,false)` и отдельные missing counts, иначе invalid_semantics/invalid_bbo занижаются при пропусках.
2. **Input provenance:** quotes читаются wildcard, хотя hashes проверяются по manifest. Использовать ровно manifest filenames и проверить их уникальность, чтобы новый/посторонний parquet не попал в расчёт без hash verification.
3. **Provider fallback BBO:** в сохранённом `normalize.rs` price-change best_bid может быть заменён field price. Проверка bid≤ask не доказывает, что это настоящая BBO. Нужны event_type composition, book-only sensitivity и/или неизменяемая пометка provider-only/unknown fallback. Это не исправляется просто numeric filter.
4. **Clock sensitivity:** первоначально ±1 секунда меняет и публикует только coverage. Для проверки устойчивости именно displacement следует показать metric и состав сопоставимых строк тоже; иначе нельзя утверждать ценовую устойчивость.
5. **Result naming:** `interval_only` неверно обозначает point descriptive quote metric, для которого bounds не посчитаны. Предпочтительно отдельное `provider_normalized_quote_diagnostic`; финансовый результат остаётся not_estimable.

Отдельное ограничение: исключение точного quote/arrival timestamp tie **не доказывает** причинную упорядоченность trade/quote при секундантном block time. Общая conditional qualification должна сохраняться после всех фильтров.

## Review окончательного трёхдневного диагностического расчёта

Проверены исправленный `analyze_alignment.py`, `alignment-results.json`, `partial-trade-legs.csv` и `coverage-by-token.csv`. Проверенный исходный JSON имеет SHA256 `38fd2bec4d86f8347823b23935745ef725da7a1e4d36a072d5bfa64b1cc2588c`; последующие дополнительные sensitivities могут изменить hash, сохранив primary результаты. Reviewer не менял analyzer или результаты.

Все пять замечаний первоначального review учтены: nullable invalid counts исправлены; input paths берутся из manifests; event composition/provider-only evidence class добавлены; clock sensitivity выводит displacement; result_kind исправлен. Book-only расчёт не объявлен полноценной альтернативой: в интервале всего 38 book rows против 1 607 486 price-change rows, и этот предел явно виден.

Независимая арифметическая проверка Python standard library подтвердила:

- 193 045 строк trades = 20 597 BUY + 172 448 SELL; совпадает с суммой source_rows в partial-trade-legs.csv.
- 1 607 524 quotes = 38 book + 1 607 486 price_change.
- Перекрёстные totals coverage-by-token.csv совпадают с JSON по каждой задержке; funnel монотонен.
- Eligible counts: 39 550 / 36 560 / 38 883 для 0.5 / 2 / 5 секунд. Coverage: 20.4875% / 18.9386% / 20.1419% от subset denominator.
- Общая complete-case группа — 23 804 fills, 12.3308% subset denominator; по каждому lag ровно 3283 BUY + 20 521 SELL. Это правильная общая группа для descriptive lag comparison.
- На 5 секундах все 29 conflicting-BBO случаев одновременно входят в 11 706 exact-timestamp ties. Эти причины **пересекаются**: нельзя сложить обе категории как независимые потери funnel.

### Критическая находка времени доступности

На условных +2 секундах **19 657 из 36 560** eligible source-clock совпадений (53.7664%) имеют **даже самое раннее** время ingest позже arrival. Значит, source-clock ASOF не доказывает, что эти котировки были доступны recorder к предполагаемому времени. Это не скрытая ошибка вычисления signed displacement: diagnostic заранее условный. Но такой результат запрещает переименовать его в реалистичный copier replay.

Имеется ещё 23 совпадения, для которых первое появление той же BBO до arrival, но одно из повторений позже. Поэтому latest-ingest filter даёт 16 880 оставшихся совпадений, тогда как earliest-ingest filter — 16 903. Ни одно из этих чисел не является долей исполнимых сделок.

Предложенная после просмотра conservative sensitivity `latest_ingest ≤ arrival` допустима **отдельным post-inspection результатом**. Она сохраняет primary calculation и явно называется conservative subset, а не новым preregistered результатом. Она чрезмерно исключает некоторые уже известные identical BBO и не восстанавливает предыдущую доступную recorder котировку после отклонения последней. Для настоящего recorder replay нужен bitemporal state reconstruction по порядку получения плюс проверка clocks/sequence, а не один фильтр.

### Границы принятого результата review

Арифметика агрегатов и причинно корректное направление source-clock ASOF проверены. Это не независимое подтверждение каждого onchain event, fee attribution, семантики provider fallback или доступной L2-глубины. Gross signed notional остаётся частичным proxy; полный cash/token ledger не построен. Явно сохранённый `comparison_blocked_by_horizon_and_data`, zero 30-day outcomes и отсутствие численных wallet scores соответствуют доказательствам. Преимущество CE/LCB этим результатом не установлено.

## Дополнительный независимый review targeted L2 PMXT

Проверены `source-audit/analyze_pmxt_target.py`, `pmxt-target/target-events.parquet`, соответствующие audit JSON и snapshot/trade joins. Дополнительный L2 срез имеет один выбранный condition и два его токена; это примерно 31 минута 1 марта, а не L2-покрытие всех трёх дней и 19 conditions. Конкретный источник выбран после BBO-диагностики; результат exploratory.

**Что независимо пересчитано:**

- В parquet timezone обеих временных колонок — UTC; `.timestamp()` не интерпретирует naive local time.
- По исходным 8766 snapshot rows independently проверены finite p/q, допустимый диапазон цены, положительные активные sizes, дубли цен и crossed books: нарушений не найдено.
- Для первоначальных 858 допустимых по конфликтам snapshot/trade joins VWAP пересчитан непосредственно из исходного snapshot: sorted asks, gross budget $5, `quantity = Σ(spend_at_level / price)`, `VWAP = 5 / quantity`. Все совпали в пределах 1e−10. Это gross displayed capacity, не комиссия-inclusive precheck и не исполненная покупка. Одно последующее exact-arrival-tie исключение оставило 857.
- Join использует точный token; snapshot availability равна `max(received, created)` и не позже assumed arrival. Соответствие timestamps доказано только внутри часов коллектора, без гарантии синхронизации с биржей/блоком.
- После исправлений primary +2 s даёт 1284 BUY rows; 857 fresh/unconflicted/strictly-prior snapshot matches и 857 gross $5 fits, отдельно 347 conflicting-latest exclusions и 1 exact-arrival-tie. Первоначальные 1169/1153 устарели и не должны идти в итоговый отчёт.

**Критическая граница состояния:** первоначальный snapshot-only join не применял промежуточные price_change. Независимый пересчёт первоначальной версии нашёл 526 из 858 joins с изменениями строго после snapshot и до arrival. После учёта всех изменений **включая совпадающие со snapshot availability** каждый из 857 окончательных joins содержит хотя бы один intervening-or-tied price_change. Independent hash окончательного joins: `e48e2d9f7ff12c1a1f554bb3a581c3c62f302202be485893e64d114cabaa484f`.

Это не доказывает, что все 857 книги непригодны или покупка невозможна: tied update мог уже войти в snapshot, но порядок не установлен. Строгое правило «snapshot без вмешавшихся/неупорядоченных изменений» не подтверждает ни одного arrival state. Допустимый вывод: gross capacity вычислима **на снимке**, доступная capacity **на момент прихода** пока не доказана. 1642 конфликтные группы snapshot availability и 73 расхождения полной книги из 8764 сравнений со следующим snapshot дополнительно запрещают объявлять delta replay полностью восстановленным. Совпавшая следующая snapshot тоже не доказывает корректность промежуточных состояний.

Код дополнен в ходе review numeric QA, конфликтами snapshots, exact-tie exclusion и счётчиком промежуточных/совпадающих изменений. Вычислений PnL или wallet-score здесь нет. Ни один из этих тестов не утверждает fees, queue priority, воздействие заявки на книгу или достоверную live latency.

## Уточнение поведения будущего paper-движка по ADR-0024

В предварительном протоколе §5 формулировка о сохранении резерва при unknown покупке относится к **уже созданному намерению/заявке с неизвестным результатом**. Она не должна применяться к отсутствующей заявке только потому, что quote/depth отсутствует.

По принятому [ADR-0024](../../docs/decisions/0024_show_missing_market_data_without_simulated_fill.md), если данных недостаточно **до** создания виртуального намерения, копия не создаётся, бюджет не резервируется, расходы/PnL не выдумываются. Пользовательский сигнал получает `Skipped` с точной причиной отсутствующих данных. В исследовательском audit это при этом остаётся unknown execution feasibility, а не доказательством недостаточной ликвидности. Если покупка уже находится в unknown, резерв удерживается до сверки согласно ADR-0020/0021. Frozen protocol оставлен неизменным; это clarification для следующей реализации, не новая продуктовая политика.
