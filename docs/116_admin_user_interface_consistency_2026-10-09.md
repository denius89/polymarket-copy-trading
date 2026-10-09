# Админка ↔ пользовательский интерфейс: техническая сверка

Дата: **09.10.2026**. Сопутствующий контракт: [115 — техническая спецификация админки](115_admin_console_technical_specification_2026-10-09.md). Этот документ не разрешает frontend, изменение Figma или live-операции.

## 1. Назначение и предел доказательств

Задача — связать ADM-01–ADM-18 с четырьмя существующими пользовательскими прототипами: Mobile RU `33:2`, Mobile EN `29:2`, Desktop RU `205:2`, Desktop EN `186:2` файла `lxPP2um7FvIbt02K8eeH4T`. Согласованные правила берутся из ADR и последних прямых решений основателя; наличие рисунка не утверждает backend-контракт.

Источники: [106 — предыдущая приёмка](106_four_prototypes_acceptance_2026-10-06.md), [109 — последний срез](109_latest_design_review_2026-10-06.md), [113 — последние кнопки и реакции](113_button_copy_and_reaction_fixes_2026-10-06.md), [114 — аудит админки](114_admin_console_audit_and_plan_2026-10-06.md), [единая бизнес-логика](MVP_BUSINESS_LOGIC.md), [mobile route audit](../design/qa-2026-10-06/mobile-route-audit.md), [desktop route audit](../design/qa-2026-10-06/desktop-route-audit.md).

В этом цикле выполняется read-only структурное чтение конкретных существующих Figma frames и текстов. Оно не является визуальной проверкой, полным аудитом реакций или ручным прохождением Present. Предыдущие проходы документа 106 предшествуют изменениям 109/113. Поэтому утверждение «все четыре финальных прототипа приняты» не подтверждено.

Ссылки ниже показывают существующие опорные состояния, а не готовность всего сценария. Старые узлы из отчётов 49/52 могут оставаться историческими; текущий рабочий маршрут 106/109/113 имеет приоритет. Формулы, durable storage, ввод, настоящие email/Telegram, RBAC и исполнение Figma не реализует.

### 1.1 Свежий структурный срез Figma

09.10.2026 прочитаны 35 опорных узлов на четырёх страницах через Figma API: все найдены. Проверены названия и ограниченные выборки текстовых потомков. Подтверждены разделение first-run / active demo, $200 и отсутствие fills в новой сессии, $180.38 и резерв в подготовленном примере, учебные cancel/fill тексты, переписки D-1042, disconnected будущие счета и отдельная feedback форма Desktop EN. Полное чтение страниц сначала превысило лимит ответа; успешный повтор был ограничен опорными узлами.

Проверка свойства `visible` у текстового слоя не проверяет видимость всех его предков: унаследованные скрытые варианты и дубли текста могли попасть в выборку. Количество больших frames страницы не является количеством рабочих экранов. Поэтому структурный результат не доказывает отсутствие дублей, переносы строк, порядок слоёв или интерактивную доступность. В desktop учебных текстах прочитаны строки с литеральным `\\n`; перед визуальной приёмкой проверить, не показывается ли escape вместо переноса. До screenshot/Present это потенциальный контентный дефект, а не подтверждённый визуальный баг.

## 2. Прямые входы и актуальные опорные узлы

| Сценарий | Mobile RU | Mobile EN | Desktop RU | Desktop EN |
| --- | --- | --- | --- | --- |
| Общий вход, два сценария | `1839:57824` | `1839:57862` | `584:265` | `584:225` |
| Новая пустая сессия | `949:4398` | `949:9307` | `949:13177` | `949:16981` |
| Подготовленная активная главная | `888:1701` | `905:1754` | `905:9074` | `905:9713` |
| Учебная отмена остатка | `1740:12765` | `1740:16753` | `1740:8763` | `1740:23884` |
| FAQ / помощь, документ 52 | `440:57` | `440:770` | `213:350` | `212:499` |
| Переписка поддержки, документ 52 | `663:306` | `669:659` | `673:479` | `671:479` |

[Figma — карта экранов](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1664-2), [единый старт](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3-2).

Опорные текущие средства desktop: RU `905:9228`, EN `905:9867`. Mobile EN future-account: Polymarket `951:9956`, Limitless `1963:4861`, входы с карточек `951:10199`/`951:10202` по документ 113. Funding не означает доступность реальных денег.

## 3. Матрица UI ↔ admin ↔ контракт

