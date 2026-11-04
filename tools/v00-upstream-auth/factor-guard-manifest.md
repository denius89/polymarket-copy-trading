# Applicable UB16: stale local factor binding

04.11.2026. Preparation against merged runtime `411d17b` / runtime source `210044b`.
This package adds an HTTP probe and four local test groups. It changes no runtime,
SQL, permissions, product rule, provider factor or lifecycle endpoint. Its probe
is **NOT RUN** unless explicitly used in a separate recorded operator execution.
An operator-authored probe has its own source/revision; do not relabel its results
as execution of this file. Pending PR247/248 are not prerequisites for this probe.

## Accepted guard and exact scope

[D02 guard table](../../docs/technical/first-session/backend-auth-d02-contracts.md#7-матрица-ошибок-и-восстановления)
and the [private contract](../../docs/technical/first-session/v00-oci/upstream-db-verification/private-contract.md)
distinguish stale version409 AUTH_CONTEXT_STATE_CONFLICT, unavailable factor503
RECORD_UNAVAILABLE and proved proof/access revocation401 AUTH_REVOKED. None is a
wrong-code rejection or permission to increment a failure counter.

`plan_totp` in DB004 checks the context's bound factor against current_factor before
reading/computing with a provider seed. The current V00 profile performs local
all-matching verification inside one DB transaction; it has no late external TOTP
callback. The applicable case here is removal of the current **local mapping**
before a new verification request from an older context.

One genuinely enrolled/verified synthetic factor F1 remains unchanged at the
provider. After real C02 creates the TOTP stage, the isolated operator takes the
same actor X used by runtime and conditionally clears subjects.current_factor
from F1 to NULL for exactly that actor, changing exactly one row, then commits.
This is a fixture invalidation, **not** provider disable, a full F1→F2 rotation,
enrollment/reset/reenrollment, security-version revocation or product policy change.
Do not issue a new C02/no-MFA login against the intentionally detached mapping.
Do not delete F1, alter its seed, rewrite the old context/challenge or invent F2.
Oracle setup/mutation is solely the authorized server operator's responsibility.

## Probe and private inputs

Use a fresh or still-valid dedicated fixture alias `factor_stale`. Check both the
Auth context and original challenge remain unexpired. No COMMIT-loss shim or proxy
is needed; retain the unchanged runtime command and real trusted TLS client profile.

```sh
python3 tools/v00-upstream-auth/factor_probe.py /private/client.json --ca /private/ca.pem --fixture factor_stale
```

1. At `need_email_code`, issue the fixture's real email OTP once after hooks and
   allowlist setup; provide private stdin with exactly `code`.
2. The probe records C02's original auth_step_required result and challenge and
   emits `factor_guard_ready`. It has not sent any TOTP request at this point.
3. Capture a short `REPEATABLE READ READ ONLY` snapshot before the scoped operator
   change. Commit the actor-scoped conditional mapping clear described above and
   capture a second consistent snapshot. Do not hold actor X while waiting on stdin.
4. Supply private stdin with exactly `transition_observed: true`, `evidence_id`
   (a safe alias, not secret/SQL/body), and `code` (a currently valid code of F1).
   The operator must independently establish the transition; a boolean alone is
   not its evidence. No codes or raw mapping values enter public artifacts.
5. The probe creates one original AUTH_TOTP_VERIFY operation with the old context/
   challenge and sends exactly one POST. It does not accept caller factor IDs,
   renew the challenge, retry the operation, generate a replacement key, or call
   provider TOTP. It reads the same operation and the original C02 history only.

## Expected observations

- The original POST returns409 AUTH_CONTEXT_STATE_CONFLICT with no Set-Cookie.
  A technical503 or wrong-code401 is a different branch and fails this case.
- GET the same TOTP operation returns202/unresolved, null result and resolvedAt,
  with the exact source reference and no cookie. The ingress admission may exist;
  a guard reply is not fabricated as verification_rejected or a saved completion.
- The old C02 result, challenge and resolvedAt remain byte-for-byte unchanged.
- Independent consistent DB snapshots show the historical context still bound to
  F1, current_factor NULL, one new immutable TOTP admission at most, and no new
  result/plan/login/used-step or failure/pause change. Existing audit/results and
  provider generation/witness remain unchanged. Prove both sources/expiry so the
  409 cannot merely be an expired/replaced challenge.
- No new external provider effect occurs during TOTP verification. A one-row DB
  count alone does not prove network behavior; use the declared local-adapter
  path and the operator's independent observations.

Retain the unresolved admission and old history; do not erase them or reissue an
executor capability to make another attempt pass. This scoped test does not
implement final closure/drain/reopening, negative email classification, persistent
quotas, factor-management writers or a V01 acceptance decision.

## Local checks and review boundary

The four new local test groups exercise unchanged bridge guard propagation without
completion/crypto/provider effects, one client attempt with immutable source,
stopping before TOTP without operator evidence, and rejecting success/503 as a
false stale-version pass. They use doubles and cannot prove DB counters, locking,
real provider enrollment or any Oracle execution. No runtime defect was inferred
from these guards and no production code changed.
