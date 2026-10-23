---
name: cct-copy-replay
description: Review copier replay and backtest feasibility with arrival-time data, liquidity, expenses and project lot rules. Not a live execution adapter or automatic historical-fill simulation.
---

# S12 · Реалистичность replay копирования

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Зафиксируй стандарт копировщика: venue, budget, horizon, sizing/limits, exit/lot rules, latency, fees и начальное состояние; различай accepted и research proposals.
2. Данные signal/book должны быть доступны к simulated decision; quote с event timestamp до cutoff, но полученный позже, не доступен заранее.
3. Исполнение рассчитывай по стороне и depth после arrival, с ограничениями и расходами; maker leader price/last/mid не наша доступная цена.
4. Проверь rejects/skips, partial/cancel/unknown/reserves, конкурентные сигналы и открытые позиции; будущий resolution не заменяет выход на дату оценки.
5. Покажи отдельно cash, действующий reserve и available на каждом подтверждённом переходе. Неиспользованный максимум резерва — вычислимый остаток, но не доказательство его освобождения: terminal confirmation и правило release должны быть заданы. Если их нет, available после release — только условный результат; размер остатка не устанавливает новый переход состояния.
6. Выдай разбор realizable/approximate/not_identifiable, coverage и sensitivity. BBO sample без depth не позволяет обещать исполнение объёма; результат не меняет финансовые правила.

## Дополнительные материалы

[пакет S12](../../../docs/ai-system/learning/S12.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/score.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
