# Forward shadow: протокол сравнения · 18.10.2026

Статус **collecting / not eligible**. Этот пакет начинает сбор наблюдений и проверку инструмента без реальных денег. Он не объявляет уже полученные данные проверкой моделей. [Машиночитаемый протокол](comparison-config.json) фиксирует объект и блокировки; [стандарт копировщика](../trader-score-reference-2026-10-18/COPIER_STANDARD.md) остаётся неизменным.

## Что будет результатом

1. Сохранённый поток публичных наблюдений с собственным receivedAt, последовательностью получения, gap/reconnect журналом и хешами. Сам API-ответ ещё не финансовый результат.
2. Отдельные расчётные copy-сессии: виртуальные $200, BUY $5, gross-лимиты $20/$30, местная полночь Europe/Warsaw; H = 30 календарных дней. Исследовательская панель не заменяет пользовательский shadow 7–14 дней ADR-0011.
3. При выполненных prerequisites — **условные** денежные исходы общего симулятора, интервалы исполнения и покрытие. Без отправки настоящего ордера нет наблюдаемого counterfactual fill: даже непрерывная книга доказывает только сценарий доступной ликвидности, не гарантированное исполнение.
4. Только после независимого аудита, замораживания кандидатов и накопления будущих исходов — сравнительное исследование; без выпуска публичной цифры.

Новая живая версия площадки не наследует проверку исторического Polymarket v1. Нужен отдельный проверенный binding и новая версия forward-profile: контракты/единицы, signal identity, cash/token lifecycle, тарифы, price rule, порядок/семантика книги, её ограничения. Сам хеш frozen v1 не снимает его `eligible_for_model_comparison=false`. Тестовые fee $0.10/$0.05 и quanta из инженерного примера **запрещено** переносить в forward. Limitless имеет отдельный scope и допуск; публичные данные и приватные account endpoints оцениваются раздельно. Недоступная площадка не получает вымышленный нулевой результат.

## Prospective universe и знаменатель

До сравнения замораживается scope manifest публичного activity-источника: площадка/версия, endpoint/subscription, markets/tokens, filters, page/cursor coverage, лимиты, начало наблюдения и причина конечного scope. В universe попадают **все canonical identity, впервые увиденные по активности в этом scope**, независимо от цены, прибыли, будущего выживания и качества последующего результата. Если источник не раскрывает identity, наблюдение остаётся в coverage, но не становится выдуманным адресом. Адреса не склеиваются эвристически; подтверждённая связь хранится отдельно и учитывается в grouping.

Enrollment фиксирует identity, first_observed_at и evidence hash **до** её будущих исходов. Состав уже открытого cohort не переписывается. Новые адреса входят в следующий cohort по тому же правилу. Сбор ограниченного списка markets — панель этого scope, а не все трейдеры площадки. Leaderboard, вручную выбранные победители и исследовательские старые адреса могут быть отдельной exploratory панелью, но не unbiased universe.

Неактивный после enrollment адрес остаётся. Подтверждённое отсутствие подходящих действий при полном покрытии даёт cash/no-trade; outage/неполные страницы не равны отсутствию действий. Неизвестность, исчезновение и delisting остаются в исходном знаменателе. Common paired subset показывается отдельно с полным funnel и причинами исключения; complete-case победитель не обобщается на весь universe.

## Объект и исполнение

Primary `X = terminal_net_wealth / 200` **одной** сессии. Все модели используют одинаковые auditable monetary paths и одинаковые правила skip/unknown/reserve. Для proportional SELL нужен известный contemporaneous остаток лидера и экономическая идентичность изменения. Нельзя считать полный выход, игнорировать продажу или подставлять ноль при неизвестном знаменателе.

Точка цены/глубины не заменяет execution oracle. Рабочий результат имеет `forward_shadow_conditional`, интервал либо `not_estimable`. Для точечного *условного* X нужны заранее зафиксированная модель fill, полный provenance, отсутствие критичных gaps, применимые расходы, сверка собственной копии и as-of terminal bid liquidation с exit costs. Без этого point wealth = null; не ноль и не cash по умолчанию. При наличии неизвестного обязательного денежного компонента session остаётся в coverage, но не в paired point comparison. Диапазон исполнения, меняющий порядок моделей, запрещает объявить победителя.

Собственная нулевая начальная позиция копии известна; полная история collateral лидера не требуется для её внутреннего ledger. Однако leader inventory для продаж требуется. Виртуальный счёт не имеет on-chain остатков: независимая проверка — отдельная реализация проводок + документированная проверка исходных публичных фактов, а не фиктивная RPC-сверка виртуального кошелька.

## Время, обучение, validation, confirmation

Текущие наблюдения сначала **instrumentation/development**. Ни дата документа, ни первый удачный GET не являются стартом финансового H30. Сессия начинается в заранее зафиксированную local-midnight отсечку после enrollment и всех prerequisites; конец — через 30 местных календарных дней Europe/Warsaw. DST меняет длину UTC-интервала. Все времена получения и зависимости хранятся UTC с исходной точностью; source time не заменяет receivedAt.

При cold start минимум три **полных неперекрывающихся** train H30 на адрес позволяют лишь диагностический bootstrap. Это не доказательство хвостов. Одновременные сотни адресов одного месяца не заменяют три режима. Минимум 90 дней train + отдельные 30 validation + 30 confirmation = 150 календарных дней при идеальном непрерывном покрытии и уже готовом инструменте; это нижняя календарная оценка, **не обещание готовности через 150 дней**. На короткой истории численный scorer недоступен.

