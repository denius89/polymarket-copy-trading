# Isolated V00-07 email-entry DB candidate

04.11.2026. Main30b0844, runtime dependency411d17b. Direct owner approval in
administrative message01a1a768-8604-7292-bf2a-f5cf4de4503c covers C01/C03, uncertain
send and negative email verification on closed Oracle. **Server chat only operates
Oracle.** The operator reported001–007 installed; setup then failed as recorded
below. Additive008 and its SQL regression remain NOT RUN; no HTTP/runtime success
is claimed. $0, synthetic/internal mail only.

## Exact installation scope

Fresh isolated copy of the previously verified provider Auth2.197.0/PostgreSQL17.11,
`v00-session-db/001-storage.sql`,002-api,003-logout,004-observer, and upstream001–008
as previously installed (no session005). Existing pgcrypto1.3 in the private upstream
schema is reused; this package installs no extension. Do not overwrite any prior stand.
Record source commit/tree and all SQL SHA256 before execution. Stop on first error,
preserve the incomplete run; never relabel it PASS after a correction.

Run001-storage,002-context-admission,003-send,004-provider-verify,005-completion,
006-integrity-observer,007-operator-directory,008-input-shapes-fix **in that order**
with ON_ERROR_STOP. Existing exact001–007 installations receive only additive008;
never overwrite/replay the installed originals.008 changes five function definitions
and adds an owner-only typed validator; it writes no fixture/runtime rows.
Each file has its own transaction; these are fresh namespace definitions, no silent
IF NOT EXISTS/update of an unknown prior schema.002 references send_guard defined
by003; do not serve requests until the complete set is installed and catalog/ACL
checked. Installation is not an atomic whole-package success if a later file fails.

Prepare distinct existing confirmed synthetic provider users; TOTP where required.
Use previous upstream seed_fixture for **subjects only, contexts=[]**. The new
directory rejects actors already owning upstream/session contexts or fixed clocks.
`seed_directory.py private-fixture.json private-keys.json` accepts entries containing
**exactly actor_id/normalized_email** (no supplied address_digest/address_key_id), derives the exact address HMAC and calls operator-only
seed_directory through psql17 bound parameters. V00_EMAIL_PSQL_COMMAND_JSON is a
trusted operator argv array for this isolated DB. Source files must have private
permissions. No plaintext address/HMAC/code is printed in its result.

The old upstream HTTP service/executor must not be usable for these directory actors.
New TOTP checks both new and old used-step histories, but the old verifier does not
know new histories. Therefore this is **not** a two-way cross-runtime one-use proof.
No fixture endpoint is exposed in the new backend service. No actor or provider IDs
are accepted from ordinary HTTP requests. Operator enrollment is not public signup.

## Roles and trust boundaries

- v00_email_ingress: context_create, capture only. request_started_at comes from the
  adapter at HTTP start alongside monotonic time, before parsing/key/cipher/DB waits.
  A future timestamp or exhausted10s is unavailable; clock skew is not silently fixed.
- v00_email_executor: explicit wrapper allowlist only. No direct table writes,
  provider secrets, synthetic completion, owner membership or witness call.
- v00_email_witness: send_observed only on a distinct trusted egress connection after
  actual pinned provider200/{} for the exact permitted dispatch. Neither client nor
  runtime finalizer supplies success=true. DB additionally checks the sole changed
  committed generation and original user/seal/time. Uncontrolled provider token writers
  invalidate this profile: no concurrent operator resend/manual provider bypass.
- v00_email_observer: safe snapshot(context UUID) only; no secret/plaintext/tag/token.
  Capture every snapshot in a **short REPEATABLE READ READ ONLY transaction**.
- v00_email_owner: NOLOGIN installer/definer inheriting the existing owners. No runtime
  ownership/superuser/BYPASSRLS. Provider RLS remains the original synthetic allowlist.

Use existing protocol/key/secret redaction checks on this new adapter too. Parameter
binding, trusted statements and fixed errors do not by themselves prove live log
redaction. Keys stay outside DB. Email cipher purpose/key is separate from address,
proof, comparison and cookie keys. Details: [private contract](../../docs/technical/first-session/v00-oci/email-entry-db/private-contract.md).

## Expected state and future actual cases

| Case | Expected transport / storage |
| --- | --- |
| EE01 ready | Public create201 then explicit GET200; fixed30min, no actor/address/login. C01 cannot silently confirm GET |
| EE02 first send | Early capture/binding before cipher; committed one send seal; one provider request; witnessed acceptance and challenge/result/current pointer one T;202 resolved. Acceptance evidence is not mailbox delivery |
| EE03 resend | After60s, one C03 of current expected challenge; old challenge replaced, old result immutable, current issued/expiry from new generation; no family counter reset |
| EE04 live wrong | Trusted current-generation mismatch against both provider branches, one401 result+proof+counter+audit atomically; **zero provider verify requests**, no verify seal/login/steps. Same key gives original401 with no second counter |
| EE05 expiry/foreign/stale | Expired current code401/counter0, foreign404, replaced/stage409; malformed400 before capture. Context expiry401 takes precedence over code handling |
| EE06 send no-forward | One sealed admission, proxy accepts one request and forwards0; no accepted observation/result/challenge. GET202; repeats/new keys do not send again |
| EE07 send response lost after effect | Separate address; one real provider generation/mail, adapter gets no success. No send_observed/accepted result/current challenge; original seal remains unresolved, GET202. Loss of response never permits another send |
| EE08 business limits | Across contexts same address: resend≥60s, at most5 accepted/15min and10/hour; persistent accepted observations count. Any possible unresolved send blocks address sends even after timeouts/windows; no automatic release. Exact replay/GET do not add a send slot |
| EE09 races | Two new C03 of one expected and C02/C03 in both orders with real barriers: one winner, dependent unknown503, no second effect. A timeout is not rollback evidence |
| EE10 existing completion | Correct current code→one verify seal/provider consume+same-T session witness→full dependency bundle or original TOTP stage. All-matching TOTP, recovery/Q01/logout remain guarded; lifetime30d/7d anchored to exact completedAt |
| EE11 locale | RU is valid input but this pinned sender has no per-request locale.503 before seal/network/accepted slot; no silent EN fallback. Exact saved replay is sought first; full RU capability remains open |
| EE12 negative/ACL | Runtime cannot insert results, invoke trusted witness, read secrets or call synthetic dependency completion. Unsupported provider403 is503/unresolved; unavailable record/clock/crypto is never a wrong-code counter |

