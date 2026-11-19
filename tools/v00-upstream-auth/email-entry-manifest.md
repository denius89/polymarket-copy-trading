# V00-07: ordinary email entry — backend package

04.11.2026. Base `f53b54de5546752c8cf0042c5def4f97d6aaca05` (PR248/249
are merged). Separate approved V00 implementation, not a new product contract or
V01 acceptance. Direct authorization: management user message
`01a1a768-8604-7292-bf2a-f5cf4de4503c`. Oracle is operated by the server chat only.

## Scope and prerequisite

The existing approved forms in
[Auth addendum §§4–7](../../docs/technical/first-session/backend-auth-contracts-addendum.md)
are used: real empty context creation, proof-confirming GET, C01, C03, C02, existing
TOTP/completion/Q01/recovery/logout projections. New entry does not expose fixture
bootstrap or manufacture a context subject before email identity proof.

This first profile uses a synthetic **existing confirmed** provider user, private
Mailpit and a separate `v00_email` test namespace. Signup and per-request RU email
delivery are not implemented by this profile. RU is a valid request value but its
new send must fail503 before a dispatch permit; it must never silently send EN or
change user metadata/global templates. The EN template and actual letter are checked
by the operator. Accepted RU product support remains open, not removed.

The DB chat owns `scripts/v00-email-db` and its private-contract/independent verifier.
Install only its separately sealed, reviewed package into an isolated copy with the
unchanged `v00_session`/`v00_upstream` dependencies. This document is not a SQL install
command. Code preparation and local doubles do not establish that SQL is runnable.

## Trust and execution

- `email_serve.py` is disabled unless `V00_EMAIL_ENTRY_ENABLED=1`. Its handler captures
  UTC milliseconds and monotonic deadline before parsing and DB/key/cipher work.
  `email_ingress.py` supplies `request_started_at` through the separate ingress role;
  no client field/header can set the clock, epoch, executor, address material or user.
  DB rejects future/untrusted/stale time and retains the original10s deadline.
- C01 capture holds only the canonical address HMAC/key ID and original raw-input
  comparison; it returns the immutable context expiry. Encryption occurs afterward.
  `seal_send` binds the encrypted address and one dispatch before any network call.
  GET alone marks context access confirmed; internal context inspection cannot do so.
- `email_database.py` has three closed method sets: ingress (create/capture), executor
  (guarded operations), and witness (`send_observed` only). PostgreSQL17 parameters
  use the existing extended bound protocol; secrets are not SQL statement text.
- Dispatch is one passwordless `POST /otp` with `create_user=false`, including C03.
  No redirects/retries/refresh or fallback `/resend`. Only actual200/empty object
  permits a separate trusted observer call; DB additionally requires the exact
  generation transition. This proves observed acceptance, not SMTP delivery.
- A positive C02 candidate is sealed, sent once, and completed only from the exact
  provider consumption/session witness. Provider403 is not a wrong-code proof.
  A source-pinned local precheck can instead prove a wrong live code under DB locks,
  then commit one immutable rejection and one family-counter update **without** an
  external `/verify`. Both confirmation/recovery and raw/pkce_ hash variants matter.
- The accepted address limits60s/5 per15min/10 perhour and wrong-family5/15min live in
  DB. One unresolved sealed send blocks the address; no timeout release/new-key bypass.
  Transport quotas are a separate capability. Full production quota/cipher/closure
  support is not claimed by this isolated package.
- Saved results are immutable. Direct accepted send returns202/resolved, history
  returns200/resolved; unknown execution503, history202/unresolved. Error envelopes
  contain no receipt/result. Current navigation comes from current protected state;
  GET operation navigation is always null. No cookie before confirmed completion COMMIT.

## Private configuration

Provide the existing context/credential/comparison/cipher keys plus **independent**
`email_address` (`email-address-1`) and `email_cipher` (`email-cipher-1`) random32-byte
keys in the private key file. Never print or publish it. The test codec is explicitly
`v00-test-email-xchacha20poly1305-v1`, not a full production AC07 certification.
Address HMAC framing includes ENV, email_send, ascii-email-v1, canonical email.
AAD binds ENV/user/secret/context owner/purpose/format/original context expiry.

`email_prepare.py` can generate fresh private input files, without network/SQL or
context creation. Its mode0600 source has exactly `origin,entries`; each entry has
`name,actor_id,email` from the verified operator inventory. It writes a new0700
directory containing six independent keys, empty app config, per-alias client
configs and `directory-input.json` for the operator-only DB loader. Existing paths
are never overwritten. The loader checks the actual provider email; the file is
not proof of provider identity by itself.

```sh
python3 email_prepare.py /run/private/verified-identities.json /run/private/email-entry
```

Required environment names in the isolated service:

