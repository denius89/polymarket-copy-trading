# EN RU тексты ключевого пути paper MVP

Уточнение 02.10.2026: [ADR-0013](decisions/0013_consolidated_ux_and_risk_boundaries.md) и [план 55](55_consolidated_product_plan_2026-10-02.md) имеют приоритет в изменённых правилах. При первом входе показать демо, прохождение необязательно; будущая реальная ветка имеет отдельные gates. Мониторинг предлагает ручные действия, финансовые пороги ещё не утверждены.

Дата: 29.09.2026. Статус: рабочий каталог для следующего Figma-прототипа. English — исходная версия, русский — полноценная первая локаль. Численные defaults приняты в ADR-0012.

## Правила прототипа

- Экран всегда явно сообщает, что shadow не использует реальные деньги.
- `Profit` не используется для неопределённого результата; показывается `Profit/loss` или `Result`.
- Виртуальная комиссия не маскируется под фактическое списание.
- Кнопка описывает действие и не обещает исполнение до подтверждения.
- Суммы и даты форматируются по locale; USDT и названия площадок не переводятся.

## Знакомство и просмотр

| Key | English source | Русский |
|---|---|---|
| `language.title` | Choose your language | Выберите язык |
| `onboarding.title` | See how copy trading could work for your budget | Посмотрите, как копирование могло бы работать с вашим бюджетом |
| `onboarding.body` | Follow selected trader actions in a simulation before using real funds. Results may differ from the trader and can include losses. | Наблюдайте за действиями выбранного трейдера в симуляции до использования реальных средств. Ваш результат может отличаться и включать убыток. |
| `onboarding.paperBadge` | Paper mode — no real trades | Демо-режим — без реальных сделок |
| `onboarding.primaryAction` | Browse traders | Смотреть трейдеров |
| `traders.title` | Traders | Трейдеры |
| `traders.quality.label` | Copy quality | Качество копирования |
| `traders.netResult.label` | 30-day simulated result after fees | Результат симуляции за 30 дней после комиссий |
| `traders.drawdown.label` | Largest simulated decline | Максимальное снижение симуляции |
| `traders.copyability.label` | Actions that could be copied | Действия, которые удалось бы скопировать |
| `traders.minBudget.label` | Suggested minimum budget | Рекомендуемый минимальный бюджет |
| `traders.insufficientData` | Not enough data for a rating | Недостаточно данных для рейтинга |
| `traders.manualAddress.action` | Check an address | Проверить адрес |

## Профиль и настройка

| Key | English source | Русский |
|---|---|---|
| `trader.profile.dataPeriod` | Based on {days} days and {count} eligible actions | На основе данных за {days} дней и {count} подходящих действий |
| `trader.profile.venue` | Activity source: {venue} | Источник действий: {venue} |
| `trader.profile.disclaimer` | Past and simulated results do not predict future results. | Прошлые и смоделированные результаты не определяют будущий результат. |
| `shadow.setup.action` | Try in shadow mode | Проверить в демо-режиме |
| `backtest.period.7d` | 7 days | 7 дней |
| `backtest.period.30d` | 30 days | 30 дней |
| `backtest.period.90d` | 90 days | 90 дней |
| `backtest.period.unavailable` | Not enough reliable data for this period | Недостаточно надёжных данных за этот период |
| `budget.title` | Set your copying budget | Задайте бюджет копирования |
| `budget.paper.default` | Starting paper balance: $200 | Начальный демо-баланс: 200 $ |
| `budget.rangeHint` | A budget from {min} to {max} covers this trader’s typical activity more reliably. | Бюджет от {min} до {max} лучше покрывает обычную активность этого трейдера. |
| `budget.insufficient` | This budget may cause more actions to be skipped. | С таким бюджетом больше действий может быть пропущено. |
| `risk.maxPosition.label` | Maximum per position | Максимум на одну позицию |
| `risk.dailyLimit.label` | Daily limit for new positions | Дневной лимит новых позиций |
| `risk.maxAge.label` | Do not copy events older than | Не копировать события старше |
| `risk.default.summary` | 10% per position · 15% new buys per day · 30 sec signal age | 10% на позицию · 15% новых покупок в день · давность сигнала 30 сек |
| `risk.reentry.manual` | Do not reopen this market after a manual close unless I allow it | Не открывать этот рынок снова после ручного закрытия без моего разрешения |
| `risk.explanation` | These limits reduce new exposure. They cannot guarantee a maximum loss. | Эти ограничения уменьшают новое увеличение риска, но не гарантируют максимальный убыток. |

