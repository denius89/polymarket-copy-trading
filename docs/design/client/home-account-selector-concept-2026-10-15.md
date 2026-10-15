# Выбор счёта на Главной: принятое решение

Дата: 15 октября 2026 года. Область: клиентские Final RU/EN, mobile/desktop. Админка не менялась.

Текущий paper MVP показывает один виртуальный демо-счёт и **не показывает переключатель**. Рабочие Главные: [RU desktop](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-53), [EN desktop](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2504-3), [RU mobile](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2498-26193), [EN mobile](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2502-17237). На desktop стоимость демо, структура счёта, копирование, предупреждение и позиции подписаны по смыслу; цветовая шкала имеет текстовую легенду. RU/EN и mobile/desktop сохраняют одинаковую продуктовую логику, хотя компоновка различается.

Для **будущего** состояния с несколькими реально доступными счетами принят выбор внутри финансовой карточки. Нейтральная вторичная кнопка «Сменить счёт» / “Switch account” не конкурирует с главным действием. Desktop раскрывает список внутри карточки, mobile — нижнюю панель. В раскрытом desktop-виде список целиком закрывает показатели карточки, чтобы сумма или шкала не выглядели обрезанными. Смена счёта меняет только финансовую карточку; остальные блоки явно остаются демо-контекстом. Демо и реальные суммы не складываются. Неподключённый Limitless отсутствует в списке; условные суммы Polymarket относятся только к будущему сценарию.

| Версия | Демо | Polymarket | Открытый выбор |
|---|---|---|---|
| RU desktop | [Карточка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2679-4943) | [Карточка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2679-5078) | [Демо](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2681-5031) · [Polymarket](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2682-5075) |
| EN desktop | [Card](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2690-4840) | [Card](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2690-4986) | [Demo](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2690-5132) · [Polymarket](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2690-5272) |
| RU mobile | [Карточка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2685-137594) | [Карточка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2685-137748) | [Демо](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2685-137902) · [Polymarket](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2685-138048) |
| EN mobile | [Card](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2685-2970) | [Card](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2685-3125) | [Demo](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2685-3280) · [Polymarket](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2685-3427) |

Все будущие кадры выбора счёта названы в Figma `Final future`. Кнопка открытия, выбор Демо/Polymarket, закрытие мобильной панели и пункт «Все счета» / “All accounts” связаны в прототипе; последний ведёт в соответствующий Final-экран средств. Зона нажатия мобильной кнопки и закрытия панели не меньше 44 px. Эти состояния не подключены к текущему paper-маршруту.

Исходные эксперименты с вкладками на уровне всей страницы остаются историей сравнения и не являются утверждённым решением. Правила 0/1/N счетов и незавершённых сессий описаны в [карте состояний](home-account-states-2026-10-15.md).
