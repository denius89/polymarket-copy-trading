# Карта дизайна админки

[Открыть карту в Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2105-5766). Обновлено 12.10.2026. Карта размещена на существующей странице RU над экранами; новые страницы и ветки не создавались.

18 разделов из задания 118, 92 RU и 92 EN состояния. «Макеты есть» означает наличие дизайна, а не финальное согласование или работающую функцию. «Частично» — отдельные сценарии без полного раздела. «Запланировано» — нет отдельных макетов. Группы из задания — структура карты; окончательный состав меню будущих разделов ещё вычитываем.

| Раздел | Группа | Статус | RU / EN |
| --- | --- | --- | --- |
| ADM-01 Обзор | Обзор | Макеты есть | 3 / 3 |
| ADM-02 Пользователи | Операции | Макеты есть | 9 / 9 |
| ADM-03 Сессии | Операции | Макеты есть | 22 / 22 |
| ADM-04 Инциденты | Операции | Частично | 1 / 1 |
| ADM-05 Сверка | Операции | Частично | 2 / 2 |
| ADM-06 Площадки и данные | Операции | Запланировано | 0 / 0 |
| ADM-07 Трейдеры | Операции | Запланировано | 0 / 0 |
| ADM-08 Тарифы и рефералы | Финансы | Макеты есть | 14 / 14 |
| ADM-09 Поддержка | Коммуникации | Запланировано | 0 / 0 |
| ADM-10 Уведомления | Коммуникации | Запланировано | 0 / 0 |
| ADM-11 Обратная связь | Коммуникации | Запланировано | 0 / 0 |
| ADM-12 Журнал действий | Управление | Запланировано | 0 / 0 |
| ADM-13 Финансы и выплаты | Финансы | Макеты есть | 41 / 41 |
| ADM-14 Сотрудники и доступ | Управление | Запланировано | 0 / 0 |
| ADM-15 Подключения и безопасность | Управление | Запланировано | 0 / 0 |
| ADM-16 Тексты и языки | Управление | Запланировано | 0 / 0 |
| ADM-17 Аварийное управление | Аварийное управление | Запланировано | 0 / 0 |
| ADM-18 Маркетинг | Коммуникации | Запланировано | 0 / 0 |

## Поддержание карты

При каждом новом или изменённом пакете дизайна обновляем эту же карту, статус раздела, ссылки, права и индекс RU/EN. Сверяем реальные ID и переходы, затем публикуем sitemap.json и sitemap.md вместе с передачей дизайна. Не создаём дубликат карты. Карта не заменяет реакции прототипа.

Общие элементы: sidebar из UI kit, заголовок, контекст среды/площадки, язык, профиль и состояния доступа. Общий поиск, уведомления, вход и отозванная admin-сессия — запланированы. Полная реализация оболочки не заявляется.

Денежные действия и публикация численных условий — Owner; Operations объединяет поддержку и операции. Кастомные роли получают выбранные права, но не Owner-only денежные полномочия. Контент и маркетинг публикуются по правам с журналированием без обязательного Owner approval.

## Ключевые сценарии

- VIP пользователя · Owner: [Пользователь](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37844) → [Форма VIP](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37913) → [Проверка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37972) → [VIP применён](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38026).
- Выплата партнёру · Owner; второй Owner при срабатывании защиты: [Выплаты](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-520) → [Маршрут PM / LL](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-574) → [Проверка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-713) → [Отправлено](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-876) → [Подтверждено](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-916).
- Тариф · публикация Owner: [Тарифы](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-803) → [Черновик](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-859) → [Симулятор](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-942) → [Предпросмотр](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-993) → [Запланировано](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1033).
- Сессия · Operations по правам: [Сессия](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-398) → [Пауза](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-433) → [Запрос принят](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-460) → [Подтверждено](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-485).

