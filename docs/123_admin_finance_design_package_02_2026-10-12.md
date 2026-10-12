# 123 — Дизайн админки: финансы и условия

12.10.2026 · v0.1 на вычитку. По уточнению владельца продолжаем **только дизайн админки**. Добавлены ADM-13/08: финансы сервиса, партнёры, full payouts, реквизиты/независимые подтверждения, защитные пороги, тарифы, lifetime-рефералы и partner VIP.

116 новых редактируемых RU/EN состояний и 1,156 переходов. Макеты 1440×1120, Inter/Dark. UI kit пополнен Finance row и Form field Input/Select на общих foundations. Поля индивидуальных чисел/дат/причин разнесены; прежние client masters сохранены.

[RU финансы](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2003-2&starting-point-node-id=2003-2&scaling=scale-down) · [EN finance](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2007-2&starting-point-node-id=2007-2&scaling=scale-down) · [RU тарифы/рефералы](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2005-803&starting-point-node-id=2005-803&scaling=scale-down) · [EN pricing](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1070&starting-point-node-id=2008-1070&scaling=scale-down)

[Состав](design/admin/package-02/README.md) · [Все экраны](design/admin/package-02/screens.md) · [Сценарии](design/admin/package-02/prototype.md) · [QA](design/admin/package-02/qa.md)

Сохранены: два Owner, деньги только Owner, полная выплата по выбранной площадке, net/fee отдельно, reserve при unknown, отсутствие partial-paid/resend/manual success; другая identity для новых реквизитов/защитных порогов/пороговой выплаты. Обычный тариф и VIP не требуют второго Owner. Alpha 0%, будущий draft 1%; referral share от нашей комиссии и lifetime ladder без месячного reset. Нельзя пересчитать прошлую историю.

Реальные financial sources/routes/assets не определялись; все суммы и адреса — fixtures будущего платного сценария. Внутренний учёт 1 USDT = $1 не доказывает поддержку USDT площадками. Формы редактируемы в Figma; Present демонстрирует фиксированные значения и переходы.

Все 116 фреймов и destinations структурно проверены, 5 опорных views визуально проверены с исправлениями и повторными renders; основные RU payout/unknown и EN pricing/referral маршруты пройдены в Present. Полной приёмки P-03/04/05/13/14 пока нет; недостающие состояния перечислены в QA. Пакет 01 получил навигационные bridge-кнопки: RU `2023:567`, EN `2023:1132`; его 396 reactions в отчёте 122 относятся к прежнему snapshot, после bridge к нему добавлены 2 URL reactions.

Следующая область дизайна — health обеих площадок, подключения/безопасность, сотрудники и кастомные роли, журнал и аварийные переключатели/recovery; затем поддержка, тексты/языки и маркетинг. Полировка финансов и общая сквозная приёмка остаются в очереди. Никакого начала разработки этим пакетом не предусмотрено.
