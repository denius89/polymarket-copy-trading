# Прогресс low-fidelity дизайна в Figma

Обновлено: 28 сентября 2026 года.

## Результат текущего цикла

Создан отдельный Figma Design-файл: [Controlled Copy Trading — Paper MVP](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T).

В файле уже находятся:

- обложка с четырьмя утверждёнными принципами продукта;
- dark-first foundations: палитра, типографика, spacing и radius;
- локальные Figma variables с WEB code syntax;
- текстовые и effect styles;
- компонент `Button` с вариантами Primary, Secondary, Destructive и Ghost, а также Default и Disabled;
- визуальная проверка обложки, foundations и исправленного Button.

Работа выполнялась по [утверждённому брифу](33_approved_design_brief.md), [карте экранов](34_screen_and_state_map.md), [EN/RU copy](35_bilingual_low_fidelity_flow.md) и [handoff](37_design_task_handoff.md).

## Структура файла

Тариф Figma Starter допускает только три страницы и один mode в каждой коллекции variables. Поэтому исходные разделы 00–08 распределены по трём страницам, а внутри оформляются именованными секциями:

| Страница Figma | Разделы handoff |
|---|---|
| `00 Overview & Foundations` | `00 Cover and decisions`, `01 Foundations` |
| `01 Mobile Flows & States` | `03 Mobile flow EN`, `04 Mobile flow RU`, `05 State library` |
| `02 Components, Admin & Prototype` | `02 Components`, `06 Admin desktop`, `07 Prototype`, `08 Review notes` |

Это ограничение не меняет scope. После перехода на Professional секции можно разнести по отдельным страницам без изменения компонентов или экранов.

## Foundations

Созданы четыре коллекции:

| Коллекция | Mode | Состав |
|---|---|---:|
| `Primitives` | `Value` | 22 цвета |
| `Color` | `Dark` | 22 семантических цвета |
| `Spacing` | `Default` | 11 значений |
| `Radius` | `Default` | 5 значений |

Также созданы девять стилей Inter (`Display`, три heading, два body, `Label`, `Caption`, `Numeric`) и эффект `Elevation/Dialog`. Все семантические цвета связаны с primitives, scopes заданы явно, broken aliases отсутствуют.

Светлая тема остаётся подготовленной спецификацией. Добавить второй mode на текущем Starter-плане нельзя; это не блокирует утверждённый dark-first MVP.

## Проверенный компонент

`Button` содержит восемь вариантов:

- Style: `Primary`, `Secondary`, `Destructive`, `Ghost`;
- State: `Default`, `Disabled`;
- Size: `Medium`, минимальная высота 44 px;
- редактируемое TEXT-свойство `Label`.

Фон, текст, радиусы и padding связаны с variables. После визуальной проверки исправлен fallback primary-цвета; повторный screenshot прошёл проверку.

## Что остановило цикл

После создания foundations и Button Figma MCP вернул лимит вызовов Starter. Операция создания `Status`, `Field` и `Trader Card` не была записана. Проектные данные не потеряны: полный следующий объём закреплён в [manifest](../design/figma-build-manifest.json) и документах 34–37.

## Следующий Figma-сеанс

1. Продолжить с `Status`, `Field`, `Trader Card`, `Session Card`, `Activity Row` и `Confirmation Drawer`.
2. Собрать основной EN flow: Language → Intro → Traders → Profile → Budget → Risk → Account → Review → Active shadow → Activity → Result.
3. Собрать RU-версию теми же компонентами и проверить расширение строк.
4. Добавить state library: loading, empty, stale, partial, unknown/reconciliation, closing, close failed и insufficient data.
5. Собрать desktop admin: Overview → Incident → Reconciliation → Audit log и Users → Session.
6. Соединить обязательные переходы и провести QA на 320/360/390 px и text zoom 200%.

Obra Community Edition остаётся рекомендуемым reference kit, но импорт не является блокером: локальная основа уже совпадает с shadcn-подходом и продуктовой моделью состояний.

## Gate

Frontend-разработка остаётся на паузе. Дизайн-гейт считается закрытым после сборки и совместной проверки EN/RU flow, state library, admin path и обязательных прототипных веток.