## Регистрация и подтверждение

| Key | English source | Русский |
|---|---|---|
| `account.gate.title` | Save and start your shadow session | Сохраните и запустите демо-сессию |
| `account.gate.body` | Create an account to keep the session and receive important updates. No wallet is required for paper mode. | Создайте аккаунт, чтобы сохранить сессию и получать важные обновления. Для демо-режима кошелёк не нужен. |
| `account.email.label` | Email | Электронная почта |
| `account.email.code.body` | We’ll email you a one-time link or code. No password is required. | Мы отправим одноразовую ссылку или код на почту. Пароль не нужен. |
| `account.create.action` | Create account | Создать аккаунт |
| `account.signIn.action` | Sign in | Войти |
| `review.title` | Review your shadow setup | Проверьте настройки демо-сессии |
| `review.budget` | Copying budget | Бюджет копирования |
| `review.actualFee` | Charged service fee | Фактическая комиссия сервиса |
| `review.actualFee.paperValue` | 0% in paper mode | 0% в демо-режиме |
| `review.virtualFee` | Estimated future service fee | Расчётная будущая комиссия сервиса |
| `review.noRealFunds` | No real funds or orders will be used. | Реальные средства и ордера не используются. |
| `review.start.action` | Start shadow session | Запустить демо-сессию |

## Активная сессия и состояния

| Key | English source | Русский |
|---|---|---|
| `shadow.active.title` | Shadow session active | Демо-сессия активна |
| `shadow.singleSession` | Stop and reconcile the current session before starting another. | Остановите и завершите сверку текущей сессии перед запуском новой. |
| `shadow.progress` | {days} of 7 days · {count} of 10 eligible actions | {days} из 7 дней · {count} из 10 подходящих действий |
| `shadow.result.ready` | Enough data to review this session | Данных достаточно для просмотра результата |
| `shadow.result.insufficient` | Not enough activity to assess this session | Недостаточно действий для оценки этой сессии |
| `activity.copied` | Simulated | Смоделировано |
| `activity.partial` | Partially simulated | Смоделировано частично |
| `activity.skipped` | Skipped | Пропущено |
| `activity.unknown` | Checking result | Уточняем результат |
| `activity.stale.reason` | Received too late to copy within your limit | Получено слишком поздно для установленного вами лимита |
| `activity.budget.reason` | Not enough available budget | Недостаточно доступного бюджета |
| `activity.liquidity.reason` | Not enough market liquidity for the full amount | Недостаточно ликвидности рынка для полной суммы |
| `activity.unknown.body` | We are reconciling this event. New risk-increasing actions are paused until its status is known. | Мы сверяем это событие. Новые действия, увеличивающие риск, приостановлены до уточнения статуса. |
| `activity.help.action` | What happened? | Что произошло? |

## Управление

