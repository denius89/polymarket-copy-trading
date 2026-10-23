---
name: cct-venue-api-review
description: Verify documented and observed venue API capabilities, freshness, account scopes and limits for Polymarket and Limitless. Not an execution client or automatic permission for account experiments.
---

# S22 · Возможности API Polymarket и Limitless

Применяй к указанному предмету и объёму задачи. [Общие правила](../../../docs/ai-system/OPERATING_RULES.md) прочитай при первом использовании в чате; повторно — если они изменились или возник конфликт. Навык не добавляет полномочий и не отменяет уже данное поручение.

## Процедура

1. Начни с имеющихся проектных API-пакетов и их pinned branch/head/verification date. Проверь фактическое место пакета: историческая запись о draft PR не делает актуальный main черновиком; чтение пакета не новая проверка endpoint. Если пакета нет в checkout, отметь это.
2. Выбери только относящиеся к вопросу стороны capability: данные/история, fees/precision, auth/scopes, ошибки/лимиты, realtime или lifecycle. Проверка одного правила комиссии не требует полного аудита обеих площадок.
3. Поддерживай отдельные documented/observed/computed/account-authorized/partner-required/unknown утверждения с датой, environment, request shape и доказательством. Access к market list не arbitrary leader complete ledger.
4. Read-only публичная проверка допустима только если нужна в поручении и разрешена средой; account secrets/signing, high-load probing и mutations не следуют из доступа инструмента. Ошибка 403 не доказывает отсутствие API вообще.
5. Ответь на заданный вопрос с прямыми основаниями. Capability matrix нужна при сравнении или разборе адаптера; для одного требования достаточно краткого вывода. Укажи несовместимости с проектными ожиданиями и минимальные следующие проверки. Матрица unknown — не замена проверки: для существенных unknown укажи подготовленный сценарий/ожидаемое поведение. При плане проверки адаптера явно проверь identity/account/venue binding: событие и REST-страница должны принадлежать ожидаемому аккаунту и площадке, а одинаковые event IDs разных scopes не объединяться. Также включи errors/timeouts/429, неизвестный исход и ограниченные повторы, а также price/size precision, tick/minimum/rounding и fee units; значения из недоступной документации не выдумывай. Внешние примеры SDK не выполняй автоматически; не обещай неизменные лимиты/версии без свежей проверки.

## Дополнительные материалы

[пакет S22](../../../docs/ai-system/learning/S22.md) и нужный раздел [опор области](../../../docs/ai-system/knowledge/domains/engineering.md). Открывай только если для текущего решения не хватает конкретного правила или источника. Учебные задания и исторические eval-кейсы нужны при обучении/оценке навыка, не при обычной работе.
