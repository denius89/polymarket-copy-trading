# Прогресс low-fidelity дизайна в Figma

Обновлено: 28 сентября 2026 года.

## Результат цикла

Рабочий файл: [Controlled Copy Trading — Paper MVP](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T).

Тариф команды обновлён до Figma Professional, место владельца — Full. Работа ведётся через официальный Figma connector/plugin Codex. Дополнительный UI-плагин для записи макетов не требуется; Obra Community Edition остаётся визуальным reference kit.

Исходный low-fidelity пакет сохранён как продуктовая схема. После первой проверки дополнительно собран современный интерактивный вариант v2, готовый к совместной проверке основателем и коллегой:

- девять отдельных страниц 00–08;
- dark-first foundations и связанный Light mode;
- локальные variables, text styles и effect style;
- Button, Status, Field и Trader Card;
- 15 мобильных экранов EN и 15 эквивалентных экранов RU;
- 17 обязательных продуктовых состояний;
- шесть desktop-представлений операционной админки;
- 37 основных и ветвящихся переходов;
- отдельная review page с решениями, QA и следующим gate.

## Современный интерактивный прототип v2

Добавлены две отдельные страницы: «09 Modern prototype EN» и «10 Modern prototype RU». Каждая содержит десять экранов основного пути — от первого знакомства до активной shadow-сессии и разбора неопределённого события.

- [Запустить EN-прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=29-3&starting-point-node-id=29%3A3&scaling=scale-down&content-scaling=fixed&page-id=29%3A2)
- [Запустить RU-прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=33-3&starting-point-node-id=33%3A3&scaling=scale-down&content-scaling=fixed&page-id=33%3A2)

В v2 добавлены градиентные продуктовые карточки, графики активности, рейтинг трейдера, slider-представление бюджета, risk toggles, активная dashboard, журнал событий и визуальная timeline для UNKNOWN. Основные CTA используют Smart Animate; нижняя навигация на ключевых экранах имеет отдельные кликабельные зоны.

Работа выполнена по [утверждённому брифу](33_approved_design_brief.md), [карте экранов](34_screen_and_state_map.md), [EN/RU copy](35_bilingual_low_fidelity_flow.md) и [handoff](37_design_task_handoff.md).

## Структура файла

| Страница | Содержимое |
|---|---|
| `00 Cover and decisions` | утверждённые продуктовые принципы |
| `01 Foundations` | цвета, типографика, spacing, radius и режимы |
| `02 Components` | локальные интерактивные компоненты |
| `03 Mobile flow EN` | 15 экранов английского сценария |
| `04 Mobile flow RU` | 15 экранов русского сценария |
| `05 State library` | 17 состояний продукта и восстановления |
| `06 Admin desktop` | обзор, пользователи, инциденты, комиссии и feedback |
| `07 Prototype` | карта двух сценариев и кликабельные переходы |
| `08 Review notes` | зафиксированные решения и следующий gate |
| `09 Modern prototype EN` | современный кликабельный EN-сценарий |
| `10 Modern prototype RU` | локализованный современный RU-сценарий |

## Foundations и компоненты

Сохранены четыре коллекции variables: `Primitives`, `Color`, `Spacing` и `Radius`. В `Color` работают связанные режимы `Dark` и `Light`; dark остаётся режимом MVP по умолчанию. Созданы девять стилей Inter и эффект `Elevation/Dialog`.

Компоненты текущего low-fi:

- `Button`: Primary, Secondary, Destructive, Ghost; Default и Disabled;
- `Status`: Paper, Active, Warning, Error, Info и Paused;
- `Field`: label, value и hint;
- `Trader Card`: имя, источник, показатели и выделенный бюджет.

Составные экраны пока используют эти primitives напрямую. Выделять Session Card, Activity Row, Incident Table и другие крупные блоки в отдельные компоненты следует на high-fidelity этапе после проверки структуры.

## Пользовательский сценарий

Обе локали используют одинаковую последовательность:

`Language → Value → Traders → Trader → Budget → Risk → Account → Review → Active → Activity → Event → Result`.

Дополнительные ветки ведут к Home, управлению сессией, профилю и уведомлениям. Просмотр доступен без аккаунта; регистрация появляется при сохранении и запуске shadow-сессии. Все исполнения симулируются, а интерфейс не обещает заработок.

## State library и админка

State library включает загрузку, пустое состояние, ошибку, устаревшие данные, недоступную площадку, недостаточный бюджет, дневной лимит, старый сигнал, низкую ликвидность, `UNKNOWN`, паузу, закрытие, частичное закрытие, ошибку закрытия, отзыв разрешения, недостаточные данные и готовность к review.

Админка покрывает Overview, Users, User detail, Incident queue, Incident detail с reconciliation/audit log и Fees & feedback. В ней нет ручной отправки сделки, вывода, доступа к ключам или слепого retry.

## Проведённая проверка

- EN и RU экраны визуально просмотрены; длинные русские строки не обрезают основной сценарий.
- Исправлены размеры Field и Trader Card после проверки экземпляров.
- State library, admin, prototype map и review page проверены по screenshot.
- Для EN и RU назначены отдельные prototype starting points.
- `UNKNOWN` блокирует новый риск; остаток после частичного или неудачного закрытия остаётся видимым.

Проверка 320/360 px и text zoom 200% переносится на high-fidelity, где будут утверждены окончательные размеры, responsive rules и production copy.

## Следующий gate

Основатель и коллега открывают именно ссылки «Запустить EN/RU-прототип» выше, проходят сценарии и отмечают только блокирующие изменения. После согласования визуального направления, порядка экранов, формулировок и границ админки можно расширить v2 до полного high-fidelity UI kit. Frontend-разработка остаётся на паузе до отдельного решения.
