# Настройки демо-копирования и знакомство: результат 05.10.2026

Уточнение того же дня: [ADR-0017](decisions/0017_copy_size_fixed_or_percent_of_trader_trade.md) добавил процент от суммы сделки трейдера как второй способ. Описанные ниже экраны фиксируют состояние до этого уточнения; $20 больше не единственный допустимый способ.

## Что принято и изменено

Референсы Polyfox использованы для структуры, а не для копирования визуального стиля, рейтинга или обещаний доходности. В существующей тёмной системе `shadow` пересобраны мобильные и десктопные настройки копирования: выбранный трейдер и demo-режим, компактные пары «параметр — значение», отдельная проверка перед запуском и редактирование индивидуальных лимитов. Сумма новой копии в первом paper-сценарии фиксирована; текущее значение **$20** при виртуальном бюджете **$200**. Предел одной позиции **$20**, новых покупок в день **$30**, возраст сигнала **30 секунд**.

В индивидуальных лимитах Momentum Fox выделены выбранные значения. Знакомство теперь даёт два ясных пути: настроить демо или посмотреть трейдеров. Сохранены RU/EN и mobile/desktop. На EN desktop добавлен отсутствовавший экран проверки настроек. В каталоге указан размер demo-набора, в профиле трейдера исторический результат отделён от исторической симуляции; карточки с длинным объяснением профиля убраны из первого слоя.

Продуктовое правило и конфликт со старым proportional sizing записаны в [ADR-0014](decisions/0014_fixed_paper_copy_size_and_settings_scope.md). Старые материалы остаются историей решений.

## Ссылки для прохода

| Версия | Начало | Настройки | Проверка | Лимиты Momentum Fox |
|---|---|---|---|---|
| RU mobile | [старт](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=33-2) | [настройки](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-4275) | [проверка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-4316) | [лимиты](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=965-4984) |
| EN mobile | [старт](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=29-2) | [settings](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-9184) | [review](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-9225) | [limits](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=965-18165) |
| RU desktop | [старт](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=205-2) | [настройки](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-13057) | [проверка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-13097) | [лимиты](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=965-18321) |
| EN desktop | [старт](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=186-2) | [settings](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=949-16861) | [review](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1616-6998) | [limits](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=965-18478) |

[Единая стартовая страница четырёх версий](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3-2).

## Проверка и границы

Визуально проверены setup/review, индивидуальные лимиты, профиль и примеры знакомства; проверены назначения основных переходов. Это Figma-прототип на синтетических данных, не работающее торговое приложение. Перед кодовой реализацией отдельно определить правила дневного сброса, ожидающих операций, комиссии, конкурентных сигналов, версий настроек, источников и методики исторической симуляции. Полная приёмка всех остальных экранов файла не заявляется.
