# Пакет 06 · поддержка

13.10.2026. Дизайн на вычитку, без backend/live. Источники: ADR-0036, 115 §13, 118 ADM-09. Исходный main: `ffd396a2a95e7cb7d9cefe09dcc413520e2c2ef1`.

[Прототип RU](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2185-21070&starting-point-node-id=2185-21070&scaling=scale-down) · [EN](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2188-84282&starting-point-node-id=2188-84282&scaling=scale-down) · [Контракт](support-contract.md) · [Реестр](manifest.json) · [QA](qa.json).

## Что добавлено

33 RU + 33 EN состояния: очередь/фильтры/пагинация/empty/error; public reply и отдельная staff-only заметка; submitting/sent/failed/send_unknown; назначения/конфликт версии; waiting_user/resolved/closed/reopen; read-only/no-access; разрешённый user/session context и история. Всего 287 RU + 287 EN (574). Прежние страницы и IDs сохранены; новых страниц/веток дизайна нет. Поддержка — 14-й пункт sidebar, язык остаётся в профиле.

UI kit 0.4.7: Admin/Support ticket row (4 состояния), Admin/Support message (3 вида); 19 семейств / 118 вариантов state-library. Client/Textarea переиспользована без изменения клиентских masters/экранов. Общие Shadow tokens, Inter и grid12/gap16/padding24.

## Учебные данные

[SHADOW-SUPPORT-01](fixtures.json) полностью вымышлен. Сквозной пример: TKT-1042 / USR-1007 / S-CP-041. Общий TKT-1050 и Limitless TKT-1046 имеют свои карточки/ответы/user/message IDs. В их demo-capabilities только view/reply; управление показывается на основном сценарии. Остальные строки очереди ведут к unavailable-примеру вместо подстановки чужой identity.

Сценарии — независимые snapshots, не постоянно обновляющаяся база. RU/EN сообщения — редакторские варианты для вычитки; реальный сервис не обещает автоматический перевод переписки. Demo права/время/период не production defaults. Пользовательская public conversation берётся из общего источника, staff-only notes из отдельной разрешённой projection.

## Проверки и ограничения

Проверены 33 новых экрана каждого языка: нет выхода за экран, collapsed text, IMAGE fills или несуществующих targets. Навигация поддержки проверена на обеих страницах. 663 перехода на язык. Пустой ответ не отправляется; submitting/unknown не позволяют повтор/переключение режима. Private note отличается текстом, цветом и действием сохранения.

Present RU: очередь → ticket → note draft → saved; reply draft → submitting → unknown → check → sent. EN визуально/структурно проверен, полный EN/manual pass всех 574 состояний и совместная приёмка ещё не проведены. UI-only проверка не подтверждает server security/delivery.

Вложения/SLA не добавлены. Поддержка не исполняет денежные команды и не меняет risk/VIP/balances. Другие typed contexts (position/order/activity/account), длинная история и close/reopen ownership/retention требуют последующей детализации. Тикет не заменяет incident/reconciliation.

Следующий дизайн-блок: тексты/языки → объявления в приложении → сквозная вычитка. Construction/wiring/navigation/fix scripts — исторические рецепты, не frontend и не точный backup Figma. Перед реализацией читать свежий main и текущие узлы.

[Очередь](previews/queue-ru.png) · [Заметка](previews/note-ru.png) · [Переписка EN](previews/ticket-en.png) · [Общий вопрос EN](previews/general-en.png) · [UI kit](previews/ui-kit-support.png).
