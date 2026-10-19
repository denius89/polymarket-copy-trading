---
name: cct-copy-replay
description: Review copier replay and backtest feasibility with arrival-time data, liquidity, expenses and project lot rules. Not a live execution adapter or automatic historical-fill simulation.
---

# S12 · Реалистичность replay копирования

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Зафиксируй стандарт копировщика: venue, budget, horizon, sizing/limits, exit/lot rules, latency, fees и начальное состояние; различай accepted и research proposals.
2. Данные signal/book должны быть доступны к simulated decision; quote с event timestamp до cutoff, но полученный позже, не доступен заранее.
3. Исполнение рассчитывай по стороне и depth после arrival, с ограничениями и расходами; maker leader price/last/mid не наша доступная цена.
4. Проверь rejects/skips, partial/cancel/unknown/reserves, конкурентные сигналы и открытые позиции; будущий resolution не заменяет выход на дату оценки.
5. Покажи отдельно cash, действующий reserve и available на каждом подтверждённом переходе. Неиспользованный максимум резерва — вычислимый остаток, но не доказательство его освобождения: terminal confirmation и правило release должны быть заданы. Если их нет, available после release — только условный результат; размер остатка не устанавливает новый переход состояния.
6. Выдай разбор realizable/approximate/not_identifiable, coverage и sensitivity. BBO sample без depth не позволяет обещать исполнение объёма; результат не меняет финансовые правила.

## Знания и проверка

Для предметной работы: [пакет S12](../../../docs/ai-system/learning/S12.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/score.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Найти lookahead по observation time.
- Не использовать leader price вместо доступной книги; обозначить непроверяемое исполнение.

Смежные процедуры: S11, S03. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