| Пользовательская область | Админ-раздел | Общий контракт и требуемая реакция UI | Доказательство / пробел |
| --- | --- | --- | --- |
| Первый запуск, email, пустая новая сессия | ADM-02 Users, ADM-03 Sessions, ADM-12 Audit | `user_id`, `session_id`, `mode`, `venue`, состояние входа, settings version; создание сессии idempotent; один активный сеанс. Нет автоматически добавленной истории или баланса подготовленного примера. | Узлы новой сессии в §2; email-переходы в 106. Настоящий вход/сохранение ещё не реализованы. |
| Подготовленное активное demo | ADM-01/03 | Синтетическое fixture обозначено как demo; изолировано от новых пользовательских сессий, service finance и доходов. | Активные главные в §2; 41 заявка по 106. Учебный partial-fill отдельно и не увеличивает ledger. |
| Настройка фиксированной суммы / процента покупки | ADM-03, ADM-08 preview | `copy_size_mode`, выбранное значение, `settings_version`, timezone, venue. Начальные 3% — редактируемый default, не бюджетная пропорция. Админ показывает те же effective значения; не пересчитывает старые действия. | RU desktop fixed `949:13057`, percent `1707:34154`; EN `949:16861`/`1709:6862`; ADR0014/17 и 101. Числовой ввод прототипом не доказан. |
| Ограничения и причина пропуска | ADM-03, ADM-04, ADM-06 | Применимые ограничения с происхождением; полная желаемая BUY-сумма помещается в каждое. User и admin получают один `reason_code`/evidence. Unknown freshness/fee не заменяются 0. | ADR0018/19/22/23/24/25/28. Полный приоритет нескольких причин и диапазоны — BL-08/BL-06, не принятое правило. |
| Pause, stop copying, close | ADM-03 Controls, ADM-17 | Pause запрещает новые позиции/увеличения и сохраняет обработки уменьшений/выходов; stop copying отделяет отслеживание; close — отдельное намерение с подтверждением. Операторская emergency-пауза не равна пользовательскому закрытию. | ADR0011/13, сокращённые Manage manually/Confirm close в 113. Terminal lifecycle BL-07 открыт; админ не объявляет позиции закрытыми по нажатию stop. |
| Заявки, fills, отмена остатка | ADM-04 Incidents, ADM-05 Reconciliation | Одно operation identity; `requested`, `filled`, `remaining`, `cancel_state`, `reserve`, fee evidence. Late fills уменьшают резерв без двойного расхода; cancel request не является final cancel. | Пять учебных состояний каждой версии в 102 и §2. $20 → $8 fill/$12 reserve → ещё $4 = $12 fill/$8 reserve; весь $20 = «Отмена не успела». |
| Неизвестный итог / зависшая операция | ADM-04/05/12 | `unknown` отдельный статус. Повторная отправка запрещена; резерв сохранён; поддержка может читать/сверять, не исправлять торговую истину вручную. Таймаут не равенfailed. | Mobile EN unknown detail `905:8733` по 106; ADR0020/21/26/27. Все редкие ветки четырёх версий финальным Present не подтверждены. |
| Позиции и результат / отчёт | ADM-03, ADM-05 | Размер/стоимость позиции, PnL и движение средств раздельны. Ручные/detached части не изменяются exits лидера; отсутствие необходимой оценки не равно нулю. Отчёт не разрешает ликвидацию либо удаление истории. | Desktop EN report `1753:7561`, history `1753:7649`, markets `1753:7689`; 106/109. BL-05 lots и BL-07 completion остаются открыты. |
| Demo-средства, PM/LL accounts | ADM-06, ADM-15, ADM-17 | `mode`, venue account ID, available/reserve/position/withdrawable раздельны; disconnected не означает healthy или нулевой реальный баланс. User funds не являются собственностью сервиса. | Средства §2; 49 и 113. Будущие funding операции не подключены. |
| Отключение пополнения/вывода | ADM-17 Emergency | `DEPOSITS_OFF`/`WITHDRAWALS_OFF` от global/environment/venue; UI показывает причину, backend/worker проверяет повторно. Уже выданный адрес/отправленный перевод не отменяется. Прямой внешний кошелёк вне контроля Shadow. | ADR0030 принят; существующие future funding screens могут служить основой. Emergency blocked/recovery states на всех четырёх UI пока не подтверждены. |
| TECH_MODE / GLOBAL_STOP | ADM-17 | TECH_MODE закрывает продуктовые интерфейсы/API/jobs, оставляя emergency console, monitoring/evidence/reconciliation. UI получает безопасный локализованный status reference и заранее опубликованный fallback bundle. Recovery не снимает остальные запреты. | ADR0031; отдельные пользовательские экраны технического режима/восстановления пока не подтверждены. |
| Health двух площадок / stale market data | ADM-06/07/15 | `source_time`, `observed_at`, freshness/capability/health по venue; потеря данных даёт причину пропуска, а не успешный fill или автоматическую торговлю на другой площадке. | Неизвестные показатели каталога в 109; ADR0024/28. Детальный UI degraded overlay и разрешённые пороги не подтверждены. |
| Каталог, поиск адреса, рейтинг | ADM-07 Traders & ingestion | Админ наблюдает provenance, достаточность данных, версию методики и компонент рейтинга. Не «редактирует score» без воспроизводимого пересчёта. Manual address lookup venue-scoped. | Каталог возвращён в 109; first-run только Momentum Fox, full prepared catalog отдельный. ADR0011 рейтинг сохраняется; формулы на неполных данных открыты. |
| Тарифы / расходы / user VIP | ADM-02 VIP, ADM-08 Tariffs | `effective_policy_version`, service/venue/network cost раздельны; userVIP отличается от partnerVIP. Публикация/назначение только Owner, без пересчёта истории. Обычные тексты не меняют тариф. Alpha service fee0% сохраняется до отдельного платного gate. | ADR0035/38/39; user-side effective VIP disclosure ещё не подтверждено. Synthetic $0.01 fill-expense не является текущим тарифом. |
| Поддержка и контекстные обращения | ADM-09 Support, ADM-02/03 | Ticket ownership server-enforced; `user_id`, optional `session_id`, venue/mode + operation/position/event reference; отдельная public conversation и internal notes; staff assignment, message persistence, reply notification. | Threads §2; general Mobile RU `714:97`, EN desktop `714:1536`; контекст `710:97`/`710:262`/`710:427` по 52. Возвраты исправлены 113. Live PM/LL support context пока не смоделирован. |
| Отзыв | ADM-11 Feedback | Не тикет; отдельная очередь и category/status, контекст/actor если доступен. Не обещает персональный ответ. | Desktop EN feedback `1963:37190`/success `1963:37263`; entry `203:508` по 113. |
| Уведомления и Telegram | ADM-10 delivery, ADM-15 provider health | `message_id`, class/purpose, channel, user, locale, template version, delivery evidence. Read/display не равно provider delivered. Optional Telegram не заменяет email-вход. | 52 support reply notification; ADR0013/0033. Откладывается массовый Telegram marketing, а не существующие operational/transactional уведомления. |
| Объявления in-app | ADM-18 Marketing, ADM-16 Content | Publish по scopes без постоянного Owner approval; аудит, версии, расписание, suppress/consent по purpose. In-app announcements отдельно от mandatory incident/support messages. | ADR0031/0033. Текущий notification center можно использовать как вход; announcement placement/schedule/read-tracking не подтверждены четырьмя прототипами. |
| Тексты RU/EN, FAQ и языки | ADM-16 | Стабильные semantic keys с placeholders; draft/publish version, fallback locale, rollback новой версией; preview четырёх сочетаний device/locale. Числа и поведение приходят из contract, не из редактируемой строки. | ADR0034; Figma тексты RU/EN есть, но dynamic content bundle backend отсутствует. Landing builder позже; Figma landing не означает готовый CMS. |
| Owner finance и партнёрские выплаты | ADM-08/13 | USD сводка, USDT 1:1; подтверждённый полный available balance выбранного venue; комиссия отдельно; Owner подтверждает, система выполняет/сверяет; unknown удерживает резерв. Пользовательские кошельки исключены из источников. | ADR0037/0040/0041. Партнёрский кабинет вне MVP; обычный user funding Withdraw не должен запускать partner payout. Платформенные маршруты уточняются при API-интеграции. |
| Роли / audit / admin session revoke | ADM-12/14/15 | Пользователь не получает admin scope; внутренние notes, audit, credentials и health details не отдаются в user API. Revoke admin session не равен разрыву user copying session или venue delegation. | ADR0029/0032; полноценных admin auth/permission states нет в пользовательских прототипах и они там не должны появиться. |

