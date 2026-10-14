# Живая карта админки

Текущий срез 14.10.2026: **427 RU + 427 EN корневых макетов**, из них 422 основных состояния и 5 технических оболочек на язык. Карта 0.12, набор компонентов админки 0.4.20 (28 наборов / 168 вариантов). [Последние решения и передача](SYNC_2026-10-14.md). Ниже сохранён исторический журнал; его промежуточные числа и версии не заменяют текущий реестр.

13.10.2026 · ревизия 0.7: 295 RU + 295 EN, включая по три меню аватара для viewport прототипа. Личный аккаунт пересобран как обзор и отдельные страницы. [Паттерн, узлы и QA](account-hub-2026-10-13/README.md).

13.10.2026: актуально 291 RU + 291 EN. Добавлены профиль Noor, настройки обоих пользователей и отдельный просмотр Operations; группировка меню и breadcrumbs — на 280 экранах с sidebar каждого языка. Две ранние карточки сохранены и дополнены входом в настройки; полная пересборка ждёт согласия после auto-review. [Узлы, проверки и ограничения](profile-navigation-2026-10-13/README.md). Пакет пока локальный; код/live не начаты.

Ревизия 0.3, 12.10.2026. 18 разделов, 216 RU + 216 EN состояний. [Карта в Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2105-5766). Макеты на вычитке, не работающие функции. [Пакет 04](package-04/README.md) · [Demo dataset](fixtures/README.md) · [Точные ID](sitemap.json).

Краткий вход для просмотра всего файла — [карта админки на странице «00 · Начать здесь»](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2149-17217). Подробные статусы и ссылки остаются здесь.

## ADM-01 · Обзор

Макеты есть. Обзор, свежесть, пустое состояние и учебные сценарии SHADOW-ADM-01.

| Состояние | RU | EN |
| --- | --- | --- |
| Обзор | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37690) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38513) |
| Обзор · данные устарели | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37735) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38558) |
| Обзор · пока нет данных | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37763) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38586) |
| Рабочие сценарии админки | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-9818) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67397) |

## ADM-02 · Пользователи

Макеты есть. Список, карточка пользователя, назначение VIP.

| Состояние | RU | EN |
| --- | --- | --- |
| Пользователи | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37788) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38611) |
| Пользователи · нет совпадений | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37819) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38642) |
| Карточка пользователя | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37844) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38667) |
| Пользователь · Operations | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37877) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38700) |
| Назначение VIP | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37913) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38736) |
| VIP · ошибка заполнения | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37945) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38768) |
| VIP · проверка перед применением | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-37972) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38795) |
| VIP · версия изменилась | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38001) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38824) |
| VIP применён · demo | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38026) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38849) |

## ADM-03 · Сессии

Макеты есть. Список и карточка, пауза, возобновление, отключение demo; Operations.

| Состояние | RU | EN |
| --- | --- | --- |
| Сессии | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38062) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38885) |
| Демо-сессия | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38090) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38913) |
| Поставить demo на паузу? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38128) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38951) |
| Пауза · запрос принят | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38155) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38978) |
| Демо-сессия · пауза | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38180) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39003) |
| Возобновление ограничено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38216) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39039) |
| Возобновить demo? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38250) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39073) |
| Demo возобновлена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38279) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39102) |
| Отключить demo-сессию? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38313) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39136) |
| Отключение · в обработке | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38340) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39163) |
| Demo отключена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38365) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39188) |
| Сессия · неизвестный результат | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-38392) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1982-39215) |
| Демо-сессия · Operations | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-398) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38802) |
| Подтверждение паузы | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-433) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38837) |
| Запрос паузы принят | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-460) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38864) |
| Пауза подтверждена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-485) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38889) |
| Возобновление заблокировано | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-518) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38922) |
| Подтверждение возобновления | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-552) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38956) |
| Demo возобновлена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-579) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-38983) |
| Подтверждение отключения demo | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-613) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-39017) |
| Отключение в обработке | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-640) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-39044) |
| Demo отключена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-665) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1984-39069) |

