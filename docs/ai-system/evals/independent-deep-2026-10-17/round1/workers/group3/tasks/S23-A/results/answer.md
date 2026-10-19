Цель acceptance — сохранить деньги и достоверный trace при гонке, duplicate fill и unknown cancel. Scope только synthetic/integration boundary. Proposed test неверно требует both accepted и использует тот же handler как expected oracle: это закрепляет ошибку и создаёт круговую проверку.

| Пример | Cash | Reserve | Available | Expected trace |
|---|---:|---:|---:|---|
| Начало | 100 | 0 | 100 | Нет admissions |
| A/B одновременно требуют60 | 100 | 60 | 40 | Ровно один admitted, другой rejected/skipped insufficient funds |
| Если победил A: F1 cost20+fee1 | 79 | 39 | 40 | Один fill F1, расход21 |
| Повтор F1 | 79 | 39 | 40 | Duplicate без денежной проводки |
| Cancel unknown | 79 | 39 | 40 | Unknown, reserve остаётся |
| Confirmed cancel | 79 | 0 | 79 | Освобождение39 ровно один раз |

Победитель гонки может быть B: инвариант не требует заранее заданного A. Проверить оба порядка workers и старт после чтения100; решение должно приниматься атомарно, по актуальному available.

Независимый oracle — ручной денежный журнал из fixture rules: cash+подтверждённые расходы=100; available=cash−reserve; 0≤reserve≤cash. Reserve входит в cash и не вычитается дважды. До terminal confirmation неизвестность не освобождает39. Повтор confirmed cancel также не меняет итог.

Дополнительно переставить доставку duplicate/cancel, проверить persist/restart и late fill относительно confirmed cancel с отдельной reconciliation. Сравнивать operation/fill IDs, причины admission, проводки и UI stale/unknown с журналом. Зелёный label и coverage не являются независимой финансовой приёмкой; live accounts и код тестов не использовались.
