# Выбор бесплатного Figma kit

Дата: 28.09.2026. Статус: read-only shortlist и рекомендация для пилота. Ничего не приобреталось и не скачивалось.

## Решение для пилота

Первым кандидатом выбран **Obra shadcn/ui Community Edition 2.x**. Официальная страница shadcn/ui называет его наиболее полным бесплатным community kit с полным набором компонентов и системой тем. Документация Obra описывает нужные компоненты, light/dark variables и лицензию CC BY 4.0, которая допускает коммерческое использование и изменение при сохранении атрибуции.

Пилот не означает окончательного принятия. Сначала нужно продублировать Community file в Figma, проверить шесть проектных сценариев, локализацию и responsive behavior, затем записать точную версию и атрибуцию.

## Сравнение

| Кандидат | Сильные стороны | Ограничения и проверка | Решение |
|---|---|---|---|
| Obra shadcn/ui Community Edition | полный бесплатный shadcn-набор; Card, Chart, Data Table, Dialog, Drawer, Field, Slider, Table, Badge; light/dark variables; ясная CC BY 4.0 | Community ограничен стилем Nova; автоматический CSS/token export относится к Pro; нужна атрибуция | основной пилот |
| Sitsiilia shadcn/ui | официальный список отмечает как бесплатный, структурированный и регулярно поддерживаемый; публичный registry/skill содержит широкое покрытие и code recipes | лицензию именно Figma Community file и его фактический component inventory не удалось подтвердить через доступные первичные страницы; проверить внутри Figma | резерв после проверки |
| shadcncraft Free Starter | native Figma variables, восемь shadcn styles, dark/light, matching React и импорт тем | бесплатный scope на разных страницах описан неодинаково; proprietary license ограничивает распространение Figma/source, что повышает риск для публичного проекта | не использовать первым |
| Pietro Schirano shadcn design companion | бесплатный кандидат из официального списка, заявлено соответствие коду | не подтверждены актуальная лицензия, variables/dark и покрытие сложной админки | не использовать без ручной проверки |

## Покрытие Obra для проекта

| Сценарий | Компоненты основы |
|---|---|
| Карточка трейдера | Card, Avatar, Badge, Chart, Button |
| Бюджет | Input, Slider, Radio Group, Tabs, Alert |
| Risk controls | Field, Switch, Select, Alert, Tooltip |
| Подтверждение запуска | Dialog или mobile Drawer, Data List, Button |
| Активный shadow | Progress, Chart, Tabs, Alert, Badge |
| Инциденты админки | Data Table, Table, Badge, Pagination, Combobox |

Покрытие компонента не означает готовность сценария. Неизвестный статус, частичное закрытие, причина пропуска и безопасные действия проектируются как собственные составные компоненты.

## План проверки в Figma

1. Продублировать точную Community Edition file и сохранить ссылку, версию и дату.
2. Проверить license panel и записать атрибуцию Obra Studio в обложке Figma и будущем `NOTICE` репозитория.
3. Создать проектные variables для графита, фиолетового акцента, текста, границ и семантических состояний.
4. Собрать шесть сценариев из таблицы без detached components.
5. Проверить English/Russian, расширение текста, 320/360/390 px и desktop admin.
6. Проверить focus, disabled, loading, empty, stale, partial, unknown и error variants.
7. Сопоставить component/variant/property names с будущими shadcn/ui файлами и design tokens.
8. После проверки принять kit либо повторить тот же тест с Sitsiilia.

## Правила публичного репозитория

- Не загружать сторонний Figma source в GitHub, если лицензия прямо этого не разрешает.
- В репозитории хранить наши tokens, спецификации, ссылки и обязательную атрибуцию.
- Не копировать платные blocks, templates или plugin assets.
- Любое изменение кандидата сохраняет shadcn/ui foundation из ADR-0011 и повторяет шесть тестовых сценариев.

## Источники

- [Официальный список Figma resources shadcn/ui](https://ui.shadcn.com/docs/figma)
- [Obra documentation](https://shadcn.obra.studio/documentation)
- [Obra components](https://shadcn.obra.studio/documentation/components)
- [Obra colors and variables](https://shadcn.obra.studio/documentation/colors)
- [Obra license](https://shadcn.obra.studio/license)
- [Sitsiilia public shadcn Figma skill](https://github.com/Sitsiilia/shadcn-figma-skill)
- [shadcncraft free kit](https://shadcncraft.com/docs/free)
- [shadcncraft variables](https://shadcncraft.com/docs/figma/variables)
- [shadcncraft license](https://shadcncraft.com/license)

## Gate выхода

Кандидат становится рабочим Figma kit только после успешной проверки всех шести сценариев, EN/RU и лицензии. До этого разрешены low-fidelity wireframes на нейтральных компонентах и проектных tokens.
