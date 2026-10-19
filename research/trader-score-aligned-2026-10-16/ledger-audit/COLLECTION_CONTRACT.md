# Контракт сбора для независимой денежной сверки

Цель: доказать сохранение USDC.e и outcome tokens на Polygon для заранее выбранных держателей позиций за **1 марта 2026 00:00:00 UTC включительно — 4 марта 2026 00:00:00 UTC исключительно**. Полнота и текущие пробелы описаны машинно в [ledger-completeness.json](ledger-completeness.json). Контур ограничен Standard Binary CTF v1; он не подменяет полную историю кошелька и не даёт проверку прибыльности копирования.

## Снимки на границах

Найти первый canonical block с timestamp ≥ 1772323200 и первый с timestamp ≥ 1772582400. Начальные остатки запросить на блоке непосредственно перед первым, конечные — на блоке непосредственно перед вторым. Сохранить соседние заголовки, чтобы независимо проверить границы. Номер/время блока не угадывать по средней длительности блока.

На обеих границах сохранить raw `balanceOf(holder)` USDC.e и `balanceOf(holder, tokenId)` каждого scoped outcome token. Каждая запись имеет chainId, holder, contract, tokenId/null, blockNumber, blockHash, raw integer amount, decimals, RPC method/params, request time, source и response hash. Запрос в latest недопустим. Список holder адресов должен учитывать proxy/safe; список tokens должен явно обозначать полный universe либо subset. Неизвестное начальное количество не заменяется нулём.

## События внутри окна

Получить для scoped адресов все USDC.e `Transfer` и CTF `TransferSingle`/`TransferBatch`; сохранить mint/burn, self-transfers и прямые внешние переводы. Для каждой затронутой транзакции получить полный receipt, чтобы восстановить связанные transfer, OrderFilled/OrdersMatched, split/merge/redemption, refunds и комиссии. Условие отбора: `start_block <= blockNumber < end_block`; сортировка по blockNumber, transactionIndex, logIndex. Batch необходимо раскрывать с индексом элемента, сохраняя исходный log.

Каждый event хранит chainId, blockHash, blockNumber, blockTimestamp, transactionHash, transactionIndex, logIndex, contractAddress, topics, rawData, receiptStatus, decodedEvent, decoderVersion и source response hash. Устойчивый event key включает chainId/blockHash/logIndex; batch element добавляет elementIndex. Reorg меняет canonical set, а не создаёт вторую проводку.

Сохранить historical code/ABI версию, decimals, token→condition/indexSet mapping, collateral/parentCollection, payout numerator/denominator и момент их известности. Для нестандартных partition и nested collections применять отдельную подтверждённую семантику. Время resolution из позднего справочника не становится автоматически моментом известности выплаты.

## Выход и критерий приёмки

- `opening_balances`, `closing_balances`: независимые historical state responses в целых единицах.
- `canonical_events`, `transaction_context`, `asset_registry`: исходные доказательства с hashes и версиями decoder.
- `postings`: transfer-derived изменения активов, отдельно economic classification и unknown classification. Trade/CTF события объясняют эти изменения и не проводятся повторно.
- `reconciliation`: opening + received − sent − closing отдельно для collateral и каждого token; допустимая разница ровно 0 native units. Любая ненулевая разница/пропуск означает failed/incomplete.
- `coverage`: диапазоны блоков/запросов, пагинация, gaps, retries, API limitations, полный или частичный token/address universe.

Отдельный PnL допускается только после классификации внешних потоков и наблюдаемой переоценки открытых позиций на обеих границах. Для PnL копировщика дополнительно нужны его собственные денежные состояния и исполнимые книги; нормализованные gross trade legs из архива не выполняют этот контракт.
