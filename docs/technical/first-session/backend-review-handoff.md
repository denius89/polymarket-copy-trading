# Пакет бэкенда для вычитки: формы, механизмы и доказательства

Обновление02.11.2026 после публикации PR №201: владелец сообщил, что по вычитке вопросов нет, и поручил продолжить без кода. Ожидание замечаний завершено. [Карта дальнейших работ](backend-delivery-map.md) фиксирует основание и следующий этап D01–D04; прежние ниже статусы ожидания относятся к моменту подготовки пакета. Новые физические поля/реестр и runtime-проверки этим сообщением не созданы.

02.11.2026 · Поручение владельца: «Давай всё закроем и передадим коллеге на вычитку». Основа — принятый PR №199 и ответ БД PR №200, main1f108e6b2c36cfd05f29f5e27a0d76d112b92e68. **По всем12 BA-G и8 RV подготовлен предметный документальный ответ. Это готовность проекта к вычитке, а не одобрение всех новых решений, готовность к реализации или прохождение испытаний.** Код, SQL, миграции, установка, аккаунты и развёртывание не выполнялись.

## 1. Что читать

1. [Принятый Auth-контракт](backend-auth-contracts-addendum.md) — обязательная основа; прошлые «ещё нет формы» читать вместе с новым проектом, но не переписывать историю принятия.
2. [Оставшиеся API](backend-review-api-spec.md) — точные кандидатные маршруты/формы user MFA, admin reset, staff bootstrap/login/recovery, guest и email-link.
3. [Механизмы Auth↔БД](backend-review-mechanisms.md) — карта фактов/ключей/readers/writers, Q01/window, protected selector, claim guard/fence и restore.
4. [Компоненты и доказательства](backend-review-operations.md) — версии с источниками, роли/ресурсы, fixtures, evidence schema/storage/ACL, backup/WAL/witness и observer.
5. [Ответ БД PR №200](database-auth-handoff-review.md) — обязательные замечания и DA01–DA12; [передача бэкенда](backend-database-change-list.md) связывает эти пакеты.

Все файлы Markdown. В них нет исполняемых схем/SQL или утверждения, что новый service account/таблица/секрет уже существует. Схема Shadow остаётся принятой36-table схемой, реестр v5; кандидатные дополнительные action/role/audit виды не вписываются в него задним числом.

## 2. Закрытие описания по BA-G01–12

| Позиция | Конкретный ответ для вычитки | Статус/оставшаяся граница |
| --- | --- | --- |
| BA-G01 | API §§1–4: purpose-specific context/email, factor prepare/secret/confirm, completion/read-only outcome после отзыва, admin case | Проект форм готов; новые management значения ещё не утверждены/не реализованы |
| BA-G02 | API §§5–6/8: staff options/assertion/registration/current login/cookie/logout, bootstrap/one-owner/pair recovery, codes/сроки | Проект готов; нужны вычитка угроз/проверка устройств и фактические identities до стенда |
| BA-G03 | API §4: P-RESET, два разных owner approval одной версии, независимое основание и закрытый case/evidence | **Порядок принят владельцем02.11.2026.** Техническое назначение grants/audit и enforcement остаются на вычитке |
| BA-G04 | API §7 + mechanisms §5: постоянный guest/proof/refresh/expiry, связь с actor C04, loss/unknown и отсутствие user fallback | Предложение полно по механизму; новый guest lifecycle и physical mapping требуют принятия |
| BA-G05 | Mechanisms §5: versioned immutable bindings, candidate locator и повторная проверка, G1/G2/order/guard, точные writers | Проект selector готов; новая H01 physical дельта и все writers должны быть проверены БД |
| BA-G06 | Mechanisms §§2–4/6: закрытый storage inventory, dispatch seal/result, cookie-window row, consent/200/202, epoch drain против позднего claim | Проект границ готов; число/имена таблиц и физические constraints ещё не приняты; внешний adapter capability — блокирующая проверка |
| BA-G07 | Operations §§1–2/6: pinned candidate versions/источники/SRI/time data, pool/roles/процедуры, полный Q02 budget; mechanisms §6 exact claim key | Кандидат зафиксирован; binary BOM/совместимость/производительность не испытаны |
| BA-G08 | API §8 и mechanisms §7: persistent cookie, secret purposes/expiry, external witness/head/epoch, restore gate | Проект готов; новая availability цена witness и фактические ключи/recipients — отдельная оценка |
| BA-G09 | Operations §3: физически отделённый test-control, closed fixture/observation/barrier/fault contract, mapping I02–I08 | Текущий test-source описан; полноценные future lifecycle DB/API критерии остаются not_run/dependency, не исключены из A |
| BA-G10 | Operations §§4–5: exact evidence manifest, immutable paths/digests/roles, delivery receipt и restore approval | Проект готов; хранилище/права/подписи/доставка не созданы/не проверены |
| BA-G11 | Operations §6: Node/pg/pool/минимальные procedure boundaries, lease/token/fifth attempt/unknown | Принятые числа H04 сохранены; E13/F/I ещё не выполнялись |
| BA-G12 | API §§7–8: общий email challenge/link, ограниченный foreground ticket, закрытый provider ingress; operations3–7 и DA mapping | Проект пути/границ готов; тесты и защита от автоматизированного авторизованного браузера не объявлены доказанными |

