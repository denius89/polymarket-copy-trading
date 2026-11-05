# Candidate5: one-byte assertion syntax correction

05.11.2026. Same owner-authorized bounded correction cycle as
[candidate4](OPERATOR-CANDIDATE4.md); only the server operates Oracle after
independent exact-package review and ordinary automatic permission review.

Candidate4 commit4efa726b50ca5e2f3ad0141a0e5e492e87c738e3, manifest
`67a006f7bd56fbe873e0c121f4ed1a741881ba40c9f522bf645674a4edb8fa10`,
installed001–007 in a fresh offline copy with the expected disabled2/2/2/4 seed.
The suite passed its original helper denial and the added exact whitelist,
grant-option and PUBLIC assertions, then failed to parse the final new assertion.
Safe output: `/private/tmp/shadow-polygon-paper-candidate4.xLDE4A/oracle-db-only-safe.txt`.
No final51 JSON exists; numerical suite and008 did not run. Operator reported
cleanup trap completion; final cleanup evidence belongs to its operator record.

## Exact change

Remove one extra closing parenthesis after the first NOT EXISTS in
`owner_future_function_defaults_private`. Previously it prematurely closed
assert_true before AND NOT EXISTS; both global and schema-default predicates
now form the first boolean argument, followed by the unchanged label argument.
No predicate or assertion is removed. Expected counts remain51+40.

All installation SQL001–008 and test-numbers are byte-identical to candidate4.
Only test-disposable has this one-byte executable difference; README and this
operator note record the observed failure. Static parentheses inspection is not
PostgreSQL execution or proof of91 PASS.

## Repeat boundary

Verify current SHA256SUMS and independent backend review. Execute exactly the
candidate4 procedure on a fresh DB-only offline Oracle clone with checked
name/label/mount, network=none and local socket only:001–007, then the two separate
rollback suites expecting51 and40. No008, existing Auth scripts or provider seeds.
Capture safe outputs, verify rollback state and remove only the verified clone.
Stop at the first error; do not alter a mounted package or skip a check.

No permanent database change, activation, expense, live/public, actual claim,
Q06, Owner grants or staff extension. HTTP/concurrency/browser/restore are not
established by this pass. Candidate4's observed result is historical; this note
and the current manifest identify the corrected candidate5.
