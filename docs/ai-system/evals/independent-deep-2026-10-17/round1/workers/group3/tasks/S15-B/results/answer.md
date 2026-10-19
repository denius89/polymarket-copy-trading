Decision log: подготовка пересчёта допустима только как отдельный версионированный результат. Historical as-known r12 остаётся неизменяемым: cutoff12:00, observed≤12:00, X61 и исходный data hash. Correction имеет eventTime11:00, но observed14:00; раннее событие не означает раннее знание.

| Решение | Основание | Следствие |
|---|---|---|
| Сохранить r12 | Fixture требует immutable historical outputs | Не заменять hash и X61 |
| Отдельный as-known snapshot после14:00 | Correction теперь доступна | Новый ID и lineage; значение требует пересчёта |
| Отдельный retrospective corrected view | Разрешён только labelled/versioned | Не изображать его исторически известным |
| m9 оставить draft | Правила ещё не приняты | Не смешивать исправление данных и изменение метода |

X68 — предложенное аналитиком значение, а не подтверждённый выполненный расчёт. Replay «как будто всегда знали» можно подготовить лишь как явный контрфактический retrospective view. Он не воспроизводит реальные решения копировщика и не должен менять совершённые сделки или историческую линию as-known ради плавности.

В comparison package включить original output, corrected view, correction ID, eventTime/observedAt, cutoff, data/code/method/config versions, copier settings и причину расхождения. На графике показать прежнюю линию X61 и отдельно обозначенную corrected серию с датой знания correction. Проверить, какие downstream outputs действительно затронуты.

Затем review независимой сверки, согласование и публикация проходят отдельные стадии. Prototype force score не даёт production полномочий и не заменяет расчёт. Rollback оформляется новой версией с сохранением outputs и evidence. Ни rating eligibility, ни correction сами по себе не останавливают текущую copying session: требуется соответствующее принятое правило.
