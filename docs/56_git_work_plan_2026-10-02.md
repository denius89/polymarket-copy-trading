# План работы в GitHub

Дата: 02.10.2026. Основание: [план 55](55_consolidated_product_plan_2026-10-02.md), [ADR-0013](decisions/0013_consolidated_ux_and_risk_boundaries.md). Это очередь проверяемых результатов, а не разрешение на всю разработку. Каждая строка — отдельная задача, один небольшой PR и ссылка на доказательства. Ответственный назначается командой; сроки оцениваются после разбора зависимостей.

## Очередь и критерии приёмки

| ID | Приоритет / зависимость | Работа и результат PR | Приёмка |
|---|---|---|---|
| G01 | P0 / сейчас | Консолидировать документы 01–03, 23, 34–35, 42–54; таблица «старое правило → новое → ADR → статус». | Нет конфликтов weekly default, optional demo, отдельных счетов, 2FA и мониторинга. Рейтинг и тарифы не заменены неподтверждёнными предложениями. |
| G02 | P0 / G01 | Инвентаризация всех user screens/actions; одна оболочка, шапка, навигация и модель кнопок; Figma links и manifest отдельным PR. | Все действия доступны в RU/EN на ПК/mobile; balance → funds, bell → notifications, avatar → profile. Одна семантика и порядок действий; возвраты сохраняют контекст. Нет пересечений секций. |
| G03 | P0 / G02 | Первый вход, возвращение, настройка, запуск и состояния demo/live. Отдельный тестовый вход для подготовленных сценариев. | Первый запуск предлагает демо, не заставляет проходить его; реальный путь показывает свои gates. Новая демо-сессия начинается пустой, не с выдуманного day-3 результата. Вход сохраняет черновик. |
| G04 | P0 / G02 | Детали событий, ордеров и позиций; история всех статусов; cancel/edit остатка, detach, ручная продажа и длительные операции. | Разделены signal/order/fill/position/settlement; canceled без fill не создаёт позицию. Unknown не допускает blind retry. Отдельные partial, late fill, cancel failure и ручное управление. Возможности площадки явно ограничивают действия. |
| G05 | P0 / G02 | Средства, профиль, тикеты, passwordless вход и отдельные live 2FA/recovery states. | PM/LL/demo не суммируются и не смешивают истории; суммы маркируют дату/состояние. Тикет можно отправить и открыть ответ, auth сохраняет черновик. Демо без 2FA; реальное действие не получает ложный success. |
| G06 | P1 / G01 | Каталог, профиль, периоды, статистика и отчёты; словарь метрик и происхождение каждого поля. | Публичный PnL, личный результат копий и будущий aggregate различимы. 24h/7/30/90 доступны при валидных данных; личная история за время копирования. Weekly/daily выбор проверен; monitor только объясняет. Новые подборки/score сначала согласовать. |
| G07 | P0 / G01; отдельный spike gate | Контракт данных и capability matrix двух adapters: units, fees, freshness, pagination, order states, cancel/replace, wallet permissions, API version. | Для каждого поля указаны endpoint/источник, полнота и fallback. Recorded fixtures без секретов; обнаруживаются пропуски/дубли/late events. Документация API не считается проверкой аккаунта. Миграции API проверены перед интеграцией. |
| G08 | P0 / G07; gate модели | Ledger и virtual lots; атрибуция fills/fees/payouts, equity/PnL/flows; математическая модель автопаузы и atomic reservation. | Расходы один раз; поток денег не выглядит доходом; позиции разных сессий корректно распределены. Replay partial/cancel/unknown/concurrent fills, illiquid/stale, settlement и manual detach. K/H/P и версия риска сохраняются; пороги согласованы после калибровки. |
| G09 | P1 / G07–G08 | Финансы владельца: отдельный ledger сервисных начислений, payments, refunds, referral liabilities, payout reconciliation и read-only обзор. | Начислено/получено/выплачено/долг не смешаны; каждый показатель трассируется до записи и внешнего подтверждения. Клиентские средства не считаются выручкой. Нет admin withdrawal permission. Тарифные альтернативы остаются открыты. |
| G10 | P0 / G03–G06 | QA прототипа: маршруты, понятность, reflow, компоненты, суммы и локализация; коллега получает отдельную checklist. | Проверены 320/360/390 и 1024/1280/1440, длинный RU, 200% текста, контраст и зоны нажатия. Нет пустых кнопок; совпадают задачи на устройствах. Runtime keyboard/screen reader явно отложены до интерфейса. |
| G11 | P0 / G07–G08 + G10 + отдельное разрешение frontend/paper | Минимальный paper вертикальный срез: выбор → risk → account → session → journal → result. | Реальный order sender недоступен технически, fixtures не подменяют факты. Проверены дедупликация, resume/reconciliation, предторговые лимиты и причины skip. Рабочая доступность и соответствие Figma проверены. |
| G12 | Later / G11 + per-venue security/legal/wallet gates | Ограниченный live пилот по отдельному решению, затем видео после готовности всех Figma-экранов. | Каждая площадка проходит gates отдельно. Согласованы капитал, участники, тариф, остановка, recovery и отзыв полномочий. Не считать планы пилота разрешением на деньги. Видео объясняет фактически готовые сценарии. |

