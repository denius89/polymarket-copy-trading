# D03-07 isolated session adapter

Separate verification code for the user-realm cookie/Q01/logout slice. Baseline
`f223aa6213668fa84fcbdd3b20eb42d5bdec60a2`; execution authorization is indexed in
[CURRENT_AUTHORIZATIONS](../../docs/CURRENT_AUTHORIZATIONS.md). The server chat is
the only Oracle operator. This directory does not modify prior D03-04/05 code,
Auth or `v00_db`. No public ports, real identities, delivery or trades.

## Scope and evidence

The **synthetic upstream step is assumed**, not verified against Supabase. Private
fixture capabilities authorize only their preassigned context/operation/login.
They are not public Auth credentials, and the fixture endpoints must never be
deployed as a product login route. The service has the DB executor role, not the
owner/observer or operator revoke/time privileges.

| Layer | Checks | Recorded result, 04.11.2026 |
| --- | --- | --- |
| Offline | 25 tests: single transaction, commit uncertainty, key/verifier failure, history, closed recovery, completion replay, selected target, parsing, private generator, psql command tags and pipe fault | Passed locally; crypto is mocked here |
| Library | `crypto_probe.py`: actual libsodium roundtrip and rejected wrong key/AAD | Passed on Oracle, libsodium1.0.18; not independent crypto certification |
| HTTP | `client_probe.py`: completion/history/recovery/Q01/erasure/logout/read/repeat/selected header |12 passed on Oracle, plus12 targeted operator cases; not browser evidence |
| Browser | `browser_probe.py`: actual cookie store/HttpOnly/Strict/expiry, lost cookie, recovery, A/B logout/continuation, both completion-response loss cases and lost logout |37 passed on Chromium156.0.8078.79 with trusted CA |
| DB and races | Independent `scripts/v00-session-db` checks/observer/lock barriers | PostgreSQL17.11:39 pass/0 fail/3 not_run at SQL layer, in each of two runs; independent runtime observer review separate |

Runtime results must be appended with tested commit, image/library/browser/DB
versions and exact scope. A failed run remains evidence; use fresh fixtures for
another complete run, never clear history to make a rerun pass.

