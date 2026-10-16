# Живая карта админки

Текущий срез 16.10.2026: **522 RU +522 EN корневых макета**, из них 517 основных состояний и 5 технических оболочек на язык. Карта 0.17, набор компонентов 0.4.20 (28 наборов /168 вариантов). [Партнёрские правила, тарифы и VIP](partner-rules-tariffs-vip-2026-10-16/README.md). Ниже — исторический журнал; он не заменяет текущий реестр.

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

Учёт, полная выплата, реквизиты с задержкой 24 часа, формы своих источников и ограничений, ручное и восстановительное пополнение. Часть ветвей ещё открыта.

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
| Полная выплата · комиссию платит партнёр | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2003-778) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2007-778) |
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
| Владелец B · проверка полной выплаты | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-806) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-596) |
| Подтверждение Owner B сохранено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-844) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-634) |
| Реквизиты PART-024 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-879) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-669) |
| Предложение реквизитов | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-935) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-725) |
| Новые реквизиты ожидают проверки | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-983) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-773) |
| Владелец B · новые реквизиты | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1021) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-811) |
| Новый адрес · ожидание 24 часов | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1056) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-846) |
| Предложение отклонено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1089) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-879) |
| Защитные пороги выплат | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1122) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-912) |
| Новая защитная policy | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1160) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-950) |
| Policy не готова | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2004-1208) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-998) |
| Owner B · проверка policy | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-767) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1034) |
| Выплата принята · комиссия партнёра | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1417) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1684) |
| Проверяется · комиссия партнёра | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1450) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1717) |
| Полная выплата · комиссия партнёра | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2005-1483) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2008-1750) |
| Источник выплат · SRC-PM | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-88865) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-43053) |
| Владелец B · изменение источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-89179) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-43369) |
| Проверка пополнения источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-89473) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-43665) |
| Пополнение · результат неизвестен | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-89771) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-43965) |
| Сверка пополнения · без отправки | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-90061) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-44257) |
| Пополнение запрещено · полное отключение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-90355) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-44553) |
| Владелец B · разрешить маршрут восстановления | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-90641) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-44841) |
| Владелец B · восстановительный перевод | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-90935) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-45137) |
| Новый адрес активен · 24 часа истекли | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-91229) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-45433) |
| Смена адреса отменена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-91515) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2827-45721) |
| Добавить собственный источник | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-45444) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-145968) |
| Владелец B · регистрация источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-45784) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-146307) |
| Источник зарегистрирован · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-45939) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-146461) |
| Настройки собственного источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-46074) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-146595) |
| Источник не готов к проверке | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-46418) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-146938) |
| Источник ожидает второго владельца | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-46758) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-147277) |
| Версия источника изменилась | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-46905) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-147423) |
| Конфигурация источника сохранена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-47032) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-147549) |
| Остатки и лимиты источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-47171) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-147687) |
| Проверьте ограничения источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-47442) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-147957) |
| Владелец B · ограничения источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-47709) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-148223) |
| Ограничения сохранены · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-47864) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-148377) |
| Экстренно отключить источник? | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-48007) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-148519) |
| Источник отключён | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-48142) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-148653) |
| Владелец B · возврат источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-48277) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-148787) |
| Пополнить источник своими средствами | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-48424) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-148933) |
| Пополнение принято · ждёт результата | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-48663) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-149171) |
| Пополнение подтверждено · демо | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-48806) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-149313) |
| Пополнение отклонено · подтверждено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-48945) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-149451) |
| Восстановительный перевод · результат неизвестен | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-49084) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-149589) |
| Восстановительное пополнение сверено | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-49227) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2867-149731) |
| Выплата на новый адрес · проверка | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2868-47683) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2868-143426) |
| Баланс источника · состав и подтверждения | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-154943) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-44958) |
| Поступление ожидает подтверждений | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-155101) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-45116) |
| Баланс устарел · отправка недоступна | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-155239) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-45254) |
| Не удалось проверить баланс | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-155385) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-45400) |
| Такая выплата уже создана | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-155523) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-45538) |
| Средства источника уже зарезервированы | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-155661) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-45676) |
| Резервы источника · только просмотр | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-155811) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-45826) |
| Проверка окончательного отказа выплаты | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-155953) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-45968) |
| Выплата не исполнена · отказ доказан | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-156095) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-46110) |
| Получено меньше ожидаемого · инцидент | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-156237) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-46252) |
| Версия реквизитов изменилась | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-156383) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-46398) |
| Подтверждавший владелец утратил доступ | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-156525) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-46540) |
| 24 часа истекли · активация запрещена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-156671) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-46686) |
| Реквизиты v3 · новое предложение | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-156817) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-46832) |
| Владелец B · повторная проверка v3 | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-156955) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-46970) |
| Реквизиты v3 · новые 24 часа | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-157097) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-47112) |
| Выплата · история согласий | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-157235) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-47250) |
| Согласие истекло · отправки нет | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-157381) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-47396) |
| Версия изменилась · согласия отменены | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-157515) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-47530) |
| Разрешение восстановления отозвано | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-157649) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-47664) |
| Срок маршрута восстановления истёк | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-157791) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-47806) |
| Восстановительный перевод · отказ доказан | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-157933) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-47948) |
| Восстановление · перевод не выполнен | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-158079) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-48094) |
| Повторное отключение после отправки | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-158221) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-48236) |
| Архивировать собственный источник | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-158367) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-48382) |
| Владелец B · архивирование источника | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-158509) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-48524) |
| Источник архивирован · история сохранена | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-158651) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-48666) |
| Неполное поступление · подтверждающие данные | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2906-54214) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2906-152259) |
| Источники · после архивирования | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2906-54352) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2906-152397) |

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

