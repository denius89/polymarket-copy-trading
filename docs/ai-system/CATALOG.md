# Каталог проектных навыков S01–S23

17.10.2026 · версия 0.4 · подготовка AI Product Engineering System для существующего Controlled Copy Trading.

Подготовлены все 23 проектные процедуры и 23 начальных учебных пакета. Три навыка первой партии сохранены с их независимыми проверками; остальные 20 имеют предметные workflows, знания, практику и отдельные новые задания. Это рабочая библиотека подготовки/review, а не заявление о полном освоении всех профессий.

Общие границы: [OPERATING_RULES](OPERATING_RULES.md). Машинный индекс: [catalog.json](catalog.json). Источники: [43 карточки](knowledge/sources.json) с разным охватом чтения; одна страница недоступна, два project API locators требуют перечитывания. Все 43 не объявлены полностью проверенными учебниками.

| ID | Процедура | Учебный пакет | Зависимости знаний | Проверка |
| --- | --- | --- | --- | --- |
| S01 | [Рамка проекта](../../.agents/skills/cct-project-context/SKILL.md) | [Практика](learning/S01.md) | — | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S02 | [Продукт, рынок и экономика](../../.agents/skills/cct-product-discovery/SKILL.md) | [Практика](learning/S02.md) | S01, S21, S03, S22 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S03 | [Механика рынков и денежные инварианты](../../.agents/skills/cct-market-domain/SKILL.md) | [Практика](learning/S03.md) | S01, S21 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S04 | [Финансовый UX и UI](../../.agents/skills/cct-financial-ux/SKILL.md) | [Практика](learning/S04.md) | S03, S05, S08 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S05 | [Работа с Figma и передача](../../.agents/skills/cct-figma-handoff/SKILL.md) | [Практика](learning/S05.md) | S01, S10 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S06 | [Качество frontend и performance](../../.agents/skills/cct-frontend-quality/SKILL.md) | [Практика](learning/S06.md) | S04, S05 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S07 | [Backend, БД и целостность](../../.agents/skills/cct-backend-data/SKILL.md) | [Практика](learning/S07.md) | S03, S08, S22 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S08 | [Кошельки, права и безопасность админки](../../.agents/skills/cct-wallet-security/SKILL.md) | [Практика](learning/S08.md) | S01, S03 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S09 | [Надёжность и эксплуатация](../../.agents/skills/cct-reliability-operations/SKILL.md) | [Практика](learning/S09.md) | S17, S23 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S10 | [Качество AI](../../.agents/skills/cct-ai-quality/SKILL.md) | [Практика](learning/S10.md) | S01 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S11 | [Данные собственного Copy Score](../../.agents/skills/cct-score-data-audit/SKILL.md) | [Практика](learning/S11.md) | S03, S22 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S12 | [Реалистичность replay копирования](../../.agents/skills/cct-copy-replay/SKILL.md) | [Практика](learning/S12.md) | S11, S03 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S13 | [Исследование методики Copy Score](../../.agents/skills/cct-score-methodology/SKILL.md) | [Практика](learning/S13.md) | S11, S12 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S14 | [Независимая валидация Copy Score](../../.agents/skills/cct-score-validation/SKILL.md) | [Практика](learning/S14.md) | S10, S12, S13 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S15 | [Версии и управление скором](../../.agents/skills/cct-score-governance/SKILL.md) | [Практика](learning/S15.md) | S08, S14 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S16 | [Понятное объяснение скора](../../.agents/skills/cct-score-explanation/SKILL.md) | [Практика](learning/S16.md) | S04, S14, S15 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S17 | [План инфраструктуры](../../.agents/skills/cct-infrastructure-plan/SKILL.md) | [Практика](learning/S17.md) | S07, S08 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S18 | [Подготовка настройки и hardening](../../.agents/skills/cct-server-hardening/SKILL.md) | [Практика](learning/S18.md) | S08, S17, S20 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S19 | [Выпуск, восстановление и данные](../../.agents/skills/cct-deployment-data-ops/SKILL.md) | [Практика](learning/S19.md) | S07, S09, S18, S23 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S20 | [Git, PR и сохранение изменений](../../.agents/skills/cct-git-collaboration/SKILL.md) | [Практика](learning/S20.md) | S01, S10 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S21 | [База знаний](../../.agents/skills/cct-knowledge-curation/SKILL.md) | [Практика](learning/S21.md) | S01 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S22 | [Возможности API Polymarket и Limitless](../../.agents/skills/cct-venue-api-review/SKILL.md) | [Практика](learning/S22.md) | S03, S10 | 2 сложных кейса; отдельная оценка; CLI implicit pass |
| S23 | [Сквозная стратегия качества](../../.agents/skills/cct-product-qa/SKILL.md) | [Практика](learning/S23.md) | S06, S07, S08 | 2 сложных кейса; отдельная оценка; CLI implicit pass |

## Выбор и использование

Для родительской рабочей папки создана локальная `.agents/skills` ссылка на каталог репозитория. Native CLI discovery проверен: 23 положительных запроса без имён навыков и 5 отрицательных, успешные чтения подтверждены trace. Из реальной родительской папки проверены 23 metadata и одно implicit выполнение S01. Перезагрузка discovery уже открытого Desktop-чата отдельно не проверена; при отсутствии процедуры в его контексте читать её явно. Сначала выбрать предмет задачи; соседние процедуры подключать по нужным знаниям/evidence. Зависимости не разрешают автоматически запускать работу или агентов.

Документальный review не превращается в реализацию. S18/S19 сейчас готовят/оценивают runbooks; само описание provisioning/deploy не разрешает серверные действия. Для дальнейшего разрешённого исполнения потребуется актуальный environment-specific контекст, подходящие инструменты и принятые gates.

## Знания и ограничения

Предметные опоры: [продукт](knowledge/domains/product.md), [дизайн](knowledge/domains/design.md), [домен и инженерия](knowledge/domains/engineering.md), [скор](knowledge/domains/score.md), [операции](knowledge/domains/operations.md), [Git/Figma](knowledge/domains/collaboration.md). У каждой области есть текущие правила, исключения и маршруты чтения. Глубокий curriculum, актуальные vendor limits, юридические источники под страну/оператора и первичные научные работы выбираются под конкретное решение — вводная страница не заменяет эту работу.

## Проверки и evidence

[Первая тройка](FIRST_BATCH.md) сохраняет проверку v0.2. [Проверка полного каталога](evals/independent-catalog-2026-10-17/REPORT.md) отделяет structure, независимый synthetic кейс и manual metadata routing. Один кейс на навык — smoke, не доказательство универсальной компетенции или production readiness. Исторический smoke не измерял automatic discovery. Последующий [глубокий прогон](evals/independent-deep-2026-10-17/REPORT.md) содержит 46 задач, отдельные оценки, исправления/повторы и native CLI discovery. Исходные результаты и ограничения не заменены общим ярлыком «готово». Сравнение с no-skill baseline и экономия не измерены; token counters сохранены только для CLI-прогона.

Подготовка не меняет код продукта, функции, финансовые правила, score method, API-аккаунты, Figma, серверы или публикации.