## ADM-04 · Инциденты

Частично. Есть карточка инцидента по выплате. Общая очередь и полный цикл — впереди.

| Состояние | RU | EN |
| --- | --- | --- |
| INC-021 · сверка выплаты | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-552) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1085) |

## ADM-05 · Сверка

Частично. Есть проверка и расхождение выплаты. Общая очередь сверки — впереди.

| Состояние | RU | EN |
| --- | --- | --- |
| Проверка результата | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-481) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1014) |
| Расхождение результата | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-514) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1047) |

## ADM-06 · Площадки и данные

Частично. Health Polymarket/Limitless, данные и актуальность источников.

| Состояние | RU | EN |
| --- | --- | --- |
| Подключения и здоровье площадок | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-5830) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-54469) |
| Проверка не завершена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-6174) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-54813) |

## ADM-07 · Трейдеры

Запланировано. Рейтинг, показатели, сбор данных, проверка адреса.

Макеты ещё не созданы.

## ADM-08 · Тарифы и рефералы

Макеты есть. Версии, симулятор, накопительная лестница, VIP партнёра. Публикация — Owner.

| Состояние | RU | EN |
| --- | --- | --- |
| Тарифы и реферальные условия | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-803) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1070) |
| Черновик тарифа v2 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-859) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1126) |
| Тариф не прошёл проверку | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-909) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1176) |
| Симулятор условий | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-942) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1209) |
| Предпросмотр версии тарифа | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-993) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1260) |
| Версия запланирована · пример | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1033) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1300) |
| Версия изменилась | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1068) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1335) |
| История условий | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1101) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1368) |
| Накопительная реферальная лестница | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1153) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1420) |
| Настройка лестницы | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1215) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1482) |
| Проверьте уровни | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1263) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1530) |
| Предпросмотр лестницы | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1296) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1563) |
| Партнёрские VIP-условия | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1331) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1598) |
| Проверка партнёрского VIP | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1379) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1646) |

## ADM-09 · Поддержка

Запланировано. Обращения, переписка, назначение, связь с пользователем и сессией.

Макеты ещё не созданы.

## ADM-10 · Уведомления

Запланировано. Операционные сообщения, попытки доставки и результат.

Макеты ещё не созданы.

## ADM-11 · Обратная связь

Запланировано. Список, карточка и обработка обратной связи.

Макеты ещё не созданы.

## ADM-12 · Журнал действий

Частично. Журнал, фильтры, страницы, образец CSV, отказ экспорта и целостность.

| Состояние | RU | EN |
| --- | --- | --- |
| Журнал действий | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52274) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57011) |
| AUD-041 · детали изменения | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52393) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57130) |
| Фильтры журнала | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66255) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76153) |
| Журнал · изменения доступа | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66380) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76278) |
| Событий по фильтру нет | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66504) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76402) |
| Журнал · страница 2 из 2 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66608) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76506) |
| Экспорт разрешённой выборки | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66730) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76628) |
| Демонстрационный CSV готов | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66849) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76747) |
| Файл экспорта не подготовлен | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66955) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76853) |
| Целостность · учебное совпадение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67052) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76950) |
| Целостность не подтверждена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67167) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-77065) |
| Обнаружено расхождение журнала | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67282) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-77180) |

## ADM-13 · Финансы и выплаты

Макеты есть. Учёт, обязательства, партнёры, источники, полная выплата, реквизиты и защитные пороги.

