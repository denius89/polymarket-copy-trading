# Строки со стрелкой: подпись и действие рядом

15.10.2026. По скриншоту владельца «Помощь по этой записи» / «Назад» проверены восемь клиентских страниц Figma: RU/EN, mobile/desktop, исходные и Final. В двухчастных строках `SettingsRow`, `Settings`, `Settings row` и `Related action` текстовый слой подписи и слой `›` занимали фиксированные широкие области; стрелка оказывалась у правого края далеко от действия.

Исправлены **412 строк**. Подпись и стрелка теперь подстраивают ширину под содержимое, а расстояние задаётся текущим интервалом auto-layout: 8 px на мобильных `SettingsRow`, 12 px в десктопных `Related action`/`Settings`. Сами строки, их размеры и существующие реакции не менялись: полная ширина остаётся зоной нажатия. В двух строках EN Final desktop («Deposit / Withdraw · future scenario») реакции отсутствовали и до правки — они остались неактивными. Админка и библиотечные masters не затрагивались.

| Клиентская страница | ID | Исправлено |
| --- | --- | ---: |
| [Исходная EN mobile](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=29-2) | `29:2` | 76 |
| [Исходная RU mobile](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=33-2) | `33:2` | 83 |
| [Исходная EN desktop](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=186-2) | `186:2` | 85 |
| [Final EN mobile](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-2) | `2499:2` | 54 |
| [Final RU mobile](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2477-528) | `2477:528` | 63 |
| [Final EN desktop](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-3) | `2499:3` | 51 |

Исходная и Final страницы RU desktop (`205:2`, `2477:529`) также проверены: таких двухчастных строк с `›` там нет. Их раскрывающиеся selectors содержат отдельное выбранное значение между подписью и `⌄`; это другая компоновка, не затронутая данной правкой.

Итоговая структурная проверка всех 412 строк: стрелка стоит на заданном расстоянии от подписи, не выходит за пределы строки, оба текста имеют ширину по содержимому; существующие реакции сохранены. Визуально просмотрены [RU mobile help](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2498-27815), [RU mobile Back](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1037-24580), [EN mobile Funds](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2502-18556) и [EN desktop Help with this record](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2504-3816). Полный Present-клик всех строк не проводился. Изменения Figma и этот отчёт пока локальны; публикация в GitHub не подтверждена.
