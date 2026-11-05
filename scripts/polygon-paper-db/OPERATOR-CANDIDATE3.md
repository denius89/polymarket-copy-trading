# Candidate3: minimal correction after the candidate2 install failure

04.11.2026. This replaces candidate2 for review, not permission to run it.
The direct permission for manifest
`e8755604304ba40c6c05ae1652b8799ee182c533de447330cdbb42e7e4e53667`
does not authorize this changed package. Only the server chat operates Oracle;
the administrative chat obtains the exact new permission before another attempt.

## Observed candidate2 result

The server reported an offline DB-only Oracle clone and two successful backup
manifest verifications. Independently read safe output confirms 001–004 COMMIT
inside that clone, followed by a syntax error while creating `session_valid` in
005: `syntax error at end of input`, at the unparenthesized CASE in the IF condition.
006,007, both assertion suites and008 did not run. None of the87 assertions passed
or failed: they were not reached. The server reported clone cleanup; final absence
verification belongs to its separate operator evidence. No production activation
or whole-package SQL correctness follows from those four successful install files.

Safe operator evidence: `/private/tmp/shadow-polygon-paper-candidate2.iO35AN/oracle-db-only-safe.txt`.

## Exact executable change

Only005 changes: surround the scalar CASE in
`sl.generation IS DISTINCT FROM (CASE ... END)` with parentheses. PL/pgSQL's IF
expression reader otherwise reaches the CASE's THEN as the IF delimiter. Expected
generation is unchanged:1 for an absent slot, previous generation+1 otherwise.

Static inspection of every CASE in001–008 and both suites found no other bare
CASE in an IF condition: the other CASE expressions are nested in function/ROW
arguments, SQL statements or assignments; the numerical helper's CASE statement
has its matching END CASE. This is source inspection, not a PostgreSQL compilation
or behavioral result. No helper, constraint, role, grant, fixture or assertion is
removed or widened. All other SQL files are byte-identical to candidate2.

## Requested repeat, only after new permission

The exact boundary and ordered procedure in [candidate2](OPERATOR-CANDIDATE2.md)
remain applicable to this newly pinned candidate: a fresh disposable DB-only clone
inside Oracle, offline/local socket,001–007, two rollback suites expecting47+40,
safe evidence, verified cleanup. Use the current SHA256SUMS and record its full
hash.008 remains excluded; permanent database, existing keys and application are
untouched. Stop on the first error, retain its pin, and do not edit mounted files
or retry this package under candidate2's permission. Concurrency, HTTP/browser,
unknown COMMIT, permanent activation and staff remain outside this pass.