The actual adapter revision is **`8da826db08043201daf343fe9868b4fd464b6d95`**.
Later additions of `psql_commit_loss.py`, its offline tests and this report do
not change the tested controller/crypto/storage/client/browser runtime. See the
[operator's sanitized actual](https://github.com/denius89/polymarket-copy-trading/blob/main/docs/technical/first-session/v00-oci/d0307-operator-actual-2026-11-04.json),
[S01–S10 matrix](https://github.com/denius89/polymarket-copy-trading/blob/main/docs/technical/first-session/v00-oci/d0307-matrix.md)
and [independent DB package](https://github.com/denius89/polymarket-copy-trading/blob/main/docs/technical/first-session/v00-oci/session-db-verification/README.md).

Targeted HTTP cases cover just before/exactly at/after the recovery deadline,
earlier context expiry, missing cipher key, corrupt ciphertext, revoked/expired
login, known noncompletion, rejected-result historical timestamp and wrong/neighbor
context proofs. Negative recovery responses did not issue cookies. SQL-only
not_run flags remain in their original report; cross-layer evidence is linked
separately rather than rewriting those historical flags.

Actual COMMIT-loss used a **temporary operator-authored pipe shim**, not this
repository's later reusable shim. After observing real psql COMMIT it withheld
the acknowledgement from the adapter. Observed:503 without cookie, original GET
resolved without cookie, Q01 denied, explicit recovery, Q01 success. Independent
DB observations found one original valid completion/login/plan, matching source
links, then window closure and lawful cipher erasure; permanent credential stayed.
No before-snapshot existed for that observer pass: the observation proves the
final persistent bundle, not the number of Set-Cookie transmissions. Transport
and browser evidence establish their own cookie observations separately.

**Not implemented/claimed:** full D02, all78 tables, actual upstream Auth/MFA,
staff, claim, trusted clock infrastructure, external witness, full audit schema,
quota storage/admission (D03-10), lifecycle/archive/backup, product UI tab-selection
logic or V01. A successful browser cookie check does not prove the application's
UI state machine. Cross-site browser suppression needs its own second-origin/CDP
observation; absence of CORS access alone is not that proof. This probe implements
strict selected-cookie lookup and POST Origin/CSRF checks, not production server
capacity/hardening. Auth result history uses DB `resolved_at`, not current time.

## Runtime and private inputs

Python3.11 and psql17.11 in the private ARM64 runner. XChaCha20-Poly1305 uses the
official combined-mode libsodium C API through ctypes. Operator candidate:
Debian Bookworm ARM64 `libsodium23=1.0.18-1+deb12u1`, `libsodium.so.23`.
No pip packages. Verify the actual version with `crypto_probe.py`; installation
and image provenance are recorded by the server. API reference:
[libsodium XChaCha20-Poly1305](https://libsodium.gitbook.io/doc/secret-key_cryptography/aead/chacha20-poly1305/xchacha20-poly1305_construction).

Run commands from repository root **on the operator's isolated runner**:

```sh
python3 tools/v00-session-recovery/prepare.py /run/private/d0307-fixtures
python3 scripts/v00-session-db/seed_adapter.py /run/private/d0307-fixtures/seed.json
python3 tools/v00-session-recovery/crypto_probe.py
python3 tools/v00-session-recovery/controller.py
```

Install DB package first, including its forward update005 when using a previously
created test DB. Follow its manifest; this adapter does not install SQL. Seed with
the operator role, run the service as a dedicated LOGIN member of
`v00_session_executor`, never the owner. A generator directory must not exist;
files are exclusive-create0600, directory0700. It generates21 contexts/19 actors,
two same-actor pairs, no full logins. All login bundles go through plan/complete.
Existing test rows are never overwritten. Fixed time is generated from current
UTC milliseconds; `wall` alone uses the real DB clock. Exact login deadlines are
explicit fixture policy, not proof of real policy provisioning. Browser wall
expiry remains distinct from controlled DB time.

Service environment (values are paths/references, not secrets on command line):

| Variable | Meaning |
| --- | --- |
| V00_FIXTURE_CONFIG | private `server.json`, mounted only to adapter |
| V00_KEY_FILE | private `keys.json`, mounted only to adapter; reread per use |
| V00_ORIGIN | exactly `https://session-d0307.invalid:8443` |
| V00_TLS_CERT_FILE / V00_TLS_KEY_FILE | trusted test certificate/private key files |
| V00_SODIUM_LIBRARY | optional full library path; default library lookup |
| PORT |8443 by default |
| PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSFILE | dedicated DB executor connection; private password file |
| V00_PSQL_COMMAND_JSON | optional trusted argv, default `["psql"]`; never client-controlled |

The service listens0.0.0.0 inside its isolated container; do not publish its port
on the host. Adapter joins lab+client networks; browser/transport client joins
only client network. Client gets `client.json` and CA, **not** server/key/seed or
DB credentials. Do not enable verbose WebDriver/access/psql query logging: such
logs could record fixture capabilities or cookies. Sanitized probes print only
case verdicts and component versions. Socket/TLS errors must not print private
responses. Runtime keys never enter Git; unavailable original keys cause503.

## Routes and client commands

Every protected request uses `requestSchemaVersion=v1`. POSTs are same-origin
JSON with `X-Shadow-Auth-Request: 1`; optional Sec-Fetch-Site must be same-origin.
GETs have no body. Headers/cookies are validated explicitly, not selected by jar
order. Every protected response is no-store. Unsupported fixture command types
are rejected, not silently interpreted as C02.

| Route | Closed request / purpose |
| --- | --- |
| GET `/__v00__/runner` | Minimal page for same-origin WebDriver fetches |
| POST `/__v00__/fixtures/:name/context` | schema only, scoped Bearer fixture capability; issues preseeded Auth-context cookie; no new DB context/expiry |
| POST `/__v00__/fixtures/:name/complete` | schema, commandType=C02, exact authOperationId; scoped capability plus context cookie; synthetic confirmed upstream only |
| GET `/api/auth/contexts/:ctx/operations/:op` | query schema+commandType=C02; immutable result, no Set-Cookie |
| POST `/api/auth/contexts/:ctx/operations/:op/login-cookie` | schema+commandType=C02; original context proof, no client loginId |
| GET `/api/me` | query schema, mandatory X-Shadow-Login-Id and matching cookie; returns synthetic en profile and select_trader |
| POST `/api/auth/logout-contexts` | schema; selected original login credential, even expired/revoked for this proof only |
| POST `/api/auth/logout-contexts/continue` | schema+sourceLogoutContextId+authorizationMode original_login/current_user; selected authorizer separate from immutable target |
| POST `/api/auth/logout` | schema+commandType=C07+logoutContextId+authOperationId; optional selected header must equal target |
| GET `/api/auth/logout-contexts/:ctx/operations/:op` | query schema; protected original context; no side effects/cookie |

Client commands, each against **fresh generator/seed** for a full repeat:

```sh
python3 tools/v00-session-recovery/client_probe.py /run/private/client.json --ca /run/private/ca.crt
python3 tools/v00-session-recovery/browser_probe.py /run/private/client.json --webdriver http://127.0.0.1:9515
```

Transport consumes `basic`; browser consumes `recovery`, `logout_a/b`,
`loss_before/after`. Other named fixtures are reserved for operator fault/boundary
probes. WebDriver must already run in the isolated client container. The browser
uses a trusted CA; `acceptInsecureCerts=false`, no ignore-certificate flags. Raw
WebDriver cookie values are compared only in memory, never printed as evidence.

## Transaction and cookie rules

One psql connection: BEGIN → plan_completion → actual encrypt → complete →
confirmed COMMIT → Set-Cookie. Plan supplies trusted IDs/deadline for AAD. On an
error the uncommitted connection closes/rolls back. A `ROLLBACK` command tag, psql
failure, missing confirmation or timeout cannot be treated as a successful
COMMIT. No automatic transaction/POST retry, no new operation ID after unknown.
The transaction budget is4.5s, statement4s/lock3s; this bounds the DB/crypto
portion, not a measured end-to-end5s SLA. TLS/body transport measurements remain
the operator's responsibility.

Recovery holds DB locks while decrypting and comparing the recovered secret with
the permanent verifier. Only confirmed COMMIT permits its Set-Cookie. A legal
deadline409 can commit close/erasure with no cookie; complete errors always roll
back the plan. First successful Q01 commits closure/erasure before200, without
idle extension. History remains readable under its own live context proof after
login revocation; it does not grant current access. Exact completion replay
after closed recovery returns original completion **without** cookie.

Full cookie name includes its exact login ID, with original absolute Expires;
Auth-context cookie is a session cookie; logout-context has fixed15-minute
Expires. All Secure/HttpOnly/SameSite=Strict/Path=/, no Domain. Logout deletes only
target A's cookie and never retargets authorizing B. A delayed already prepared
cookie cannot override server revoke. `loss_before/after` faults close the real
connection after commit before headers / after flushed headers before body.
`logout_lost` drops its response before headers after committed logout. Faults
are operator fixture settings, never client request flags.

### Separate COMMIT acknowledgement loss

For one unused fixture on a separate fault-adapter process, set the trusted
`V00_PSQL_COMMAND_JSON` argv to Python + `psql_commit_loss.py --action complete
--marker /run/private/commit-loss.jsonl --`. The shim relays real psql commands
and results, sees a real COMMIT tag, then closes the pipe without forwarding it.
The adapter must return503 without Set-Cookie. The private marker contains only
action/fault/commit-tag observation, never the SQL or result. An independent DB
observer must confirm exactly one complete original bundle, after which the
normal adapter reads the original operation and explicitly recovers its cookie.
Do not re-execute completion or introduce another operation ID to resolve this.
The same shim can target recover/Q01/logout separately with fresh fixtures.
This is actual acknowledgement loss at the psql-to-controller boundary after
DB commit, not a database crash/before-commit test. The offline shim tests use a
fake child process; only the operator's real PostgreSQL run counts as DB evidence.

## Pinned test crypto profile and D03-08 gap

AC06 random-context verifier uses D02 registry§3.1 exactly (domain, length framing,
decoded32-byte proof); logout kind is separate. AC07/AC38 do not yet have a full
normative byte formula in accepted sources. They are therefore labelled
`v00-test-short-secret-xchacha20poly1305-v1` / `v00-test-login-cookie-v1` here,
never the production names. This is a test-codec choice, not product acceptance.

`D(label)=ASCII(label)||00`; `F(bytes)=uint32be(length)||bytes`. Test credential
HMAC-SHA256 uses separate key32 and domain `shadow.v00.login-verify.v1`, then F
of environment, realm, canonical login UUID string, test credential format and
the43 ASCII cookie characters. Cookie is random32 bytes encoded canonical
base64url without padding, distinct from context proof. No plain SHA secret hash.

Cipher plaintext is those same43 ASCII characters. XChaCha20-Poly1305 key32,
random nonce24, combined tag16. AAD domain `shadow.v00.session.aad.v1` then F of
the twelve metadata strings in `crypto.META_FIELDS` order, including trusted
secret/login/source IDs, format and exact fixed deadline. Changing any bound
value fails authentication. Cipher/verifier/context/comparison keys are separate.
Fixture intent fingerprint uses its own HMAC/domain and sorted closed ASCII JSON;
it is **not** a generic AC08/JCS implementation. No key rotation or default-key
fallback. Cipher erasure does not remove the permanent credential or history.

## Local checks

```sh
python3 -m unittest discover -s tools/v00-session-recovery -p 'test_*.py'
npm run check
npm run test:repository
git diff --check
```

Offline tests never install a DB/library/browser or connect to Oracle. The psql
protocol tests use an independent fake subprocess and reject a ROLLBACK tag; they
do not substitute for real PostgreSQL failure/concurrency tests.