## 4. Противоречия документации, которые 115 должен разрешить

1. **114, таблица demoV1, «Контент/FAQ максимум просмотр»** против принятого ADR0034: управляемые тексты/переводы/версии закладываются сразу. В115 V1 имеет registry, редактор, preview/publish/version contract; landing builder позже.
2. **114, early owner finance/payout «Proposed / детали открыты»** не отражает ADR0040/41 полностью. Уточняется механизм адаптера; полный баланс, Owner-only и автоматическое исполнение после подтверждения уже согласованы. Capability-disconnected состояние не отменяет требования экрана.
3. **114 «консоль не кошелёк/без treasury»** нужно понимать как отсутствие пользовательской custody и открытых секретов. Оно не запрещает согласованный отдельный сервисный payout-worker/signer. Не называть торговый worker процессом выплат.
4. **114 generic mutation partially succeeded** не может стать состоянием партнёрской выплаты. Неполный перевод — reconciliation mismatch; выплаты частями не разрешены. Partial read data, partial enforcement и order partial fills остаются допустимыми отдельными понятиями.
5. **102 счётчик 42 / «добавлена заявка»** исторически заменён 106: 41 текущая заявка + отдельный учебный пример. Пример нельзя включать в баланс/резерв активного fixture.
6. **34 proportional sizing** исторически заменён ADR0014/17: фиксированная сумма либо процент конкретной покупки; UI/админке нужен один effective settings contract.
7. **49 header без общей суммы** не равно отмене нового единого USD reporting ADR0040. Сводка имеет разбивку по площадкам и не даёт расходовать сумму другого venue; демо/пользовательские средства/финансы сервиса раздельны.
8. Старые mandatory Owner approvals marketing/critical text отменены ADR0031. Owner-only pricing/VIP/payout сохраняется, GLOBAL_STOP/TECH_MODE recovery требует независимого второго подтверждающего.