У выплаты есть отдельный маршрут Limitless, ветви второго Owner, недостатка средств, неизвестного результата и сверки. Нормальная выплата погашает весь подтверждённый доступный баланс выбранной площадки. Карта не подтверждает конкретные внешние API маршруты.

Аварийное управление ещё предстоит нарисовать: область/последствия → причина → активация → фактическое применение. Восстановление — Owner и независимый уполномоченный сотрудник; без автоотправки старой очереди.

Позже: ротация ключей интеграций, массовые внешние каналы, конструктор лендинга, вложения и SLA.

## Полный индекс существующих экранов

### ADM-01 · Обзор

Сводка, свежесть данных, пустое состояние.

| Состояние | RU | EN |
| --- | --- | --- |
| Обзор | [1982:37690](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37690) | [1982:38513](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38513) |
| Обзор · данные устарели | [1982:37735](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37735) | [1982:38558](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38558) |
| Обзор · пока нет данных | [1982:37763](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37763) | [1982:38586](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38586) |

### ADM-02 · Пользователи

Список, карточка пользователя, назначение VIP.

| Состояние | RU | EN |
| --- | --- | --- |
| Пользователи | [1982:37788](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37788) | [1982:38611](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38611) |
| Пользователи · нет совпадений | [1982:37819](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37819) | [1982:38642](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38642) |
| Карточка пользователя | [1982:37844](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37844) | [1982:38667](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38667) |
| Пользователь · Operations | [1982:37877](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37877) | [1982:38700](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38700) |
| Назначение VIP | [1982:37913](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37913) | [1982:38736](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38736) |
| VIP · ошибка заполнения | [1982:37945](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37945) | [1982:38768](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38768) |
| VIP · проверка перед применением | [1982:37972](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37972) | [1982:38795](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38795) |
| VIP · версия изменилась | [1982:38001](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38001) | [1982:38824](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38824) |
| VIP применён · demo | [1982:38026](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38026) | [1982:38849](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38849) |

### ADM-03 · Сессии

Список и карточка, пауза, возобновление, отключение demo; Operations.

| Состояние | RU | EN |
| --- | --- | --- |
| Сессии | [1982:38062](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38062) | [1982:38885](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38885) |
| Демо-сессия | [1982:38090](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38090) | [1982:38913](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38913) |
| Поставить demo на паузу? | [1982:38128](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38128) | [1982:38951](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38951) |
| Пауза · запрос принят | [1982:38155](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38155) | [1982:38978](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38978) |
| Демо-сессия · пауза | [1982:38180](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38180) | [1982:39003](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39003) |
| Возобновление ограничено | [1982:38216](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38216) | [1982:39039](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39039) |
| Возобновить demo? | [1982:38250](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38250) | [1982:39073](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39073) |
| Demo возобновлена | [1982:38279](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38279) | [1982:39102](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39102) |
| Отключить demo-сессию? | [1982:38313](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38313) | [1982:39136](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39136) |
| Отключение · в обработке | [1982:38340](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38340) | [1982:39163](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39163) |
| Demo отключена | [1982:38365](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38365) | [1982:39188](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39188) |
| Сессия · неизвестный результат | [1982:38392](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38392) | [1982:39215](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39215) |
| Демо-сессия · Operations | [1984:398](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-398) | [1984:38802](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38802) |
| Подтверждение паузы | [1984:433](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-433) | [1984:38837](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38837) |
| Запрос паузы принят | [1984:460](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-460) | [1984:38864](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38864) |
| Пауза подтверждена | [1984:485](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-485) | [1984:38889](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38889) |
| Возобновление заблокировано | [1984:518](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-518) | [1984:38922](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38922) |
| Подтверждение возобновления | [1984:552](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-552) | [1984:38956](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38956) |
| Demo возобновлена | [1984:579](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-579) | [1984:38983](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38983) |
| Подтверждение отключения demo | [1984:613](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-613) | [1984:39017](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-39017) |
| Отключение в обработке | [1984:640](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-640) | [1984:39044](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-39044) |
| Demo отключена | [1984:665](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-665) | [1984:39069](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-39069) |

