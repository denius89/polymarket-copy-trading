# Каталог проектных навыков S01–S23

17.10.2026 · версия 0.3 · подготовка AI Product Engineering System для существующего Controlled Copy Trading.

Подготовлены все 23 проектные процедуры и 23 начальных учебных пакета. Три навыка первой партии сохранены с их независимыми проверками; остальные 20 имеют предметные workflows, знания, практику и отдельные новые задания. Это рабочая библиотека подготовки/review, а не заявление о полном освоении всех профессий.

Общие границы: [OPERATING_RULES](OPERATING_RULES.md). Машинный индекс: [catalog.json](catalog.json). Источники: [43 карточки](knowledge/sources.json) с разным охватом чтения; одна страница недоступна, два project API locators требуют перечитывания. Все 43 не объявлены полностью проверенными учебниками.

| ID | Процедура | Учебный пакет | Зависимости знаний | Проверка |
| --- | --- | --- | --- | --- |
| S01 | [Рамка проекта](../../.agents/skills/cct-project-context/SKILL.md) | [Практика](learning/S01.md) | — | Первая партия: независимые сценарии v0.2 |
| S02 | [Продукт, рынок и экономика](../../.agents/skills/cct-product-discovery/SKILL.md) | [Практика](learning/S02.md) | S01, S21, S03, S22 | Структура pass; 1 независимый synthetic кейс pass |
| S03 | [Механика рынков и денежные инварианты](../../.agents/skills/cct-market-domain/SKILL.md) | [Практика](learning/S03.md) | S01, S21 | Структура pass; 1 независимый synthetic кейс pass |
| S04 | [Финансовый UX и UI](../../.agents/skills/cct-financial-ux/SKILL.md) | [Практика](learning/S04.md) | S03, S05, S08 | Структура pass; 1 независимый synthetic кейс pass |
| S05 | [Работа с Figma и передача](../../.agents/skills/cct-figma-handoff/SKILL.md) | [Практика](learning/S05.md) | S01, S10 | Структура pass; 1 независимый synthetic кейс pass |
| S06 | [Качество frontend и performance](../../.agents/skills/cct-frontend-quality/SKILL.md) | [Практика](learning/S06.md) | S04, S05 | Структура pass; 1 независимый synthetic кейс pass |
| S07 | [Backend, БД и целостность](../../.agents/skills/cct-backend-data/SKILL.md) | [Практика](learning/S07.md) | S03, S08, S22 | Структура pass; 1 независимый synthetic кейс pass |
| S08 | [Кошельки, права и безопасность админки](../../.agents/skills/cct-wallet-security/SKILL.md) | [Практика](learning/S08.md) | S01, S03 | Структура pass; 1 независимый synthetic кейс pass |
| S09 | [Надёжность и эксплуатация](../../.agents/skills/cct-reliability-operations/SKILL.md) | [Практика](learning/S09.md) | S17, S23 | Структура pass; 1 независимый synthetic кейс pass |
| S10 | [Качество AI](../../.agents/skills/cct-ai-quality/SKILL.md) | [Практика](learning/S10.md) | S01 | Первая партия: независимые сценарии v0.2 |
| S11 | [Данные собственного Copy Score](../../.agents/skills/cct-score-data-audit/SKILL.md) | [Практика](learning/S11.md) | S03, S22 | Структура pass; 1 независимый synthetic кейс pass |
| S12 | [Реалистичность replay копирования](../../.agents/skills/cct-copy-replay/SKILL.md) | [Практика](learning/S12.md) | S11, S03 | Структура pass; 1 независимый synthetic кейс pass |
| S13 | [Исследование методики Copy Score](../../.agents/skills/cct-score-methodology/SKILL.md) | [Практика](learning/S13.md) | S11, S12 | Структура pass; 1 независимый synthetic кейс pass |
| S14 | [Независимая валидация Copy Score](../../.agents/skills/cct-score-validation/SKILL.md) | [Практика](learning/S14.md) | S10, S12, S13 | Структура pass; 1 независимый synthetic кейс pass |
| S15 | [Версии и управление скором](../../.agents/skills/cct-score-governance/SKILL.md) | [Практика](learning/S15.md) | S08, S14 | Структура pass; 1 независимый synthetic кейс pass |
| S16 | [Понятное объяснение скора](../../.agents/skills/cct-score-explanation/SKILL.md) | [Практика](learning/S16.md) | S04, S14, S15 | Структура pass; 1 независимый synthetic кейс pass |
| S17 | [План инфраструктуры](../../.agents/skills/cct-infrastructure-plan/SKILL.md) | [Практика](learning/S17.md) | S07, S08 | Структура pass; 1 независимый synthetic кейс pass |
| S18 | [Подготовка настройки и hardening](../../.agents/skills/cct-server-hardening/SKILL.md) | [Практика](learning/S18.md) | S08, S17, S20 | Структура pass; 1 независимый synthetic кейс pass |
| S19 | [Выпуск, восстановление и данные](../../.agents/skills/cct-deployment-data-ops/SKILL.md) | [Практика](learning/S19.md) | S07, S09, S18, S23 | Структура pass; 1 независимый synthetic кейс pass |
| S20 | [Git, PR и сохранение изменений](../../.agents/skills/cct-git-collaboration/SKILL.md) | [Практика](learning/S20.md) | S01, S10 | Структура pass; 1 независимый synthetic кейс pass |
| S21 | [База знаний](../../.agents/skills/cct-knowledge-curation/SKILL.md) | [Практика](learning/S21.md) | S01 | Первая партия: независимые сценарии v0.2 |
| S22 | [Возможности API Polymarket и Limitless](../../.agents/skills/cct-venue-api-review/SKILL.md) | [Практика](learning/S22.md) | S03, S10 | Структура pass; 1 независимый synthetic кейс pass |
| S23 | [Сквозная стратегия качества](../../.agents/skills/cct-product-qa/SKILL.md) | [Практика](learning/S23.md) | S06, S07, S08 | Структура pass; 1 независимый synthetic кейс pass |