RV01 соответствует BA-G01/02/04/06/12; RV02→BA-G05; RV03→BA-G06/07; RV04→BA-G07; RV05→BA-G08; RV06→BA-G09; RV07→BA-G10; RV08→BA-G11. У каждой RV теперь есть конкретный ответ, **но ни одна не получает фиктивное «проверено»**. Для коллеги это единая вычитка, не просьба заново изобретать уже принятые C04/C06/Q02/Q06.

## 3. Новые дельты, которые нельзя смешивать с прежними принятиями

| Дельта | Предлагаемое решение / предмет замечаний |
| --- | --- |
| RD01 · reset-policy | Свежий email + ранее подтверждённый независимый канал + два owner approval; нет основания — отказ, без паспортных документов. Порядок принят явным ответом владельца02.11.2026; техническая реализация ещё не выполнена |
| RD02 · новые HTTP формы | Purpose-specific management namespace; отдельные staff/guest/result readers;65536 только WebAuthn registration, новые actions/results/purposes и candidate audit kinds. Нужна конечная сверка реестра при принятии |
| RD03 · новые сроки и лимиты | Recovery24h/10 личных160bit codes/HTTP quotas; guest7d server validity и30d browser cookie; action-specific activity ticket. Проверить отсутствие ухудшения принятого draft/user lifecycle |
| RD04 · Auth physical mapping | Логические группы auth_control, binding/operations/results/window/counters и guards. Не добавлены скрыто в36 таблиц; требуется отдельное согласование точной physical дельты |
| RD05 · claim unknown | Общий environment admission fence/epoch+drain и свежая сверка вместо пустого SELECT под свободным guard. Цена — временное ограничение доступности среды; запрет второго пространства claim-key сохранён |
| RD06 · witness | Внешний append-only журнал intent/confirmed, fail-closed при недоступности, сведения вне restore DB. Проверить5s/10s budgets и операционную доступность; нельзя обещать распределённую атомарность |
| RD07 · M02/evidence/restore | Isolated test-control без расширения production lifecycle, точный evidence format/path/roles; обе owner подписи отчёта открытия как кандидат инфраструктурной процедуры. Не перепутать contract тест и настоящий DB/API pass |

Эти дельты — единый предмет вычитки/итогового принятия. P-RESET/RD01 принят отдельным явным ответом владельца; остальные RD02–07 остаются проектом. Принятие порядка не доказывает совместимость компонентов. При принятии пакета обновить реестр/ADR явно; прежнюю историю не редактировать как будто она уже содержала RD01–07.

## 4. Проверка стыков с ответом БД PR №200

| DA / область | Где дан ответ и что проверить |
| --- | --- |
| DA01 · Auth unknown | Mechanisms §3: dispatch seal до внешнего вызова, один performer, result recovery. Provider без нужной корреляции остаётся uncertain; это release-block, не скрытый повтор |
| DA02/03 · Q01/window/revoke | Mechanisms §4: общий X/window source, first confirm и сохранённый deadline, обе очередности; неизвестная фиксация не200, late cookie не оживляет login |
| DA04 · TOTP | API §§2–3 + mechanisms §3: единые used steps по factorVersion, отдельные failures по purpose, clock failure без increment, adapter capability доказать |
| DA05 · logout target | Принятый Auth §9 + API §5 staff-вариант: новый login доказательство, не цель; unknown не204 |
| DA06 · binding/navigation | Принятый Auth §10 + storage inventory: insert-only binding, согласованное current read, отсутствие null вместо denied/unknown |
| DA07/08 · consent/late read | Принятый Auth §11 + mechanisms §§2/6: typed historical consent, active login той же identity,200/202 разные основания; read не execution |
| DA09 · delayed old claim | Mechanisms §6: epoch captured до dispatch, X gate/drain, закрытый old consent, fresh primary result. Свободный guard/expiry не доказательство отсутствия будущего исполнения |
| DA10 · quotas | API §8 + mechanisms §2: stable subject scopes, общие accepted counters, rejection не сдвигает окно, unknown counter503 |
| DA11 · factor mutation/login | API §§2–4 + mechanisms §§1/3/4: local transition barrier, внешняя неопределённость, различие enroll/disable/reset, уведомление отдельно |
| DA12 · staff/Q06 | API §§5–6 + mechanisms local gate/grants: один current slot и отдельное полное recovery; принятые NA/DB-API-09 сохраняются |

Для G1/G2/Q02 проверить stale snapshot после ожидания, все binding/source/access publishers и оба порядка Q06/C06/revoke. Для claim проверить запрос, который задержан **до** guard, и не только два уже вошедших в SQL процесса. Для witness проверить crash до intent/после DB commit/до external ack и отсутствие доказательства после restore. Для MFA проверить прямые provider endpoints и операции с новым login после завершённого disable/reset.

