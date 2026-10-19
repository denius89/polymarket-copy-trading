# Проверка активации рыночных профилей

19.10.2026 · baseline main `e6642caef80bcb2eafcb75d9e10fbfa3e73a77d4`. Объект: [ADR-0059](decisions/0059_clob_market_profiles_freshness_price_and_fees.md)/[136](136_venue_market_profiles_and_quote_gates_2026-10-19.md). **Результат: ни один профиль пока не допущен к paper-исполнению.** Новые торговые правила не принимаются; runtime остаётся выключенным. [Машиночитаемые статусы](policies/paper-clob-market-profiles-v1.json), [проверки/источники](qa/profile-activation-2026-10-19/README.md), [manifest](qa/profile-activation-2026-10-19/evidence/manifest.json).

## Вывод по семействам

| Профиль | Что подтверждено | Что не позволяет включить |
|---|---|---|
| Polymarket CTF v1 | Публичная книга, 2 начальных снимка/переподключения, replay 12 кадров; market fee fd подтверждён в предыдущей сверке; exponent-1 арифметика совпадает с опубликованными примерами | Не доказана суммарная погрешность часов publisher+collector ≤250 мс; начальные книги могут не пройти возраст 2 с. Нет независимых settlement vectors, границы fee-rounding при разбивке и проверенного исполняющего adapter |
| Polymarket protocol v2 | Правила версии/выбора ID и fee описаны документацией; общие fault fixtures | В ограниченной выборке не наблюдён, отдельные book/units/clock/fee/adapter доказательства отсутствуют |
| Limitless legacy | Публичный поток: 118 полных снимков, начальный снимок после обоих подключений, отдельные synthetic fault checks | Не доказаны часы publisher; точная предварительная fee-кривая/rounding и fee-owner context; обнаружены несовместимости inspected SDK с ожиданиями |
| Limitless COLLATERAL | Формула/half-up и cashflow gross/net проверены reference-векторами | В ограниченной выборке не наблюдён соответствующий venue; нет независимых deployed execution vectors, clock proof и доказанного числа fee charges/верхнего резерва для partial/delayed attempt |
| Limitless AMM | Вне первого исполнимого профиля по решению владельца | Отдельная quote/fee/SELL модель; этот аудит её не включает |

Наблюдение/запись public market data допустимы для двух проверенных семейств; из этого не следует разрешение создавать fills, P&L или резервы при неизвестных данных. Формулы Polymarket exponent=1 и COLLATERAL Limitless готовы как проверяемые reference-модели для разработки, но ещё не как включённый adapter. UI/приложение/Figma не изменены.

## 1. Потоки и восстановление

Записаны **все** полученные relevant кадры двух ограниченных сессий каждой наблюдённой venue (окна 25 и 15 секунд, по одному market); лимит 500 кадров на сессию не достигнут. Polymarket: 7+5 кадров, по одному полному book, остальные price_change. Limitless: 73+45 full snapshots. Время от начала подключения до первого кадра: Polymarket 363/580 мс, Limitless 241/252 мс — в этих четырёх попытках ≤1 с. Это локальное наблюдение, не SLO/p95 или доказательство поведения на любых рынках.

Replay Polymarket связывает market и asset ID, читает `price_changes[].asset_id`, фильтрует другой outcome в том же кадре; size заменяет абсолютный уровень, не прибавляется. Первоначальный наивный разбор по одному top-level asset_id не принимал mixed-outcome кадры; диагностическая модель исправлена и покрыта regression fixture. После новой generation дельты не используют старый seed.

Limitless snapshots заменяют полную книгу. На записанной выборке нет потери identity/конфликтов version; пустоты в нумерации не считаются количеством пропущенных fills. Synthetic fixtures отдельно проверяют duplicate, out-of-order, jump, одинаковую version с разным содержимым, generation restart с меньшим номером, version=0 и чужую identity. Это **смоделированные** неисправности; реальный publisher failover, длительное отключение и исчерпывающая полнота потока не наблюдались. Replay не доказывает атомарный admission или соответствие последующего fill первоначальной книге.

Без clock correction разница receive−source: Polymarket 38–7436 мс, 2 из 12 кадров >2 с (начальные books); Limitless 24–240 мс для 118 кадров. Это диагностические разницы, не сертификат возраста; свежие дельты не доказывают пригодность первоначального состояния без доверенного seed/continuity. В report нет выборочного удаления плохих кадров.

Discovery: один исходный keyset и один newest keyset Polymarket, три страницы по 25 Limitless; точные URL, количества строк/уникальных IDs в evidence. V2/COLLATERAL в этой ограниченной выборке не найдены. Это не утверждение об их отсутствии на площадках. Не подставлять legacy market как доказательство COLLATERAL или CTF как V2.

## 2. Часы

Локальные read-only SNTP запросы, без -s/-S и без изменения системных часов:

| Источник | Оценка смещения | Заявленная диагностическая погрешность |
|---|---:|---:|
| time.apple.com | +6,865 мс | ±58,401 мс |
| time.cloudflare.com | −6,878 мс | ±45,337 мс |

Это согласованные однократные наблюдения локального collector, не подтверждение постоянной синхронизации будущего сервера или независимая гарантия UTC. Чтение host time-service configuration требует администратора; привилегии/настройки не менялись.

