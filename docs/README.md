22.10.2026 — [Таблица пользователей и рабочая карточка](design/admin/users-workspace-2026-10-22/README.md): список с денежными колонками, отдельный вымышленный снимок кошельков, внутренние разделы клиента, прежние настройки и ролевые переходы. Paper Alpha 0%; бюджет не является балансом. Ссылки существующих корней сохранены. Только дизайн; результаты ограниченной проверки — в пакете.

22.10.2026 — [Контекст сотрудника, профиль и назначение роли](design/admin/navigation-assignment-2026-10-22/README.md): Меню и переходы сохраняют сотрудника и рабочее назначение; профиль всех ролей использует согласованную компоновку, личные данные, защиту и свои сессии. Назначение роли: подготовка → проверка → подтверждение. Карта 0.34: 884 пары /900 корней на язык, UI kit 0.4.21. Только дизайн и подготовленные значения; результаты и границы проверки — в пакете.

21.10.2026 — [Собственный аккаунт всех ролей](design/admin/account-self-service-2026-10-21/README.md): Завершены собственные аккаунты всех ролей в согласованной компоновке: черновики личных данных, защита и свои сессии, сохранение состояния RU/EN. Владелец A дополнен на прежних маршрутах; для остальных контекстов — 466 внутренних состояний. Восстановление открывается отдельно от рабочей админки. Карта 0.33: 884 пары /900 корней на язык, UI kit 0.4.21. Только дизайн и подготовленные значения, без реальной авторизации.

21.10.2026 — [Исправления понятности UX01–UX09](design/admin/intuitiveness-fixes-2026-10-21/README.md): получатель VIP, проверка полной выплаты, явный учебный сотрудник, независимые статус и ответ, предметные подсказки и свои права. RU/EN и выбранные ручные цепочки проверены. 1788 корней, карта 0.32, набор компонентов 0.4.21; новых корневых экранов нет. Справочник: 27 уточнённых карточек, все 878 карточек и 1804 ссылки сохранены. Это исправления затронутого дизайна, не общая приёмка продукта.

# Документация проекта

**Текущий приоритет по поручению владельца 19.10.2026: закончить клиентские интерфейсы и админку. Дальнейший технический разбор/исследования и переход к реализации остановлены.** [Точка остановки и отложенный план 138](138_interfaces_first_and_deferred_technical_plan_2026-10-19.md) сохраняют решения, результаты и порядок продолжения. Технические «следующие шаги» в прежних записях ниже — backlog после интерфейсного этапа, не текущая команда к выполнению. Профили остаются выключенными.

Срез навигации: **19 октября 2026**. Проект находится на этапе дизайна и подготовки; приложение и реальные операции не реализованы. Исторические отчёты сохраняют дату и границы своих проверок.

## Начать здесь

| Задача | Основной материал |
| --- | --- |
| Что делаем сейчас | [ROADMAP](ROADMAP.md) |
| Последние изменения и история | [PROJECT_STATE](PROJECT_STATE.md) |
| Согласованные правила | [Бизнес-логика MVP](MVP_BUSINESS_LOGIC.md), [ADR](decisions/README.md) |
| Сверка правил и актуальных макетов | [Бизнес-аудит 19.10.2026: замечания, открытые решения и evidence](qa/business-logic-2026-10-19/README.md) |
| Проверка активации · пока ни один | [Аудит 137](137_profile_activation_audit_2026-10-19.md), [replay/clock/fee evidence](qa/profile-activation-2026-10-19/README.md) |
| Рыночные CLOB-профили · контракт принят, активация blocked | [ADR-0059](decisions/0059_clob_market_profiles_freshness_price_and_fees.md), [136](136_venue_market_profiles_and_quote_gates_2026-10-19.md), [JSON](policies/paper-clob-market-profiles-v1.json), [наблюдения/QA](qa/venue-profiles-2026-10-19/README.md) |
| Числовые параметры paper MVP · принято | [ADR-0058](decisions/0058_paper_mvp_numeric_settings_policy.md), [политика 130](130_paper_copy_settings_numeric_policy_proposal_2026-10-18.md), [JSON](policies/paper-mvp-settings-v1.json), [проверка](qa/numeric-policy-2026-10-19/README.md) |
| BL-08: лимиты и причина отказа · принято | [ADR-0057](decisions/0057_effective_limits_and_rejection_reason_priority.md), [контракт 135](135_effective_limits_and_rejection_reasons_2026-10-19.md), [проверка](qa/effective-limits-reasons-2026-10-19/README.md) |
| Бюджет/настройки активной сессии · принято | [ADR-0056](decisions/0056_active_session_budget_flows_and_settings_revisions.md), [контракт 134](134_active_session_budget_and_settings_versions_2026-10-19.md), [проверка](qa/session-settings-revisions-2026-10-19/README.md) |
| Точная арифметика частей · принято | [Контракт 133](133_exact_position_arithmetic_contract_2026-10-19.md), [принятый ADR-0055](decisions/0055_exact_rational_position_attribution.md), [проверка](qa/exact-position-arithmetic-2026-10-19/README.md) |
| Поздние исполнения, продажи и округление | [ADR-0052](decisions/0052_late_fills_follow_ownership_and_exit_target.md), [ADR-0053](decisions/0053_serialize_sells_and_preserve_exit_targets.md), [ADR-0054](decisions/0054_round_down_without_limit_bypass_and_keep_dust.md); [модель и предел проверки](qa/late-fill-sell-rounding-2026-10-19/README.md) |
| Части позиции и завершение | [ADR-0049](decisions/0049_position_parts_cost_and_manual_sales.md), [ADR-0050](decisions/0050_shadow_assessment_boundary_and_exit_only_tail.md), [ADR-0051](decisions/0051_strict_session_completion_and_paper_reset.md); [исходное предложение](131_position_parts_and_session_completion_proposal_2026-10-19.md) с границей принятия |
| Все документы, включая ранние | [Полный каталог](DOCUMENT_INDEX.md) |
| Как хранить, публиковать и завершать задачи | [Карта и правила репозитория](REPOSITORY_GUIDE.md), [каталог внешних архивов](storage/catalog.json) |
| История уборки и восстановление | [Проверенный срез 19.10.2026](REPOSITORY_MAINTENANCE_2026-10-19.md) |

