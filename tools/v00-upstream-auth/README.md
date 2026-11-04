# V00 upstream Auth adapter

04.11.2026. Executable candidate for the authorized isolated V00-05/06 slice.
Authorization was verified against the owner's management-chat message
`01a1a6f3-387b-7cf0-82a2-66936cd8a3be`. Server chat is the sole Oracle operator.
No production, live trading, new expenses, or admission to V01.

This package implements single-attempt email verification, closed private response
decoding, capture/admission handoff, TOTP transaction orchestration, original
completion, recovery/Q01, and delegation of the existing logout projection through
new restricted wrappers. It does not implement the provider's TOTP algorithm:
the trusted DB verifier must validate the actual active provider factor.

## Contract and trust boundaries

- [Private interface and commit rules](../../docs/technical/first-session/v00-oci/upstream-db-verification/private-contract.md),
  [provider prerequisites](../../docs/technical/first-session/v00-oci/upstream-db-verification/provider-manifest.md),
  [UB01–18](../../docs/technical/first-session/v00-oci/upstream-db-verification/verification-plan.md).
- `database.py` permits only `v00_upstream` wrappers. It cannot call the old
  synthetic `v00_session.plan_completion` endpoint or an operator reconciliation.
  Separate `IngressTransaction` can call only `capture`; grants must independently
  enforce this at the DB boundary. A class allowlist is not a substitute for ACLs.
- Capture additionally binds a random executor ID and SHA256 of a canonical
  base64url 32-byte executor proof. The raw proof stays in handler memory. Runtime
  receives the original admission ID, cannot reset its epoch/deadline, and cannot
  restore the original executor proof after a lost response.
