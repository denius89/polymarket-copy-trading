# Админка · пакет 08 · Маркетинг

13.10.2026. Дизайн на совместную вычитку; frontend/backend и реальные отправки не начаты.

[Открыть RU прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2376-29545&starting-point-node-id=2376-29545&scaling=scale-down) · [EN прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2378-102168&starting-point-node-id=2378-102168&scaling=scale-down)

## Что подготовлено
37 RU + 37 EN состояний на существующих admin страницах. Каталог с фильтрами и заголовками столбцов; RU/EN редактор, черновик и ошибка перевода; аудитория с агрегатами и исключениями; клиентский предпросмотр и локальный тест; публикация, расписание и runtime permission failure; показатели доставки/показов/прочтения; unknown/failed; подтверждение паузы и её ошибка; историческая доставка после паузы; история, A-1 и сохранение нового черновика A-3; view-only, edit-only и no access.

Публикация самостоятельная по правам, без Owner approval. Неизвестное правило consent блокирует targeted marketing. Пауза сохраняет уже увиденную историю. A-1 восстанавливается новым черновиком, без автоматического перезапуска.

## Компоненты и тестовые данные
Admin UI kit 0.4.17: Announcement row (Default/Hover/Focus) и standalone Announcement table header. 25 component sets / 148 variants. Общие Shadow tokens, Inter, grid, nav, формы, Metadata row/header, метрики, alerts и Client/Textarea переиспользованы. Клиентские masters и страницы не изменены. В «Управление» добавлен «Маркетинг» через исходную группу; новых страниц/веток Figma нет.

Вымышленные ANN-DEMO-01/02, A-1/A-2/A-3 и AS-DEMO-02. 124 кандидата → 100 eligible → 98 enqueued после двух поздних отказов. 90 available + 4 failed + 4 unknown = 98; display 60 и read 38 — вложенные показатели. Правила согласия и частоты — fixtures, не production решения. Автор черновика Ирина Волкова; публикация/пауза — Елена Морозова.

Прототип статический: не хранит изменения/роль в backend, каталог является исходным demo набором. Сохранение восстановленного A-3 — конец этой ветки; повторная публикация должна пройти новую проверку.

## Проверки и ограничения
180 связей действий (90 на язык), четыре source navigation links. 74 состояния проверены: горизонтальные/вертикальные выходы текста, наложения в вертикальном Auto Layout, Inter, отсутствие raster UI — ошибок нет. Native screenshots каталога, редактора, paused и delivery-history RU/EN проверены. На текущих страницах 366 RU + 366 EN root frames, включая функциональные меню аккаунта.

Основной RU P-07 пройден вручную в Present: новый черновик → missing translation → исправление → аудитория → preview → publication → pending → active → delivery → pause → confirmed paused. Также history → A-1 → A-3 draft → saved. EN проверен структурно и визуально; полный ручной EN/role/редкие отказы остаются совместной приёмкой.

[Контракт и сверка с клиентским UI](marketing-contract.md) · [Узлы и переходы](screen-ledger.json) · [QA](qa.json) · [Операции](operations.json).
Скрипты — история сборки, не backup Figma и не runtime-контракт. Перед реализацией читать принятую версию repo и актуальные узлы Figma. Окончательные consent bindings, placement, frequency, snapshot TTL и evidence ещё требуют подтверждения.

Пакет сохранён локально, GitHub в этом цикле не обновлялся. Следующий дизайн-блок — трейдеры и данные (ADM-07 / ADM-06); затем общие очереди incidents/reconciliation, уведомления/feedback и общая вычитка. Bulk email/Telegram/push, landing builder и key rotation остаются позднее.

Проверки репозитория: npm run check и git diff --check прошли.
