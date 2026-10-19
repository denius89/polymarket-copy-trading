# Минимальная стратегия приёмки

Сохраняются узкие результаты build b7: RU mobile paper happy-path screenshot и 100% unit coverage formatters. Это не подтверждает permissions, retry, EN, venue L или денежную корректность. Mock с немедленным completed исключает критические переходы новой версии.

| Приоритет / уровень | Сценарий в изоляции | Независимое ожидаемое свойство |
|---|---|---|
| P1 integration/API | Tenant A читает/меняет tenant B через прямой запрос | Отказ без утечки и изменения данных |
| P1 API/E2E | Support пытается mutating action; разрешённая роль выполняет своё действие | Support только read-only; разрешения проверяются сервером |
| P1 integration | Unknown withdrawal, timeout, retry и duplicate receipt | Без reconciliation нет повторной отправки; одно экономическое списание |
| P1 fault/concurrency | Crash между отправкой/commit, два retry, out-of-order confirmation | Нет двойного эффекта, сохранены reserve и trace |
| P1 integration | Revoke до retry/отложенного выполнения | Актуальный запрет проверяется в точке исполнения |
| P2 E2E/visual | RU/EN mobile, обе venues, loading/error/unknown | Явный статус и корректные деньги, без ложного completed |

Использовать stateful synthetic/recorded fixtures с tenant B и обеими venues, а не always-completed mock. Oracle — отдельно составленная таблица разрешений и переходов, сверка cash/reserve/операций по receipts; не та же функция, что реализует retry. Резерв меняется по fixture-правилам; unknown не считать завершением.

После новых проверок регрессировать затронутый happy path на новой версии и связать evidence с build. Приёмка обеих venues остаётся неполной до закрытия соответствующих пробелов. Real withdrawal не разрешён; тестов на аккаунте не проводилось.
