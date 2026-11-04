# Независимая сверка upstream Auth — 04.11.2026

**Узкий сквозной путь подтверждён; весь Auth и V01 не приняты.** Серверный чат
выполнил операции в отдельной тестовой БД и передал очищенные отчёты. Чат БД
независимо сопоставил сохранённые связи с источниками HTTP/браузера: **812 условий,
0 несовпадений**, 7 исходных входов и 7 адресных выходов. Эти сравнения не являются
812 новыми сквозными испытаниями. Прямые обращения БД-чата к Oracle не выполнялись.

Исполнявшийся DB head `2747516132a8bbc585eb2343dca52952e993850c`, tree
`ee442e35eb40be104c60ae34051683498adca353`; backend head
`210044b3ecee092499baa4602f3a36f0344a6cf4`, tree
`92ec7a8b7fbb00f96925ddae62dec456f4fd2e56`. Новые auditor/отчёты добавлены после
этого исполнения; они не меняют SQL, установленный оператором.

## Что именно наблюдалось

| Слой | Доказательство | Вывод и граница |
| --- | --- | --- |
| SQL harness | [32 pass, 3 not_run, completed=true](evidence/storage-after-008.json) | RFC/all-matching, права, capture/replay, rollback, deferred completeness, used-step rejection, recovery, generation history и old epoch. Provider fixtures и cipher здесь сконструированы; это не реальный email/MFA |
| HTTP | [58 утверждений](evidence/transport-anonymized.json) | 3 цепочки: basic, MFA, потеря ответа провайдера `after_body` до передачи адаптеру. Последний случай не означает потерю публичного ответа: Shadow смог завершить C02 по durable witness |
| Chrome 156.0.8078.79 | [65 утверждений](evidence/browser-anonymized.json) | basic/MFA, потеря публичного ответа до и после получения cookie; Q01 перед recovery, исходная история, стирание recovery cipher и адресный logout |
| Хранение | [7 snapshots](evidence/observer-anonymized.json), [независимый отчёт](evidence/independent-review.json) | 7 точных context/operation/action/login связей с клиентскими отчётами; все full bundles, audits, provider witnesses и logout targets согласованы |
| Логи | [отчёт оператора](evidence/redaction-anonymized.json) | В наблюдавшихся логах отсутствуют проверенные fixture proofs/tokens и email OTP; это ограниченный поиск конкретных значений, не доказательство отсутствия любых секретов |

У 3 MFA-входов сохранены два отдельных результата: C02 `auth_step_required` с
исходным challenge и AUTH_TOTP_VERIFY `login_completed`. У каждого — один
использованный шаг своего factor version; полный all-matching collision проверен
отдельным SQL fixture с двумя совпадающими шагами, а не подменён этими 3 наблюдениями.
У остальных 4 входов завершение принадлежит C02, использованных TOTP-шагов нет.
Во всех 7 цепочках generation остаётся `consumed`, seal относится к исходному
admission, consumption и provider-session outcome имеют один transaction id.
Snapshot сам по себе не доказывает число сетевых dispatch или правдивость источника.

У всех 7 входов сохранены credential и строка recovery secret; cipher уже стёрт
после первого Q01, исходный login/result не удалён. Logout result указывает на тот
же login, который отозван, и имеет единственное соответствующее событие аудита.
Сверка не полагается только на предоставленный producer-флаг `valid=true`.

## История исправлений и воспроизведение

- [Первый прогон](evidence/storage-initial-incomplete.json): 10 pass, незавершён;
  alias `r` конфликтовал с PL/pgSQL row variable. Исправлен forward delta007.
- [После007](evidence/storage-after-007-incomplete.json): 17 pass, незавершён;
  deferred trigger при COMMIT потерял definer-контекст. Delta008 задаёт SECURITY
  DEFINER существующему NOLOGIN owner с фиксированным search_path; runtime table
  grants не расширены. Также сохраняется история consumed при следующей issuance.
- После008: 32 pass, completed=true. Успешный полный COMMIT и запрещённый plan-only
  COMMIT проверены раздельно. Прежние незавершённые прогоны не переписаны как pass.

SHA256 delta007 `c44012bf4767ade3d29d7caa84f540f99904182628156f2867e220e189f131ad`,
delta008 `4e83a9ee83d56b7836209160818d9d0e29b731aad63332620e1e33fa57e38baa`,
SQL runner `161bff8d336c8947e3494bb58ae909f280f95dcbd71a34e880d6d0d5100b6c61`.
Хеши всех 7 исходных JSON — в independent-review. Четыре runtime JSON публикуются
только в дополнительно обезличенной форме: 99 исходных UUID заменены согласованными
порядковыми обозначениями, 21 transaction id — согласованными числами, абсолютные
времена сдвинуты на одно целое число дней, TOTP steps — на одну общую константу.
Интервалы, точность, равенства и различия сохранены; даты/номера в опубликованной
копии синтетические. Таблица соответствий не публикуется. На исходниках и копии
одни и те же812условий дали0различий. Три SQL runner reports не содержат таких
идентификаторов и сохранены без изменения. Хеши обеих форм различены в отчёте.

Автоматическая проверка публикации отклонила исходные runtime JSON из-за внутренних
идентификаторов и временных данных. Их не отправляли другим инструментом/чатом:
публичный пакет минимизирован описанным преобразованием. Исходники доступны
локально оператору; Git-копия позволяет воспроизвести сверку связей, но сама не
доказывает подлинность исходной выгрузки. Серверные fault-профили: provider
`after_body`, браузер `drop_before_headers` / `drop_after_headers`.

[Offline auditor](../../../../../scripts/v00-upstream-db/audit_snapshot.py)
принимает один `v00-upstream-snapshot-v1`; функция `audit` применена ко всем
элементам observer-actual. Он не подключается к БД или сети. 14 локальных тестовых
групп RFC и auditor прошли, включая намеренное повреждение source/step/transaction/
logout audit и точности времени. `v00_session.utc()` выводит миллисекунды (MS),
upstream snapshot — микросекунды: сравнивается точное усечение до миллисекунд,
не произвольный допуск. Первоначальная ошибка этой предпосылки была в auditor;
изменять runtime-данные ради совпадения не потребовалось.

## Что остаётся открытым

SQL-harness строки real-provider и HTTP/browser остаются `not_run` **в том runner**;
их узкое сквозное покрытие дано отдельными отчётами выше. Global drain/reopening
не проверен и не закрыт. Конкурентные запросы, весь unknown/late-result набор,
остановка/возобновление после restore и случаи коррумпированного provider source
требуют своих наблюдений; эти 7 последовательных цепочек их не заменяют.

Не реализованы полный C01/C03/resend, достоверный email negative classifier,
долговременные quotas, challenge renew/MFA lifecycle, текущий navigation resolver
и production lifecycle сравниваемых секретов. Разрешение V00 не разрешает V01,
публичный Auth, реальные сделки или автоматически весь каталог 78 таблиц.
Общий остаток ведёт серверный чат в [V00 checklist](../v00-exit-checklist.md).
