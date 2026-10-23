---
name: cct-frontend-quality
description: Assess frontend state handling, accessibility, responsive behavior and measured performance for this project. Use for frontend implementation review; a Figma-only layout change does not require runtime performance testing.
---

# S06 · Качество frontend и performance

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Установи, есть ли runtime, код или только дизайн; выбери доказуемый охват. Реализацию не начинай по запросу на review.
2. Проверь semantic navigation/forms, focus/keyboard, error/status announcements, zoom/reflow, locale and reduced motion; UI status не источник финансовой истины.
3. Раздели server state, pending/optimistic state и подтверждённый денежный факт; persisted черновик не подтверждение операции.
4. Для performance зафиксируй build/device/network/cache/route и измерение; раздели field и lab. Диагностируй LCP/INP/CLS, images/fonts/bundle и bottleneck до советов memoization/virtualization.
5. При reconnect/retry проверь bounded backoff с jitter, предел попыток/общего времени, один активный цикл и отмену устаревшего timer/request при unmount, смене соединения или успешном sync. Для review предложи конкретную стратегию и проверку, а не только название storm; параметры без принятого бюджета обозначь предложением. Для денежных запросов сначала сверка unknown/idempotency, а не слепой retry.
6. Выдай отдельные functional, visual, accessibility и performance выводы с воспроизводимыми условиями. Числовые бюджеты бери из актуального проекта или предложи явно, не придумывая принятие.

## Дополнительные материалы

[пакет S06](../../../docs/ai-system/learning/S06.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
