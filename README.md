![Controlled Copy Trading — Polymarket + Limitless](docs/preview/repository/cover.svg)

# Controlled Copy Trading

**Русский** · [English](README.en.md)

[![Проверка репозитория](https://github.com/denius89/polymarket-copy-trading/actions/workflows/repository-check.yml/badge.svg)](https://github.com/denius89/polymarket-copy-trading/actions/workflows/repository-check.yml)

Mobile-first продукт для контролируемого копирования сделок на **Polymarket** и **Limitless**. Замысел: выбрать трейдера, разобраться в его истории, попробовать демо с виртуальными средствами и задать понятные ограничения копирования.

[Дорожная карта](docs/ROADMAP.md) · [Интерфейсы](docs/design/client/sitemap.md) · [Документация](docs/README.md) · [Исследования](research/TRADER_SCORE_README.md) · [Как работаем](docs/REPOSITORY_GUIDE.md)

> **Этап: техническое планирование · pre-MVP.** Админка v1 согласована; [BI-01–BI-04](docs/design/client/business-rule-fixes-2026-10-27/README.md) исправлены в клиентских прототипах и документах. Приняты [три технических решения](docs/decisions/0062_paper_first_modular_backend_and_first_slice.md); подготовлен [проект первого сценария](docs/technical/first-session/README.md). Приложение и торговые адаптеры ещё не реализованы; реальные операции выключены. Срез — **27 октября 2026**.

## Начать с нужного

| Понять продукт | Посмотреть дизайн | Продолжить работу |
| --- | --- | --- |
| [Правила MVP](docs/MVP_BUSINESS_LOGIC.md) | [Клиент: карта и Final-якоря](docs/design/client/sitemap.md) | [Текущая очередь](docs/ROADMAP.md) |
| [Принятые решения и предложения](docs/decisions/README.md) | [Админка: живая карта](docs/design/admin/sitemap.md) | [Handoff клиентского UI kit](design/client-ui-kit/HANDOFF.md) |
| [Copy Score: исследования и ограничения](research/TRADER_SCORE_README.md) | [Лендинг v2 на согласовании](docs/design/landing/hero-2026-10-19/v2/README.md) | [История и последний результат](docs/PROJECT_STATE.md) |

## Что готово и что впереди

| Область | Состояние |
| --- | --- |
| Клиент и админка | [Админка v1 согласована](docs/design/admin/rebuild/v1-final/README.md); [финансовые состояния клиента исправлены](docs/design/client/business-rule-fixes-2026-10-27/README.md) в четырёх версиях. Полная приёмка работающего приложения впереди. |
| Первый вход | [ADR-0048](docs/decisions/0048_unified_registration_and_first_entry.md) принят; [вход четырёх Final-версий обновлён](docs/design/client/adr48-entry-fixes-2026-10-19/README.md). Runtime-auth и полная сквозная приёмка впереди. |
| Copy Score | Семь исследовательских пакетов и исходные данные сохранены. Формула публичного рейтинга не утверждена. |
| API площадок | Справочники [Polymarket](docs/api/polymarket/README.md) и [Limitless](docs/api/limitless/README.md); свидетельства от 06.10.2026, свежесть проверяется под задачу. |
| Приложение | `apps/` и `packages/` пока описывают будущие границы. Разработка, paper и live проходят отдельные gates. |

Последний дизайн-срез: [админка v1](docs/design/admin/rebuild/v1-final/README.md), [общая клиентская модель](docs/design/admin/rebuild/client-alignment/README.md), [BI-01–BI-04](docs/design/client/business-rule-fixes-2026-10-27/README.md). По [плану 139](docs/139_shadow_technical_implementation_plan_2026-10-27.md) подготовлены [схема данных, команды и приёмка первого сценария](docs/technical/first-session/README.md); код отдельно не поручен. Дизайн и Present не заменяют серверную приёмку.

## Дизайн в Figma

[**Открыть «Начать здесь» →**](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3-2)

| Клиент Final | RU | EN |
| --- | --- | --- |
| Mobile | [Страница макетов](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2477-528) | [Страница макетов](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-2) |
| Desktop | [Страница макетов](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2477-529) | [Страница макетов](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2499-3) |

Ссылки ведут на страницы дизайна, а не запускают готовое приложение. Нужные состояния и маршруты Present выбирайте по [карте клиента](docs/design/client/sitemap.md); админку — по [её карте](docs/design/admin/sitemap.md).

<details>
<summary>Исторический визуальный срез · 6 октября 2026</summary>

Эти изображения показывают прежние демонстрационные макеты. Актуальные входы находятся в таблице выше.

<table><tr><td><img src="docs/preview/2026-10-06/fresh-home-ru.png" width="240" alt="Исторический макет новой демо-сессии, 6 октября 2026"></td><td><img src="docs/preview/2026-10-06/trader-profile-ru.png" width="240" alt="Исторический макет профиля трейдера, 6 октября 2026"></td></tr></table>

</details>

## Где что хранится

```text
docs/               продукт, решения, спецификации и навигация
  design/           контракты экранов, живые карты и проверки дизайна
  ai-system/        знания, обучение и оценки проектных навыков
design/             машиночитаемый handoff UI kit и исторические QA-пакеты
research/           воспроизводимые исследования, код, результаты и manifests
.agents/skills/     проектные навыки и Impeccable
apps/ · packages/   границы будущего приложения; infra/ — план инфраструктуры
artifacts/          опубликованные презентации
scripts/            проверки структуры, ссылок и правил хранения
```

**GitHub** хранит актуальные документы и проверяемые результаты. **Google Диск** — большие исходные данные и закрытые резервные копии. [Единый реестр внешних архивов](docs/storage/catalog.json) содержит ссылки, manifests и контрольные суммы; архивы не скачиваются при clone. [Карта хранения и правила](docs/REPOSITORY_GUIDE.md) объясняют роли папок и порядок восстановления.

## Рабочий цикл

**Задача → отдельная ветка → проверка → PR → main → уборка.** Каждый законченный блок сохраняется вне компьютера. После merge ветка PR удаляется автоматически с проверкой её версии; локальная рабочая копия убирается после проверки сохранности. Незавершённая работа остаётся в своей ветке или draft PR.

```bash
npm run check
npm run test:repository
git diff --check
```

Требуются Node.js 22+ и Python 3.10+. Эти команды проверяют репозиторий, а не запускают приложение. [Правила участия](CONTRIBUTING.md) · [Безопасность](SECURITY.md) · [Инструкции агенту](AGENTS.md) · [Проверка организации проекта](docs/qa/repository-structure-review-2026-10-19.md).
