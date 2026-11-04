# Operator probes A/B — unchanged tested Auth runtime

04.11.2026. These tools extend the **test harness only**. The runtime baseline is
PR244 commit `210044b3ecee092499baa4602f3a36f0344a6cf4`; adapter/bridge/provider/crypto
files are unchanged by this addition. Server chat alone operates Oracle. Use fresh
synthetic fixtures, internal networks, zero extra cost; no production or V01.

Prior scenario results do not establish the new A/B cases. Runtime evidence is a
separate operator/DB artifact, not embedded in this code package. New harness
scenarios start as **NOT RUN**. Six new local tests
cover proxy acceptance, duplicate concurrency, strict source matching and safe
observations; they are not real provider/DB/browser tests.

## A. Same-user TOTP race

Prepare `race_a` and `race_b` through `prepare.py` with the **same** provider user,
same actually enrolled/verified factor and therefore one Shadow actor/factor version.
Give the client only client.json and the public CA. The provider/DB/seed stay outside
the client network. No fixed clock or direct insertion of a verified factor.

```sh
python3 tools/v00-upstream-auth/fault_probe.py race /private/client.json --ca /private/ca.pem --fixtures race_a race_b --confirm-unadmitted-retry
```

1. At each `need_email_code` event, issue exactly one real fixture OTP for the named
   context after hooks/allowlist installation, and supply one private stdin JSON
   line with exactly `code`. The probe resolves C02 for A before requesting B's
   email code. Both must reach `auth_step_required`; no login/cookie yet.
2. At `race_ready`, the operator may hold the shared actor row in a separate admin
   transaction. Record safe backend PID/actor/lock identifiers. Supply a fresh
   current TOTP as one private `code` JSON line; the probe creates two different
   original TOTP operation IDs and emits `race_dispatching` with their safe refs.
3. Two independent clients start through a barrier. Observe **two actual waiters**
   on the held actor, then release promptly: runtime lock timeout is3s. Use a bounded
   observation shorter than that timeout; if both waiters are not observed, release
   and mark overlap evidence insufficient. Never hold until both requests time out
   merely to claim a concurrency test. Two overlapping HTTP intervals alone are not
   DB contention evidence.
4. Expected: exactly one200 completion. The other is either401 with a saved
   `verification_rejected`, or503 when capture sees the first unresolved admission.
   No cookie accompanies the loser. Record the actual branch; do not call503 a
   used-step rejection. Both failures or two successes fail this test.
5. For a503 loser, the probe performs GET of that **same** operation and emits
   `race_unresolved`. No automatic POST follows. With the optional flag above it
   waits for an operator decision. Only an independent snapshot proving **no
   admission was created for that loser** and a resolved winner permits one explicit
   replay of the exact original request/code/operation ID. Supply private JSON with
   exactly `retry`, `admission_absent`, `evidence_id`; true/true requires the actual
   safe evidence identifier. If an unresolved admission exists, send retry=false
   and do not reissue an executor capability or invent a new operation.
6. The exact request must still be inside the code's valid step window. If it is
   not, stop this case and report its limit; do not replace the code under the same
   key. After a known401, one explicit exact replay checks that the saved rejection
   remains401, without a new cookie. GET history stays immutable.

Required independent before/after DB observations: same actor/current factor;
two original resolved C02 stages; one full TOTP result/plan/login; complete original
matching set consumed once; no additional step from the losing attempt. If401
occurred, exactly one failure increment/result/audit, and no increment on exact
replay. If503 remained, no fabricated failure result/count. Match every row to the
two operation IDs. The winner remains usable through Q01.

The report distinguishes `initial_statuses`, `final_loser_status`, exact retry
evidence and HTTP intervals. `lock_wait_evidence` and step/counter evidence remain
explicit external requirements; the probe cannot certify them by itself.

## B. Accepted dispatch with no provider outcome