Перед validation заморозить exact code/config/data/features hashes, candidate list и все attempts; перед confirmation — ещё отобранную версию процедуры и manifest train/validation cutoff, enrollment, групп и holdout access log. Train label известен полностью до prediction time. Никаких settlement после cutoff, нормализации на будущем, настройки по confirmation или повторного использования старого просмотренного архива как слепого holdout. Изменённая после просмотра версия получает новый experiment ID и новый будущий confirmation interval.

Основная оценка — forward времени; shared economic event/condition, связанные адреса и календарные shocks учитываются как зависимые блоки. Нельзя разбивать отдельные fills случайно. Primary operational переносит продолжающиеся markets только по известным на cutoff данным; отдельный secondary new-event test исключает пересечение economic groups train/test и сообщает потерю coverage. Purge полностью удаляет train label windows, заканчивающиеся после cutoff; произвольное число embargo дней не объявляется лечением всех зависимостей.

## Кандидаты и контроль

Сохраняем исследовательские конструкции прошлого предложения, исправляя трактовку, а не принимая новые product веса:

| Кандидат | Объект |
|---|---|
| Cash | X=1 для каждого сохранённого слота |
| Random eligible | Один адрес из общего eligible universe, fixed seed |
| Mean net | Mean(X_train)−1 |
| LCB mean | Q10 posterior mean net при общих Dirichlet weights |
| LCB CE2 | Q10[1 / Σ(p/X) −1], γ=2 — исследовательская гипотеза |
| Predictive CE2 | 1 / E_predictive(1/X) −1, отдельная sensitivity |
| Действующий quality index | 30/25/25/20, только наблюдение после замораживания нормализации |

Bootstrap: 2000 draws, shared seed и веса в паре LCB/CE, по неперекрывающимся X; X=0 не заменять epsilon (CE=−100%). Posterior параметра CE не является predictive distribution X; универсального порядка двух CE-конструкций нет. Narrow bootstrap interval не доказывает отсутствие редких ненаблюдавшихся потерь. γ=2 не является утверждённым владельцем допустимым риском. Artifact hashes сейчас null: перечисление формул не означает готовность их реализации.

Для списков — 5 одинаково взвешенных слотов; primary пользователь выбирает **один** слот с вероятностью 1/5. Пустой слот хранит cash, капитал не перераспределяется. LCB кандидаты показываются до positive gate и отдельно после него; ties canonical identity ascending. Utility суммарного портфеля — отдельный secondary estimand. Не усреднять CE адресов и не выдавать это за CE пользовательского распределения.

## Что считать и когда не выбирать победителя

Paired conditional X доступны только на common audited paths; отдельно исходный universe coverage. Сообщаем mean/median/loss frequency, net CE2, worst outcome, sampled drawdown с частотой valuation, долю unknown/skip, gaps, fee/inventory/terminal-book coverage, зависимости и фактические независимые calendar/event clusters. Intervals получаются парным resampling **общих** блоков, а не fills или bootstrap draws как новых наблюдений. При единственном режиме они exploratory. Forecast calibration применяется к predictive X/CDF, не к posterior CE; отбор top и индивидуальная калибровка проверяются отдельно.

Допустимый риск, minimum useful economic effect δ и достаточное независимое покрытие для inferential claim пока **не утверждены**. Они остаются null. Старые +1 п.п./+2 п.п. из предложения не переименованы в решение владельца. Текущий пакет не выполняет winner ranking, statistical acceptance или mapping 0–100. Gate-скрипт проверяет структуру/evidence links и будущие даты, не удостоверяет содержание аудита.

Отчёт всегда может честно сказать `collecting`, `not_eligible` или `engineering_complete_comparison_not_authorized`. Ни прошедший schema check, ни положительная краткая доходность не меняют ADR-0011/0044 и не публикуют score.

## Воспроизведение gate

`python3 compare_models.py --config comparison-config.json --out comparison-readiness.json` выводит текущие блокировки; с `--sessions sessions.json` проверяет протокол входов ниже. Файл результата создаётся только по новому пути. Он не запускает сеть, не торгует и не вычисляет выдуманную доходность из raw capture.

Sessions schema: `{schema_version: "forward-session-evidence-v1", sessions: [...]}`. Каждая запись содержит session_id, venue_binding_id, canonical_identity, started_at, cutoff_at, observed_until, outcome_kind, ledger_status, unknown_components, terminal_net_wealth (decimal string or null), path_sha256, standard_sha256, evidence (список относительных path+sha256), и requirement_evidence: mapping каждого требования конфигурации к списку хешей приложенных evidence. Каждое время — timezone-aware ISO8601. Хеши и пути проверяются; file existence не заменяет предметное независимое review. Поля и отзывы не конвертируются в самоутверждённый production pass.

Raw envelope сборщика `forward-observation-v1` хранит runId, sequence, observedAt, observedMonotonicNs, venue/kind/transport/scope, rawBase64/bodySha256 и recordSha256/prevRecordSha256. Эти наблюдения не являются sessions input и не получают X автоматически. Hash chain показывает целостность сохранённой последовательности, но сам по себе не доказывает полноту внешнего потока.
