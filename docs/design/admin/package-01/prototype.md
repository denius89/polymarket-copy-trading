# Прототип и покрытие

396 reactions: 198 RU + 198 EN. Точные source/screen/destination/type/label сохранены в [RU](evidence/ru-reactions.json) и [EN](evidence/en-reactions.json). Пустые выбранные/self-переходы пропущены; invalid/self NODE destinations не найдены. Language switch ведёт на соответствующий fixture другого языка. Навигация Operations сохраняет ограниченный root вместо Owner карточки.

Фактический Present:

- RU Owner: обзор → список → пользователь → VIP form → preview → результат; пользователь → session → pause confirm → accepted → paused; resume → risk blocked → возврат; disconnect → processing → disconnected.
- RU disconnected → EN disconnected: язык сохраняет показанное состояние.
- EN: обзор → Operations user без VIP → Operations session → pause confirm → accepted → paused → resume confirm → resumed; роль Operations сохраняется.

Полный прогон каждого ребра, роли и языка в Present не заявляется. Структурная проверка покрывает все 68 фреймов. Состояние не хранится: прямые кнопки примера и возвраты открывают подготовленные fixtures.

| Сценарии brief 118 | Покрытие |
| --- | --- |
| P-01 | Фрагмент session operations; incidents/reconciliation ещё не выполнены |
| P-06 | Частично: VIP assign/preview/active/error/conflict; future/end отсутствуют |
| P-11 | Не покрыт: Auditor/custom role audit/export ещё не выполнены |
| P-12 | Не покрыт: диагностика площадки ADM-06/15 ещё не выполнена; stale/unknown текущего пакета не заменяют P-12 |
| P-02–05, P-07–10, P-13–18 | Следующие пакеты |

Завершённый пакет для вычитки не равен полной приёмке этих P-сценариев. Финальные критерии — 118, включая 18 сценариев после ADR-0043.
