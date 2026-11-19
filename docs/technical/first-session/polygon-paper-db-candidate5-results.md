# Синтетический paper-профиль: результат candidate5

Дата:05.11.2026, Europe/Warsaw. Область: новая одноразовая offline DB-only копия
на существующем Oracle. Исполнитель — серверный чат; БД независимо сверил его
сохранённые безопасные результаты. Постоянная активация не выполнялась.

## Проверенный пакет

- Source commit `4deb119971bb1b57f781b1ccb77882fabcbaf86c`.
- SHA256 файла SHA256SUMS:
  `e7a856711a1b8edf6275084c9b608d592f737efe464217584285cb30d7b1bc7d`.
- Все15 перечисленных файлов пакета совпали с manifest в операторской копии.
- [Порядок candidate5](../../../scripts/polygon-paper-db/OPERATOR-CANDIDATE5.md):
  установка001–007, затем test-disposable и test-numbers.008 отсутствует в run-order.
- Независимая статическая вычитка бэкенда:
  `/private/tmp/polygon-paper-candidate5-backend-review.json`.

## Фактический результат

| Наблюдение | Результат |
| --- | --- |
| Проверка резервной копии для клона | Две строки backup successfully verified в операторском журнале |
| Установка001–007 | Все семь файлов завершили COMMIT только в копии |
| Исходное состояние | users2, venues2, sources2, traders4, profile enabled=false |
| Предметная suite |51 assertions,51 разных labels, финальный JSON и ROLLBACK |
| Числа/кодирование/hash |40 assertions,40 разных labels, финальный JSON и ROLLBACK |
| Контроль после suites | Guard подтвердил profile disabled, seed2/2/2/4 и отсутствие command keys/receipts/reviews/sessions/journal entries/audit/outbox; контрольная read-only T завершилась ROLLBACK |
| Очистка | cleanup-safe подтверждает удаление disposable копии и отсутствие polygon schema в постоянной БД; существующий HTTPS ответил204 |

**Узкий SQL/ACL результат:91 проверка пройдена.** Подтверждены обе площадки,
fixed/percent, точные начальные суммы, replay C04/C06, сохранённый отказ/Q05 HTTP200,
изоляция пользователей, полный начальный финансовый комплект и проверки прав
функций, включая private defaults. Числовая suite проверила grammar/range/step,
приоритеты fieldErrors, дроби, null/empty/Unicode/NUL/base64 и независимый JCS hash.
Проверенный срок C06 в этой suite — UTC; поведение DST этим не подтверждается.

Источник фактов:
`/private/tmp/shadow-polygon-paper-candidate5.atwSbN/oracle-db-only-safe.txt`.
SHA256 журнала:
`21ccbecce75ed14b6bdcc22554eaecc12e803b09be8e3ccbf94dc0380d49dcb0`.
Операторские run-order.txt, SHA256SUMS и cleanup-safe.txt находятся в той же папке.
БД не выполнял дополнительный серверный прогон: независимо прочитал артефакты,
сверил их hash/состав/числа/уникальность labels, отсутствие ERROR и три ROLLBACK.
Очистка подтверждается операторским свидетельством, не отдельным подключением БД.

## История обнаруженных дефектов

Candidate2 остановился на неограниченном скобками CASE в PL/pgSQL IF.
Candidate3 установился, но обнаружил ошибку effective ACL: per-schema default
REVOKE не отменял глобальный PUBLIC EXECUTE. Candidate4 исправил права, но
допущенная лишняя скобка в последней новой assertion остановила suite.
Candidate5 удалил только эту скобку. Ранние статические PASS не подтверждали
компиляцию: исходные остановки сохранены, проверки не пропускались и не ослаблялись.

## Что этим не закрыто

Actual runtime LOGIN/HTTP adapter/браузер, конкурентные запросы, потеря COMMIT,
повторное включение после инцидента, paper restart/restore и постоянная установка
не доказаны91 SQL-проверкой. Fixtures использовали локальные синтетические Auth
completions; они не доказывают вход через провайдера или passkey. Нет P04 PASS,
actual claim, Q06, прав владельца, реальных средств или live/public доступа.

Следующий согласованный технический шаг — минимальная API+SQL интеграция на новой
одноразовой копии: отдельный непривилегированный runtime LOGIN, приватные test
fixtures, точные HTTP/SQL наблюдения и очистка. Её состав готовят БД/бэкенд/сервер
отдельно;008 и постоянная активация не следуют из текущего результата.
