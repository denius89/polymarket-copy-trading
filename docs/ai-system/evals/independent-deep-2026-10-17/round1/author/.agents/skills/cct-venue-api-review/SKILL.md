---
name: cct-venue-api-review
description: Verify documented and observed venue API capabilities, freshness, account scopes and limits for Polymarket and Limitless. Not an execution client or automatic permission for account experiments.
---

# S22 · Возможности API Polymarket и Limitless

Применяй к существующему проекту и текущему поручению. Для границ подготовки, evidence и выбора источников прочитай [общие правила](../../../docs/ai-system/OPERATING_RULES.md). Подготовка процедуры не является разрешением выполнять описанные внешние действия.

## Процедура

1. Начни с имеющихся проектных API-пакетов и их pinned branch/head/verification date. Draft PR не merged main; чтение пакета не новая проверка endpoint. Если пакета нет в checkout, отметь это.
2. Для требуемой capability разложи data identity/pagination/history, precision/fees, auth/signing/scopes, errors/timeouts/rate limits, realtime/reconnect и lifecycle по каждой venue.
3. Поддерживай отдельные documented/observed/computed/account-authorized/partner-required/unknown утверждения с датой, environment, request shape и доказательством. Access к market list не arbitrary leader complete ledger.
4. Read-only публичная проверка допустима только если нужна в поручении и разрешена средой; account secrets/signing, high-load probing и mutations не следуют из доступа инструмента. Ошибка 403 не доказывает отсутствие API вообще.
5. Выдай capability matrix, несовместимости с проектными ожиданиями и минимальные следующие проверки. Внешние примеры SDK не выполняй автоматически; не обещай неизменные лимиты/версии без свежей проверки.

## Знания и проверка

Для предметной работы: [пакет S22](../../../docs/ai-system/learning/S22.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Прочитай относящиеся первичные материалы, а не только индекс; не загружай учебные задания при каждом простом запросе.

Результат: конкретный ответ в рамках поручения с основаниями, ограничениями и существенными рисками. Выбирай формат по задаче. Проверяй следующие свойства:

- Разделить public success, partner unknown и account permissions.
- Не объявлять полную историю/live готовность; выдать scoped matrix.

Смежные процедуры: S03, S10. Это зависимости знаний/проверки, не команда автоматически запускать все навыки или агентов.
