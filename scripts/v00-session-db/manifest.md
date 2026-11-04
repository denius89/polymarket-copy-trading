# D03-07: private storage interface

Status: isolated test implementation; PostgreSQL execution and independent actual results are recorded separately. This is not the full Auth schema, provider verification, production crypto codec, or V01 approval. Operator installs `001-storage.sql`, `002-api.sql`, `003-logout.sql`, then `004-observer.sql` in a **new test database**. No existing Auth / `v00_db` database is changed.

All methods below accept exactly one JSON object with the listed keys. UUIDs use canonical UUID strings. `proof_digest`, `cookie_digest`, `fingerprint` are lowercase hex64, computed by the trusted adapter from cryptographically verified credentials/raw request. **Never trust a digest supplied by public HTTP.** NULL, malformed types, extra keys or database exceptions are technical failure (503), never a fabricated rejection/204. The executor has function execution only, no direct table access and no operator revoke/time/fixture controls.

| Method | Exact request keys | Success / absence |
|---|---|---|
| lookup_result | context_id, proof_digest, operation_id | 200/status=resolved/result/resolved_at; trusted absence 202/status=unresolved/result=null/resolved_at=null |
| plan_completion | context_id, proof_digest, operation_id, fingerprint, login_id, secret_id | New: 200/replay=false/metadata/completed_at/login_expires_at. Exact existing result: 200/replay=true/result |
| complete | context_id, proof_digest, operation_id, fingerprint, cookie_digest, ciphertext, nonce, key_id, credential_key_id | 200/result/login_expires_at |
| recover | context_id, proof_digest, operation_id | 200/result/ciphertext/nonce/key_id/credential_key_id/cookie_digest/metadata/login_expires_at; unknown result 503, known noncompletion 409 |
| q01 | login_id, cookie_digest | 200/authenticated=true/login_id/actor_id |
| logout_prepare | logout_context_id, login_id, cookie_digest, logout_proof_digest | 201/logout_context_id/target_login_id/source_context_id=null/created_at/expires_at |
| logout_continue | logout_context_id, source_context_id, authorization_login_id, cookie_digest, authorization_mode, logout_proof_digest | Same 201 shape; source_context_id is non-null; mode original_login/current_user |
| logout | logout_context_id, proof_digest, operation_id, fingerprint | 204/result (private result, never public 204 body) |
| logout_result | logout_context_id, proof_digest, operation_id | 200/status=completed/result/target_login_id; absence 202/status=unresolved/result=null/target_login_id |

Operator-only `revoke({login_id})` returns 204/target_login_id. IDs for completion/prepare/continue are trusted server-generated fixture IDs, not new user-selectable targets. No public completion bypass exists: the completion method is invoked only by the isolated fixture control after a synthetic confirmed upstream step. Actual provider/challenge checks are outside this package.

Private failures contain exactly `http` and `reason`. The adapter applies the accepted public envelope, requestId, request schemas, CSRF, selected-login header and cookie rules. Persistent distributed quota/admission D03-10 is **not implemented or proved** by this package. Missing proof is rejected by the adapter as 401 before the DB; mismatched scoped proof is 404. Key unavailable, failed AAD/decryption/verifier comparison, SQL/commit uncertainty become 503 with no cookie. Permission to inspect the original result does not grant a new current login. Immutable `resolved_at` is the trusted time of final result insertion, including saved rejection; it is not synthesized from a later read or substituted with completion time.

## One transaction, including cryptography

Use one interactive connection, READ COMMITTED, `BEGIN` → call → positively verified `COMMIT`; do not use separate one-shot psql calls for a multi-stage operation. A psql exit code alone is insufficient when an attempted COMMIT could actually report ROLLBACK. Validate the transaction command response. Exceptions and broken connection are unknown/503; no automatic POST retry or new operation key.

Completion: `BEGIN` → `plan_completion` → trusted encryption/verifier generation using returned metadata → `complete` → confirmed `COMMIT` → Set-Cookie. A plan is bound to exact context/operation/fingerprint/login/secret IDs, trusted completion timestamp/deadline and current transaction. Deferred FKs reject plan-only or partial-bundle commit. `complete` rechecks time and guards **after encryption**; any complete/plan error requires ROLLBACK. Existing result replay does not create a plan; obtaining a cookie still requires `recover` under the same rules.

