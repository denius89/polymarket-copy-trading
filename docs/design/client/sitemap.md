# Карта клиентского интерфейса

Исходная карта от **12.10.2026**, дополнение Final от **16.10.2026**. [Визуальная карта в Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2113-60630) находится на существующей странице «00 · Начать здесь», внутри [карты и таблицы 4 версий](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1664-2). Это одна информационная архитектура для RU/EN и mobile/desktop. Точные узлы и статус хранятся рядом в [sitemap.json](sitemap.json).

**Дополнение 16.10.2026 для Final:** историческая таблица ниже оставлена как карта исходной структуры. Рабочие страницы клиентского прототипа: [RU mobile](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2477-528), [EN mobile](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-2), [RU desktop](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2477-529), [EN desktop](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-3). Для ручной паузы/возобновления mobile используйте RU `2865:2966`/`2865:3095` и EN `2870:186643`/`2870:186772`; у каждой ветки собственные согласованные позиции и события. Точные проверки и desktop IDs — в [актуальной сверке](final-client-release-review-2026-10-16.md). Это дополнение не переписывает старые узлы в `sitemap.json`; при реализации первичны Final-страницы и новая сверка.

Каталоги ручной сессии отделены от первого запуска: mobile RU `2889:143739`, mobile EN `2892:3070`; desktop RU пауза/активно `2906:168747`/`2911:171729`, desktop EN `2901:49669`/`2906:156915`. Каждый возвращает через локальный профиль к своему Home. Вспомогательные общие шаблоны не задают состояние сессии для реализации.

## Как читать

1. **Первый вход и новая сессия:** знакомство → трейдеры → профиль трейдера → настройка → проверка → вход → запуск → пустая главная новой сессии. Визуальная схема показывает ключевые экраны; вход и запуск детализированы в [117](../../117_user_interface_technical_specification_2026-10-09.md).
2. **Подготовленный пример:** отдельное действие «Открыть пример» ведёт к активному демонстрационному состоянию. Оно не создаёт и не возобновляет новую пользовательскую сессию.
3. **Основная навигация активного состояния:** Главная, Трейдеры, Позиции, Активность. Заявки и операции раскрываются из Активности или контекста. Средства, помощь/поддержка, профиль/настройки доступны из шапки и контекста.

## Проверенные экранные якоря

Порядок ссылок в строке: Mobile RU, Mobile EN, Desktop RU, Desktop EN. Это репрезентативные экраны, а не полный список состояний.

| Экран | Ветка | Узлы Figma |
| --- | --- | --- |
| Знакомство | firstRun | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=333-533) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=333-65) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=955-3790) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=955-18385) |
| Каталог трейдеров | firstRun | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1839-31252) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1839-45683) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1839-52340) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1839-53961) |
| Профиль трейдера | firstRun | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1839-32467) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1839-46899) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1839-52618) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1839-54460) |
| Настройки копирования | firstRun | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-4275) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-9184) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-13057) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-16861) |
| Проверка перед запуском | firstRun | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-4316) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-9225) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-13097) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1616-6998) |
| Главная | preparedExample | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=888-1701) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-1754) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9074) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9713) |
| Позиции | activeExample | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=888-1833) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-1890) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9162) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9801) |
| Заявки | activeExample | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=888-1866) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-1924) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9184) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9823) |
| События | activeExample | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=888-1899) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-1958) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9206) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9845) |
| Средства | activeExample | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=888-1932) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-1992) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9228) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9867) |
| Помощь | activeExample | [mobileRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=888-2064) · [mobileEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-8461) · [desktopRu](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9316) · [desktopEn](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=905-9955) |

Полная инвентаризация состояний: [117 §3](../../117_user_interface_technical_specification_2026-10-09.md), [JSON-инвентарь](../../qa/117_user_interface/figma-screen-inventory.json). Семантические web-адреса в 117 §2 остаются **предложением для разработки**, не подтверждением реализованного маршрутизатора или бизнес-правила. Карта не включает админку, архив, будущие/live-функции и все 613 экранных состояний.

## Проверка и обновление

12.10.2026: карта визуально просмотрена в Figma. Все **44** URL-реакции табличных ссылок проверены по существованию цели. Восемь ссылок каталога и профиля в первом входе исправлены: теперь ведут на соответствующие first-run экраны четырёх версий; остальные 36 сохранены. Проверка существования узла не равна ручному прохождению прототипа. Present не выполнен: Computer Use не получил доступ к Figma.

При изменении пользовательского пути обновлять визуальную карту, точные ссылки четырёх версий, этот файл, JSON и [журнал проекта](../../PROJECT_STATE.md) в одном пакете. Не превращать текст или реакцию макета в новое правило без решения владельца. Админка ведёт свою карту отдельно.
