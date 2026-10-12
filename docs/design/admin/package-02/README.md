# Пакет 02 — финансы, выплаты, тарифы и рефералы

12.10.2026: текущая админка пересобрана на месте в едином стиле по Monty с палитрой Shadow. 184 состояния на двух страницах RU/EN, общий UI kit, иконки и сохранённый прототип. Новые итерации ведём в существующих экранах. Работа только над дизайном. [Актуальный дизайн и правила работы](../STYLE_GUIDE.md).

12.10.2026 · v0.1 · **draft_for_review**. Работа только над дизайном. Разделы ADM-13 и ADM-08 расширены; это не полная приёмка brief 118 и не утверждение численных правил.

116 native editable frames: 58 RU + 58 EN, 1440×1120, Dark, Inter. Страницы RU `1981:29`, EN `1981:30`. По 578 переходов — 1,156 всего. UI kit `1981:2` дополнен Finance row и Form field (Input/Select).

| Старт | RU | EN |
| --- | --- | --- |
| Финансы Owner A | [Открыть](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2003-2&starting-point-node-id=2003-2&scaling=scale-down) | [Open](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2007-2&starting-point-node-id=2007-2&scaling=scale-down) |
| Проверка Owner B | [Открыть](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2004-806&starting-point-node-id=2004-806&scaling=scale-down) | [Open](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2008-596&starting-point-node-id=2008-596&scaling=scale-down) |
| Тарифы / рефералы | [Открыть](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2005-803&starting-point-node-id=2005-803&scaling=scale-down) | [Open](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1070&starting-point-node-id=2008-1070&scaling=scale-down) |

[Все экраны](screens.md) · [Сценарии](prototype.md) · [Проверки](qa.md) · [Точный snapshot RU](evidence/ru-final.json) · [EN](evidence/en-final.json) · [UI kit additions](evidence/ui-kit-additions.json)

Финансы отделяют начисление, получение средств, обязательство, availability, pending и reservation. Единая USD-сводка не превращает два venue-баланса в одну выплату. Весь доступный баланс выбранной площадки read-only; подтверждённые варианты маршрутов определим при API-интеграции. USDT-учёт 1:1 сохранён, поддержка актива/сети/источника площадкой не обещается.

Выплаты: preview service/partner fee payer, accepted/submitted/paid, unknown/read-only recheck, discrepancy, cancellation before dispatch, no route, insufficient funds, expired preview и payouts stop. Fee-payer варианты имеют разные result fixtures: service — 120 USDT net; partner — 118.80 USDT net плюс раскрытое удержание 1.20, full gross $120 погашается целиком. Никакой штатной partial-paid и доплаты остатка.

Реквизиты: предложение Owner A, ожидание, отдельный пример проверки Owner B, активация/отклонение. Порог выплаты требует другого Owner на точный полный preview. Пороги и их изменения — отдельная security policy, не тариф. Незаполненная policy не активируется.

Тарифы: действующая alpha 0%; будущий paid draft 1%, simulator, preview, scheduled example, conflict и история. Owner публикует самостоятельно; внешнее применение отдельно. Lifetime-лестница: metric clients/turnover, отдельные threshold/share каждого уровня, срок и причина. Partner VIP отдельный от user VIP.

Все суммы/адреса — синтетические fixtures. Формы редактируются в Figma, но Present не принимает настоящий ввод и не вычисляет финансовый результат. Кнопки «пример» показывают состояния. Переход в другую роль — средство вычитки; не интерфейс изменения собственного доступа. Navigation может сбрасывать пример на подготовленное состояние. Focus/error/disabled variants новой Form field и полное динамическое поведение таблиц остаются на дизайн-полировку.

Construction script и design-data отражают этапы сборки, а не точный backup актуальной Figma. Точный текущий источник — Figma + финальные snapshots и PNG. Пакет 01 связан кнопкой Finance на его overview; добавление bridge описано в отчёте 123.
