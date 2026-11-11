# V00: narrow persistent recovery quota — DB package

2026-11-04. Local, synthetic candidate only. Original owner approval:
`call_a1a0a4dfe7574274bb2fac1ad130212c`; explicit resumption after the PR212
document-only task: user message `01a1a832-5574-7fd1-82b4-d47946c2900d`,
question `call_033ce46d039a4b80ab0ce9649ebba567`.
No GitHub publication, V01, new costs or production deployment.
The server chat is the sole Oracle operator.

DB baseline: `fccde4e9a433bef5b96f2ed45d064190ccc2d915`.
Backend source reviewed: `97bf85faccf25e4212c53a8185295203ba419f02`.
Backend independently re-reviewed 009/010 after both corrections and reported
no remaining source blockers. This is not executed SQL/ACL evidence.

## Install boundary

Use the existing isolated upstream/session/email baseline, including unchanged
email 001–008. Install 009, then 010, then run read-only 011. Installation 009
rejects existing email contexts: old profile migration is not included.
There are no new LOGIN roles. Bind the existing minimal group roles to the
separately authenticated test connections and verify their complete inheritance
and effective permissions. Never run the adapter as an owner/superuser.
011 checks group privileges; the operator must additionally check actual LOGIN
roles, not infer isolation from different connection argv strings.

009 adds five isolated candidate tables; this does not change the accepted
78-table production catalogue. Context and expected quota scope are created in
one transaction, enforced by a deferred constraint trigger. A missing expected
scope fails closed; no lazy empty-history creation or refund exists.

## Policy and transactions

Only explicit user C02/AUTH_TOTP_VERIFY login-cookie POST has this quota:
environment + original context + `user/login/cookie_recovery`, three admissions
strictly newer than trusted UTC now minus60s. Read time is taken after the
scope lock. History is immutable. A rejected fourth request does not insert or
move timestamps. No retryAt is guessed. Unknown COMMIT is503, no cookie/retry.

Transport, Origin/CSRF and current context/actor access precede admission.
Protected operation/result, resolved login and cookie-window checks follow it.
The original request start is canonical UTC milliseconds and must be finite,
not in the future and less than5s old. The trusted adapter separately preserves
the original monotonic five-second deadline from before HTTP parsing. DB
timeouts do not create a new budget. TLS handshake is outside this narrow bound.

1. Quota T: readonly access guards, quota scope X, count+admission, confirmed COMMIT.
2. Open subject T READ COMMITTED: obtain its actual PID/txid, no subject locks yet.
3. Seal T: bind one immutable attempt to that exact PID/txid, confirmed COMMIT.
4. Original subject T: first lock G1 FOR SHARE, validate original admission epoch,
   proof/source/deadline and exact target T; insert unique use; owner-only recovery.
   Hold G1 through subject COMMIT. Existing subject/window→secret locks still apply.

Admission/attempt remain after subject rollback; rolled-back use does not prove
there was no attempt. A new T cannot reuse an old target txid. Within the same T,
a second use violates uniqueness. The trusted adapter has no SAVEPOINT, arbitrary
SQL or retries; this is not protection against a malicious raw SQL credential
holder rolling back a savepoint or an administrator rewriting history.
Quota/seal T take no subject row locks. Subject T has no network/provider call.
The409 closed-window branch preserves its required COMMIT and erasure. Technical
subject failures roll back; they never refund the committed quota/attempt.

## Exact private interface

`ref` = context_id, proof_digest, operation_id, action. Errors exactly `{http,reason}`.

| Method / group | Additional input | Success |
| --- | --- | --- |
| recovery_admit / ingress | admission_token UUID, executor_id UUID, executor_proof_digest SHA256 hex, request_started_at UTC millis | http201, admission_token, deadline_at=start+5s |
| recovery_target / executor | Empty object, no ref | http200, target_pid positive integer, target_txid decimal string |
| recovery_seal / ingress | admission_token, executor_id, executor_proof, target_pid, target_txid | http200, sealed=true, admission_token, target_pid, target_txid |
| recovery_once / executor | admission_token, executor_id, executor_proof | Existing recovery response |
| recover_completion_replay / executor | Ref only | Existing recovery response |

The executor proof is canonical unpadded base64url of32 random bytes; its digest
is SHA256 of the43 ASCII characters. It is transient, not logged/persisted raw.
Legal completion replay creates a one-use guard only in the actual original
plan's exact replay after fingerprint/comparison checks, and consumes it in the
same T. It does not spend the explicit recovery quota. Raw recovery and original
renamed plans are owner-only; replay still obeys the original window/Q01 guards.

## Independent evidence

010 exposes `recovery_snapshot(context UUID)` only to email observer: existing
email snapshot plus exact scope, admissions with opaque full-row SHA256 instead
of executor digest, immutable attempts/committed uses, and replay guards. Read
each snapshot in a fresh RR READ ONLY transaction bracketed by database UTC,
PID, isolation, role and host timing. Do not substitute an empty scope for NULL.

`recovery_reference.py` is the independent integer-microsecond rolling-window
oracle. `audit_recovery.py` checks original email completeness, source/target
relations, fixed deadlines, immutable history and maximum three per window.
`test_recovery.py` mutates those relations and checks exact boundary equality.
These offline tests do not prove PostgreSQL enforcement or operator observations.

Actual cases: three admissions + adapter/client restart then429; overlapping
last-slot race; staggered slot release then immediate429; prequota rejections;
Q01 closure then charged409; subject lock timeout retaining admission/attempt;
quota lock timeout; proved quota rollback; lost ACK of actual quota COMMIT;
slow HTTP body; original deadline exhausted after committed admission.
Cookie equality/no-cookie is checked in client memory. Keep raw secrets out of
safe evidence. Collect per-case snapshots, phase traces, exact source hashes,
provider/mail counters, startup/version/time and effective-role evidence.

Controlled row locks and actor blocking apply only to the designated isolated
synthetic cases. Lock timeout is not proof of exhausting the full5s budget.
Full history loss, production AC13/14, general Auth, V01, post-handshake network
delivery guarantees and backup restore remain outside this candidate.