Prepare `unknown` and `unknown_b` as two contexts of **one new no-MFA provider
user/Shadow actor**. No other test uses that actor. Install/seed before its single
real `/otp` issuance. Then configure a dedicated isolated adapter instance (or an
exclusive test window) with unchanged runtime code and `V00_PROVIDER_ORIGIN`
pointing to the test proxy. Do not change another active stand's routing. The proxy
has no host-published port, no route/credentials to Auth/DB/Mailpit and no client
network access. Only the adapter can POST; the operator can read safe observations.

```sh
V00_NO_FORWARD_PROXY_ENABLED=1 python3 tools/v00-upstream-auth/hold_proxy.py --bind 0.0.0.0 --port 9998 --hold-seconds 7
```

Before `no_forward_proxy_ready`, supply one private stdin JSON line with exactly
`email`, `code`, `observer_token`. The email/code must exactly match the real fixture
and the later C02; observer_token is a fresh private random32-byte base64url capability.
No value enters argv, public config, tool output, shell history or verbose logs.

The proxy accepts only the exact provider POST `/verify` payload and canonical
`shadow-v00-upstream/<dispatch UUID>` User-Agent. It allows **one** request, deletes
the expected secret from its state immediately, sends no headers/body for7s, then
closes. Adapter provider timeout is5s. There is intentionally no upstream address,
forwarding function, release control, retry, stored request queue or successful Auth
response. It cannot later replay the held request. An unexpected second POST is
counted/rejected, never forwarded. Keep the process alive through all assertions.

```sh
python3 tools/v00-upstream-auth/fault_probe.py unknown /private/client.json --ca /private/ca.pem --fixtures unknown unknown_b
```

At `unknown_ready`, supply the same private `code` JSON line. The probe checks:

- First C02 returns503 without cookie; GET the original op returns202/null result
  and null resolvedAt. Lack of evidence does not mean rolled back or wrong code.
- One explicit exact POST repeat retains the same body/op and stays503, with no
  second proxy request. Explicit login-cookie recovery is503 without cookie.
- Two explicit **negative bypass probes** (new key in the same context, and a key
  in the other pre-existing context of that actor) are rejected503 before a new
  admission/dispatch. They are not used to recover/continue the original operation.
  Unexpected acceptance fails the test immediately; never force them through.
- Final GET of the original operation remains unresolved. No resend, token refresh,
  new verification route or operator finalizer is invoked.

Operator snapshot: GET `/__operator__/snapshot` on the internal proxy with its
private Bearer observer_token. It returns only counts/dispatch UUID/times, never
expected email/code or token. Read once before C02 and after the held connection
closed and all probes completed. Expected total seen=accepted=closed=1, rejected=0,
forwarded=0. More than one request fails no-repeat, even if rejected by the proxy.
Match dispatch_id to the DB seal ID; retain independent internal network isolation
evidence because a constant forwarded=0 alone is not evidence about another process.

Required DB before/after: one original immutable admission and seal; no consume/
outcome/result/plan/login/used step and no counter delta. No admission for the two
forbidden keys. Read and recovery do not change the original deadline or executor.
Retain the unknown record; do not label it cancelled or erase it to unblock tests.
The proxy's operator knowledge of zero forwarding is not an implemented U03 closure
protocol for the adapter. Test-only fixture disposal remains a separate operator act.

## Evidence and limits

Record exact Git/file hashes, DB revision, fixture aliases, safe before/after
snapshots, original refs, timestamps, HTTP statuses and cookie-presence booleans.
Record DB lock waiters for A and proxy acceptance/network observations for B.
No raw bodies, code/seed/cookie/proof values or provider token hashes in artifacts.
Private WebDriver/client/control communication must not enable verbose body logging.

If either case fails or lacks an observation, preserve that result and correct only
the identified defect. Do not convert a limit to PASS or repeat a side effect under
a fresh key. These two cases do not implement C01/C03, full lifecycle, persistent
quotas, negative email classification or U03 reconciliation.
