# Админка · пакет 09 · Данные и рейтинг

13.10.2026 · дизайн на совместную вычитку; API/backend/frontend/live не начинаются.

[RU прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2395-34055&starting-point-node-id=2395-34055&scaling=scale-down) · [EN прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2395-113367&starting-point-node-id=2395-113367&scaling=scale-down)

## Область
41 RU + 41 EN функциональных состояний: обзор, сборщики Polymarket/Limitless, настройки/validation/preview/apply/unknown, pause каталога, внутренний валидатор и его настройки, полные адреса и четыре результата lookup, методика рейтинга/ошибка суммы весов/impact/publication/history/restore, processing results R-1/R-2, диагностика профиля и ограничения доступа. Новых страниц и итерационных веток Figma нет.

Действующая методика — ADR-0011 (30/25/25/20, минимум30дней/20действий); рейтинг 0–100 не прогноз дохода. R-2 с минимумом25 — demo для вычитки, не новое принятие production правил. Численные настройки источников/freshness и NormalizationMethod implementation также не утверждены.

## UI kit и данные
UI kit0.4.18: Admin/Data sections, 5Active × RU/EN=10вариантов, на основе существующих Admin buttons. Всего26 наборов /158 вариантов. Новые связанные Data result row/header (колонки 425.6/319.2/319.2, полный адрес в 14 px), общие поля, метрики, alerts, цвета и Inter; shared grid1440/sidebar248/content1144. Новый entry «Данные и рейтинг» в Management. Client masters не менялись.
DS-DEMO-01:4синтетических профиля; A/C rating eligible R-1, B insufficient, D unavailable. R-2: C теряет rating eligibility по порогу25, оставаясь найденным адресом. Ручное назначение scores отсутствует.
Публикация требует полного готового подтверждённого снимка; до этого клиентский каталог остаётся на предыдущей версии. R-3 restore сохраняет R-1/R-2 и прошлые торговые события.

## Проверка и передача
Структурная и визуальная проверка RU/EN завершены: выходов текста за границы не обнаружено; полные адреса сохраняются в таблицах. Основные RU-сценарии сборщика, валидатора, публикации и восстановления рейтинга пройдены в Present. В финальном Main проверено 383 узла со связями на язык (это не число уникальных сценариев). Доказательства — [QA](qa.json) и 9 PNG в previews/. [Реестр](screen-ledger.json), [контракт и user UI сверка](data-rating-contract.md), [ADR-0044](../../../decisions/0044_data_ingestion_validator_and_rating_controls.md).
Этот пакет — первый проверяемый вертикальный срез настроек, а не окончательная полная API модель. Полный scope/EN/failure/stale/empty/concurrency/recompute pass и права новых команд остаются на совместной вычитке.

Прототип статический, не сохраняет изменения в backend. Начальные вкладки открывают базовый fixture; отдельный result R-2 сохраняет контекст новой методики. Скрипты — журнал сборки, не backup Figma и не runtime-авторизация.

Пакет локальный. GitHub в этом цикле не обновляется. Следующая область — общие incidents/reconciliation и уведомления/feedback; до разработки нужна общая приёмка дизайна.
