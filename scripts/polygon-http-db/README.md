# Disposable HTTP ↔ paper DB integration fixtures

05.11.2026. Separate package after the observed candidate5 SQL/ACL PASS51+40.
This package does not change frozen candidate5 or install anything by itself.
Status: prepared for independent review; HTTP+SQL execution not yet observed.

## Boundary and dependencies

Only the server operator uses a **fresh DB-only Oracle clone**, verified by its
name, labels and mounts. No permanent PG target, no008, provider network, public
listener, live funds, actual claim, Q06, staff or Owner grants. The Node API and
test harness have network=none and use a shared PG Unix socket plus local HTTP
loopback as configured/reviewed by the operator. No credentials travel to the Mac.

Install exactly candidate5 SQL001–007, manifest
`e7a856711a1b8edf6275084c9b608d592f737efe464217584285cb30d7b1bc7d`,
source commit4deb119971bb1b57f781b1ccb77882fabcbaf86c.007 needs tzdb2026e. Do not
replay old Auth/provider seeds. The two test directory identities already exist
in the cloned Auth source; paper007 maps them to fresh product users.

Backend supplies a separately reviewed/pinned API+HTTP harness, genuine selected
user-proof HMAC codec, calendar profile and synthetic credential/cursor keys.
The HTTP runner generates two random cookies and UUIDv4 login IDs **inside Oracle**,
computes each cookieDigest with the actual accepted login verifier domain, and
keeps cookies/keys in private fixture files. Runtime's credential key ID remains
credential-1, but the key material is newly generated for this clone only.
This is not a provider sign-in or browser/passkey/HTTPS test.

## Privileges and input

The operator creates a new ephemeral LOGIN only inside the clone, with no elevated
role flags, a single non-admin membership polygon_executor and no owner membership.
API connects as this LOGIN, never postgres or an owner plus SET ROLE. Operator
setup/observation connections are separate and unavailable to the API container.
The clone must NOT retain a local-trust socket rule: that would let the API choose
postgres despite its configured runtime LOGIN. Before starting it, the operator
sets a clone-only HBA policy: exact database/runtime role uses SCRAM with an
ephemeral password; the separately trusted operator uses postgres peer; other
socket roles are rejected. Node runs with a distinct non-postgres, non-root UID,
without a way to assume the operator UID, capabilities, PGDATA, Docker socket or
administrator credentials. The shared socket does not grant shared operator trust.
Negative connections from the actual Node execution identity to postgres, owners
and Auth roles, plus an incorrect runtime password, must all fail before the HTTP
run; the intended runtime SCRAM connection must succeed. Record safe verdicts only.
This connection-isolation gate is required for the effective-runtime-rights claim;
checking configured role names or pg_stat_activity alone is insufficient.
The setup verifies effective EXECUTE across the whole polygon namespace against
the nine exact RPC signatures; direct table rights, grant options, bridge EXECUTE
and schema CREATE are rejected.

Both SQL files require PGOPTIONS=-c polygon.disposable_test=offline-http-clone.
The marker prevents accidental invocation; actual isolation is the operator's
checked container/volume/network, not the marker alone.

setup-fixture.sql takes two private psql variables:

- fixture_input: a JSON object with exactly format=polygon-http-fixture-v1 and
  users=[{loginId,cookieDigest},{loginId,cookieDigest}]. Both IDs are distinct
  canonical UUIDv4; digests are distinct lowercase64hex. Array order defines
  ordinal1/2, joined to the two product users ORDER BY id.
- runtime_role: the dedicated LOGIN name whose effective privileges are checked.

No raw cookie/key enters SQL. Pass input through the operator's protected input
channel, do not echo private preparation files or SQL variable expansion into
safe evidence. On failure retain only sanitized stage/SQLSTATE/assertion details.

## Setup and exact output

