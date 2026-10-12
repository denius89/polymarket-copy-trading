# Текущая админка — единый дизайн v0.4

Актуальный старт: [сценарии RU](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2138-9818&starting-point-node-id=2138-9818&scaling=scale-down) · [EN](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67397&starting-point-node-id=2138-67397&scaling=scale-down). [Пакет 04](../package-04/README.md) и [fixture](../fixtures/README.md). Исторические ссылки пакета 03:

Новые стартовые точки: [подключения](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2109-5830&starting-point-node-id=2109-5830&scaling=scale-down), [сотрудники](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2110-6876&starting-point-node-id=2110-6876&scaling=scale-down), [аварийное управление](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52505&starting-point-node-id=2110-52505&scaling=scale-down).

12.10.2026. 432 состояния; 216 RU + 216 EN. Актуальный полный индекс — [sitemap](../sitemap.json), добавленные экраны и новые пункты меню — [пакет 03](../package-03/manifest.json). Файлы ru.json/en.json и старые reactions ниже фиксируют базовую пересборку 92 экранов на язык до пакета 03. [Правила дальнейшей работы и стиля](../STYLE_GUIDE.md).

| Старт | Ссылка |
| --- | --- |
| Обзор RU | [Прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37690&starting-point-node-id=1982-37690&scaling=scale-down) |
| Финансы RU | [Прототип](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2003-2&starting-point-node-id=2003-2&scaling=scale-down) |
| Обзор EN | [Prototype](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38513&starting-point-node-id=1982-38513&scaling=scale-down) |
| Финансы EN | [Prototype](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=2007-2&starting-point-node-id=2007-2&scaling=scale-down) |

[RU frames и QA](ru.json) · [EN frames и QA](en.json) · [Изменённые ID и итоговые проверки](layout-ledger.json).
Полный граф разделён только для хранения: [операции RU](reactions-ru-operations.json), [финансы RU](reactions-ru-finance.json), [операции EN](reactions-en-operations.json), [финансы EN](reactions-en-finance.json). Это не отдельные ветки Figma.

Перекомпоновка по сетке: на каждом языке 12 экранов 6+6, 54 состояния с рабочей колонкой 8 и 26 широких композиций. Заголовки сгруппированы, кнопки по содержимому, действия поддерживают перенос. Все root IDs и графы переходов сохранены.

Свежие снимки: [финансы RU](evidence/finance-ru.png), [обзор RU](evidence/overview-ru.png), [выплата RU](evidence/payout-ru.png), [финансы EN](evidence/finance-en.png), [тариф EN](evidence/tariff-en.png), [сессия RU](evidence/session-ru.png), [неизвестный результат RU](evidence/unknown-ru.png), [VIP RU](evidence/vip-ru.png), [реферальная форма RU](evidence/referral-ru.png), [обзор EN](evidence/overview-en.png), [реквизиты EN](evidence/recipient-en.png).

Текущий UI kit: [реестр](../ui-kit/registry.json). 25 записей components/component sets и три Admin/Button masters. Прежние package-01/package-02 — исторические документы первого создания; их ранние screenshots, page IDs и графы не описывают текущий вид. Figma остаётся источником точного визуального состояния. JSON — карта ID/переходов и проверки, а не полная резервная копия файла.
