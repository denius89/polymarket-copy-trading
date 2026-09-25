# Карта документов

Эта страница помогает быстро найти актуальный источник и отличить решение от гипотезы или исторического черновика.

## Начать отсюда

| Порядок | Документ | Зачем читать |
|---:|---|---|
| 1 | [Текущее состояние](PROJECT_STATE.md) | последние решения, факты, блокеры и ближайший результат |
| 2 | [Дорожная карта](ROADMAP.md) | этапы, очередь работ и условия перехода |
| 3 | [Архитектурные решения](decisions/README.md) | принятые и предложенные ADR |
| 4 | [Правила совместной работы](../CONTRIBUTING.md) | как менять документы и позднее код |

## Основные документы

| № | Документ | Область | Текущий статус |
|---:|---|---|---|
| 01 | [Продукт и экономика](01_product_and_economics.md) | ценность, границы, выручка, метрики | рабочий; тариф принят, остальные разделы ещё консолидируются |
| 02 | [Техническая концепция](02_technical_concept.md) | компоненты, данные, кошелёк, исполнение | рабочий; зависит от spike-проверок |
| 03 | [План реализации](03_execution_plan.md) | полный жизненный цикл продукта | исходный план; текущая очередь находится в ROADMAP |
| 04 | [Перспективы](04_project_outlook.md) | потенциал и условия масштабирования | стратегическая гипотеза |
| 05 | [Vibe-coding процесс](05_vibecoding_operating_plan.md) | рабочие циклы, модели и лимиты | действующий процесс с устаревшей очередью этапов |
| 06 | [UX-аудит](06_ux_audit_and_user_flow.md) | сценарии, экраны и состояния | рабочий материал; wireframes приостановлены |

## Материалы текущего пересмотра

| № | Документ | Что в нём |
|---:|---|---|
| 07 | [Пересмотр стратегии и архитектуры](07_strategy_architecture_review.md) | причины паузы и рамка пересмотра |
| 08 | [Агентский канал](08_agent_distribution_and_onboarding.md) | рефералы, onboarding и готовый комплект привлечения |
| 09 | [Рейтинг, комиссия и партнёрская программа](09_product_decisions_and_partner_tiers.md) | принятая тарифная сетка, начисления и защита пользователя |
| 10 | [GEO shortlist](10_geo_shortlist.md) | Сомали, Бангладеш, Марокко, Египет и Таиланд |
| 11 | [Карточка разговора с агентами](11_agent_call_sheet.md) | вопросы и фиксация результатов |
| 12 | [Архитектурные блокеры и spikes](12_architecture_blockers_and_spikes.md) | что нужно доказать до разработки |
| 13 | [Доверие, полномочия и состояния](13_trust_permissions_and_state_model.md) | signer, ledger, ордера, risk gates и reconciliation |
| 14 | [Аудит Limitless](14_limitless_read_only_audit.md) | пригодность данных и ограничения исполнения |
| 15 | [Целевая аудитория](15_target_audience_and_personas.md) | историческая сегментация; текущая персона в ADR-0009 |
| 16 | [Привлечение без обещаний дохода](16_acquisition_and_safe_messaging.md) | актуальный shadow и сообщения; агентский вход перенесён post-MVP |
| 17 | [Экономика и защитные ограничения](17_colleague_ideas_economics_and_controls.md) | расчёты коллеги, тарифный вариант и risk controls |
| 18 | [Позиционирование первой проверки](18_first_validation_positioning.md) | рабочее обещание; персона обновлена ADR-0009 |
| 19 | [Доступ к API Polymarket](19_polymarket_api_access.md) | публичные API, CLOB credentials, Builder Program и session-key request |
| 20 | [Партнёрская интеграция Limitless](20_limitless_partner_integration.md) | FutureHaus, Programmatic API, scopes, комиссии и gates |
| 21 | [План доступа и spikes Polymarket](21_polymarket_access_and_spike_plan.md) | исполнимый checklist регистрации, запросов и безопасных проверок |
| 22 | [План доступа и spikes Limitless](22_limitless_access_and_spike_plan.md) | FutureHaus, partner application, письменные вопросы и критерии GO/NO-GO |
| 23 | [Контракт адаптеров двух площадок](23_dual_venue_adapter_contract.md) | общие модели, состояния, интерфейсы, reconciliation и contract tests |
| 24 | [Параллельные потоки работ](24_parallel_workstreams.md) | исторический технический план до ADR-0009 |
| 29 | [Двуязычная продуктовая основа](29_bilingual_product_language.md) | English/Russian, словарь, безопасные тексты и Figma checklist |
| 30 | [Benchmark Binance Copy Trading](30_binance_copy_trading_ui_benchmark.md) | функции, UX-путь и рекомендации Take / Adapt / Avoid для MVP |
| 31 | [Аудит готовности проекта](31_project_readiness_audit.md) | что готово, что блокирует дизайн, paper, sandbox и live |

## Источники правды по темам

| Вопрос | Сначала открыть |
|---|---|
| Что делаем сейчас? | `PROJECT_STATE.md`, затем `ROADMAP.md` |
| Для кого MVP? | ADR-0009, затем `15_target_audience_and_personas.md` как история исследования |
| Как мы объясняем первую проверку? | ADR-0009, затем актуальные части `18_first_validation_positioning.md` и `16_acquisition_and_safe_messaging.md` |
| Как привлекаем через агентов позже? | `08_agent_distribution_and_onboarding.md`, `16_acquisition_and_safe_messaging.md`; агентский канал не входит в MVP |
| Какая комиссия? | `09_product_decisions_and_partner_tiers.md`, затем раздел открытых решений в `17_colleague_ideas_economics_and_controls.md` |
| Как устроены кошелёк и полномочия? | `13_trust_permissions_and_state_model.md`, ADR-0003 |
| Какие технические вопросы ещё не доказаны? | `12_architecture_blockers_and_spikes.md`, затем исполнимые планы `21` и `22` |
| Какие площадки обязательны и в каком порядке? | ADR-0008, затем ADR-0007 и `ROADMAP.md` |
| Что нужно для API Polymarket? | `19_polymarket_api_access.md`, затем checklist `21_polymarket_access_and_spike_plan.md` |
| Что нужно для API Limitless? | `20_limitless_partner_integration.md`, затем checklist `22_limitless_access_and_spike_plan.md` |
| Как разделены общий core и площадки? | `23_dual_venue_adapter_contract.md`, ADR-0008 |
| Что можно выполнять параллельно сейчас? | `ROADMAP.md` и `31_project_readiness_audit.md` |
| Как закладываем мультиязычность? | `29_bilingual_product_language.md`, ADR-0006 и ADR-0009 |
| Что подсмотреть у Binance Copy Trading? | `30_binance_copy_trading_ui_benchmark.md` |
| Готовы ли мы двигаться дальше? | `31_project_readiness_audit.md`, затем `ROADMAP.md` |
| Когда можно писать MVP? | ADR-0002 и gate в `ROADMAP.md` |

## Правило при конфликте

Приоритет источников:

1. последнее прямое решение основателя, записанное в `PROJECT_STATE.md`;
2. действующий ADR;
3. основной тематический документ;
4. исследовательский материал;
5. старая презентация или исходный handoff.

Конфликт нельзя разрешать молча. Зафиксируйте его как открытое решение или новым ADR.