## 5. Формат ответа коллеги

Нужна вычитка документов, без реализации/SQL/миграций/испытаний. Просьба вернуть один список замечаний:

- ID и серьёзность: blocker/important/note.
- Две конкретные ссылки на конфликтующие нормы либо ссылка на отсутствующую гарантию.
- Минимальная последовательность событий и наблюдаемый неверный результат.
- Предлагаемая правка и затронутые BA/RV/R/A/CC/F/E/DA/NA/QID/QSC.
- Меняется ли уже принятое правило/физическая схема/допуск или достаточно уточнить текст.
- Какое отдельное свидетельство позволит закрыть замечание.

Новые решения без ссылок на изменяемый контракт не считать устранением противоречия. Формулировка «проверить на реализации» не заменяет описания механизма; одновременно наличие механизма не заменяет future evidence. Коллега не должен создавать код/таблицы или реальные accounts в ходе вычитки.

Критерий готовности к итоговому принятию: нет незамеченных пустых BA/RV позиций, blocker-замечания разобраны, RD01–07 явно одобрены/исправлены, новый registry delta перечислен, физическая карта согласована с БД. Критерий допуска реализации отдельно: scoped поручение и компонентный/проверочный план. Критерий запуска отдельно: реальные испытания и доказательства, включая restore.

## 6. Что можно утверждать сейчас

Подготовлен полный **проект ответов** по всем перечисленным пробелам и единый предмет вычитки. Принятые продуктовые C04/финансовые/C06/DB-API-09 правила не изменены; источники доступны, PR №200 учтён. Реальные credentials/email/секреты не включены. Существующие README/ADR дополняются, а не переписываются.

Нельзя утверждать «все решения приняты», «все RV закрыты», «36 таблиц уже покрывают auth_control», «Auth exactly-once доказан», «будущий lifecycle испытан», «готово к развёртыванию». Ожидаются вычитка новых проектных дельт/физической карты и затем отдельно будущие испытания; P-RESET принят. Это точные границы завершения, а не очередная серия мелких вопросов о полях.

## 7. Готовое сообщение коллеге

Подготовлен единый пакет бэкенда для вычитки по всем BA-G01–12/RV01–RV08. Начните с этого листа, затем прочитайте API, механизмы Auth↔БД и компонентно-проверочный паспорт по ссылкам §1. Принятые нормы PR №199 сохранены; свежий ответ БД PR №200 и DA01–DA12 учтены.

Просьба проверить RD02–07 как проектные решения, а RD01 — на соответствие принятому порядку reset; особенно: protected guest/selector, хранение фактов до login/claim, Q01/window, поздний claim до guard, служебные права/recovery, внешние Auth outcomes и witness после restore. По каждой находке нужны ссылка, сценарий, последствие и предлагаемое исправление; формат §5. Не переоткрываем C04/last_input_receipt_id, деньги, строгий C06, принятые Q02 и DB-API-09 без конкретного противоречия.

Точные версии и источники указаны; совместимость/производительность/DB/API/Auth/concurrency/restore не испытывались. Новые физические сущности, права reset и candidate реестр ещё не выданы как принятые. Пожалуйста, верните один документальный список blocker/important/note. Код, SQL, миграции, установка, создание БД/аккаунтов и развёртывание в эту вычитку не входят.

## 8. Выполненная проверка документов

02.11.2026: структура/Markdown-ссылки/политика хранения (`npm run check`), 10 проверок хранилища и5 проверок уборки веток (`npm run test:repository`), `git diff --check` пройдены. Проведена содержательная сверка новых форм и механизмов с PR №199/200, BA-G/RV/DA и сохранёнными продуктовыми границами; уточнены отдельный restricted допуск reenroll, отзыв старого набора recovery codes, namespace результата и отсутствие циклического self-hash evidence. Это собственная документальная проверка автора; вычитка коллегой ещё не получена. Изменены только Markdown-документы. Прикладные/DB/API/Auth/конкурентные/restore испытания не выполнялись.

## 9. Ответ физической вычитки БД — проект на согласование

02.11.2026 · Подготовлены [BR01–BR09](database-backend-package-review.md) и [карта AC01–AC37](database-auth-physical-map-proposal.md). Зафиксированы конкретные замечания: возврат Q02 из G2 к G1, ABA binding без смены scopeRevision, ранний epoch admission/ограниченный reconcile при закрытом gate, typed связь witness с локальным результатом и полнота отдельных Auth namespaces. Исправления предложены в карте, этот backend-проект не переписан как уже принятый. P01–P05 вынесены единым блоком:37 новых таблиц/права и selector/fence/witness/lifecycle. До принятия каталог36 и v5 остаются действующими; capability provider и реальные доказательства не закрыты. Код/SQL/миграции/база/испытания не создавались.
