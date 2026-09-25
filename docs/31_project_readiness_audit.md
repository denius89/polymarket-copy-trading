# Аудит готовности проекта к дизайну и разработке

Дата: 25.09.2026. Статус: актуальный аудит после ADR-0009 и benchmark Binance Copy Trading.

## Итог

| Этап | Решение | Условие |
|---|---|---|
| Обсуждение дизайна с коллегой | `GO` | можно использовать Drive, benchmark и текущие продуктовые материалы |
| Design brief и карта экранов | `GO` | открытые решения фиксируются вариантами, без скрытых допущений |
| Нейтральные Figma foundations и библиотека состояний | `GO` | без финального бренда и неподтверждённых wallet/API обещаний |
| Сквозной low-fidelity user flow | `CONDITIONAL GO` | сначала определить тип MVP, первый вход и основной режим копирования |
| High-fidelity UI и передача frontend | `NO-GO` | нужны утверждённые scope, onboarding, тариф, админка и feedback |
| Paper MVP на fixtures/recorded data | `NO-GO` по процессу | требуется снять паузу ADR-0002 и разделить paper/live gates |
| Authenticated sandbox | `NO-GO` | потребуются аккаунты площадок и permission plan |
| Live с реальными средствами | `NO-GO` | нужны venue spikes, threat model, legal/GEO и отдельное решение основателя |

Регистрации Polymarket и Limitless не требуются для design brief, информационной архитектуры, Figma foundations или low-fidelity компонентов.

## Что подготовлено хорошо

- идея контролируемого копирования и отличие от простого сигнала;
- Polymarket и Limitless как две обязательные площадки с раздельным live gate;
- основной novice-first пользователь и самостоятельный вход без агента в MVP;
- mobile-first web и минимальная будущая операционная консоль;
- тарифная сетка maker/taker и бесплатное ручное/защитное закрытие;
- бюджет на трейдера, дневной лимит, stale protection и критические уведомления;
- состояния ордеров, неизвестность, reconciliation и safe stop;
- shadow/backtest как путь знакомства без обещания прибыли;
- English и Russian, терминология, plural rules и Figma localization checklist;
- benchmark Binance Copy Trading с рекомендациями `Take / Adapt / Avoid`;
- Figma и Google Drive подключены и проверены;
- документационная навигация, ADR, GitHub templates и автоматическая проверка ссылок.

## P0: решения до утверждения сквозного user flow

### 1. Определение MVP

Сейчас термин означает разные вещи: кликабельный прототип, внешний shadow/paper продукт и закрытый live-продукт. Нужно выбрать один первый выпуск:

- **рекомендуемый вариант:** публично доступный shadow/paper MVP без реальных ордеров, но с реальными или записанными рыночными данными;
- альтернативный вариант: закрытый live MVP, который сразу требует wallet, funding, venue access, security, GEO и legal gates.

Выбор меняет onboarding, набор экранов, комиссии и админку.

### 2. Первый вход новичка

Нужно утвердить порядок:

1. гостевой просмотр;
2. выбор языка;
3. age/GEO eligibility;
4. выбор трейдера;
5. shadow без кошелька либо после аккаунта;
6. регистрация через email/social/passkey;
7. создание или подключение кошелька только перед live;
8. recovery, funding и вывод.

Для design brief можно использовать как основную гипотезу `browse first → shadow first → account → wallet before live`.

### 3. Канонический direct-first продукт

ADR-0009 и `PROJECT_STATE` уже задают самостоятельного неопытного пользователя, но документы 01, 03, 15, 16, 18 и 24 сохраняют agent-first или expert-first сценарии. Перед передачей дизайнеру их нужно консолидировать; старый агентский путь оставить как post-MVP research.

### 4. Основной режим копирования

Документ 06 ставит первым Fixed Amount, а benchmark Binance рекомендует пропорциональное копирование с caps. Нужно выбрать:

- рекомендуемый default: пропорция от выделенного бюджета;
- обязательные caps: общий бюджет, максимум сделки, дневной лимит и допустимый возраст сигнала;
- Fixed Amount — расширенный режим.

### 5. Один тариф для прототипа

Для экранов review, комиссии и результата нужен один тарифный режим. Рекомендуемый вариант для первого shadow/paper MVP — фактическое списание 0% с показом виртуальной комиссии будущего платного тарифа. Первый paid tariff остаётся 0,50% taker / 0,25% maker после отдельного решения.

## P1: закрыть до high-fidelity и frontend handoff

### User application

- утвердить screen inventory и разделить `MVP / later`;
- определить формулу и default sorting короткого рейтинга;
- задать `подходит бюджету / осторожно / недостаточно данных`;
- определить завершение shadow: 72 часа, минимальное число событий и insufficient-data state;
- решить, обязателен ли shadow перед live и можно ли его пропустить;
- утвердить поведение открытых позиций при Pause, Stop и Close and stop;
- выбрать первый канал уведомлений: in-app, email или web push;
- добавить age, GEO, Terms и Risk Disclosure states;
- определить, как пользователь видит и выбирает площадку.