## Выбор и использование

Из родительской папки чата читать нужный `.agents/skills/cct-…/SKILL.md` явно. Наличие файла не доказывает автоматический discovery в текущей/новой сессии. Сначала выбрать предмет задачи; соседние процедуры подключать только когда нужны их знания/evidence. Зависимости не разрешают автоматически запускать работу или агентов.

Документальный review не превращается в реализацию. S18/S19 сейчас готовят/оценивают runbooks; само описание provisioning/deploy не разрешает серверные действия. Для дальнейшего разрешённого исполнения потребуется актуальный environment-specific контекст, подходящие инструменты и принятые gates.

## Знания и ограничения

Предметные опоры: [продукт](knowledge/domains/product.md), [дизайн](knowledge/domains/design.md), [домен и инженерия](knowledge/domains/engineering.md), [скор](knowledge/domains/score.md), [операции](knowledge/domains/operations.md), [Git/Figma](knowledge/domains/collaboration.md). У каждой области есть текущие правила, исключения и маршруты чтения. Глубокий curriculum, актуальные vendor limits, юридические источники под страну/оператора и первичные научные работы выбираются под конкретное решение — вводная страница не заменяет эту работу.

## Проверки и evidence

[Первая тройка](FIRST_BATCH.md) сохраняет проверку v0.2. [Проверка полного каталога](evals/independent-catalog-2026-10-17/REPORT.md) отделяет structure, независимый synthetic кейс и manual metadata routing. Один кейс на навык — smoke, не доказательство универсальной компетенции или production readiness. Сравнение с baseline, токены/экономия и automatic discovery не измерялись.

Подготовка не меняет код продукта, функции, финансовые правила, score method, API-аккаунты, Figma, серверы или публикации.