GLOBAL_STOP и четыре отдельных ограничения: область, применение, независимое восстановление.

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
| После остановки · очередь операций | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-158785) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-48800) |
| Старое задание требует новой проверки | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-158923) | [Макет](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2904-48938) |

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


16.10.2026: [источники, пополнения, сверка и задержка адреса 24 часа](treasury-review-2026-10-16/README.md). Карта 0.14, 437 RU +437 EN. Новых страниц Figma и компонентных наборов нет.


## Дополнение 16.10 · тарифы, VIP и партнёрские правила

- 08.15 · [Денежное правило партнёров · параметры](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-47968) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-162266)
- 08.16 · [Денежное правило · ожидает владельца B](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-48331) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-162629)
- 08.17 · [Владелец B · денежное правило](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-48491) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-162789)
- 08.18 · [Два согласия · начало запланировано](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-48671) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-162969)
- 08.19 · [Денежное правило · применение в примере](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-48827) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-163125)
- 08.20 · [Второе согласие автора запрещено](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-48991) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-163289)
- 08.21 · [Денежное правило · отклонено](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-49139) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-163437)
- 08.22 · [Денежное правило · версия изменилась](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-49287) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-163585)
- 08.23 · [Денежное правило · срок истёк](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-49435) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-163733)
- 08.24 · [Денежные правила · история](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-49583) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-163881)
- 08.25 · [Партнёрский VIP · денежное исключение](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-49735) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-164033)
- 08.26 · [Партнёрский VIP · ожидает B](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-50021) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-164319)
- 08.27 · [Владелец B · партнёрский VIP](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-50177) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-164475)
- 08.28 · [Партнёрский VIP · два согласия](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-50337) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-164635)
- 08.29 · [Партнёрский VIP · отклонён](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-50497) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-164795)
- 08.30 · [Тариф · новая версия запланирована](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-167711) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-173587)
- 08.31 · [Тариф · действует в расчётном примере](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-167867) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-173743)
- 08.32 · [Тариф · срок завершён](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-168027) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-173903)
- 08.33 · [Тариф · проверка отката](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-168175) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-174051)
- 08.34 · [Тариф · откат новой версией](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-168327) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-174203)
- 08.35 · [Применение тарифа · ожидается](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-168475) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-174351)
- 08.36 · [Применение тарифа · подтверждено в примере](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-168631) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-174507)
- 08.37 · [Применение тарифа · отказ площадки](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-168787) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-174663)
- 08.38 · [Применение тарифа · результат неизвестен](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-168943) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-174819)
- 08.39 · [Применение тарифа · маршрут не поддержан](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-169099) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-174975)
- 02.14 · [Пользовательский VIP · срок и условия](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-169255) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-175131)
- 02.15 · [Пользовательский VIP · проверка](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-169869) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-175639)
- 02.16 · [Пользовательский VIP · запланирован](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-170182) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-175952)
- 02.17 · [Пользовательский VIP · действует](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-170499) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-176269)
- 02.18 · [Пользовательский VIP · срок завершён](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-170820) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-176590)
- 02.19 · [Пользовательский VIP · прекращение](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-171129) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-176899)
- 02.20 · [Пользовательский VIP · прекращён](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-171438) · [EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2936-177208)
