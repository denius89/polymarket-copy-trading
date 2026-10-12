# Пакет 01 — v0.1 на вычитку

12.10.2026: на overview добавлены bridge-кнопки [к пакету 02](../package-02/README.md), RU 2023:567 / EN 2023:1132. Исходный snapshot пакета 01 предшествует этим двум URL reactions; подробности в [123](../../../123_admin_finance_design_package_02_2026-10-12.md).

Дата: 12.10.2026. Figma `lxPP2um7FvIbt02K8eeH4T`. Baseline GitHub перед сохранением: `068789a3c85b666793a1d358b928dc7f9a42bcf7`. Статус: **draft_for_review**, не согласованная полная админка.

68 редактируемых фреймов, по 34 RU/EN; 1440×1000, Dark, Inter. Страницы `1981:29` RU, `1981:30` EN, `1981:2` UI kit.

| Старт | Ссылка |
| --- | --- |
| Owner RU | [Открыть прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37690&starting-point-node-id=1982-37690&scaling=scale-down) |
| Operations RU | [Открыть прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37877&starting-point-node-id=1982-37877&scaling=scale-down) |
| Owner EN | [Open prototype](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38513&starting-point-node-id=1982-38513&scaling=scale-down) |
| Operations EN | [Open prototype](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38700&starting-point-node-id=1982-38700&scaling=scale-down) |

Состав: оболочка; ADM-01 обзор, пустое и устаревшее состояние; ADM-02 список и карточка пользователя, пример ограниченного Operations, назначение VIP с причиной/preview/ошибкой/конфликтом; ADM-03 список и карточка demo, пауза/возобновление/отключение, accepted/applied/unknown и запрет возобновления.

- [Все экраны](screens.md)
- [Действия и будущие контракты](actions.md)
- [Переходы и покрытие](prototype.md)
- [Фактическая проверка](qa.md)

Это статические демонстрационные данные. Поля предзаполнены; поиск, фильтры, сортировка, суммы и результаты команд не вычисляются. Пример Owner в Operations — явно обозначенный просмотр роли для вычитки; в продукте такого самостоятельного повышения прав нет. Полноценное сохранение фильтров, ввод, ошибки загрузки, authentication и responsive ещё не покрыты.

ADM-01–03 покрыты частично. Остальные ADM и полные P-сценарии идут следующими пакетами: финансы/выплаты/тарифы/рефералы; health/security/доступ/аварийное управление; поддержка/контент/языки/маркетинг; сквозная приёмка и объединение UI kit. Код и live не запускались.
