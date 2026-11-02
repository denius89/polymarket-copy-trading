# Бэкенд: компонентный паспорт и проект доказательств

02.11.2026 · Проект на вычитку для BA-G07–12/RV03–08. Основа — [принятый H04–H06](backend-operations.md), [план доказательств](database-evidence-plan.md), [Auth-механизмы](backend-review-mechanisms.md). Ни установка, ни код, ни SQL, ни реальные прогоны не выполнялись. Чтение публичных release/registry metadata не считается проверкой совместимости.

## 1. Один конкретный кандидатный состав

Версии проверены02.11.2026 по первичным источникам. Это выбранный **кандидат для будущей проверки**, не certified compatible сборка. Прежние кандидаты PostgreSQL17.11/pg8.23.1 сохранены. Автоматическое обновление до latest/RC не разрешается. Перед запуском точный bill of materials и binary/container SHA256 фиксируются в evidence; значений ещё не полученных бинарников здесь нет.

| Компонент / версия | Роль и граница | Первичный источник |
| --- | --- | --- |
| PostgreSQL17.11 | Shadow, auth_control и отдельная provider схема; Serializable/row guards/advisory/deferred integrity; pg_basebackup/pg_receivewal той же17.11 | [Release17.11](https://www.postgresql.org/docs/17/release-17-11.html) |
| Node.js24.22.2 LTS | API/worker/Auth-controller, native crypto CSPRNG/SHA/HMAC; monotonic budgets | [Release](https://nodejs.org/en/blog/release/v24.22.2) |
| TypeScript7.0.2 | Компиляция будущего сервера, не миграция текущего репозитория | [Registry](https://registry.npmjs.org/typescript/7.0.2) |
| pg8.23.1 | Выделенное соединение на всю транзакцию, numeric/bigint строками; cancel не доказательство rollback | [Registry](https://registry.npmjs.org/pg/8.23.1), [transactions](https://node-postgres.com/features/transactions) |
| Supabase Auth2.197.0 | User identity/email/provider MFA; закрытый доступ через adapter; exact OTP/TOTP/replay ещё проверяются | [Release](https://github.com/supabase/auth/releases/tag/v2.197.0) |
| @simplewebauthn/server14.0.3, browser14.0.0 | Staff verification/options и browser JSON transport; текущие provider features не заменяют local grants/recovery | [Server registry](https://registry.npmjs.org/@simplewebauthn/server/14.0.3), [browser registry](https://registry.npmjs.org/@simplewebauthn/browser/14.0.0), [документация](https://simplewebauthn.dev/docs/packages/server) |
| canonicalize5.1.0 | JCS только после strict decode; closed cursor/manifest, без Unicode normalization | [Registry](https://registry.npmjs.org/canonicalize/5.1.0), [RFC8785](https://www.rfc-editor.org/rfc/rfc8785) |
| libsodium-wrappers-sumo0.8.4 | Принятый XChaCha20-Poly1305 Q02 и short-secret encryption с разными ключами; готовность WASM/libsodium проверяется до допуска | [Registry](https://registry.npmjs.org/libsodium-wrappers-sumo/0.8.4) |
| moment-timezone0.6.6 + moment2.31.0, tzdb2026f | Только pinned transition data и календарное преобразование; денежные расчёты не Moment/Number. Правило H06 о локальных00:00/двойном времени/gap сохраняется | [Timezone registry](https://registry.npmjs.org/moment-timezone/0.6.6), [Moment](https://registry.npmjs.org/moment/2.31.0), [данные тега](https://raw.githubusercontent.com/moment/moment-timezone/0.6.6/data/packed/latest.json), [IANA](https://data.iana.org/time-zones/tzdb/version) |
| age1.3.2 | Шифрование backup/WAL/evidence для внешних recipients; не библиотека Auth proof или cursor | [Release](https://github.com/FiloSottile/age/releases/tag/v1.3.2) |

Timezone data тега0.6.6: version2026f, SHA256=3103c5c0eaa879615da630b74e2373ad9b571e0eae992e0b2a3db6e4475de2ce. Проверено чтением публичных bytes без установки пакета. Не заменять эту версию системной зоной/Intl хоста. `@js-temporal/polyfill`0.5.1 рассмотрен по metadata, но не выбран для зон: нельзя считать pinned package гарантией pinned host Intl/tzdb.

Выбор Moment ограничен lookup таблиц transitions и exact календарными правилами. Даты в принимаемом прикладном диапазоне проверяются; запрещён выход за него/автоматическое исправление несуществующего времени без политики H06. Независимый эталон — отдельный IANA tzdb2026f tool, не тот же helper, проверяющий себя. В evidence записываются версии Node/ICU/OS, но источником session expiry остаётся выбранная tzdb, закреплённая при расчёте; новая tzdb не переписывает сохранённые даты.

Проверенные SRI npm-артефактов (данные registry, не скачивание и запуск):

| Package | dist.integrity |
| --- | --- |
| pg8.23.1 | sha512-aL96AHANtWjPLDOLqnhx+ngp9+UK7ETEU8VJrDCGvsSSi/mGLcWYsS6Herg7lmaBJe4uwrfqsa7gTEFaSizDoQ== |
| @simplewebauthn/server14.0.3 | sha512-D39/0fiDiYmGV+nraY9s63D1Ho2AX/waMLy22/9gUadTUuvbAnstfb4bpbHYbwZuV5ZLDYN1SmzDKuiHzKAA4Q== |
| canonicalize5.1.0 | sha512-bab9+WefZljqQ8jT0qRwVmTyzAUU63K97QIQD3agynIBrb6sa5M2eAy8Hv8K3p4V9+ONVYZKtGYl4Dg+/5Gumw== |
| libsodium-wrappers-sumo0.8.4 | sha512-ql7hcgulKZ3ekfa2DGAogcCKsWU0diA/0nArz1CFzh93WQdb46/Kj18ka/Hifq6uA3Ush34Pc6vU/6HXeRwUkg== |

Crypto primitives не пишутся вручную; strict JSON duplicate/unicode/field decoder и exact rational normalizer — собственные будущие узкие модули с независимыми vectors, не стандартный JSON.parse с потерянными дублями. BigInt/n÷d/64 digits/version strings сохраняются. Supabase native limits/окна нельзя объявить равными проектным без проверки; его recovery-code API не заменяет отдельные staff owner codes.

## 2. Полнота транзакций и ограничения ресурсов

Кандидат подключения: прямой PostgreSQL pool без transaction-mode proxy в первом стенде; один checked-out client на транзакцию. API pool8, Auth-controller4, observer2, publishers по1; отдельный административный резерв, суммарный hard limit публикуется в environment descriptor до стенда. Query/lock/statement timeout задаётся из оставшегося принятого бюджета, ни одна внутренняя retry-пауза его не продлевает. Эти числа — пределы кандидата, не доказанная ёмкость.

До commit обязательны constraints родителя и детей: отсутствие детей не обходит deferred completeness; immutable updates/deletes закрыты; every writer повышает затронутый parent guard. Нарушение внутреннего CHECK/FK не превращается автоматически в бизнес-отказ. Unique conflict разбирается отдельно; serialization/deadlock только после доказанного rollback допускают принятый retry. Error/cancel/connection loss при commit →unknown, соединение не возвращается в pool до доказанного конца или уничтожения; fresh primary read не берётся из replica.

Q02 полный manifest не обрезается ради5s/страницы. На future performance run фиксируются число sources/traders/revisions/размеры, lock wait, hash/cipher duration, peak memory и deadline по каждому phase. Допустим только измеренный совместимый размер каталога в configured envelope. Переполнение ресурсов/бюджета503, не nextCursor=null или изменённый fingerprint. Область не сужается молча ради скорости; оптимизация/новый materialized механизм отдельной дельтой, если текущий кандидат не укладывается.

## 3. M02–M03: точные источники тестовых состояний

Сохраняются BASE/SEM/PUB/NEG/BAD/READ-FAULT и I01–I22. Каждый fixture имеет отдельную копию/ID; рабочая БД не используется. Proposal test-control storage находится **в отдельной изолированной БД**, не в36 таблицах приложения. Три точные группы: fixture_runs, lifecycle_observations, barriers. Ни API role, ни обычный staff не имеют к ним доступа; только отдельный test_prepare и test_driver. Их credentials не попадают в runtime image/production environment.

FixtureRun: fixtureRunId:U,scenarioId:string из принятого списка,mode:BASE/SEM/PUB/NEG/BAD/READ_FAULT,baselineCommit:40hex,fixtureSchemaVersion=shadow-fixture-v1,environmentId,seedDigest:64hex,expectedDigest:64hex,createdAt:T,status=prepared/running/finished/aborted. Ни один run без isolated environment attestation не допускается.

LifecycleObservation: observationId:U,fixtureRunId,sourceSessionId:U,sourceUserId:U,venueCode,observationVersion:V,kind=paused/exit_only/manual_positions/unknown_execution/dust/pending_sell/reserve_held/stopped_only/assessment_expired_unconfirmed/strictly_finished/late_final_conflict,blocksStart:boolean,strictFinalConfirmed:boolean,observedAt:T,provenanceDigest:64hex. Закрытые соответствия: все варианты кроме strictly_finished имеют blocksStart=true/strictFinalConfirmed=false; strictly_finished blocksStart=false/strictFinalConfirmed=true **только как семантический эталон**, не право удалить настоящий slot. Изменение создаёт новую observation/version, старое evidence неизменно. Соответствие: I02 paused/exit_only; I03 manual_positions; I04 unknown_execution; I05 dust; I06 pending_sell/reserve_held; I07 stopped_only/assessment_expired_unconfirmed; I08 strictly_finished и отдельный late_final_conflict.

Trusted test adapter читает эту форму только в SEM contract suite и выдаёт фиксированный domain fact функции допуска; production сборка такого endpoint/переключателя не содержит. Public DTO не принимает fixtureRunId или lifecycleClass, неверный источник не превращается в реальную session. Физические BASE/NEG/BAD проверки работают через настоящие изолированные36-table schema и её constraints. Семантическая future observation не записывается в закрытые production enums и не выдаётся за полноценную DB/API-историю будущего lifecycle.

Это закрывает **спецификацию изолированного источника**. Полные future lifecycle DB/API подслучаи A06/A17/A61 ещё нельзя объявлять пройденными без отдельной будущей модели/реализации; их карточки получают not_run/future_lifecycle_dependency, не pass/not_applicable. Предлагать изменять scope этих критериев можно только отдельным продуктовым решением. M02 целиком не закрывается одним EMPTY либо этим тестовым DTO.

Barrier: fixtureRunId,barrierId из утверждённого phase-list,participantId,phase=arrived/released/failed,sequence:V,observedAt:T. Phase-list: after_auth,after_guard,after_key,after_slot,after_draft,after_effect_before_commit,after_commit_before_response,before_witness_ack,before_cookie_emit. Расписания явно задают обе очередности; удерживание barrier не расширяет production deadline. Не использовать последовательные запросы как доказательство гонки.

Fault modes: NET-DROP (ответ потерян отдельно от DB connection), DB-CANCEL (с подтверждённым или неизвестным rollback), PROVIDER-UNKNOWN, CLOCK-UNTRUSTED, KEY-UNAVAILABLE, WITNESS-UNAVAILABLE, BAD-ROW (только повреждённая копия), PUBLISH-RACE. Изменение должно иметь один заранее известный источник, старые данные сохранены. Для NEG constraints включены; BAD готовится отдельным privileged prepare и затем проверяется обычным read-role. TEST privilege не включается в API. Cleanup только своего fixtureRunId после подтверждённого сохранения evidence; рабочая история M04 не чистится.

## 4. M05: точный пакет доказательств

Формат candidate `shadow-evidence-v1`, immutable JSON manifest плюс содержимое по hash, без executable snippets. Корень ровно schemaVersion,evidenceId,createdAt,baseline,environment,scenario,expected,actual,observations,artifacts,verdict,review,previousEvidenceId. PreviousEvidenceId nullable; исправление — новый ID/ссылка, не редактирование старого.

| Группа | Точные поля |
| --- | --- |
| baseline | repositoryUrl,commitSha,contractIds:[string],registryVersion,componentManifestSha256,tzdbVersion |
| environment | environmentId,isolated:boolean,restoreEpoch:V,runId:U; только обезличенные refs |
| scenario | id,variant,fixtureRunId:U,criteria:[A/R/CC/F/E/NA/QCAT/QID/QSC/DA IDs],scheduleDigest:64hex |
| expected | sourceRefs:[string],oracleVersion,artifactSha256:64hex; создаётся до выполнения и отдельным от actual путём |
| actual | status=not_run/executed/interrupted,startedAt:T|null,finishedAt:T|null,resultArtifactSha256:64hex|null |
| observations | [{sequence:V,participantId,phase,monotonicOffsetMs:decimal string,serverObservedAt:T|null,artifactSha256:64hex}]; offset не подменяет trusted UTC |
| artifacts | [{name:allowlisted string,mediaType,byteLength:decimal string,sha256:64hex,classification=synthetic/restricted,relativePath}]; paths без .. и абсолютных адресов |
| verdict | status=not_run/pass/fail/inconclusive,criterionResults:[{id,status,reasonCode=matched/mismatch/missing_evidence/unsupported_component/future_lifecycle_dependency}],limitations:[string] |
| review | reviewerRef:string|null,reviewedAt:T|null,signatureKeyId:string|null,manifestSignature:string|null; pending review явно nullable, не фиктивный reviewer |

Правила: actual.not_run →verdict.not_run и нет actual digest/times; interrupted не pass без полноты требуемых наблюдений; все заявленные criteria имеют отдельный criterionResult; pass одного subcase не закрывает весь A. Hash подтверждает bytes, не корректность поведения. Expected не рассчитывается тем же producer, который выдаёт actual. Финансовые ожидаемые дроби/суммы берутся из принятых ручных эталонов; HTTP200/count сами по себе не доказывают atomарность/права.

Подпись manifest: Ed25519 над UTF-8 JCS всего объекта с review.manifestSignature=null; signatureKeyId/reviewerRef/reviewedAt уже заполнены. Signature — canonical base64url без padding, ровно64 decoded bytes. Проверка доверяет отдельному актуальному каталогу verifier keys, не ключу внутри проверяемого файла. SHA256 окончательного файла считается после добавления подписи и хранится во внешнем индексе; циклического self-hash поля нет.

Предлагаемое размещение: на отдельном защищённом Mac/носителе `/Volumes/ShadowEvidence/<environment>/<evidenceId>/`, evidence/backup/witness раздельными каталогами и ключами. Это **проект пути, каталог не создан**. At-rest age encryption, получатели отдельные инфраструктурные identities владельца 1/владельца 2 и назначенного verifier; продуктовая роль Owner автоматически filesystem доступ не даёт. Service uploader может только добавлять новый ID, не менять/удалять; verifier читает назначенные пакеты; отдельный custodian отвечает за хранение и подписанные manifests. Публичный Git содержит только санитизированный индекс/hash/статус, не реальные backup/PII/секреты.

Публикация: собрать →проверить schema/полноту/hash →зашифровать →передать →получить signed receipt с evidenceId/ciphertextHash/byteLength/receivedAt →обратное чтение metadata и выборочная/обязательная для уникального оригинала проверка расшифрованных hashes →записать index. Исходник не удаляется по одному успешному upload. Неизвестная доставка не подтверждённая публикация. Применяется [правило репозитория](../../REPOSITORY_GUIDE.md); первый стенд без автоочистки истории.

## 5. Backup, WAL, witness и открытие после восстановления

Сохраняем ежедневную физическую копию и последние7 успешных внешних зашифрованных копий с полной WAL-цепочкой. Кандидат расписания: backup02:00 UTC, receive WAL постоянно, отправка закрытого WAL на внешний получатель не реже60 секунд;7 копий считаются по подтверждённой доставке, не попыткам. pg_basebackup/receivewal17.11, age1.3.2, отдельный service account/протокол добавления по ID; никакого автоматического SSH доступа из роли владельца.

При недоступности внешнего получателя backup/WAL показывается failed/pending_delivery; последний полученный LSN/time и непокрытый интервал видимы. Эти60 секунд — период отправки, **не гарантированный RPO**. RPO/RTO определяются будущим restore drill; обещаний измеренного времени нет. WAL/backup чувствительны, ключи отдельно; старые WAL зависимости семи копий не удаляются по возрасту сегмента.

Witness из mechanisms §7 имеет отдельный append-only каталог, signed hash chain и trusted head на стороне получателя. В standby/restore сервер не открывает writes по собственной старой копии head. Для каждого pending intent после restored point нужен provider/WAL/достоверный outcome; missing не означает rollback. После сверки создаётся новый epoch, отзываются прежние proof/login, проверяются назначения и scope. Reconcile manifest содержит restorePoint/LSN/непокрытый интервал/каждый unresolved outcome. Пока хотя бы затронутый исход неопределён, соответствующий gate закрыт.

Порядок разрешения открытия: оператор восстановления предоставляет evidence; отдельный verifier сверяет; оба владельца подтверждают одну версию отчёта для полигона; инфраструктурный custodian исполняет разрешённое открытие. Это кандидатная процедура инфраструктуры, не новая способность Owner в админке. Отсутствующий verifier/recipient/key/подпись не заменяются устным «копия хорошая». Фактические identities/пути доступа назначаются перед стендом отдельно, без помещения личных данных в Git.

## 6. H04: конкретный runtime-профиль observer

Остаётся один paper_start_observer, пустой payload, никаких торговых/почтовых эффектов. Worker отдельный процесс Node24.22.2/pg8.23.1, роль shadow_worker_exec, pool2. Принятые параметры: poll1s, concurrency1, lease30s без продления, processing5s, каждое ожидание≤1s/остатка, всего5 попыток, backoff1/5/30/120s. Новая внешняя очередь не нужна.

Процедуры candidate: claim_due_event,inspect_consumer_receipt,finish_observed,finish_delivery_error. Runtime не пишет эти таблицы вне процедур. Захват token/attempt/lease атомарен; receipt имеет приоритет перед исполнением; эффект только observed+processed в одной транзакции; старый token после expiry не меняет last_error/new attempt. После timeout соединение завершает/доказывает rollback; unknown сначала fresh primary receipt, не повтор наблюдения с новым токеном. Пятая неудача ведёт в принятый needs_review; существующий receipt позволяет только завершить доставку.

Будущие доказательства E13/F14–F16/I19: два worker, старый lease, crash до/после commit, потеря ответа, пятая попытка с/без receipt, source/format corrupt. Наблюдаем неизменность FIN/session/start audit и точные scope/token/receipt refs; count одного outbox недостаточен. Истёкший login пользователя не останавливает локальный observer, restore gate — останавливает.

## 7. Что проверяет коллега и что остаётся исполнению

Документально предложены версии, sources, roles, deadlines, fixtures, evidence schema, location/ACL и restore/observer процедуры. Коллега может проверить логическую согласованность и дать конкретные замечания. **Нельзя документально завершить** совместимость Supabase с точным TOTP/replay, реальные DB/Auth гонки,5s Q02/witness бюджеты, фактические права/mount/recipients, backup restore или полноту будущего lifecycle. Они остаются измеримыми gates реализации, не бесконечными вопросами о названиях полей.

Все E01–E17/A01–A112 и дополнительные auth schedules сохраняют статус not_run. Отчёт о вычитке не меняет его на pass. Нет готового стенда, lockfile/binary BOM или созданных тестовых баз. Переход к ним — отдельное поручение после согласования проектных дельт.