## 5. Пробелы перед реализацией — не новые согласования всего проекта

| Приоритет | Пробел | Что должно быть записано или добавлено |
| --- | --- | --- |
| P0 | Общая проекция user/admin | One source of truth для session/operation/reserve/status/effective policy; user API фильтрует staff/security details. |
| P0 | Emergency UX | Четыре эквивалентных локализованных состояния global/venue funding blocked, paused by service, TECH_MODE; причина без секретов, status reference, разрешённые возвраты; backend barrier независимо от UI. |
| P0 | Unknown/reconciliation | User/admin видят одинаковое подтверждённое состояние; action availability не допускает resend/успех вручную. Переходы после late fills и после рестарта требуют contract tests. |
| P1 | VIP/effective fees | User disclosure ordinary/effective tariff и date/version; expired/revokedVIP; история сохраняет ставку фактического fill. |
| P1 | Announcements/content | Placement объявления, dismiss/read semantics, RU/EN fallback, long texts/mobile, техническое fallback-message вне основного content service. |
| P1 | Support privacy | Раздельность public message/internal note; draft recovery и guest ownership; live context venue/mode/ID; reply notification ссылка на тот же ticket. |
| P1 | Открытые BL05–08 | Lots/manual parts, budget version/time, precision/minimums, quote-age, terminal lifecycle, приоритет рисков. Полный техдок админки не выдаёт их за уже утверждённую торговую логику. |
| P2 | Финальная UI-приёмка | Present после 113 для RU/EN mobile/desktop: first-run, active fixture, context support, funding future, unknown/cancel, feedback; редкие states и 320/360/1280/text zoom отдельно. |

## 6. Контрольные сценарии для совместной проверки

- Один и тот же session ID в user иadmin; первая сессия пустая, prepared fixture имеет свой контекст. Переход из поддержки/средств не меняет fixture илиlocale.
- На паузе новый BUY отклоняется с причиной, confirmed SELL/exits учитываются. Админская пауза не симулирует закрытие позиций.
- $20 intended, $8 filled, cancel pending: user/admin оба показывают $12 reserve. При late $4 fill оба показывают $12 filled/$8 reserve. При полном fill показывают $20/0, не successful cancel.
- Unknown после timeout/restart: резерв сохранён, повтор запрещён. Incident resolved не меняетorder evidence.
- WITHDRAWALS_OFF на Limitless закрывает только соответствующий путь; Polymarket действует по своему capability, GLOBAL_STOP перекрывает оба. Already broadcast transfer продолжается наблюдаться.
- Owner назначает VIP: следующий допустимый расчёт получает новую effective version, старый fill не заменяется. Marketer может изменить текст, не effective rate.
- Support ответ становится public message/notification; internal note никогда не попадает в user thread. Номер, контекст и locale сохраняются.
- In-app announcement публикуется по scope, delivery unknown не размечается delivered; массовые Telegram/email/push не подключаются самостоятельно.
- Partner payout полного available venue balance резервируется один раз, неподтверждённые начисления исключены. Customer funds/PnL не влияют на обязательство. При unknown нельзя выдать новую выплату на этот баланс.