### ADM-04 · Инциденты

Есть карточка инцидента по выплате. Общая очередь и полный цикл — впереди.

| Состояние | RU | EN |
| --- | --- | --- |
| INC-021 · сверка выплаты | [2004:552](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-552) | [2007:1085](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1085) |

### ADM-05 · Сверка

Есть проверка и расхождение выплаты. Общая очередь сверки — впереди.

| Состояние | RU | EN |
| --- | --- | --- |
| Проверка результата | [2004:481](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-481) | [2007:1014](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1014) |
| Расхождение результата | [2004:514](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-514) | [2007:1047](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1047) |

### ADM-06 · Площадки и данные

Health Polymarket/Limitless, данные и актуальность источников.

Отдельные экраны пока не созданы.

### ADM-07 · Трейдеры

Рейтинг, показатели, сбор данных, проверка адреса.

Отдельные экраны пока не созданы.

### ADM-08 · Тарифы и рефералы

Версии, симулятор, накопительная лестница, VIP партнёра. Публикация — Owner.

| Состояние | RU | EN |
| --- | --- | --- |
| Тарифы и реферальные условия | [2005:803](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-803) | [2008:1070](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1070) |
| Черновик тарифа v2 | [2005:859](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-859) | [2008:1126](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1126) |
| Тариф не прошёл проверку | [2005:909](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-909) | [2008:1176](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1176) |
| Симулятор условий | [2005:942](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-942) | [2008:1209](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1209) |
| Предпросмотр версии тарифа | [2005:993](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-993) | [2008:1260](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1260) |
| Версия запланирована · пример | [2005:1033](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1033) | [2008:1300](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1300) |
| Версия изменилась | [2005:1068](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1068) | [2008:1335](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1335) |
| История условий | [2005:1101](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1101) | [2008:1368](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1368) |
| Накопительная реферальная лестница | [2005:1153](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1153) | [2008:1420](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1420) |
| Настройка лестницы | [2005:1215](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1215) | [2008:1482](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1482) |
| Проверьте уровни | [2005:1263](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1263) | [2008:1530](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1530) |
| Предпросмотр лестницы | [2005:1296](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1296) | [2008:1563](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1563) |
| Партнёрские VIP-условия | [2005:1331](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1331) | [2008:1598](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1598) |
| Проверка партнёрского VIP | [2005:1379](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1379) | [2008:1646](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1646) |

### ADM-09 · Поддержка

Обращения, переписка, назначение, связь с пользователем и сессией.

Отдельные экраны пока не созданы.

### ADM-10 · Уведомления

Операционные сообщения, попытки доставки и результат.

Отдельные экраны пока не созданы.

### ADM-11 · Обратная связь

Список, карточка и обработка обратной связи.

Отдельные экраны пока не созданы.

### ADM-12 · Журнал действий

Кто, когда и что изменил; фильтры и разрешённый экспорт.

Отдельные экраны пока не созданы.

### ADM-13 · Финансы и выплаты

Учёт, обязательства, партнёры, источники, полная выплата, реквизиты и защитные пороги.

