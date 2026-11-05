# Candidate4: close unintended effective function privileges

05.11.2026. Owner resumed the approved closed synthetic implementation and its
checks in the administrative chat, after the overnight pause: «поехали дальше»;
«так, что случилось? я же давал явные разрешения и даю опять его».
The unchanged bounded offline correction cycle does not require a new owner
question for every hash. Automatic permission review still applies; a rejection
must not be bypassed. Only the server chat operates the existing Oracle.

## Observed failure and correction

Candidate3 manifest
`ff712deeb7f7f6b6d62d54d3de77623a2331f6a80753128666fc2b0c13c5337a`
installed001–007 in a fresh offline DB-only copy. Seed: users2/venues2/sources2/
traders4, disabled. `test-disposable.sql` reached deferred constraints under
polygon_executor, then failed `runtime_no_internal_helper_access`. No final suite
JSON was emitted;47/40 PASS is not claimed. test-numbers and008 did not execute.
Safe output: `/private/tmp/shadow-polygon-paper-candidate3.mcuXwh/oracle-db-only-safe.txt`.
Clone cleanup is recorded separately by the server operator.

Cause: per-schema default REVOKE cannot remove PostgreSQL's global default PUBLIC
EXECUTE. This affected the helper set, not merely numeric_settings; the runtime
had schema USAGE. [PostgreSQL17 reference](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html).

Exact executable delta from frozen source f7fdeac:

-001: global default REVOKE EXECUTE for the newly created polygon_owner only.
  Existing Auth owners/defaults are unchanged.
-006: explicit REVOKE ALL on all polygon functions from PUBLIC and polygon_executor
  before the unchanged nine exact RPC grants, in the same transaction.
-test-disposable: retain all47 assertions, add four effective ACL assertions.
  Every polygon function is compared against the exact nine signatures, including
  denying all other overloads/helpers; no runtime grant option; no PUBLIC EXECUTE
  on any polygon function or the Auth bridge; neither global nor schema defaults
  reintroduce PUBLIC execution for future polygon_owner functions.

002–005,007,008 and test-numbers are byte-identical to candidate3. The bridge
already has explicit PUBLIC REVOKE and only polygon_owner receives EXECUTE.
RPC shapes, auth checks, finances, complete-bundle constraints and scenarios are
unchanged. Owner-context RPCs and deferred triggers retain their required access.
This is a source correction, not proof that the corrected SQL passes.

## Frozen procedure and expected counts

Verify the new SHA256SUMS and independent backend review before execution. Use a
fresh DB-only copy entirely inside the existing Oracle, with verified container/
volume name, label and mount, network=none, listen_addresses='', local socket only.
Do not reuse a partially installed clone. Do not copy provider secrets to the Mac.

Apply001–007 in order with ON_ERROR_STOP; set polygon_tzdb_version=2026e for007.
No existing Auth scripts/provider seeds/recovery009 and no008. No new runtime LOGIN
is needed. Use two separate suite connections with
PGOPTIONS=-c polygon.disposable_test=offline-clone:

-test-disposable.sql expects51:4 Auth-fixture assertions,24 common user-loop
  assertions,6 first-user-only assertions,4 cross-user/used-priority assertions,
  6 independent aggregate assertions,3 original privilege assertions and4 new ACL
  assertions. Deferred constraints still fire under polygon_executor before RESET ROLE.
-test-numbers.sql expects40, unchanged lexical/precision/raw/Unicode/JCS cases.

Both suites ROLLBACK. Capture only safe stage/errors/final JSON and verify zero
keys/receipts/reviews/sessions/financial/audit/outbox records after rollback; seed
remains2/2/2/4 and disabled. Safely remove only the verified disposable copy after
evidence. Stop on first error and record its exact hash; never skip assertions,
relax constraints or patch a mounted package to manufacture PASS.

No permanent application,008/activation, expenses, live/public access, actual
claim, Q06, Owner grants or staff extension is included. HTTP, concurrency,
unknown COMMIT, real browser and paper restart/restore remain separate evidence.
Candidate2/3 operator notes are historical; this document controls candidate4.