### Operations console

Минимальная спецификация должна включать:

- `Overview` и состояние площадок;
- пользователей и user timeline;
- copy sessions и позиции;
- очередь incidents/reconciliation;
- risk alerts и kill switches;
- версии тарифов и виртуальные/фактические комиссии;
- feedback/support inbox;
- audit log;
- роли `support / operations / security / admin`;
- запрет raw signing, торговли и вывода от имени пользователя.

### Feedback и аналитика

Нужны:

- воронка от landing до результата shadow;
- события запуска/завершения shadow, review тарифа, запуска копирования, pause/stop и отказа;
- короткие in-product вопросы в заранее определённых точках;
- support channel и категории обращений;
- privacy notice, PII boundary, retention и удаление данных;
- правила доступа сотрудников к feedback и пользовательским данным.

### Accessibility

Принять WCAG 2.2 AA как цель и добавить проверки contrast, keyboard/focus, touch targets, reduced motion, error summary и текстовые альтернативы графикам. Документ 29 уже покрывает локализацию, zoom и screen-reader semantics.

### Экономика direct-first

Текущие таблицы в основном вычитают партнёрскую долю 25%. Нужен отдельный сценарий:

- partner share = 0 для MVP;
- direct CAC как неизвестная переменная;
- wallet, инфраструктура и поддержка;
- полная стоимость пользователя отдельно для Polymarket и Limitless;
- виртуальная комиссия shadow и фактическая платная комиссия не смешиваются.

## P0 для live, которые не блокируют дизайн

- доказать owner/signer/recovery/revoke/withdrawal boundary каждой площадки;
- измерить полноту и задержку leader events;
- проверить partial fills, minimum size, slippage и UNKNOWN recovery;
- доказать per-fill fee attribution, collection и reversal;
- создать threat model, secret inventory, RBAC и incident runbooks;
- проверить GEO/eligibility каждого live-пользователя;
- определить public security contact и private reporting channel;
- включать live отдельно для Polymarket и Limitless, deny-by-default.

До этих проверок в маркетинговом UI не используется безусловное утверждение `non-custodial`; корректнее говорить, что торговое разрешение не должно давать сервису право вывода.

## Обнаруженные противоречия документов

| Область | Актуальный источник | Что устарело |
|---|---|---|
| Пользователь и канал | ADR-0009, PROJECT_STATE | документы 01, 15, 16, 18 и 24 частично agent-first/expert-first |
| Языки | ADR-0009, документ 29 | ADR-0006 оставлял launch languages открытыми |
| Порядок площадок | ADR-0007/0008 | `packages/platforms/README.md` называл Limitless альтернативой |
| Paper gate | документ 23 | документы 24/ROADMAP смешивают public-data paper с authenticated access |
| Copy default | документ 06 против документа 30 | Fixed Amount и proportional оба названы первым режимом |
| Текущий процесс | ROADMAP/PROJECT_STATE | AGENTS.md содержал старую очередь и старые границы площадок |

## Что обсудить с коллегой по дизайну

1. Референсы: что нравится и что не нравится.
2. Финтех, букмекерский или смешанный визуальный характер.
3. Dark/light и эмоциональность интерфейса.
4. Рабочее название, бренд и цветовое направление.
5. UI kit и отношение к shadcn/Tailwind-подобной системе.
6. Точный screen inventory и навигация.
7. Guest-first или account-first.
8. Shadow: обязательность, длительность и следующий CTA.
9. Proportional или Fixed Amount как default.
10. Какие показатели рейтинга видит новичок.
11. Тариф, показываемый в MVP.
12. Pause / Stop / Close and stop.
13. Минимальная desktop admin console.
14. Feedback entry point.
15. WCAG 2.2 AA как обязательная цель.

## Следующий рекомендуемый цикл

1. Основатель обсуждает дизайн с коллегой и наполняет Drive.
2. В дизайн-задаче материалы превращаются в annotated moodboard и decision brief.
3. В текущей задаче принимаются пять P0-решений: тип MVP, first-run, direct persona, copy default и тариф прототипа.
4. Консолидируются документы 01, 03, 15, 16, 18 и 24.
5. Утверждаются user/admin screen inventory и feedback taxonomy.
6. После этого создаётся low-fidelity Figma flow на English/Russian.
7. High-fidelity и frontend начинаются отдельным решением.

## Проверки репозитория

- `npm run check`: проходит;
- `git diff --check`: проходит;
- обязательные документы и относительные ссылки: проходят;
- исходный handoff и локальные QA-файлы исключены из Git;
- секреты не обнаружены в отслеживаемых материалах;
- приложение пока не содержит production-кода, что соответствует действующей паузе.