| Key | English source | Русский |
|---|---|---|
| `control.pause.title` | Pause new positions | Приостановить новые позиции |
| `control.pause.body` | New positions and increases will stop. Simulated reductions, exits and protective actions will continue. | Новые позиции и увеличения остановятся. Смоделированные уменьшения, выходы и защитные действия продолжатся. |
| `control.resume.action` | Resume session | Возобновить сессию |
| `control.stop.title` | Disconnect and keep positions | Отключить и оставить позиции |
| `control.stop.body` | Trader actions will no longer be copied. Pending simulated buys will be cancelled, and remaining positions will require manual management. | Действия трейдера больше не будут копироваться. Ожидающие виртуальные покупки отменятся, а оставшимися позициями нужно будет управлять вручную. |
| `control.close.title` | Close positions and disconnect | Закрыть позиции и отключить |
| `control.close.body` | We will request cancellation of pending buys and closure of open positions. Some positions may remain open until the result is confirmed. | Мы запросим отмену ожидающих покупок и закрытие открытых позиций. Часть позиций может оставаться открытой до подтверждения результата. |
| `control.close.confirm` | Request close and disconnect | Запросить закрытие и отключить |
| `control.closing` | Closing requested | Закрытие запрошено |
| `control.partialClose` | Partially closed | Закрыто частично |
| `control.closed` | Closed and disconnected | Закрыто и отключено |
| `control.closeFailed` | Some positions could not be closed | Некоторые позиции не удалось закрыть |

## Результат и обратная связь

| Key | English source | Русский |
|---|---|---|
| `result.title` | Your simulated result | Ваш результат симуляции |
| `result.balance.start` | Starting virtual balance | Начальный виртуальный баланс |
| `result.balance.end` | Ending virtual balance | Итоговый виртуальный баланс |
| `result.balance.changed` | Balance changed during this session. Do not compare this result directly with an uninterrupted session. | Баланс изменялся во время этой сессии. Не сравнивайте результат напрямую с непрерывной сессией. |
| `result.pnlAfterFees` | Simulated profit/loss after virtual fees | Виртуальная прибыль или убыток после расчётных комиссий |
| `result.maxDrawdown` | Largest simulated decline | Максимальное снижение симуляции |
| `result.copySummary` | {copied} simulated · {partial} partial · {skipped} skipped | {copied} смоделировано · {partial} частично · {skipped} пропущено |
| `feedback.setup.question` | How clear was what would happen next? | Насколько понятно было, что произойдёт дальше? |
| `feedback.result.question` | What would stop you from continuing? | Что мешает вам продолжить? |
| `feedback.stop.question` | Why did you stop this session? | Почему вы остановили эту сессию? |
| `feedback.other` | Other | Другое |
| `feedback.submit.action` | Send feedback | Отправить отзыв |

## Уведомления

| Key | English source | Русский |
|---|---|---|
| `notification.inApp.label` | In-app notifications | Уведомления в приложении |
| `notification.telegram.label` | Telegram notifications | Уведомления в Telegram |
| `notification.telegram.connect` | Connect Telegram | Подключить Telegram |
| `notification.telegram.optional` | Optional. You can use the product without Telegram. | Необязательно. Продукт работает без Telegram. |
| `notification.critical.unknown` | We are checking an event with an unknown result. New risk-increasing actions are paused. | Мы уточняем результат события. Новые действия, увеличивающие риск, приостановлены. |
| `notification.critical.closeIssue` | Some positions are still open after your close request. | После запроса на закрытие некоторые позиции всё ещё открыты. |
| `notification.summary.title` | Weekly shadow summary | Недельный итог демо-сессии |
| `notification.summary.daily` | Daily summary | Дневная сводка |
| `notification.summary.weekly` | Weekly summary (default) | Недельная сводка (по умолчанию) |
| `notification.sessionReminder.title` | You’ve been viewing this session for 60 minutes | Вы просматриваете эту сессию уже 60 минут |
| `notification.sessionReminder.body` | Review what changed or pause new positions. | Проверьте изменения или приостановите новые позиции. |
| `notification.sessionReminder.continue` | Continue viewing | Продолжить просмотр |
| `notification.sessionReminder.history` | Open history | Открыть историю |
| `notification.sessionReminder.pause` | Pause new positions | Приостановить новые позиции |

## Проверка макетов

Все строки проверяются на ширинах 320, 360 и 390 px, при увеличении текста до 200% и с расширением на 30–40%. Кнопки риска и последствий не обрезаются. Переключение языка сохраняет экран, бюджет, лимиты и состояние сессии.