Сделаны 8 GET Polymarket `/time`, RTT около 154–168 мс; ответ имеет целые Unix seconds. Если **предположить** floor-to-seconds, один стабильный server clock и генерацию ответа внутри каждого request без кэша, пересечение интервалов server−local даёт примерно **[−119,320; +370,951] мс**, половина ширины 245,135 мс. Эти предпосылки не проверены как контракт. Главное: clock сервера `/time` не доказан тем же clock, который ставит timestamp book publisher. Поэтому это вычисление не закрывает ≤250 мс ADR-0059, даже если условная половина интервала чуть меньше порога. HTTP Date/PONG не исправляют этот пробел. Для Limitless подтверждённый publisher-clock bound в проверенных источниках тоже не получен.

Не повышать порог и не переключаться на receive-time-only ради зелёного статуса. Для активации нужно связанное с конкретным publisher/generation временное доказательство: документированная семантика timestamp и ограничение source-clock error либо проверенный отдельный time protocol/метод с тем же clock domain; затем добавляются collector uncertainty, drift/holdover и monotonic elapsed. Профиль обязан блокироваться при потере этого доказательства. Это требование уже принятой политики, не новый автотест, который можно заменить одним NTP-ответом.

## 3. Комиссии и legacy Limitless

Официальные источники перечитаны 19.10; [реестр](qa/profile-activation-2026-10-19/sources.json). **Торговые запросы, private profile, approvals, keys и on-chain side effects не выполнялись.**

- Polymarket exponent=1: exact reference совпала с опубликованными примерами (100 shares, price=0.5: rate 0.07→1.75; 0.05→1.25; 0.04→1.00). Это проверка формулы на официальных примерах, не независимое воспроизведение реального fee debit/округления по всем match/fill вариантам. Unknown exponents и отсутствие исходного fd не становятся нулевым тарифом.
- Limitless COLLATERAL: 100 shares по 0.40, 500 bps → fee 1.20; BUY debit 41.20 / SELL credit 38.80. Проверены quantum=10 raw, half-up на границе и fee=0 при явно заданном нулевом rate. Это reference-вектора, не подтверждённые транзакции конкретного deployed venue. Reserve должен покрывать доказанную разбивку charges; single-match формула не разрешает предположить единственное списание у любого ордера.
- **Legacy: текущая docs прямо не публикует closed-form curve.** При 300 bps формула whitepaper October 2025 даёт BUY при p=0.60 ровно 2.00% shares, текущая representative table — 2.13%; SELL при p=0.40 — 1.20% collateral против 1.44%. Интерполяция таблицы или перенос формулы другого exchange не обоснованы. Совпадение одной точки около 0.5 не подтверждает кривую. Из полученных после сделки fees нельзя автоматически получить достоверную котировку до сделки.

Дополнительно прочитан официальный TS SDK package **1.2.0**, commit `a1dbd0cbc7a0dd58994a36d4b1dbff1d333bb8ba`:

1. Inspected OrderClient берёт `rank.feeRateBps`, при отсутствии подставляет 300. Документация signing требует `effectiveFeeRateBps`, который может отличаться от rank. Таким образом ни fallback 300, ни signed rate не доказывают текущую применимую fee-кривую. SDK не устанавливался/не запускался; вывод относится к прочитанному commit, не ко всем версиям.
2. Builder при default tick=0.001 требует raw shares кратно 1000, независимо от конкретной цены. API-алгебра при price=0.5 позволила бы 200 raw shares (collateral=100 raw), но этот builder их отвергнет. Пример из 136 с шагом 0.000002 shares описывает минимальную **алгебраическую представимость**, а не доказанный рабочий шаг выбранного SDK. Для его пути требуется более строгая сетка 0.001 shares; нельзя объявить совместимость, проверив только collateral equation.
3. В проверенных OrderClient/Builder нет подтверждённого предварительного calculator, который закрывает различие источников и raw rounding. Проверка verified deployed source по explorer из этой среды не удалась; соответствие исходника адресу/байткоду не доказано. Документацию или похожий контракт нельзя выдать за проверенный deployed implementation.

Следующий минимальный evidence для legacy: authoritative calculator/quote или связанный с deployed contract исходник/версия с формулой и rounding по обеим сторонам; происхождение effective rate конкретного fee owner; raw vectors при p<0.5, =0.5, >0.5, split matches, partial/delayed, cap/rebate и fee-disabled market. Пока это не получено — legacy paper fills/финансовый результат заблокированы. Внешние сообщения площадке этим аудитом не отправлялись.

## Что можно делать дальше

Использовать записанные данные и exact fixtures для реализации parser/replay, clock-gate и fee adapters, сохраняя blocked-состояния и запрет на auto-shrink. Первый кандидат на следующую приёмку — Polymarket CTF v1: для него уже есть market/book/reconnect и понятный источник fee. COLLATERAL Limitless — отдельный следующий кандидат после получения конкретного рынка/контракта и raw vectors. Ни один из этих кандидатов сейчас не получает `enabled`.

Проверки: [18 replay/reference tests](qa/profile-activation-2026-10-19/README.md), включая реальные записи и отдельно обозначенные synthetic faults; общие repository checks отдельно. Аудит не расширяет scope на разработку приложения, deploy или торговые эксперименты.
