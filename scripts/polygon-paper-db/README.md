# Polygon paper DB candidate · POLYGON-SYNTH-01

04.11.2026. Source baseline `24076847cf48c911eaa5fb21ca34b5969f89f109`;
separate authorization [ADR-0067](https://github.com/denius89/polymarket-copy-trading/blob/57a606fafabdb0bb2fdff040abdb7ea2969daf2f/docs/decisions/0067_frontend_stack_and_polygon_delivery.md)
published in main `57a606fafabdb0bb2fdff040abdb7ea2969daf2f` (PR253).
The ADR is newer than this Auth baseline; its canonical remote source controls the
scope. The separate PR212 documentary task remains complete, without runtime tests.

Candidate2 stopped at005 during disposable Oracle installation. [Candidate3](OPERATOR-CANDIDATE3.md)
installed001–007 in a fresh copy, but the disposable suite failed on an effective
function privilege assertion; the numerical suite was not reached. [Candidate4](OPERATOR-CANDIDATE4.md)
corrected privileges; its effective ACL checks reached the last assertion, which
failed to parse. [Candidate5](OPERATOR-CANDIDATE5.md) removes one extra closing
parenthesis there, preserving all assertions and the unchanged installation SQL.
Owner resumed this bounded implementation and offline checks on05.11.2026; only the
server executes the verified frozen package after independent review. No full SQL
PASS or permanent activation is claimed before its actual evidence.

This additive candidate implements a **single fixed environment**, user-only,
synthetic first paper session. It is not an installation of all 78 product tables.
Existing V00 Auth001–010 are unchanged. Never replay recovery009, re-create the
old database, seed providers, or run a startup migration against populated Auth.
Only the server chat operates Oracle. Runtime receives a new dedicated LOGIN with
only polygon_executor membership; the existing three Auth logins are unchanged.

External independent witness is omitted only in the explicitly approved test
profile. Actual claim, guest writes, staff/Q06, real funds, execution, incident
reopening, old-session finalization, active settings edits, and outbox consumption
are absent. Outbox intent is saved, not evidence of delivery. User auth never grants
staff rights. No statement here means P04 PASS, V01 admission, or verified restore.

## Ordered application and activation

First apply only on the operator's isolated offline restore clone of the permanent
polygon, PostgreSQL17.11. The operator verifies the volume/container identity,
network=none, local socket only, and records the pinned hashes in SHA256SUMS.
Apply 001,002,003,004,005,006 in order with psql ON_ERROR_STOP, then007 with the
explicit `polygon_tzdb_version` variable matching the reviewed backend calendar.
Each install file commits separately; unexpected existing objects stop install.
On failure discard only the test clone and retry a corrected pinned candidate.
Do not patch around a failed migration on the permanent volume.

007 maps two already verified synthetic directory/provider subjects into explicit
new product users and read scopes. It does not infer identity from equal UUIDs,
create provider accounts, or expose addresses. It publishes two sources/four
traders across Polymarket/Limitless with explicit synthetic source refs. It leaves
the profile and start control **disabled**. There is no seed from GET or startup.

For isolated checks set connection option `polygon.disposable_test=offline-clone`
and execute test-disposable.sql, then test-numbers.sql in separate connections.
The first suite expects51 named assertions; the numerical suite expects40.
Both emit only labels/counts, never real credentials or raw requests.
The first constructs local synthetic Auth completions
without provider calls and rolls the entire fixture back. This is SQL evidence,
not proof of browser login or OTP/provider verification. The UTC deadline vector
does not verify backend DST behavior. No fixture script belongs in runtime mounts.

008 is a separate operator activation after the compatible DB/API/calendar package
has passed its checks, with explicit `polygon_runtime_role` and
`polygon_tzdb_version`. The LOGIN must initially have no memberships or privileged
flags. The operator verifies effective ACL, credentials and no untrusted role can
assume polygon_owner. No password/key is in this package. Permanent application
requires a verified backup and the final reviewed manifest, not this untested draft.

## Exact private RPC and transaction contract

All nine public polygon functions take one jsonb argument. Call via a static
allowlist and parameter binding, never interpolated function/body strings.
Every call starts `BEGIN ISOLATION LEVEL SERIALIZABLE`; non-Serializable is503.
Guard locks the upstream gate, then the synthetic profile, then current Auth
actor/login/context, then the reader scope. Only trusted operator writers may
change catalog/scope/control; they must hold X profile first. Existing Auth writers
keep their established locks. No network operation while these locks are held.

`auth` is exactly `{login_id, cookie_digest}` from the closed V00 adapter, not
browser actorId. Credential uses its existing V00 domain/key; no new hash of an
unverified browser value. The bridge rechecks the complete login result, credential,
revoke/block/expiry and unfrozen clock. It does not call Q01 or close its window.
Permanent user mapping and scope are operator records. All relevant operations
recheck identity inside their transaction, never trust an earlier current_identity.

| Function | Other private fields | Successful private projection |
| --- | --- | --- |
| current_identity | None | http,user_id,read_context_id,scope_id,scope_revision |
| catalog_read | venue_code | http,read_binding,descriptor,items |
| c04_save | draft_id=null/create or UUID/update,raw_encoding,request | http,command_ref,receipt |
| c05_validate | request=the four public C05 fields | http,raw_encoding,review |
| c06_prepare | request=the five public C06 fields | Existing/final result: http,command_ref,receipt; otherwise http=200,prepared=true,ticket_id,started_at,iana_timezone |
| c06_finish | ticket_id,evaluation_deadline_at,deadline_calculation_version,timezone_database_version | http,command_ref,receipt |
| q03_draft | draft_id | http,raw_encoding,draft,field_errors,field_errors_source |
| q04_session | session_id=null/current or UUID/specific | http,session |
| q05_command | command_type,client_command_id,actor_id,actor_realm=user | http,command_ref,status,receipt |

All top-level fields are required and closed. `http` is a JSON integer, versions
are positive strings, timestamps UTC with three millisecond digits. Public forms
remain backend-api-forms-addendum; TS strictly validates them and builds current
navigation/request diagnostics separately. `command_ref` maps to commandRef.
Errors without durable result are exactly `{http,reason}` with registered code;
SQL diagnostics never become public reasons. Technical exceptions map to503 and
rollback; proven serialization/deadlock rollback may retry up to3 inside the same
5s budget under the accepted policy. Unknown commit does **not** prove rollback:
Q05 with original key, no blind retry/new key. Q05 reads rejected with200.

C06 prepare/finish must use one connection and the same transaction. A ticket has
the transaction ID, original login/epoch, reviewed settings and server start time.
Its deferred mandatory receipt prevents COMMIT without finish. The backend computes
the exact calendar result locally from prepare's timestamp/zone; finish verifies
ticket/epoch/time/profile/algorithm and stores the complete session bundle. It
does not certify the calendar library's arithmetic. External success only after
confirmed COMMIT; a private prepared response never reaches the browser.

## Raw codec and exact intent

Only the five raw settings use private `raw_encoding=utf8-base64-v1`: canonical
RFC4648 standard base64, required padding where applicable, no whitespace, strict
UTF-8, at most64 decoded Unicode scalars. Null stays null; empty stays empty.
PostgreSQL bytea preserves NUL, which text/jsonb cannot store. Lone surrogates are
rejected by HTTP parsing before encoding, never replaced with U+FFFD. Active NUL
is INVALID_DECIMAL; inactive raw is retained without numerical validation.

C04's marker is a required top-level input. Its request has the exact public fields
but five raw values encoded. C05 and Q03 have the marker in their private response;
their review/draft raw values are encoded. TS strictly decodes before public DTO
validation. No marker detection/fallback; malformed storage gives503, not empty.

The key stores a32-byte SHA256 request_hash, canonical_request_version=command-jcs-v1
and hash_algorithm=sha256; it does not store a full history of raw requests. DB
decodes base64 into exact public JSON string bytes before canonicalization, including
the JSON escape for NUL. The canonical object has exactly environment,actorRealm,
actorId,commandType,operation,targetDraftId,request,reviewConfiguration. Environment
and actor are trusted; C04 reviewConfiguration=null; C06 uses its immutable saved
review projection, including checked configuration. New generated result IDs/times,
login/cookie/diagnostics and the private transport marker are excluded. Create
targetDraftId=null; update and start use their validated draft. The closed contract
has ASCII keys, strings/boolean/null/arrays and safe integral JSON values, no floating
point numbers: its JCS serializer deliberately rejects unsupported general numbers.
There is no caller-supplied digest replacing the server hash. Typed key targets and
expected version remain separate columns. A golden Unicode/NUL hash was computed
independently in Python; execution of the SQL counterpart is still pending.

## Q02 snapshot

read_binding is exactly environment,realm=user,read_context_id,scope_id,
scope_revision=`q02-read-scope-v1:<scopeId>:<version>`. Stable read_context_id is the
mapped product user, not login. descriptor contains venueId,venueCode,paperControl
and sources using the exact raw state fields of database-q02-catalog-design §9.2.
All permitted sources/traders before visibility are included, sorted by ID; items
is the sorted visible subset from the same snapshot. Backend computes the accepted
domain-separated bindings/JCS fingerprint and encrypted cursor, with no cursor TTL.
Card filtering is TS-side over this same bounded snapshot; hidden/missing is404.

This implementation's resource cap is100 sources/1000 traders per authorized venue;
overflow503, never truncation or a partial fingerprint. This is a synthetic runtime
budget, not a new product catalog limit. Hidden descriptor metadata is not public
API, cursor plaintext, or diagnostics.

## Integrity and current limitations

Deferred cyclic FKs and complete-bundle triggers bind receipt/details, draft input
version and source receipt, immutable review/settings, slot/session, exact initial
funding/journal/two balanced entries/snapshot/audit/outbox. Histories reject update
or delete. Full START requires every child; unchanged C04 creates its own receipt
without changing version/TTL/last_input_receipt_id. Expiry and later edits do not
rewrite old receipts. Q04 absent is null, never a fabricated EMPTY snapshot.

Candidate2 supersedes initial d4c779d (which was not executed): deferred integrity
triggers run under polygon_owner, the test forces them while polygon_executor is
still current, C04 TTL is168 hours independent of session TimeZone, record versions
are stored explicitly, START/outbox/source links are tightened, and command keys
store the accepted public-intent hash instead of full raw history. test-numbers.sql
adds independent numerical/Unicode/JCS expected values. No runtime grants are widened.

Candidate5 is statically reviewed, **not yet run in PostgreSQL**. Prior candidates
ran only in disposable Oracle copies and stopped on the recorded defects. Candidate3
reached runtime deferred constraints, then failed `runtime_no_internal_helper_access`;
no complete suite PASS followed. The correction revokes PUBLIC's global default only
for the new polygon_owner, closes all existing polygon functions, then grants the
same nine RPCs. Four new assertions cover the effective whitelist, grant options,
PUBLIC privileges and future owner defaults. Earlier owner/API/financial rules remain.
Candidate4 installed001–007 and reached the final new default-privilege assertion,
where a syntax error stopped the suite; no final51 result or numerical run followed.
Do not retry rejected actions via a different executor or create a Mac database.
Complete disposable suites, corrected runtime ACL, concurrency, HTTP/browser flow,
restart/restore of new paper data and permanent activation remain unproven until
separately recorded. Prior Auth/calendar evidence is not evidence for this SQL.

Static review references: [PostgreSQL17 row-lock permissions](https://www.postgresql.org/docs/17/sql-select.html),
[exact numeric operations](https://www.postgresql.org/docs/17/functions-math.html),
[bytea/base64/hash functions](https://www.postgresql.org/docs/17/functions-binarystring.html),
[global versus per-schema default privileges](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html).
Reading these references is not proof that this candidate compiles or passes tests.
