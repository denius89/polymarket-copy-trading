---
name: cct-frontend-quality
description: Assess frontend state handling, accessibility, responsive behavior and measured performance for this project. Use for frontend review or preparation, not deriving runtime success from mockups.
---

# S06 · Качество frontend и performance

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Установи, есть ли runtime, код или только дизайн; выбери доказуемый охват. Реализацию не начинай по запросу на review.
2. Проверь semantic navigation/forms, focus/keyboard, error/status announcements, zoom/reflow, locale and reduced motion; UI status не источник финансовой истины.
3. Раздели server state, pending/optimistic state и подтверждённый денежный факт; persisted черновик не подтверждение операции.
4. Для performance зафиксируй build/device/network/cache/route и измерение; раздели field и lab. Диагностируй LCP/INP/CLS, images/fonts/bundle и bottleneck до советов memoization/virtualization.
5. Выдай отдельные functional, visual, accessibility и performance выводы с воспроизводимыми условиями. Числовые бюджеты бери из актуального проекта или предложи явно, не придумывая принятие.

## Знания и проверка

Для предметной работы: [пакет S06](../../../docs/ai-system/learning/S06.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Не подтверждать INP/WCAG runtime по картинке.
- Подготовить соразмерный план измерений без начала frontend.

Смежные процедуры: S04, S05. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