| Состояние | RU | EN |
| --- | --- | --- |
| Финансы сервиса | [2003:2](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-2) | [2007:2](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-2) |
| Источники не подключены | [2003:77](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-77) | [2007:77](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-77) |
| Сводка неполная | [2003:115](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-115) | [2007:115](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-115) |
| Поступления и расходы | [2003:153](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-153) | [2007:153](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-153) |
| Запись REC-010 | [2003:213](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-213) | [2007:213](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-213) |
| Начисления и обязательства | [2003:249](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-249) | [2007:249](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-249) |
| Партнёры | [2003:313](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-313) | [2007:313](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-313) |
| PART-024 · Agent A | [2003:367](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-367) | [2007:367](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-367) |
| Условия и реквизиты PART-024 | [2003:429](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-429) | [2007:429](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-429) |
| Источники выплат | [2003:466](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-466) | [2007:466](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-466) |
| Выплаты | [2003:520](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-520) | [2007:520](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-520) |
| Выплата · Polymarket | [2003:574](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-574) | [2007:574](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-574) |
| Выплата · Limitless | [2003:627](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-627) | [2007:627](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-627) |
| Нет доступного маршрута | [2003:675](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-675) | [2007:675](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-675) |
| Проверка полной выплаты | [2003:713](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-713) | [2007:713](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-713) |
| Проверка · комиссия партнёра | [2003:778](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-778) | [2007:778](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-778) |
| Выплата принята | [2003:838](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-838) | [2007:838](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-838) |
| Отправлено · проверяется | [2003:876](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-876) | [2007:876](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-876) |
| Полная выплата подтверждена | [2003:916](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-916) | [2007:916](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-916) |
| Результат выплаты неизвестен | [2003:976](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-976) | [2007:976](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-976) |
| Отменить до отправки? | [2004:585](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-585) | [2007:1118](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1118) |
| Отменено до отправки | [2004:620](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-620) | [2007:1153](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1153) |
| Недостаточно средств источника | [2004:655](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-655) | [2007:1188](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1188) |
| Расчёт устарел | [2004:693](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-693) | [2007:1226](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1226) |
| Выплаты остановлены | [2004:728](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-728) | [2007:1261](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1261) |
| Требуется второй Owner | [2004:766](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-766) | [2007:1299](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1299) |
| Owner B · независимая проверка | [2004:806](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-806) | [2008:596](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-596) |
| Подтверждение Owner B сохранено | [2004:844](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-844) | [2008:634](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-634) |
| Реквизиты PART-024 | [2004:879](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-879) | [2008:669](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-669) |
| Предложение реквизитов | [2004:935](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-935) | [2008:725](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-725) |
| Реквизиты ожидают проверки | [2004:983](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-983) | [2008:773](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-773) |
| Owner B · реквизиты v2 | [2004:1021](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1021) | [2008:811](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-811) |
| Версия реквизитов активирована | [2004:1056](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1056) | [2008:846](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-846) |
| Предложение отклонено | [2004:1089](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1089) | [2008:879](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-879) |
| Защитные пороги выплат | [2004:1122](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1122) | [2008:912](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-912) |
| Новая защитная policy | [2004:1160](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1160) | [2008:950](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-950) |
| Policy не готова | [2004:1208](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1208) | [2008:998](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-998) |
| Owner B · проверка policy | [2005:767](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-767) | [2008:1034](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1034) |
| Выплата принята · комиссия партнёра | [2005:1417](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1417) | [2008:1684](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1684) |
| Проверяется · комиссия партнёра | [2005:1450](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1450) | [2008:1717](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1717) |
| Полная выплата · комиссия партнёра | [2005:1483](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1483) | [2008:1750](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1750) |

### ADM-14 · Сотрудники и доступ

Owner, единая Operations, кастомные роли; отзыв admin-сессий.

Отдельные экраны пока не созданы.

### ADM-15 · Подключения и безопасность

Health/metadata, изоляция подключения, монитор USDT/USD; без раскрытия секретов.

Отдельные экраны пока не созданы.

### ADM-16 · Тексты и языки

Каталог, RU/EN, версии, предпросмотр и публикация по правам.

Отдельные экраны пока не созданы.

### ADM-17 · Аварийное управление

Global stop, технический режим, отдельные ограничения пополнения/вывода/выплат и восстановление.

Отдельные экраны пока не созданы.

### ADM-18 · Маркетинг

Объявления в приложении, аудитория, расписание, доставка. Публикация по правам.

Отдельные экраны пока не созданы.

