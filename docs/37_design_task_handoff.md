# Передача в задачу дизайна и Figma

Дата: 29.09.2026. Статус: обновлённое задание следующего Figma-цикла.

## Цель следующей задачи

Обновить кликабельный прототип полноценного responsive paper MVP: mobile EN/RU, самостоятельные desktop-композиции, виртуальный баланс, recovery states и desktop-админка. Прототип должен проверить структуру, тексты, состояния и последствия действий до high-fidelity и frontend-разработки.

## Источники в порядке чтения

1. [Утверждённый дизайн-бриф](33_approved_design_brief.md).
2. [Карта экранов и состояний](34_screen_and_state_map.md).
3. [EN/RU тексты ключевого пути](35_bilingual_low_fidelity_flow.md).
4. [Выбор бесплатного Figma kit](36_figma_kit_selection.md).
5. [Двуязычная основа](29_bilingual_product_language.md).
6. [Benchmark betting, casino и trading](40_cross_industry_product_logic_benchmark.md).
7. [Стандарт интерфейса и frontend](41_product_design_and_frontend_standards.md).
8. [ADR-0010](decisions/0010_design_direction_and_paper_mvp.md), [ADR-0011](decisions/0011_shadow_controls_rating_admin_and_ui_foundation.md) и [ADR-0012](decisions/0012_paper_mvp_defaults.md).

При конфликте действующие ADR имеют приоритет. Неподтверждённые wallet/API возможности в макетах не обещаются.

## Результаты

1. Figma page `00 Cover and decisions` со ссылками на ADR, статусом paper и атрибуцией kit.
2. Page `01 Foundations` с цветами, типографикой, spacing, radius, grids и EN/RU правилами.
3. Page `02 Components` с использованными вариантами и состояниями.
4. Page `03 Mobile flow EN`.
5. Page `04 Mobile flow RU`.
6. Page `05 Desktop user` с каталогом, профилем, Copy Ticket, главной, сессией, активностью, результатом и paper balance.
7. Page `06 State library` для loading, empty, stale, partial, unknown, error и закрытия.
8. Page `07 Admin desktop`.
9. Page `08 Prototype` с кликабельным основным путём и обязательными ответвлениями.
10. Page `09 Review notes` с открытыми визуальными вопросами, без повторного открытия продуктовых решений.

## Порядок работы

### Шаг 1. Проверка kit

Продублировать Obra shadcn/ui Community Edition, проверить точную лицензию и версию, записать атрибуцию. Собрать тестовый набор из шести сценариев. Если kit не проходит EN/RU, responsive или state test, повторить ту же проверку с Sitsiilia после подтверждения лицензии Figma-файла.

### Шаг 2. Foundations

Создать собственные variables и styles поверх kit:

- dark graphite surfaces;
- purple accent;
- semantic success/warning/danger/info;
- text, muted text, borders, focus and disabled;
- spacing, radius, typography and elevation;
- modes `Dark` и подготовленный `Light`, но макеты первого выпуска только в Dark.

Не отвязывать используемые экземпляры от компонентов без необходимости. Имена tokens и variants должны быть пригодны для будущего кода.

### Шаг 3. Low-fidelity mobile

Собрать основной путь:

`Language → Intro → Traders → Trader profile → Budget → Risk limits → Account → Review → Active shadow → Activity → Result`.

Обязательные ответвления:

- недостаточный бюджет;
- stale/пропущенное действие;
- partial action;
- unknown/reconciliation;
- Pause → Resume;
- отключить и оставить позиции;
- Close → partial/failed → resolved;
- 14 дней → недостаточно данных.

### Шаг 4. Desktop user

Собрать самостоятельные desktop-композиции каталога, профиля, настройки, review, главной, активной сессии, позиций/активности, результата и paper balance. Использовать боковую навигацию, постоянную Copy setup summary там, где она полезна, и detail drawer для таблиц. Не растягивать мобильные карточки.

### Шаг 5. Админка

Собрать desktop Overview и путь инцидента:

`Overview → Incident queue → Incident detail → Reconciliation result → Audit log`.

Дополнительно показать `Users → User detail → Shadow session`. Не проектировать ручную торговлю, вывод или доступ к ключам.

### Шаг 6. Двуязычная проверка

Основной путь создаётся на English и Russian. Проверяются 320, 360 и 390 px, расширение строк, увеличение текста до 200%, locale formatting и сохранение состояния при смене языка.

### Шаг 7. Совместная проверка

Основатель и коллега проходят прототип без объяснений. Фиксируются только наблюдаемые затруднения: где остановились, что поняли иначе, какое действие не нашли и какой текст истолковали неверно.

## Что нельзя решать в дизайне самостоятельно

- название и логотип продукта;
- реальные wallet permissions, funding и withdrawal;
- live GEO/eligibility flow;
- неподтверждённые возможности API;
- расширение scope на light theme, WhatsApp, email, web push, агентский кабинет или подписку.

Defaults ADR-0012 используются без переоткрытия: $200, одна активная сессия, 10%/15%/30 секунд, passwordless email, 7/30/90 дней, добровольный Telegram и 60-минутное напоминание. Выбор конкретного auth-провайдера, live stale thresholds и модель partial fill остаются техническими задачами и не меняются в Figma самостоятельно.

Эти места отмечаются нейтральными placeholders или открытыми заметками, если они нужны для композиции.

## Gate завершения

Low-fidelity этап завершён, когда:

- все результаты и страницы из этого документа существуют в Figma;
- основной путь и ответвления кликабельны;
- EN/RU и ключевые состояния проверены;
- kit и атрибуция подтверждены;
- основатель и коллега прошли прототип;
- замечания внесены без изменения принятых продуктовых решений;
- после повторной проверки отдельно принято решение о high-fidelity.

Frontend не начинается автоматически после завершения этого handoff.
