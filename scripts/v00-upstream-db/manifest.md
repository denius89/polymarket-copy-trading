# Isolated V00 upstream DB executable package

Baseline `a90ee69`; direct continuation V00-06 message
`01a1a6f3-387b-7cf0-82a2-66936cd8a3be`, 04.11.2026. Only the server chat operates
Oracle. No production/current stands, extra spend, live execution or V01 admission.
This file describes the implementation subset of [PR239](../../docs/technical/first-session/v00-oci/upstream-db-verification/README.md).

## Install once and order

Fresh isolated upstream database with Supabase Auth2.197.0 and the unchanged
`v00-session-db/001..004` dependency, no005. Operator attested dependency39 pass,
actual provider columns, one synthetic verified/base32-looking factor, UTC, and
pgcrypto1.3 available but not installed. Those observations do not prove our hooks.

Install `001-core.sql`, `002-provider.sql`, `003-crypto.sql`, `004-completion.sql`,
`005-views.sql`, `006-fixtures.sql` in that order with stop-on-error. Each file is
atomic. No IF NOT EXISTS overwrite: an unexpected existing object stops installation.
Record all file SHA256 before execution. Core is independent of provider reads;
provider instrumentation and explicit private pgcrypto installation are separate.
On installation failure do not reset any old stand or silently continue. Correct
the candidate in this fresh test database under operator control and record it.

Existing candidate `43bb6f5` installed001–006 successfully, then runner stopped after
10 pass checks at capture: PL/pgSQL row variable `r` collided with query alias `r`.
Apply `007-capture-fix.sql` only to that installed candidate, no reset/data rewrite;
it replaces the function with the corrected body already present in fresh001.
Then run the current harness with fresh UUID fixtures. Preserve the incomplete
first run as evidence, not a pass for the rest of the package.

RLS stays enabled. Owner has SELECT/row-lock privileges only on allowlisted provider
users/factors and scoped policies. Runtime has function execution only, no seed
read/fixture/global control. Do not grant runtime `v00_session_executor`, either
owner role, superuser or BYPASSRLS. Crypto schema/function access is owner-only.

## Connections, fixtures, secrets

- `v00_upstream_ingress`: only capture; distinct trusted ingress connection before
  queue/dispatch. Captures immutable operation budget, epoch and assigned executor.
- `v00_upstream_executor`: public-adapter wrappers only.
- `v00_upstream_observer`: safe versioned snapshot only; not an HTTP user route.
- `v00_upstream_owner`: NOLOGIN installer/definer, never runtime membership.

Capture keys exactly: context_id,proof_digest,operation_id,action,fingerprint,
comparison_hmac,comparison_key_id,executor_id,executor_proof_digest. Action C02 or
AUTH_TOTP_VERIFY. Return exactly http201/200,admission_id,created true/false.
Proof is canonical unpadded base64url of32 random bytes (43 ASCII); digest SHA256 of
those ASCII bytes, lowercase hex64. Raw capability stays only with the initial
handler. Capture replay never changes digest/epoch/start/deadline or restores proof.
This is a high-entropy private V00 capability, not a replacement product Auth proof.

ReadRef includes action. WriteRef adds fingerprint/comparison_hmac/comparison_key_id.
`seal_email` and `plan_totp` add admission_id and executor_proof to PR239 signatures;
all other private keys and return/commit variants are as documented there. Seal can
return the normal replay variant when an immutable final result already exists.
Elapsed budget never hides an authorized historical result. Ingress also enforces
the original monotonic10s from HTTP acceptance; starting a later DB call does not
restart that external budget. No automatic retry on uncertain COMMIT/dispatch.

Sensitive calls MUST use PostgreSQL bind parameters, not literal/base64 SQL inlining.
PostgreSQL error statements can log inline text even when log_statement=none.
Actual preflight: psql17 `\\bind` works and a forced-error primitive did not log the
bound marker. Adapter/function redaction still needs its own actual check.
SQL exceptions use fixed text. No raw provider code/seed/cookie/proof in reports.

Operator setup order: create confirmed synthetic provider user; optionally actually
enroll/verify provider factor; invoke `seed_adapter.py /private/fixture.json`; then
issue exactly one real OTP while hooks already operate; record separate /otp response,
generation and actual mail observations. Do not create a generation retrospectively.
Provider setup/fixture is not public C01/C03 or production factor lifecycle.

Fixture JSON exactly `subjects` and `contexts` arrays. Subject keys:
actor_id,provider_user_id,factor_version,provider_factor_id,fixed_time. Last three
may be null; factor_version/provider_factor_id are both null or both UUID. Actual
HTTP actors use fixed_time=null; fixed clocks are operator-only crypto fixtures.
Context keys: id,actor_id,proof_digest,email_challenge_id,expires_at,login_expires_at,
idle_expires_at. Actor must occur in this envelope. Provider rows are validated,
never created/changed by the loader. No raw secrets. No overwrite on conflict.
`V00_UPSTREAM_PSQL_COMMAND_JSON` is an argv array ending in administrator psql for
this isolated DB; the loader uses bound JSON and confirms actual COMMIT command tag.

## Current limits and claims

Implemented first path: existing confirmed user's recovery-family consume/session
witness, optional active-provider-factor local TOTP, atomic Shadow completion,
read/recovery/Q01/logout wrappers and safe snapshot. Provider MFA AAL2 on each login
is not claimed. Base32 encoding outside the supported canonical profile fails closed,
as do unavailable crypto, provider source and untrusted clock; no failure increment.

Initial signup/confirmation completion, full C01/C03/resend/mail uncertainty,
email negative classifier, global drain/reopening/reconcile U03, quota persistence,
challenge renewal and general MFA lifecycle are NOT IMPLEMENTED. Captured attempts
that fail a new precheck remain unresolved until a separately proved closure; this
conservative first slice may strand a fixture, never grants a replacement permit.
No unattended scheduler or production admission follows from passing this slice.

No challenge renew/mutation is exposed: current challenge remains the immutable
source used by this slice's historical auth_step_required. Future renew requires a
separate immutable challenge relation before enabling it. Current navigation resolver
is not implemented; historical result alone is not fresh nextAction permission.
Comparisons are retained in a closed table for this disposable test; expiration
denies comparison use. Production secret-erasure lifecycle is not implemented.

Oracle runner results and actual real-provider HTTP evidence must be recorded
separately. Python RFC oracle pass is not SQL/HTTP/provider PASS. SQL harness uses
public RFC seeds and synthetic cipher bytes; it does not prove authenticated
encryption, real enrollment, provider dispatch count or browser behavior.