Mailpit issuance/delivery, egress dispatch count and HTTP status/body are separate
operator observations. Token generation alone is not send acceptance. known acceptance
time is DB registration of sufficient evidence after provider200, not SMTP delivery.
Provider generation lifetime is10min; local challenge expiry is min(issue+10min,
context.expiry), as accepted D02§2. Neither read nor resend extends the context.

Address serialization plus one unresolved dispatch prevents oversubscription before
acceptance; confirmed observations supply the rolling counts. There is no pending
reservation TTL or guessed no-effect release. Transport quotas are a separate
dependency: this package does not claim the full persistent AC13/14 quota matrix.

## Independent checks and remaining limits

`negative_reference.py` is a source-pinned independent synthetic SHA224 classifier
oracle; it does not authorize runtime outcomes. `audit_snapshot.py` reconciles safe
relations, original deadlines, generation/witness refs, negative proof and counter
history, dependency completion and original challenge versions without DB/network.
Its PASS does not prove SMTP/HTTP/crypto or actual lock ordering. Before/after snapshots
remain necessary to establish zero deltas for unknown. Zero rows are no-data, not PASS
for an unexecuted branch.14 local groups cover the classifier and structural auditor;
their success is distinct from SQL/HTTP/provider behavior.

The provider email-change invalidation hook is fail-closed, not a lifecycle API or
proof of global lock order. That excluded external update path can take provider row
before directory, unlike normal execution, and can deadlock; a failed transaction
must produce no wrong-code result/counter. Do not claim this lifecycle was tested.

Signup, RU delivery, public TOTP renewal/MFA management, full transport quotas,
global drain/reopening/U03 finalizers and production secret erasure remain open.
Cipher is inaccessible after context expiry but this disposable candidate has no
eraser; historical storage/backup secrecy is not certified. New namespace tables
are test implementation, not additions to the accepted production catalog78.
No publication of new raw/derived actual JSON is authorized by the implementation
approval. Prior publication/merge rejections remain separate and are not bypassed.


## Forward correction008 — actual setup findings, not HTTP results

Server reported exact5f5e757/001–007 installed on a fresh closed copy, four confirmed
synthetic subjects, zero contexts. Its first loader input failed because the backend
producer supplied four row fields while the loader accepts two. Operator projected
the two fields after checking directory0; the ensuing SQL rejected the outer entries
array via the legacy scalar-only validator. Operator confirmed rollback/directory0.
No HTTP scenario ran. Those failed setup attempts remain part of the run history.

Source review found the same boundary defect in capture (nested email_binding,
nullable challenge/locale), seal_send (object/null binding), and C01/C03 action checks
in capture, read_operation and finalize_send.008 replaces exactly five functions: capture, read_operation,
seal_send, finalize_send and seed_directory. Nested scalar bindings/rows still use
strict legacy validation; all other legacy calls are scalar C02/TOTP or have no action.
Legacy v00_upstream.keys and v00_session.require_keys remain unchanged. Missing or
extra fields, undeclared null/nested types, invalid digests and unknown actions still
fail closed. Capture additionally enforces the action-specific challenge/locale/binding
shape before locks or writes. Known C01 replay may pass null cipher binding as already
agreed; a new send still requires the full immutable cipher object.

Backend owns the email_prepare producer correction to emit exactly the two loader
input fields; the loader remains strict and derives the keyed digest itself. Existing
private files are preserved; a corrected input must not regenerate keys or contexts.
No automatic retry of a possibly committed fixture is introduced.

`check_input_shapes.sql` is an operator-only, rollback-only validator regression after
008. It exercises accepted nested/nullable/action forms and rejects wrong types,
unknown/missing fields, invalid digests and any widening of the legacy validator.
It also calls capture with valid action-specific shapes against an unknown context
(expected404), rejects invalid dependent/null/nested binding combinations before
access, and verifies no context/admission creation. It requires an open trusted gate
and may acquire its shared lock until rollback; it creates no fixtures.
New-send versus replay material checks still require the later EE02/EE03 runtime
cases: this regression does not simulate saved results or committed dispatches.
It is prepared, **NOT RUN locally**. It creates no Auth fixture or external effect;
it does not prove C01/C03 HTTP/provider behavior or the full runtime guards.
