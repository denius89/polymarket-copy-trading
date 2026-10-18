# Ручные настройки paper-копирования · клиентский Final

Дата изменения Figma: 18.10.2026. Файл: [`lxPP2um7FvIbt02K8eeH4T`](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T). Область: RU/EN × mobile/desktop, первый paper-запуск и видимые экраны лимитов. Админка и исходные/архивные страницы не менялись. Это дизайн и интерактивные переходы, не работающий ввод и не серверная валидация.

## Что изменено

- Демо-бюджет и размер нового BUY показаны как редактируемые поля. Стартовые $200/$20 заполняют форму, а не блокируют её. Режимы «сумма» и «% от сделки» имеют отдельные проверяемые состояния; 3% относится к **подтверждённой покупке трейдера**, не к бюджету или PnL.
- «Настроить ограничения» ведёт к двум числовым полям: на позицию 10% бюджета ($20 при $200) и на новые BUY за день 15% ($30 при $200). На mobile поля идут друг за другом, на desktop стоят рядом. Давность сигнала 30 с показана отдельно как системное правило без ручного ввода.
- С экрана обзора демо-ограничений убраны видимые Low/Medium/High и варианты 15/60 с. Обзор ведёт к ограничениям выбранного трейдера. На review отображаются выбранный способ размера, оба процента и их суммы в долларах.
- Отдельное состояние ошибки показывает `B=$100`, `F=$20`: при 10% позиции и 15% дневного лимита максимальная полная покупка составляет $10. Ошибка стоит у поля, продолжение отключено; значение не исправляется молча.

Диапазоны формы ($100–$1 000, $5–min(P,D), 1–20%, 5–20%, 10–30%) взяты из [числового предложения 130](../../130_paper_copy_settings_numeric_policy_proposal_2026-10-18.md). **Они остаются предложением для paper v1, не принятым ADR и не live-правилом.** Принятые стартовые значения и смысл полной пропущенной покупки сохраняются. До реализации серверной политики диапазоны и шаг должны получить отдельное утверждение.

## Точные узлы Final

Порядок столбцов: RU mobile, EN mobile, RU desktop, EN desktop. В ссылках Figma `:` узла заменён на `-`.

| Состояние | RU mobile | EN mobile | RU desktop | EN desktop |
| --- | --- | --- | --- | --- |
| Сумма: настройка | [2498:28817](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2498-28817) | [2502:19857](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2502-19857) | [2499:3617](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-3617) | [2504:5521](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2504-5521) |
| Сумма: проверка | [2498:28917](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2498-28917) | [2502:19957](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2502-19957) | [2499:3711](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-3711) | [2504:7176](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2504-7176) |
| 3%: настройка | [3086:3287](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3086-3287) | [3087:3295](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3087-3295) | [3087:192504](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3087-192504) | [3087:192749](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3087-192749) |
| 3%: проверка | [3086:3391](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3086-3391) | [3087:3399](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3087-3399) | [3087:192601](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3087-192601) | [3087:192865](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3087-192865) |
| Лимиты: ручной ввод | [2498:30136](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2498-30136) | [2502:21221](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2502-21221) | [2499:4837](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-4837) | [2504:6943](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2504-6943) |
| Лимиты: путь из 3% | [3093:192648](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3093-192648) | [3093:192769](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3093-192769) | [3093:88661](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3093-88661) | [3093:192893](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3093-192893) |
| Ошибка B100/F20 | [3089:3313](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3089-3313) | [3091:6648](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3091-6648) | [3091:192723](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3091-192723) | [3091:192567](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3091-192567) |
| Обзор демо-ограничений | [2498:30080](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2498-30080) | [2502:21163](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2502-21163) | [2499:4786](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-4786) | [2504:6883](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2504-6883) |

Новые 3% и error-фреймы сгруппированы в отдельной секции на каждой Final-странице: RU mobile `3086:3286`, EN mobile `3087:3294`, RU desktop `3087:192503`, EN desktop `3087:192748`. Исходный fixed-маршрут сохранён. Переход «% от сделки» ведёт в локальный 3% setup; «Настроить ограничения» открывает его локальные лимиты и после сохранения возвращает в 3% setup; «Проверить» ведёт в 3% review; «Изменить настройки» возвращает в 3% setup. Это пример сохранения режима в прототипе, не runtime-хранилище формы.

## UI kit и проверка

Использован существующий `Shared/Field` component set `987:74` с вариантами Default и Error; у него также есть Focus/Disabled/Loading для реализации. Переключатели режима и CTA — существующие экземпляры. Новых masters, вариантов, переменных, стилей, токенов и CSS нет; `manifest.json` и `tokens.json` не менялись. На страницах изменены экранные instances, их текстовые overrides и связи прототипа. Скрытые legacy-слои оставлены как историческая подложка, не участвуют в видимой композиции.

Сделаны структурная сверка узлов, визуальные снимки setup/review/limits/error во всех четырёх сочетаниях и проверка целевых IDs процентного пути для RU mobile и обоих desktop, затем отдельно EN mobile. У этих проверенных видимых фреймов нет Low/Medium/High или 15/60 с. Снимки подтверждают вёрстку, но не ввод с клавиатуры, пересчёт при наборе, фокус/экранный диктор, валидацию API или серверное сохранение. **Ручной проход Present после этой правки не выполнялся**; его нельзя считать перенесённым из приёмки 16.10.2026. Перед кодом отдельно пройти фиксированный и процентный маршруты во всех четырёх версиях и проверить изменение активной сессии с уже занятым бюджетом/резервом.

Связанные правила: [контракт настроек 129](../../129_copy_settings_contract_proposal_2026-10-18.md), [числовое предложение 130](../../130_paper_copy_settings_numeric_policy_proposal_2026-10-18.md), [API и прежние расхождения 128](../../128_copy_settings_and_venue_api_comparison_2026-10-18.md), [передача UI kit](../../../design/client-ui-kit/HANDOFF.md).
