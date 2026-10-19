Лог подтверждает получение seq 100, 101 и после reconnect — 105. Он не подтверждает отсутствие пропусков. Между 10:00:01 и reconnect 10:02:01 прошло 120 секунд, что превышает documented resume window 60 секунд. Seq 102–104 не наблюдались; неизвестно, соответствуют ли они fills, другим событиям или иной последовательности. Даже последний seq 105 не устанавливает полноту истории.

| Capability | Основание и предел |
|---|---|
| WS account feed с seq | Documented; три seq observed в fixture |
| Resume within 60s | Documented; этот reconnect вне окна |
| REST fills | Documented paginated own account; полнота не проверена |
| Orders idempotency | Documented key; scope/window не предоставлены |
| Fees/precision | Unknown |
| Наш account access | Permission evidence отсутствует |

Минимальные контрактные проверки адаптера: обнаружить разрыв/выход за resume window и выставить incomplete; инициировать проект read-only backfill всех REST страниц с контролем cursor/end, стабильной identity и дедупликацией WS/REST; проверить duplicate/out-of-order/late события и race между backfill и новым WS. Покрытие нельзя считать восстановленным до сверки временного диапазона и границы синхронизации. Сценарий внутри окна проверять отдельно от восстановления вне окна.

SDK не устанавливать и не запускать: startup example вызывает createOrder, что нарушает fixtures-only review и не является read-only. Own-account feed не предоставляет основания для всех лидеров. Проверки здесь спроектированы документально; authenticated permissions, фактическое восстановление gaps и live readiness остаются неизвестными.
