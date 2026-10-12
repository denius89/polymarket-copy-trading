# 122 — Первый дизайн-пакет админки

12 октября 2026. Статус: **v0.1 на совместную вычитку**, принятие пользователем не получено. По поручению основателя созданы редактируемые RU/EN макеты, кликабельные переходы и admin UI kit в существующем Figma-файле.

[RU прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37690&starting-point-node-id=1982-37690&scaling=scale-down) · [EN prototype](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38513&starting-point-node-id=1982-38513&scaling=scale-down) · [UI kit](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1981-2)

68 фреймов (34 на язык), 396 reactions. Первый пакет частично покрывает ADM-01–03: обзор/актуальность, пользователи/VIP, demo session operations. Отдельно показана роль Operations без VIP. Представительные маршруты пройдены в Present, реестр всех узлов/реакций и PNG сохранён.

[Состав и starts](design/admin/package-01/README.md) · [Экраны](design/admin/package-01/screens.md) · [Действия/контракты](design/admin/package-01/actions.md) · [Прототип/покрытие](design/admin/package-01/prototype.md) · [QA](design/admin/package-01/qa.md) · [UI kit](design/admin/ui-kit/README.md)

В основе 115–120, ADR-0029–0043 и клиентский UI 117. Два Owner, объединённый Operations и кастомные роли сохранены. Alpha fee = 0; будущая конфигурируемая комиссия/VIP только Owner. Demo pause/resume не снимает risk/venue/global ограничения; unknown не разрешает повтор; бюджеты клиентов не доход сервиса. Макет статический: переходы результата иллюстрируют будущие asynchronous contracts.

Далее по 118: финансы сервиса и выплаты всего доступного баланса по выбранной площадке через Owner; protected recipients/пороги и независимое подтверждение по ADR-0043; версии тарифов, lifetime referral ladder/VIP и simulator; health/metadata обеих площадок, отзыв staff sessions, аварийные переключатели и recovery; поддержка, тексты/переводы/версии, in-app маркетинг и delivery; полный audit/permissions. Монитор USDT/USD — configurable alert/freshness, ledger 1 USDT = $1 сохраняется без автоматического пересчёта. Реальные сети/активы/источники payout проверяются при API интеграции. Ротация venue keys, external campaigns, landing builder, attachments/SLA — поздние этапы.

Пока не выполнены: полный ADM-01–18, все 18 P-сценариев, responsive/accessibility, динамические таблицы/формы и объединение UI kit с клиентским. Код, backend и live не запускались. До передачи в реализацию нужны вычитка и свежая сверка GitHub/Figma/ADR. Construction scripts не являются точной копией дизайна.