| Состояние | RU | EN |
| --- | --- | --- |
| Финансы сервиса | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-2) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-2) |
| Источники не подключены | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-77) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-77) |
| Сводка неполная | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-115) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-115) |
| Поступления и расходы | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-153) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-153) |
| Запись REC-010 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-213) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-213) |
| Начисления и обязательства | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-249) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-249) |
| Партнёры | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-313) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-313) |
| PART-024 · Agent A | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-367) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-367) |
| Условия и реквизиты PART-024 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-429) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-429) |
| Источники выплат | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-466) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-466) |
| Выплаты | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-520) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-520) |
| Выплата · Polymarket | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-574) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-574) |
| Выплата · Limitless | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-627) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-627) |
| Нет доступного маршрута | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-675) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-675) |
| Проверка полной выплаты | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-713) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-713) |
| Проверка · комиссия партнёра | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-778) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-778) |
| Выплата принята | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-838) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-838) |
| Отправлено · проверяется | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-876) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-876) |
| Полная выплата подтверждена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-916) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-916) |
| Результат выплаты неизвестен | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-976) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-976) |
| Отменить до отправки? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-585) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1118) |
| Отменено до отправки | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-620) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1153) |
| Недостаточно средств источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-655) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1188) |
| Расчёт устарел | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-693) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1226) |
| Выплаты остановлены | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-728) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1261) |
| Требуется второй Owner | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-766) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-1299) |
| Owner B · независимая проверка | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-806) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-596) |
| Подтверждение Owner B сохранено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-844) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-634) |
| Реквизиты PART-024 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-879) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-669) |
| Предложение реквизитов | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-935) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-725) |
| Реквизиты ожидают проверки | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-983) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-773) |
| Owner B · реквизиты v2 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1021) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-811) |
| Версия реквизитов активирована | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1056) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-846) |
| Предложение отклонено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1089) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-879) |
| Защитные пороги выплат | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1122) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-912) |
| Новая защитная policy | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1160) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-950) |
| Policy не готова | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1208) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-998) |
| Owner B · проверка policy | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-767) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1034) |
| Выплата принята · комиссия партнёра | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1417) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1684) |
| Проверяется · комиссия партнёра | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1450) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1717) |
| Полная выплата · комиссия партнёра | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1483) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1750) |

## ADM-14 · Сотрудники и доступ

Частично. Вход, MFA, пять сотрудников, назначения/изменения/отзыв ролей, компрометация и scoped recovery.

| Состояние | RU | EN |
| --- | --- | --- |
| Сотрудники и доступ | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-6876) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55811) |
| STAFF-203 · Operations | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-6995) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55931) |
| Кастомная роль · Маркетолог | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-7106) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56043) |
| Предпросмотр итогового доступа | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-7243) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56179) |
| Роль сохранена · demo | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-7358) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56295) |
| Роль изменена другим сотрудником | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-7456) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56394) |
| Admin-сессии STAFF-203 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-51751) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56488) |
| Отозвать admin-сессию? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-51860) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56597) |
| Сессия отозвана · demo | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-51959) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56696) |
| Заблокировать скомпрометированный аккаунт? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52058) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56795) |
| Аккаунт заблокирован · demo | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52165) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-56902) |
| Недостаточно прав | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-53375) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-58112) |
| Вход в Shadow Admin | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-9959) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67538) |
| Подтвердите вход | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-9997) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67576) |
| Не удалось подтвердить вход | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-10035) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67614) |
| Сеанс завершён | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-10057) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67636) |
| Доступ этого сеанса отозван | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-10079) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67658) |
| Доступ обоих Owner потерян | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-10101) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67680) |
| Восстановление Owner: безопасный порядок | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-10212) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67791) |
| Назначить роль сотруднику | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-57454) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-67897) |
| Проверка назначения роли | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-57580) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68023) |
| Роль назначена · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-57700) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68143) |
| Редактировать роль «Маркетолог» | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-57816) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68259) |
| Изменение прав · v2 → v3 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-57954) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68397) |
| Версия роли сохранена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58065) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68508) |
| Снять назначение роли? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58172) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68615) |
| Назначение снято · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58283) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68726) |
| Расширение доступа запрещено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58390) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68833) |
| Восстановление учётной записи | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59614) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70057) |
| Независимая проверка сотрудника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59729) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70172) |
| Доступ сотрудника восстановлен · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59844) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70287) |
| Восстановление не разрешено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59959) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70402) |

