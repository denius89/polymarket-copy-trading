# Контракты действий первого пакета

Визуальный контракт v0.1, 12.10.2026. Предлагаемые API из 115 используют prefix `/admin/v1`; API ещё не реализован. Для resume точный endpoint будет закреплён при реализации; право `session.resume_demo` уже описано. Нельзя выводить новый endpoint или enum только из названия фрейма.

| Действие | Данные / результат | Право / проверка | API и граница макета |
| --- | --- | --- | --- |
| Обзор и актуальность | Источник, площадка, observed_at, полнота, подключённость; unknown не zero | Scope просмотра; пользовательские бюджеты не доход сервиса | Read projection по 115, в макете синтетическая сводка |
| Список пользователей / карточка | Stable user ID, locale, sessions, ticket references, effective VIP | user-context scopes; только разрешённый контекст | `GET /users`, `GET /users/{id}`; будущие query/pagination/loading/error |
| Назначить VIP | User ID, policy version, параметры, effective interval, причина; preview, проверка, active | Только два персональных Owner; user VIP отдельно от partner VIP | `POST /users/{id}/vip`; изменить/завершить и future/ended остаются следующему пакету |
| Просмотр сессии | Session/version, venue, mode, risk/restrictions, budgets/positions/orders, desired/observed state | session view в scope; demo явно обозначено | `GET /sessions/{id}`; данные должны совпадать с user UI |
| Пауза | Причина, actor, expected version; accepted не applied | `session.pause`; прекращение новых BUY не равно GLOBAL_STOP | `POST /sessions/{id}/pause`; common domain workflow |
| Возобновить demo | Только разрешённая причина паузы; проверка risk/venue/global restrictions | `session.resume_demo`; нельзя снять независимый запрет или запустить catch-up | Endpoint уточняется по 115; risk frame демонстрирует отказ |
| Отключить demo | Preview позиций/ордеров, desired state, reconciliation progress | `session.disconnect_demo`; только demo, не удалить кошелёк/историю | `POST /sessions/{id}/disconnect-demo`; fixture имеет 0 позиций/ордеров |
| Unknown | Command ID, безопасное сообщение, ссылка на проверку | Просмотр статуса; неизвестность не разрешает повтор/освобождение резервов | Poll/stream/reconciliation контракт позже; не новая отправка |
| Язык / навигация | Точная соответствующая роль/состояние RU/EN | Не меняет permissions | Prototype URL/NODE, не денежная команда |
| Показать результат / пример состояния / Owner preview | Переход между статическими fixtures | Только инструмент вычитки | Не переносить в production как mutation, polling или self-escalation |

Будущие mutations: сервер заново проверяет identity, permissions, object scope, environment/venue/mode и restrictions перед execution. Ожидаемая версия и idempotency key защищают от устаревшего preview и повторного клика. Conflict возвращает свежий контекст и требует нового preview. Audit хранит actor, target, время, reason и безопасный diff без секретов. Конкретные DTO/version/idempotency схемы — контракт реализации 115, не уже работающий API.

Demo alpha fee = 0; будущая базовая 1% настраивается Owner, VIP не меняет прошлые начисления. Макет не доказывает live capability обеих площадок. Staff pause визуально помечена актором; это не утверждение нового backend enum.
