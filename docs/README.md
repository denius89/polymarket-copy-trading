# Документация проекта

Срез навигации: **19 октября 2026**. Проект находится на этапе дизайна и подготовки; приложение и реальные операции не реализованы. Исторические отчёты сохраняют дату и границы своих проверок.

## Начать здесь

| Задача | Основной материал |
| --- | --- |
| Что делаем сейчас | [ROADMAP](ROADMAP.md) |
| Последние изменения и история | [PROJECT_STATE](PROJECT_STATE.md) |
| Согласованные правила | [Бизнес-логика MVP](MVP_BUSINESS_LOGIC.md), [ADR](decisions/README.md) |
| Все документы, включая ранние | [Полный каталог](DOCUMENT_INDEX.md) |
| Ветки, PR и локальные материалы | [Уборка репозитория 19.10.2026](REPOSITORY_MAINTENANCE_2026-10-19.md) |

## Интерфейсы и передача в разработку

| Область | Материалы |
| --- | --- |
| Клиентские Final-экраны | [Карта экранов и актуальные якоря](design/client/sitemap.md), [handoff](../design/client-ui-kit/HANDOFF.md) |
| Клиентский UI kit | [Каталог](../design/client-ui-kit/README.md), [правила применения](../design/client-ui-kit/USAGE.md) |
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

[CONTRIBUTING](../CONTRIBUTING.md) · [безопасность](../SECURITY.md) · [карта хранения и состояние PR](REPOSITORY_MAINTENANCE_2026-10-19.md). Номера исторических документов и старые ссылки сохранены.