## ADM-15 · Подключения и безопасность

Частично. Health обеих площадок, изоляция/scoped recovery, заполненный учебный USDT-профиль и уведомления.

| Состояние | RU | EN |
| --- | --- | --- |
| Polymarket · подключение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-5947) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-54585) |
| Limitless · подключение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-6061) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-54699) |
| Изолировать Polymarket? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-6273) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-54913) |
| Изолировать Limitless? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-6382) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55023) |
| Подключение изолировано в Shadow | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-6491) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55133) |
| Подключение изолировано в Shadow | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-6598) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55241) |
| USDT / USD · контроль отклонения | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2109-6705) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55349) |
| Настройки контроля USDT | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-6537) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55469) |
| Настройки не готовы | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-6667) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55600) |
| Предупреждение USDT · пример | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-6766) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-55700) |
| Polymarket · проверка завершена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58492) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-68935) |
| Проверка возврата Polymarket | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58598) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69041) |
| Независимая проверка Polymarket | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58727) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69170) |
| Polymarket · возврат проверенных функций | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58837) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69280) |
| Polymarket · восстановление заблокировано | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-58947) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69390) |
| Limitless · проверка завершена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59053) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69496) |
| Проверка возврата Limitless | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59159) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69602) |
| Независимая проверка Limitless | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59288) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69731) |
| Limitless · возврат проверенных функций | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59398) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69841) |
| Limitless · восстановление заблокировано | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-59508) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-69951) |
| USDT / USD · нормальный учебный сценарий | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-63876) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-74319) |
| Настройки контроля · заполненный пример | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-64012) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-74455) |
| Проверка учебного профиля | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-64155) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-74598) |
| Учебный профиль сохранён | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-64269) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-74712) |
| Настройки изменились | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-64904) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-74822) |
| Основной источник недоступен | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65005) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-74923) |
| Источники курса расходятся | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65119) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75037) |
| Критическое отклонение · учебный пример | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65233) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75151) |
| Уведомления контроля USDT | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65347) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75265) |
| ALERT-017 · критическое отклонение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65467) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75385) |
| Ознакомление отмечено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65581) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75499) |
| Тестовая доставка не удалась | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65687) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75605) |
| Результат доставки неизвестен | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65788) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75706) |
| Цена нормализовалась: запрет ещё действует | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-65893) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75811) |
| Независимая проверка рыночного gate | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66027) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-75925) |
| Рыночный gate снят · учебный пример | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-66141) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-76039) |

## ADM-16 · Тексты и языки

Запланировано. Каталог, RU/EN, версии, предпросмотр и публикация по правам.

Макеты ещё не созданы.

## ADM-17 · Аварийное управление

Частично. GLOBAL_STOP и четыре отдельных ограничения: область, применение, независимое восстановление.

