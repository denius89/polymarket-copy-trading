# Проверка подписей частичных торговых данных

Проверен `../analyze_alignment.py` в рабочем дереве 16 октября 2026. Root-файл не изменялся. Его вводный комментарий, `diagnostic_kind`, caveats и scope правильно ограничивают результат диагностикой котировок: PnL, balances и рейтинг не объявляются рассчитанными.

## Что исправить перед распространением CSV

1. `implied_gross_cash_leg` может читаться как восстановленный cash flow конкретного taker. Лучше `provider_normalized_signed_notional_proxy_usd`. Это знак normalised source notional по direction поставщика; не сверенное перемещение денег. Имена `taker` и `taker_direction` желательно снабдить provider prefix либо constant evidence class.
2. CSV легко отделяется от README. Добавить поля `evidence_class=provider_normalized_trade_legs_unreconciled`, `scope=quote_selected_token_subset_taker_attribution_only` либо обязательный соседний schema/metadata JSON с этими значениями и SHA256 CSV. В метаданных явно `is_wallet_cashflow=false`, `is_pnl=false`, `fees_attributed_to_wallet=false`.
3. `archive_fee_field_usd` — допустимое имя source поля, но не комиссия этого taker. V1 fee принадлежит исполняемому order и удерживается из получаемого актива; provider перевод в USD и attribution не воспроизведены. Не вычитать эту сумму из signed proxy для «net».
4. В `semantics_ok` нет проверки `fee_usdc`. При сохранении сумм показывать finite/nonnegative/missing fee counts отдельно. SQL sum игнорирует NULL, поэтому неизвестность может скрыться внутри суммы; `allow_nan=False` остановит JSON лишь при некоторых нечисловых результатах, но не поймает ignored NULL. При unknown поле «общая fee» должно оставаться unknown либо быть названо sum_of_observed_valid_fee_field с coverage.
5. `count(*) WHERE NOT semantics_ok` не считает SQL NULL. Для полноты QA заменить диагностический счётчик на `WHERE NOT coalesce(semantics_ok,false)` и отдельно unknown fields. Допуск уже coalesce(false), поэтому это прежде всего полнота отчёта, не включение malformed rows.

Не требуется добавлять maker cash leg через противоположный знак: это было бы ошибкой для mint/merge match. `usdc_amount/price` также не станет независимо сверенным token transfer. Этим CSV можно описать объём и знак полей исходника; его нельзя использовать как training target полной прибыли адреса.

## Дополнительная оговорка по книге

Основной as-of использует source timestamp, а не recorder received time; код считает `eligible_ingested_after_arrival`, что полезно. Необходимо сохранять название «условная диагностика» и не переводить eligible в «доступно копировщику». Фактически полученная после предполагаемого arrival котировка не доказывает доступность на arrival. Это ограничение уже отражено в caveats; изменение фильтра после просмотра чисел не следует выдавать за заранее зафиксированный primary test.