Recovery: `BEGIN` → `recover` → decrypt, check AAD, recompute and compare permanent credential verifier **while transaction still holds locks** → confirmed `COMMIT` → Set-Cookie. No cookie, ciphertext, verifier, nonce, key or proof enters public history/observer/evidence. A lawful 409 recovery close at the deadline may COMMIT its erasure without a cookie. On crypto failure ROLLBACK. HTTP errors never become new saved Auth results.

Q01: confirmed COMMIT of first confirmation, close/erasure and audit before 200. No idle touch. Logout: confirmed COMMIT of target revoke/erasure/result/audit before 204 and deletion of only target cookie. Prepare/continue/read never revoke. Continued context does not resolve or rewrite an old unknown operation.

## Exact metadata and test formats

Metadata keys are exactly: environment=`v00-d03-07`, realm=`user`, login_id, secret_id, source_context_id, source_operation_id, owner_kind=`login`, owner_id=login_id, purpose=`login_cookie`, cipher_format=`v00-test-short-secret-xchacha20poly1305-v1`, credential_format=`v00-test-login-cookie-v1`, reveal_until (UTC `YYYY-MM-DDTHH:mm:ss.SSSZ`). The fixed deadline is min(completed_at + 300 seconds, original context expiry). Login absolute expiry is returned separately. Nonce is base64 of 24 bytes; ciphertext is base64 including the 16-byte tag; trusted adapter supplies key IDs.

The production AC07/AC38 **exact byte codec is not selected by this test**. Backend pins a separate test codec in its package; do not relabel it with production format names. AC06/AC08 retain their accepted profiles. Crypto keys stay outside PostgreSQL. Runtime service must fail closed on missing keys or corrupt stored material, never rotate a cookie silently.

## Serialization and observation

Actor row X-lock precedes login rows (UUID order), source Auth contexts (UUID order), logout source/context, window X, secret X, results/audit insertion. Actor lock exists before a result and serializes concurrent completion for the same actor. Continue first reads only immutable IDs to determine lock set; all rights and bindings are rechecked under locks. Different actors get a non-disclosing 404; target is always read from the original logout context. Same-actor A/B and B/A cannot invert locks. Keep locks through crypto and COMMIT, not merely until the function returns.

Fixed time is operator-only per actor; wall-clock actors have NULL fixed_time. Concurrency proof must observe a real PostgreSQL lock wait using distinct connections before releasing the winning transaction. Merely launching concurrent threads is not proof. The observer exposes safe structural facts only. Production auth enums, complete audit schema, retention jobs, rate limiting, provider, backup, public availability and V01 remain outside this narrow implementation.

## Operator commands and evidence

`V00_SESSION_PSQL_COMMAND_JSON` is a JSON argv array for the operator's administrator psql process (for example a container exec wrapper, ending with `psql -U <isolated-admin> -d shadow_d0307`). No shell interpolation of private material is used. `verify_storage.py` creates fresh UUID fixtures, never resets a database, and switches each application call to executor. Corruption probes are operator-only rollback transactions. `seed_adapter.py /private/path/seed.json` accepts exactly `actors` and `contexts` arrays as agreed with backend; it rejects unknown fields, duplicates and cross-envelope actor references, atomically inserts new rows, and prints counts only. Never publish the private seed/config.

Observer `SELECT v00_session.snapshot(<actor uuid>)` under `v00_session_observer` returns IDs, bindings, deadlines, markers, safe audit, validated immutable result and structural counts. Invalid result payload is suppressed. It never returns ciphertext, nonce, key identifiers, cookie/proof/fingerprint digests or raw credentials. The observer is operator-only, not a public user endpoint. Real lock waits are observed by the operator through `pg_stat_activity`, not by widening executor/observer grants.

`verify_storage.py` prints a JSON report of independently specified expectations and actual observations. It marks cryptographic, network uncertainty and browser checks `not_run`; only their separate actual can close those cases. Its synthetic nonce/cipher bytes are deliberately not an encryption test. The single short wall-clock probe tests deadline recheck after the adapter phase; fixed-clock boundary checks remain separately labelled.