| Состояние | RU | EN |
| --- | --- | --- |
| Аварийное управление | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52505) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57242) |
| Включить глобальную остановку? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52624) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57361) |
| Остановка применена не полностью | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52729) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57466) |
| GLOBAL_STOP включён · demo | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52837) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57574) |
| Проверка перед восстановлением | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-52944) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57681) |
| Независимая проверка восстановления | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-53061) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57798) |
| Поэтапное восстановление · demo | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-53171) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-57908) |
| Восстановление заблокировано | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-53282) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2110-58019) |
| Технический режим | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60069) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70512) |
| Включить ограничение? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60194) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70637) |
| Применение не подтверждено полностью | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60308) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70751) |
| Ограничение применено · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60418) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70861) |
| Проверка перед восстановлением | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60532) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-70975) |
| Независимое подтверждение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60653) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-71096) |
| Поэтапный возврат функций | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60767) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-71210) |
| Возврат функций заблокирован | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60881) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-71324) |
| Отключение пополнений | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-60991) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-71434) |
| Включить ограничение? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-61116) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-71559) |
| Применение не подтверждено полностью | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-61230) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-71673) |
| Ограничение применено · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-61340) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-71783) |
| Проверка перед восстановлением | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-61459) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-71902) |
| Независимое подтверждение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-61580) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72023) |
| Поэтапный возврат функций | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-61694) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72137) |
| Возврат функций заблокирован | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-61808) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72251) |
| Отключение пользовательских выводов | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-61918) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72361) |
| Включить ограничение? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62043) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72486) |
| Применение не подтверждено полностью | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62157) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72600) |
| Ограничение применено · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62267) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72710) |
| Проверка перед восстановлением | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62381) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72824) |
| Независимое подтверждение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62502) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-72945) |
| Поэтапный возврат функций | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62616) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73059) |
| Возврат функций заблокирован | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62730) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73173) |
| Отключение выплат партнёрам | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62840) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73283) |
| Включить ограничение? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-62965) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73408) |
| Применение не подтверждено полностью | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-63079) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73522) |
| Ограничение применено · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-63189) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73632) |
| Проверка перед восстановлением | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-63303) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73746) |
| Независимое подтверждение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-63424) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73867) |
| Поэтапный возврат функций | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-63538) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-73981) |
| Возврат функций заблокирован | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-63652) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-74095) |
| Поступления при отключённых пополнениях | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-63762) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2138-74205) |

## ADM-18 · Маркетинг

Запланировано. Объявления в приложении, аудитория, расписание, доставка. Публикация по правам.

Макеты ещё не созданы.

## Правило поддержания

Обновлять эту же карту при каждом дизайн-пакете, сохранять реальные ID и RU/EN соответствия. Ссылки карты открывают редактор; реальные реакции прототипа проверяются отдельно. Статус «Макеты есть» не означает согласованную функцию или реализацию. Для следующих шагов использовать текущий ROADMAP, исторические срезы не расширяют задачу.

## Личный кабинет сотрудника · пакет 05

[RU](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2155-19298) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2155-79040). 38 новых состояний на язык внутри ADM-14; всего 254 RU + 254 EN. Вход через иконку профиля справа, как в клиентском UI. Язык перенесён в личный профиль; 432 прежних переключателя удалены. Основной сайдбар не расширен. Подробные IDs и ограничения — [пакет 05](package-05/README.md).

## Поддержка · пакет 06

13.10.2026: 33 RU + 33 EN новых состояний в ADM-09, всего 287 RU + 287 EN. [RU](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2185-21070) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2188-84282). [Материалы и границы](package-06/README.md). Sidebar14, статус частично/на вычитке.


13.10.2026 · ревизия 0.8: ADM-16 на вычитке, 34 RU + 34 EN новых состояний; всего 329 RU + 329 EN. [Пакет и реестр](package-07/README.md).


13.10.2026 · ADM-18: 37 RU + 37 EN состояний на вычитке. Всего 366 RU / 366 EN root frames; living sitemap 0.9, UI kit 0.4.17. [Пакет 08](package-08/README.md). Следующая область — трейдеры/данные, затем общие ops очереди и сквозная вычитка.

13.10.2026 · revision 0.10: ADM-07 «Данные и рейтинг» в группе «Управление»: 41 RU / 41 EN состояний. Всего 407 RU + 407 EN root frames. [Пакет 09](package-09/README.md); машинная карта — sitemap.json; карточка 2105:5809 ведёт на 2395:34055.

Revision 0.11: 425 RU +425 EN root frames. [Пакет 10](package-10/README.md): единый вход «Инциденты и сверка» в Management; 18 RU/EN состояний суммарно ADM-04/05.


14.10.2026: [Контекстные подсказки аварийных ограничений](control-help-2026-10-14/README.md). UI kit 0.4.20; карта 0.12, 427 RU +427 EN.