## Интерфейсы и передача в разработку

| Область | Материалы |
| --- | --- |
| Клиентские Final-экраны | [Карта экранов и актуальные якоря](design/client/sitemap.md), [handoff](../design/client-ui-kit/HANDOFF.md) |
| Клиентский UI kit | [Каталог](../design/client-ui-kit/README.md), [правила применения](../design/client-ui-kit/USAGE.md) |
| Вход по ADR-0048 и исправления аудита | [Четыре Final-версии, пояснение EN mobile и проверки](design/client/adr48-entry-fixes-2026-10-19/README.md) |
| Ручные настройки копирования | [Handoff](design/client/manual-copy-settings-2026-10-18.md), [предложение контракта 129](129_copy_settings_contract_proposal_2026-10-18.md) |
| Десктопное знакомство | [Сцены и веб-превью](design/client/desktop-introduction-2026-10-18.md) |
| Единый первый вход | [Принятый ADR-0048](decisions/0048_unified_registration_and_first_entry.md); реализация и обновление прототипов остаются открытыми |
| Лендинг | [Первый экран v2](design/landing/hero-2026-10-19/v2/README.md), дизайн на согласование |
| Клиентская техническая спецификация | [117](117_user_interface_technical_specification_2026-10-09.md) |
| Админка | [Стиль и порядок работы](design/admin/STYLE_GUIDE.md), [техническая спецификация 115](115_admin_console_technical_specification_2026-10-09.md), [сверка с клиентом 116](116_admin_user_interface_consistency_2026-10-09.md) |
| Последняя проверка админки | [Роли и сквозные сценарии](design/admin/role-scenario-pass-2026-10-19/README.md), [повторное чтение клиентских состояний](design/admin/role-scenario-verification-2026-10-19/README.md) |

[Открыть Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3-2). Макет, структурная проверка и работающая реализация имеют разные статусы; полный перечень незакрытых проверок находится в соответствующем handoff.

## API площадок

| Площадка | Справочник | Дата свидетельств |
| --- | --- | --- |
| Polymarket | [README и разделы](api/polymarket/README.md), [проверки и ограничения](api/polymarket/verification.md) | 06.10.2026 |
| Limitless | [README и разделы](api/limitless/README.md), [проверки и ограничения](api/limitless/verification.md) | 06.10.2026 |

Перенос справочников в эту ветку не является новой проверкой API. Перед использованием меняющихся требований сверять официальные источники. Интеграции и реальные операции требуют отдельных gates.

## Работа с репозиторием

[CONTRIBUTING](../CONTRIBUTING.md) · [безопасность](../SECURITY.md) · [действующая карта хранения и рабочий цикл](REPOSITORY_GUIDE.md) · [проверка структуры](qa/repository-structure-review-2026-10-19.md). Номера исторических документов и старые ссылки сохранены.

## Проектные навыки и Copy Score

- [Каталог S01–S23](ai-system/CATALOG.md), [учебные пакеты](ai-system/learning/S01.md), [реестр знаний](ai-system/knowledge/GUIDE.md), [статусы и доказательства проверок](ai-system/FIRST_BATCH.md).
- [Исследования Copy Score: единый вход](../research/TRADER_SCORE_README.md), [последняя перепроверка](../research/trader-score-review-2026-10-18/README.md), [реестр крупных исходных файлов](../research/DATA_ARCHIVE_2026-10-19.json).

Публикация переносит существующие материалы. Она не утверждает новую формулу рейтинга и не означает полную приёмку навыков или продукта.