- Sensitive requests use PostgreSQL17 `psql` **extended protocol parameters**:
  SQL contains `$1`, followed by `\bind` and `\g`. Base64 is only transport encoding,
  not encryption. No OTP/proof is in the server SQL statement. The operator must
  verify `log_parameter_max_length_on_error=0`, safe function errors, and a real
  negative redaction probe. [Official psql17 semantics](https://www.postgresql.org/docs/17/app-psql.html#APP-PSQL-META-COMMAND-BIND).
- `provider.py` never retries, redirects, refreshes tokens or mints JWTs. A 200 or
  a bearer in its response does not authorize login. Exact DB evidence does.
- Cookie material leaves `Bridge` only after confirmed COMMIT. Unknown COMMIT
  raises a technical error. A saved 401 result and a 409 window-erasure are committed
  when required; full partial plans/steps are rolled back on crypto/complete failure.
- Existing D03-07 AC07/AC38 **test** codecs/environment are reused unchanged, with
  fresh isolated keys. This is not production byte-codec certification.

## Files and local checks

`bridge.py` handles transaction sequencing; `protocol.py` validates closed results;
`ingress.py` builds the nonsecret fingerprint and purpose-bound AC08 comparison;
`app.py` projects the narrow routes; `serve.py` supplies strict parsing and TLS.
`dependency.py` imports helpers from the unchanged `../v00-session-recovery/`.

```sh
python3 -m unittest discover -s tools/v00-upstream-auth -p 'test_*.py'
python3 -m compileall -q tools/v00-upstream-auth
```

63 local checks passed after adding the separate fault harness (43 runtime/protocol
checks plus20 operator-boundary checks): injected provider/COMMIT loss,
rejection commit, crypto rollback, source mismatch, closed recovery, parser and
role allowlists, and separation of bound values from server SQL. These are local
protocol tests with doubles, **not** PostgreSQL/Auth/browser tests or UB passes.

## Operator launch manifest

Run only after the matching `scripts/v00-upstream-db/` package is installed and
its required capabilities/roles/fixtures are confirmed by the operator. Use the
fresh separate `shadow_v00` instance with the D03-07 dependency `001–004` and
the upstream wrappers; no inheritance of `v00_session_executor` by runtime.

Required environment (all files and service credentials remain private):

| Name | Value/meaning |
| --- | --- |
| `V00_UPSTREAM_ENABLED` | `1`; default is disabled |
| `V00_ORIGIN` | `https://session-upstream.invalid:8443` |
| `V00_PROVIDER_ORIGIN` | internal `http://auth:9999`, inaccessible from client |
| `V00_UPSTREAM_CONFIG` | private mode0600 JSON with `fixtures` map, described below |
| `V00_KEY_FILE` | fresh private D03-07 key file; context/credential/cipher/comparison purposes separate |
| `V00_UPSTREAM_PSQL_COMMAND_JSON` | e.g. `["psql","service=v00_upstream_runtime"]` |
| `V00_INGRESS_PSQL_COMMAND_JSON` | e.g. `["psql","service=v00_upstream_ingress"]`; distinct role/connection |
| `PGSERVICEFILE`, `PGPASSFILE` | private service configuration and credentials; no password in command arguments |
| `V00_TLS_CERT_FILE`, `V00_TLS_KEY_FILE` | operator's isolated trusted TLS pair |
| `PORT` | `8443` by default |

Each trusted fixture entry contains `context_id`, `email`, `proof`, `fixture_token`.
These must correspond to installed source bindings; no client-selected provider
identity/factor is accepted. The fixture bootstrap route returns only the existing
context proof cookie. No `/fixtures/.../complete` route exists. Synthetic email OTP
issuance and provider factor enrollment are separate operator fixture work, with
instrumentation installed **before** email issuance.

Optional per-fixture faults are operator-only: `provider_fault` is one of `none`,
`before_send`, `after_send`, `after_headers`, `after_body`; `response_fault` is
`drop_before_headers` or `drop_after_headers`. They are never taken from public input.
An injected pre-send failure does not reset the durable permit or authorize retry.

```sh
python3 tools/v00-upstream-auth/serve.py
```

No service setup, image build, role assignment or secret generation happens on import
or in this launch command. The operator supplies the environment and matching DB.

### Fixture and client commands

The operator supplies a private mode0600 provider mapping with root `fixtures`
array. Each item contains exactly `name`, `email`, `provider_user_id`,
`provider_factor_id` (null for a verified no-MFA subject). Provider accounts and
verified factors must already exist from real provider setup; these commands do
not create them. A repeated provider user shares one Shadow actor across contexts.

```sh
python3 tools/v00-upstream-auth/prepare.py /private/provider-map.json /private/upstream-fixtures
python3 scripts/v00-upstream-db/seed_adapter.py /private/upstream-fixtures/seed.json
```

The second command uses the operator-only loader connection from the DB manifest;
never reuse that privileged connection when launching the runtime adapter.
The output directory is new (no overwrite), with private keys/server/client/seed
files. The operator now issues the single real fixture OTP while hooks are active.
Copy only client.json and the public CA into the isolated client environment.

```sh
python3 tools/v00-upstream-auth/client_probe.py /private/client.json --ca /private/ca.pem --fixture basic
python3 tools/v00-upstream-auth/client_probe.py /private/client.json --ca /private/ca.pem --fixture mfa --mfa
```

At each safe `need_code` event, supply one private JSON line on stdin with exactly
`code` containing the fresh six-digit code. The operator reads test email or computes
the fixture TOTP privately; do not print the line, put it in argv, or give the client
provider/DB credentials or a seed. The probe emits only safe checks and source IDs.
`--allow-response-loss` is only for a fixture configured to drop its HTTP response;
it reads the original operation and checks Q01 before an explicit cookie recovery.
It never repeats a verify POST automatically. Transport results are not browser proof.

For real Chrome cookie observations, start the already prepared ChromeDriver in
the isolated client container with trusted CA and without verbose request logging:

```sh
python3 tools/v00-upstream-auth/browser_probe.py /private/client.json --fixture browser_basic
python3 tools/v00-upstream-auth/browser_probe.py /private/client.json --fixture browser_mfa --mfa
python3 tools/v00-upstream-auth/browser_probe.py /private/client.json --fixture loss_before --response-loss
python3 tools/v00-upstream-auth/browser_probe.py /private/client.json --fixture loss_after --response-loss
```

Codes again arrive only on private stdin. The browser driver forbids insecure
certificate acceptance; it observes actual cookie attributes, JavaScript isolation,
explicit recovery after loss, unchanged secret/expiry, Q01 closure and selected
logout. Cookie values stay in memory and are never emitted in the report. Run each
fixture once with its original operation flow; do not reuse a consumed OTP across
separate probes. Browser and transport fixtures are separate unless a run explicitly
shares one original operation rather than starting another.

## Actual scope and open dependencies

The first bridge starts after real fixture email delivery. Public C01/C03, resend,
send uncertainty, persistent HTTP quotas, full MFA lifecycle, and the email negative
classifier are **NOT IMPLEMENTED** here. Provider `403/otp_expired` alone does not
distinguish wrong code from expired/consumed code: the narrow adapter stays unresolved
without a wrong-code counter/result. Unknown blocks dependent work, not a new key.

The current intermediate-result projection uses a separate authorized read for the
immutable `resolvedAt` and conservative null navigation. Full current navigation
resolution is not claimed. It must be addressed before claiming complete API fidelity.
Late-result decoding supports the accepted U03 union; the operator reconciliation
writer still needs its own implemented/proved path.

Runtime revision `210044b` and DB008 are the current integration baseline. Actual
operator results and independent DB review are separate evidence artifacts in
[the accepted DB review](https://github.com/denius89/polymarket-copy-trading/blob/main/docs/technical/first-session/v00-oci/upstream-db-verification/runtime-review.md).
They are not embedded or republished by this harness update. Full V00/D03 acceptance
remains open.

[Separate fault harness A–E](fault-manifest.md) supplies same-user/independent-actor
race, no-forward unknown, seal/completion COMMIT loss and late-outcome probes without
changing that runtime. These added scenarios remain
NOT RUN until the operator records their actual overlap, proxy and DB evidence.