## Как вести Git

Задачи созданы через GitHub plugin:

- [G01 · #1](https://github.com/denius89/polymarket-copy-trading/issues/1)
- [G02 · #2](https://github.com/denius89/polymarket-copy-trading/issues/2)
- [G03 · #3](https://github.com/denius89/polymarket-copy-trading/issues/3)
- [G04 · #4](https://github.com/denius89/polymarket-copy-trading/issues/4)
- [G05 · #5](https://github.com/denius89/polymarket-copy-trading/issues/5)
- [G06 · #6](https://github.com/denius89/polymarket-copy-trading/issues/6)
- [G07 · #7](https://github.com/denius89/polymarket-copy-trading/issues/7)
- [G08 · #8](https://github.com/denius89/polymarket-copy-trading/issues/8)
- [G09 · #9](https://github.com/denius89/polymarket-copy-trading/issues/9)
- [G10 · #10](https://github.com/denius89/polymarket-copy-trading/issues/10)
- [G11 · #11](https://github.com/denius89/polymarket-copy-trading/issues/11)
- [G12 · #12](https://github.com/denius89/polymarket-copy-trading/issues/12)


1. Issue содержит проблему, source section, статус решения, зависимости, границы, acceptance checklist и ссылки на Figma/fixtures. Не закрывать по одному факту «экран нарисован».
2. Ветка `docs/...`, `design/...`, `spike/...` или `feat/...`; один проверяемый результат. Никаких ключей, cookies, персональных данных и закрытых reference-файлов.
3. PR объясняет конечное поведение, проверку и оставшиеся ограничения. Обновляет ROADMAP/PROJECT_STATE, если меняются очередь или gates; ADR — при новом принятом решении.
4. Перед публикацией `npm run check` и `git diff --check`; после UI — visual QA, после поведения — соответствующие тесты. Merge не подтверждает readiness live.
5. Работа сейчас: G01–G06 и G10 в документах/дизайне. G07–G09 требуют согласованного spike/model scope; G11 и G12 заблокированы отдельными gates. Сначала закончить согласование и дизайн, не открывать все потоки одновременно.

## Открытые решения, которые нельзя спрятать в задаче реализации

- Название и методика score: ADR-0011 действует до явного замещения; benchmark не является готовой формулой.
- Global/trader risk inheritance, корректная область detach/повторного входа, атрибуция при общей market/outcome позиции.
- Valuation, минимальная ликвидность, stale threshold и финансовые пороги после replay, не по демонстрационным цифрам.
- Реальные permissions, recovery, GEO, 2FA, funding и withdrawal для каждого счёта.
- Монетизация/тарифные альтернативы, доступ к referrals и финансовая сверка владельца; действующую политику не отменять молча.

## Проверка этого документационного цикла

Исходный Google Doc сохранён полностью как текст в 55; согласованные уточнения вынесены в ADR-0013; очередь определена здесь. Figma, frontend и торговые операции в этом цикле не изменяются. Результат публикуется через GitHub plugin в отдельной ветке и PR, задачи G01–G12 ведутся в issue-трекере.
