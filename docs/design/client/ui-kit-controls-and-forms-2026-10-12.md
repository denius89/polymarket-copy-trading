# Клиентский UI kit: исправление контролов и форм

Дата: **12.10.2026**. По шести скриншотам владельца исправлены только Controls и Patterns на [единой странице Client UI kit](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1976-2). Админка, продуктовые экраны, prototype reactions и бизнес-правила не менялись.

| Видимый дефект | Причина и исправление |
| --- | --- |
| [Icon button](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1978-795) выглядел как checkbox, иконки внутри 44 px кнопок сидели высоко. | Шесть мастеров Client/Icon имели геометрию 24×48 вместо 24×24. Они приведены к 24×24; пять обычных состояний используют нейтральную Info-иконку, Loading сохраняет отдельный spinner. Сам target остаётся 44×44, INSTANCE_SWAP работает. |
| [Touch switch](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38469) был прижат к левому краю невидимой области касания, disabled off почти исчезал. | В шести 96×60 вариантах Shared/Switch 48×44 центрирован на x=24; disabled opacity повышена до 0,6. Shared/Switch master и его IDs сохранены. |
| В [source guide Icon button](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2105-5923) подпись следующего Checkbox выглядела прилипшей к панели. | Источники Controls ниже панели сдвинуты на 32 px; между панелью и Checkbox set теперь 56 px. Компоненты не дублировались. |
| [Feedback form](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1980-480) и [Support form](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1980-391) показывали сжатое пустое поле и визуально выступающую заливку. | В мастере [Client/Textarea](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1978-941) многострочная область ошибочно имела высоту Hug: пустой текст сжимал её с 72 до 48 px. Установлен фиксированный минимум 72 px, ширина вариантов 360 px; формы и review boards выросли автоматически, сохранив отступы. |

Итоговая геометрия: Textarea 360×182 (4 состояния), Support Draft/Error 400×416/444, Feedback 400×304. Шесть Icon button variants — 44×44; шесть Touch switch variants — 96×60. Дефолтная иконка Info не меняет назначение кнопки: в продукте icon задаётся через swap по конкретному действию.

Проверены PNG-рендеры шести затронутых обзоров/панелей, размеры мастеров, 228 текущих нативных instances и отсутствие потерянных main-component links. Ручной Present не выполнялся; это библиотечная правка, а не проверка маршрутов. При реализации отдельно проверить клавиатуру, 200% text zoom, RU/EN строки и адаптивность. Текущий реестр — [manifest.json](../../../design/client-ui-kit/manifest.json), правила — [USAGE.md](../../../design/client-ui-kit/USAGE.md), границы QA — [qa.json](../../../design/client-ui-kit/qa.json).