Run setup before starting API requests. It requires the fresh disabled paper seed
with no commands/drafts/reviews/sessions/slots. Under one transaction it creates
two **synthetic** local Auth completions using supplied login IDs and cookie
digests. Context/operation/secret IDs are generated locally. Proof and opaque
secret ciphertext/nonce are intentionally fixture-only: no cookie recovery or
real Auth encryption proof is claimed. Existing Auth rows are not reseeded.

The script enables profile/start controls only in this disposable clone and
COMMITs so subsequent real HTTP transactions can see the fixture. It does not run
008 or create runtime credentials. Only after confirmed COMMIT it emits:

`{format:"polygon-http-descriptor-v1",users:[{ordinal,userId,loginId,venueId,traderId},...]}`

This descriptor has no cookie/proof/secret. Ordinal1 is Polymarket/fixed and
ordinal2 is Limitless/percent. The descriptor is joined to private harness cookies
by ordinal and matching loginId, never by guessed UUID identity equality.

## Agreed HTTP scenario and independent observation

Backend's bounded scenario includes actual HTTP C04/C05/C06 and Q02/Q03/Q04/Q05,
strict shape/origin/auth/key-reuse/cross-user denials and exact replay:

- Ordinal1 creates rawBudget containing200 followed by NUL. C05 stores the invalid
  numeric review. C04 update to300 yields version2; a new unchanged save preserves
  last_input_receipt_id; a stale save stores VERSION_CONFLICT. A valid review
  starts a session; two concurrent identical C06 requests return the same receipt.
- Ordinal2 uses percent: budget100, copy3.5%, market5%, daily10%. After start, a new
  C06 key on the used draft stores DRAFT_USED. Q05 reads the saved result.
- Q02 uses limit1, cursor continuation and cross-user cursor rejection;
  Q03 restores byte-exact input/errors/source, Q04 reads the same EMPTY session.

The pinned HTTP harness expects46 labels. Cursor replay/tamper are covered by
separate component tests, not claimed as exercised by this HTTP integration.

Expected committed state:2 drafts,8 keys/receipts/details,3 reviews; C04 has4
successes and1 VERSION_CONFLICT, C06 has2 successes and1 DRAFT_USED. Reviews have
2 valid plus1 numeric refusal preserving bytea32303000. No extra keys from early
transport/auth/key-reuse failures or exact replay.

After the harness, **while Node's pool is still alive**, run observe-effects.sql
with the same marker and runtime_role. It reads pg_stat_activity for
application_name=shadow-polygon-paper-api: at least one actual connection exists,
and all use the dedicated LOGIN. The harness retains one real client from the
API runtime pool without an open transaction, writes HTTP_COMPLETE in its private
coordination directory, and waits up to60 seconds for OPERATOR_OBSERVED. The operator
runs the observer in this window and writes OPERATOR_OBSERVED only on success.
The harness then releases the client and closes its runtime; timeout or observation
failure is a failed integration, not PASS. This avoids dependence on the10-second
idle pool timeout. No artificial statistics or operator connection may impersonate
the API application name.

The observer independently checks exact history counts plus2 sessions/settings/
fundings/journals/snapshots/audit/outbox,4 balanced journal entries, each user's
300 or100 budget/free/equity and strict source tuples. It additionally invokes
the existing complete-session validator, which is not its only oracle. Safe
output format polygon-http-effects-v1 contains aggregate counts/sums and the
financial/runtime checks. The observer itself is READ ONLY and ROLLBACKs.

## Evidence and teardown

HTTP writes really COMMIT **inside the disposable clone**; this suite does not
claim their rollback in one encompassing transaction. After evidence, stop only
the disposable API/harness and remove only the verified clone, socket volumes and
private ephemeral fixture material. Verify the existing permanent service is
unchanged and no polygon schema/activation was added there.

Freeze all component manifests before execution and stop at first failure.
Do not modify a mounted package or weaken an assertion to obtain PASS. This pass
can show API/SQL transport/codec/commit compatibility and the tested duplicate
request outcome; it does not establish forced lock-wait coverage, unknown-COMMIT
fault injection, browser/Auth provider, production readiness or permanent008.
