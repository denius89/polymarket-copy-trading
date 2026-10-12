# Сценарии и границы прототипа

## Фактически пройдено в Present

- RU finance → partners → PART-024 → Polymarket route → full preview → accepted → submitted → unknown. В unknown отсутствуют resend/manual-paid; доступна проверка прежнего результата.
- RU unknown → EN unknown через URL: то же состояние и Owner A. Переключение открывает отдельную вкладку.
- EN unknown → pricing → tariff form → simulator → lifetime referral ladder → configure ladder. Проверены новые поля и арифметика примера: $3,200 × 1% = $32; 25% от комиссии = $8; сервису до расходов $24.

Полный ручной прогон каждого из 1,156 переходов не заявляется. Не проходились все ветки Owner B и payout-paid вручную; они структурно связаны и входят в реестр. 1280×900 — scaled Present, не адаптивная версия макета.

## Привязка к brief 118

| P | Покрытие дизайном |
| --- | --- |
| P-03 | Основной full payout route и paid states созданы; фактические источники/маршруты placeholder, полного Present по обеим площадкам нет |
| P-04 | Unknown, expired, insufficient, stop созданы; source-busy и existing-intent варианты ещё нужны |
| P-05 | Tariff/referral forms, simulator, preview/history/scheduled созданы; действительные числа, live venue application и полноценный publish/end/rollback polish ещё нужны |
| P-13 | Recipient proposal/independent review/active/reject показаны; provider evidence синтетическое, conflict/revocation варианты позже |
| P-14 | Second Owner review и full amount показаны; численная security policy остаётся на ввод, activation/revocation/conflict ветки не завершены |

Ни один P этим пакетом не объявляется полностью принятым. P-06 user VIP — предыдущий пакет; partner VIP не подменяет его. P-01/02/07–12/15–18 остаются дальнейшим дизайном.

## Точные переходы

В ru-final.json/en-final.json: `edges` — строки `sourceId|frameIndex|N destinationFrameIndex` либо `U targetNodeId`. Индексы относятся к массиву frames того же файла. NODE ведёт на текущую страницу; URL — язык или пакет 01. All NODE destinations проверены, self/invalid не обнаружены. Starts сохранены в flows. Действия с денежным смыслом — только переходы между макетами.