## 7. Итог

Согласованные правила админки могут быть связаны с текущим пользовательским интерфейсом без замены основных маршрутов. Однако полное соответствие не доказано: нужен общий контракт проекций, недостающие emergency/VIP/announcement состояния и финальный Present после последних исправлений. Новые требования выплат относятся к сервисному финансовому контуру и не отменяют частичное исполнение пользовательских ордеров.

## 8. Проверка черновика 115 после разработки

Черновик [115](115_admin_console_technical_specification_2026-10-09.md) прочитан после его создания и сопоставлен с матрицей выше и свежими 35 опорными Figma-узлами. Основные контракты согласованы: две площадки, общий user/admin источник состояния, отдельные финансовые контуры, fresh/fixture isolation, unknown и резервы, order partial fills отдельно от полных partner payouts, Owner-only pricing/VIP/payout, самостоятельная публикация контента/маркетинга, funding controls и отдельный recovery. Документ 115 правильно не заявляет текущую визуальную или интерактивную приёмку.

Ниже замечания первого чтения черновика; все пять внесены в финальный документ 115 и проверены повторным чтением соответствующих разделов. Это техническая полнота уже согласованных интерфейсных сценариев, а не новые продуктовые решения.

| Место 115 | Пробел | Требуемая доработка | Основание |
| --- | --- | --- | --- |
| §13 Support | Ticket имеет только user/session/incident/venue; невозможно достоверно восстановить contextual position/activity/account flow | `TicketContext` с environment/mode/venue и типизированным reference `session/position/order/activity/account`; general question допускает `null`. Backend проверяет принадлежность reference пользователю; привязка сохраняется в переписке и возврате | 52 contextual examples,113 исправленные возвраты; live-read threads D-1042 |
| §13 Support, §18.1 tests | «Общая переписка» не запрещает показ internal notes пользователю | Public `TicketMessage` и staff-only `InternalNote` раздельны по модели/serializer/permissions. Staff evidence и расширенная PII не входят в user response; тест утечки nested context/internal note | Матрица §3 Support privacy; ограниченный пользовательский контекст ADR0029/36 |
| §6.3 | Все BL-01–BL-08 названы открытыми | Указать только остающиеся аспекты BL-05–BL-08 и метрик/защиты; решения BL-01–BL-04 и принятые части последующих вопросов остаются в силе | MVP_BUSINESS_LOGIC §12, ADR0015–28 |
| §11.1 / §17 manual address | Manual address lookup заявлен, но отдельного контракта чтения не хватает | Предлагаемый `readTraderByAddress(venue,address)` с format validation, found/not_found/insufficient_data, provenance; недостаточный рейтинг не препятствует показу найденного профиля, не гарантирует возможность launch | User U04, ADM07, сохранённый manual-address продуктовый путь |
| §4.2 / §5 ADM03 | Команда resume в карте есть, scope в каталоге отсутствует | Явно выбрать `session.resume` либо отдельное обозначенное правило reuse; resume снимает только разрешённую причину паузы, не emergency/venue controls | ADR0011,115 §6.1, матрица §3 Pause |

Исправления самого 115 выполняет автор документа. Итоговый readback: §13 содержит typed TicketContext и public/internal boundary; §6.3 сохраняет закрытые BL-01–04; §11.1 содержит readTraderByAddress; §4.2 содержит session.resume_demo. Все пять замечаний закрыты в спецификации, не в реализации Figma/backend.

## 9. Финальная сверка технического документа

После агентской проверки в 115 добавлены source-spend reservations для конкурирующих выплат разных партнёров, posting matrix и ограничения ledger, typed API/events, bridged destination evidence, deterministic time/version pinning, capability invalidation, неизвестные metadata, operation-specific maintenance и граница control-store outage. Они поддерживают общую user/admin truth и не меняют пользовательские маршруты. Открытые UI-пробелы emergency/VIP/announcements и свежий Present остаются явно обозначенными; эти экраны не создавались.

Устаревшие формулировки 114 о view-only контенте, обязательных approvals и делегировании численных настроек исправлены в тематическом плане. Раздел 4 выше фиксирует найденные при исходном чтении конфликты, а не утверждает, что они остались в новом контракте.

Финансовый повторный review также исправил semantic unique keys без policy version и учёт реальной комиссии неуспешной попытки до освобождения остатков source reservations. Неполный перевод остаётся mismatch/unknown, а не partial-paid.
