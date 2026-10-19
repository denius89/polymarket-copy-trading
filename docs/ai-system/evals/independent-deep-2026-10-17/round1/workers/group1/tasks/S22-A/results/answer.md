# Capability matrix: supplied snapshot

Use case — arbitrary leader, полный 30-дневный ledger включая cashflows. Он не подтверждён ни для одной venue. P package: branch api-review, head p9, draft PR, **не merged main**, verified Oct10. L package: main l4, verified Oct12; documentation snapshots Oct14. Свежесть scopes неизвестна; endpoints заново не проверялись.

| Capability | P | L |
|---|---|---|
| Public market list | Observed GET 200 Oct10 | Observed GET 200 Oct12 |
| Own fills | Documented: authenticated own account, pagination, retention 7 дней | Evidence отсутствует |
| Arbitrary leader fills | Observed page1: IDs 1–3, next=p2, timeout; история частичная | Documented partner-required; account request 403 Oct12 |
| Cashflows полного leader ledger | Не предоставлено | Нет excerpt/request |
| Scopes, fees, precision, limits | Не установлены | Не установлены |

Три ID не подтверждают конец истории. Семидневный documented retention own fills не обеспечивает 30 дней и не переносится автоматически на чужого leader. L403 показывает отказ конкретному запросу/доступу, а не отсутствие API; partner capability и account authorization — отдельные утверждения.

Минимальные следующие проверки для последующего поручения: зафиксировать documented request shapes, pagination termination, retention и identity для leader; установить разрешённый account/partner scope по каждой venue; проверить cashflow completeness, opening balances, precision/fees и ограничения. Для 30 дней может потребоваться разрешённый архив, но его наличие нельзя предположить. Затем сверить временные границы и полноту ledger независимыми totals.

Внешних действий не выполнялось. Публичный успех не означает доступ к полной истории или прохождение live-gate. Матрица сохраняет public observations и пробелы.
