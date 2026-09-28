# Передача в задачу дизайна и Figma

Дата: 28.09.2026. Статус: готово к выполнению в отдельной дизайн-задаче.

## Цель следующей задачи

Создать кликабельный low-fidelity прототип mobile-first paper MVP и минимальной desktop-админки на основе уже принятых решений. Прототип должен проверить структуру, тексты, состояния и последствия действий до high-fidelity и frontend-разработки.

## Источники в порядке чтения

1. [Утверждённый дизайн-бриф](33_approved_design_brief.md).
2. [Карта экранов и состояний](34_screen_and_state_map.md).
3. [EN/RU тексты ключевого пути](35_bilingual_low_fidelity_flow.md).
4. [Выбор бесплатного Figma kit](36_figma_kit_selection.md).
5. [Двуязычная основа](29_bilingual_product_language.md).
6. [ADR-0010](decisions/0010_design_direction_and_paper_mvp.md) и [ADR-0011](decisions/0011_shadow_controls_rating_admin_and_ui_foundation.md).

При конфликте действующие ADR имеют приоритет. Неподтверждённые wallet/API возможности в макетах не обещаются.

## Результаты

1. Figma page `00 Cover and decisions` со ссылками на ADR, статусом paper и атрибуцией kit.
2. Page `01 Foundations` с цветами, типографикой, spacing, radius, grids и EN/RU правилами.
3. Page `02 Components` с использованными вариантами и состояниями.
4. Page `03 Mobile flow EN`.
5. Page `04 Mobile flow RU`.
6. Page `05 State library` для loading, empty, stale, partial, unknown, error и закрытия.
7. Page `06 Admin desktop`.
8. Page `07 Prototype` с кликабельным основным путём и обязательными ответвлениями.
9. Page `08 Review notes` с открытыми визуальными вопросами, без повторного открытия продуктовых решений.

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

### Шаг 4. Админка

Собрать desktop Overview и путь инцидента:

`Overview → Incident queue → Incident detail → Reconciliation result → Audit log`.

Дополнительно показать `Users → User detail → Shadow session`. Не проектировать ручную торговлю, вывод или доступ к ключам.

### Шаг 5. Двуязычная проверка

Основной путь создаётся на English и Russian. Проверяются 320, 360 и 390 px, расширение строк, увеличение текста до 200%, locale formatting и сохранение состояния при смене языка.

### Шаг 6. Совместная проверка

Основатель и коллега проходят прототип без объяснений. Фиксируются только наблюдаемые затруднения: где остановились, что поняли иначе, какое действие не нашли и какой текст истолковали неверно.

## Что нельзя решать в дизайне самостоятельно

- название и логотип продукта;
- численные значения risk presets;
- конкретный способ регистрации email/social/passkey;
- реальные wallet permissions, funding и withdrawal;
- live GEO/eligibility flow;
- неподтверждённые возможности API;
- расширение scope на light theme, WhatsApp, email, web push, агентский кабинет или подписку.

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
