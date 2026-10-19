# Capability matrix по supplied fixtures

| Capability | Статус и evidence | Предел вывода |
|---|---|---|
| Public market list | `observed`: HTTP 200 вчера | Успех указанного публичного чтения; body/schema, pagination и полнота не даны |
| Partner endpoint | `observed`: HTTP 403 | Доступ этим запросом не получен; причина и право аккаунта неизвестны, отсутствие API не доказано |
| Own-account WS | `documented` | Документация описывает свой аккаунт; runtime, account authorization и reconnect не проверены |
| All-wallet histories | `unknown / not_verified` | Ни market GET, ни own-account WS не доказывают произвольные кошельки, backfill и полную историю |
| Полные cashflows | `unknown / not_verified` | Не подтверждены opening balances, transfers, fees, settlements и сверка ledger |

Этих данных недостаточно для обещания полной истории лидеров, воспроизводимого денежного результата или live готовности копирования. Venue, environment, точная календарная дата «вчера», request shape и pinned versions не предоставлены; нельзя переносить наблюдения на обе площадки автоматически. Account-authorized capability в snapshot не установлена. Partner-required статус также требует условий endpoint, а не одного HTTP кода.

Следующий минимальный план без выполнения запросов: установить venue и идентификаторы доказательств, прочитать актуальный контракт нужных history/cashflow endpoints, определить wallet/account scopes, retention, pagination, precision, fees, limits и realtime gap recovery. Затем отдельно согласовать доступ и проверку полноты на контролируемом наборе с независимой сверкой денежных потоков. SDK-примеры, signing и account mutations из этого review не следуют. Новых запросов не было.
