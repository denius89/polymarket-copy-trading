# Исправления кнопок RU/EN mobile/desktop — 6 октября 2026

По утверждённому владельцем пакету из [аудита 112](112_button_copy_and_reaction_audit_2026-10-06.md) обновлены четыре рабочие страницы существующего [Figma-файла](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T): Mobile EN `29:2`, Mobile RU `33:2`, Desktop EN `186:2`, Desktop RU `205:2`.

Исторические Desktop RU D29/D30 не изменялись. Новые бизнес-правила не вводились.

## Исправленные маршруты

- Удалён ложный возврат к ещё не существующей сессии во всех четырёх версиях.
- Возвраты из поддержки теперь открывают указанный контекст: позицию, событие, сессию или баланс.
- Фактические возвраты в Help названы «К помощи» / Back to help.
- Mobile RU/EN «Открыть связанную позицию» / Open related position теперь открывает настоящую позицию.
- Desktop RU/EN действие отправки отзыва открывает форму отзыва.
- Desktop RU/EN blank-форма общего обращения продолжает email/guest-сценарий.
- Шесть Desktop EN related-record controls получили рабочие переходы к Order, Event или Position details.

## Limitless в Mobile EN

Создан отдельный future-account экран Limitless `1963:4861` на основе структуры Polymarket без изменения продуктовой логики.

- `951:10202` Limitless account → `1963:4861`;
- `951:10199` Polymarket account → `951:9956`;
- кнопки обоих future-account экранов названы Deposit и Withdraw; ограничение future остаётся в содержании экрана.

## Feedback в Desktop EN

В английской desktop-странице отдельной формы отзыва не было. Для функциональной эквивалентности RU созданы два локализованных состояния:

- форма Feedback `1963:37190`;
- подтверждение Feedback sent `1963:37263`.

Share feedback `203:508` ведёт в форму. Cancel и Profile возвращают в EN profile `905:9977`, Send feedback открывает подтверждение, Contact support — общую EN-форму `714:1536`. Навигация Home, Traders, Positions и Activity также связана с текущими EN-разделами. На подтверждении удалены устаревшие повторные Cancel/Send actions.

## Удалённые дубли

- На empty-session состояниях каждой версии оставлено одно действие «К сессии» / Back to session.
- В Mobile RU две одинаковые кнопки позиции сведены к одной «Открыть позицию».
- На последнем onboarding-экране Mobile EN удалён Skip, дублировавший Choose a trader.
- На feedback success Desktop RU скрыты активные на вид, но неработающие Cancel и Send feedback; оставлен рабочий возврат в профиль.

## Короткие подписи и словарь

- «Назад к каталогу» / Back to catalog → «Трейдеры» / Traders.
- «События» / Events в актуальной навигации → «Активность» / Activity.
- «Позиции за время копирования» / Positions during copying → «Все позиции» / All positions, поскольку переход не устанавливает фильтр периода.
- Применены согласованные короткие действия: «Текущая сессия» / Current demo, «Управлять самостоятельно» / Manage manually, «Обратиться в поддержку» / Contact support, «Подключить Telegram» / Connect Telegram, «Подтвердить закрытие» / Confirm close, «Изменить email» / Change email, «Настроить риски» / Set limits и связанные сокращения из отчёта 112.
- Подписи действий с важными последствиями сохранены явными; выбранные вкладки и периоды не превращались в искусственные переходы.

## Проверка

- На каждой странице выполнен read-only повторный просмотр изменённых node IDs, подписей и destinations.
- Удалённые дубли и ложные CTA отсутствуют.
- Все новые и изменённые destination nodes существуют.
- Mobile RU: прошли 38 основных и 4 дополнительных assertions.
- Mobile EN: проверены 2 245 reaction-bearing nodes и 164 уникальных назначения; отсутствующих destinations нет.
- Desktop EN: 17 ключевых исправленных маршрутов, удалённые элементы, новые feedback states и сокращения проверены отдельными assertions.
- Получены и просмотрены рендеры затронутых support, empty-state, trader-profile, account, feedback и action экранов. Новые подписи не обрезаны, наложений не обнаружено.
- В новой Desktop EN feedback-форме не осталось RU-текста или RU-формата суммы.

Ручной Present не выполнен: попытка открыть запущенное приложение Figma через Computer Use вернула `Computer Use permissions are not granted`. Структурная проверка и рендеры не заменяют кликабельную пользовательскую приёмку.

## Следующий контроль

Пройти в Present основные ветки четырёх прототипов: first run, active demo, support request, contextual support, feedback, empty session и future venue accounts. После этого зафиксировать приёмку либо оставшиеся точечные замечания.
