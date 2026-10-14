# Поддержка · контракт дизайна

13.10.2026. Дополнение ADM-09 к ADR-0036, 115 §13 и 118. API/сервер не реализованы.

## Очередь и контекст

Ticket ID/тема, user, status, assignee, последнее обновление, optional venue/session. Фильтры: поиск в разрешённой области, статус, сотрудник, период. Empty по фильтру отличается от unavailable; сбой не означает отсутствие обращений. Пагинация продукта сохраняет фильтр; в учебном filtered-примере один результат, next недоступен.

Карточка: 8 колонок переписки + 4 контекста. Typed reference обязан принадлежать тому же user и иметь safe snapshot/environment/mode/venue. General question может иметь context=null. Unavailable/unknown не подменяет факты и не открывает чужой user/session. Показанные user/session snapshots не дают финансовых команд.

## Ответ и staff-only заметка

Public reply и internal note — разные режимы, CTA, visibility и IDs. Reply recipient определяется текущим ticket, sender — authenticated staff identity. Note visibility=staff_only; user serializer/stream исключает note, staff evidence и extended PII. Цвет/скрытие CSS не обеспечивают безопасность. Переключение режима не публикует уже сохранённую заметку. Реальная переписка сохраняет исходный язык; RU/EN fixture variants не означают функцию авто-перевода.

Empty draft не отправляется. Reply использует client message ID + idempotency. Delivery: draft/submitting/sent/failed/send_unknown. Sent не означает delivered/read. При submitting/unknown исходный draft заблокирован; до проверки не повторяем отправку. Confirmed failed допускает контролируемый retry с тем же idempotency-контрактом, без дубля. Таймаут не доказывает failed. Проверка статуса может остаться unknown; макет sent — отдельный учебный outcome.

## Назначение и версии

Только active staff с подходящим доступом. Ответственный виден в карточке; assignment и status логируются. Operations объединяет support/operator, отдельная системная Support-роль не вводится. Custom roles получают отдельные scopes/capabilities, не выводимые из заголовка роли. Обычная поддержка не требует Owner approval.

Conversation/assignment version защищает от параллельного перезаписывания и дублей. Conflict сохраняет draft/намерение, обновляет состояние и предлагает сверку версии. Право отвечать и право назначать/закрывать проверяются независимо сервером.

## Статусы и доступ

Ticket: open/waiting_support/waiting_user/resolved/closed. Delivery failed/unknown не разрешает вопрос автоматически. Resolution — отдельное осознанное действие по полномочиям; close сохраняет историю; reopen создаёт событие. Точные ownership/close/reopen права и retention до backend остаются открытыми. SLA/attachments позже.

No-access не раскрывает subject/user/messages/context. Read-only показывает только разрешённые данные, без reply/note/assignment/status mutations. Право на внутренние заметки проверить отдельно. Integration secrets, ключи, private credentials отсутствуют. Support не меняет balances/risk/VIP, не отправляет trades и не исполняет payouts. Денежный unknown/инцидент обрабатывается через разрешённую сверку/incident, не через решение ticket.

## Связь с user UI и приёмка

Один public conversation source для user/admin, отдельный staff-only поток. Context ownership и staff grants проверяются backend, ID из Figma/поля не является доказательством доступа. Visible/read receipts и unread count требуют настоящего источника, не значений макета.

Перед кодом: API/read projections, idempotency/conflict, visibility matrix custom roles, close/reopen/retention, остальные typed context screens, длинные conversations, revoked/expired session states, keyboard/responsive и receipts. Тесты: duplicate/unknown reload без blind retry, race между assignees, cross-user denial, staff-only note exclusion из user stream, all-role authz/audit. Эти гарантии не доказаны кликабельным прототипом.