- `V00_EMAIL_ENTRY_ENABLED`, `V00_EMAIL_CONFIG`, `V00_KEY_FILE`;
- `V00_EMAIL_PSQL_COMMAND_JSON`, `V00_EMAIL_INGRESS_PSQL_COMMAND_JSON`,
  `V00_EMAIL_WITNESS_PSQL_COMMAND_JSON` — distinct role connections;
- `V00_PROVIDER_ORIGIN`, `V00_ORIGIN`, `V00_TLS_CERT_FILE`, `V00_TLS_KEY_FILE`;
- optional existing `V00_SODIUM_LIBRARY`, `PORT`.

The service config is a private JSON object; `fixtures` must be absent or empty.
No operator fixture token or pre-created Auth context is consumed. Operator provisioning
still needs the verified synthetic provider user/factor directory, private keys,
closed gates, roles, trust clock, safe provider logging and effective pinned config.

Run from `tools/v00-upstream-auth` inside the approved private service container:

```sh
python3 email_serve.py
```

Client config is private mode0600 with only `origin` and synthetic `email` (not a code).
Client network reaches the application only, not Auth, Mailpit, PostgreSQL or observer.

```sh
python3 email_probe.py /run/private/email-client.json --ca /run/private/ca.pem --mode success
python3 email_probe.py /run/private/email-client.json --ca /run/private/ca.pem --mode unknown
python3 email_probe.py /run/private/email-client.json --ca /run/private/ca.pem --mode unsupported_locale
```

Use separate synthetic addresses/isolated states for the three modes: unknown blocks
its address intentionally. Probe operator inputs are one JSON line on private stdin:
`code` for each requested code, and `window_open`/`snapshot_captured` booleans at the
resend pause. These booleans coordinate the run; they do not substitute for evidence.
Do not refresh context/deadline or replace a key to force a failed case to pass.

For unknown sending, `email_hold_proxy.py` accepts/discards one exact `/otp` request,
waits7s against the real provider transport's5s timeout and never forwards. It has no
upstream address/release path. Enable only with `V00_EMAIL_NO_FORWARD_ENABLED=1` in an
operator-only network, no public/host port and no Auth/Mailpit/DB egress. Private stdin
contains exactly `email,observer_token`; operator GET snapshot needs that bearer.
The closed observer reports counts/dispatch ID only. Original `/verify` hold proxy
retains its default behavior; the new path is explicit and allowlisted.

## Independent expected observations

| Case | HTTP/transport | Required DB/provider observation |
| --- | --- | --- |
| Ready context |201 context cookie, GET200 confirms; no full login | No subject/address/login before C01; fixed30m; failed confirmation cannot send |
| C01 accepted/replay |202 resolved then same202; GET200 no cookie | One accepted dispatch/generation/challenge/result, raw comparison preserved; replay adds no send |
| Wrong current code |401; GET200 saved rejection; exact replay401 | Zero external verify, no provider session/local login/TOTP step, exactly one negative proof/result/counter; replay no increment |
| C03 | After natural60s,202 new challenge; old C02 conflict409 | Second accepted dispatch, old result/time unchanged, current pointer changes, family counter unchanged |
| Correct email/TOTP |200 stage or completion; Q01 selects same login | Exact provider witness, first identity binding, existing complete atomic bundle, first Q01 closes only recovery secret |
| Unknown send |503; GET202/null; exact repeat and second-context bypass503 | One possible dispatch; hold proxy accepts1/forwards0; no accepted send/challenge/result/login; address exclusion survives repeat |
| RU capability |503, no cookie/false accepted result | No dispatch, mail, generation, send-count, login or failure-counter effect |

Use independent short repeatable-read read-only before/after snapshots. Provider/mail
evidence and source continuity must be tied to each original operation/dispatch, not
inferred from HTTP200 or a final count. Source hash/seed/OTP/cookie/address/ciphertext
do not belong in reports. New raw or derived actual evidence is private unless its
publication is separately authorized.

## Validation and remaining work

Local test command:

```sh
python3 -m unittest discover -s tools/v00-upstream-auth -p 'test_*.py'
npm run check
npm run test:repository
git diff --check
```

Source review and local tests are separate from future Oracle results. Actual new
entry/probe execution is **NOT RUN** until separately recorded by the server and
independently verified. Full limit-window exhaustion, concurrency matrix, browser
flows, signup, RU delivery, complete D02 codecs/transport quotas and U03/global
reconciliation are not certified here. Provider email-change lifecycle is excluded;
directory invalidation fails closed and is not proof of its global lock ordering.

At the prepared backend revision,100 local tests pass:67 existing tests plus33 new
email-entry groups. Repository checks and whitespace checks pass. DB's addressed
review identified unnecessary encryption on existing C01 capture; this was corrected
and covered by a missing-cipher-key replay regression. Known replay now passes null
material and never creates a new nonce; it cannot restore a dispatch capability.
