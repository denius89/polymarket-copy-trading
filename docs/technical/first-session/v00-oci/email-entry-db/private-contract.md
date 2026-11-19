# V00-07 email entry: private DB interface

04.11.2026 · Implementation in progress, no new SQL/Oracle behavior pass claimed.
Baseline main30b08448415dd150177eea3b34bde8c0c3c9b773 (runtime dependency411d17b).
Direct owner scope: administrative message01a1a768-8604-7292-bf2a-f5cf4de4503c.
Server alone operates Oracle; isolated synthetic confirmed-user profile, $0, no V01.
This package does not include previously rejected publication payloads or runtime JSON.

## Closed common fields

All UUIDs are canonical UUIDv4 strings at the HTTP/private boundary. Timestamps are
UTC with milliseconds, as `v00_session.utc`. Runtime JSON is passed through bound
parameters, never SQL interpolation. No client-chosen provider/user/factor/time/epoch.

ReadRef: context_id,proof_digest,operation_id,action.
WriteRef: ReadRef + fingerprint,comparison_hmac,comparison_key_id.
ExecutorRef: WriteRef + admission_id,executor_proof (raw random32-byte capability,
canonical unpadded base64url; DB retains SHA256 of its ASCII encoding).
CompletionIds: login_id,secret_id.
Every failed private guard returns exactly http,reason (existing registry code).

Distinct roles: v00_email_ingress (context creation/capture), v00_email_executor
(guarded operations), v00_email_witness (trusted send observation only),
v00_email_observer (safe projections); owner NOLOGIN, no runtime owner/table grants.
No general success/failure boolean supplied to a finalizer.

## Context and encrypted address — frozen interface

context_create accepts exactly context_id,proof_digest. context_read accepts exactly
the same two keys. Replies exactly http,auth_context,observed_at,paused_until,
pending_operation. Create201/accessConfirmed=false; read200/true after proof check.
Public auth_context contains the **12** fields in Auth addendum§4; no email/actor.
paused_until and pending_operation are private current-state inputs for navigation,
not historical result fields. Reading does not extend expiry. Fixed context30min.
context_for_send accepts the same two keys and returns the same five-key shape200,
but requires already confirmed access and never sets it. Use it for internal C01
cipher preparation and current navigation; only the explicit public GET calls
context_read and confirms access. Otherwise C01 would silently bypass the required GET.

Email binding exactly address_digest,address_key_id,secret_id,ciphertext,nonce,key_id,
cipher_format,reveal_until. Source context ID is implicit in capture; private return
email_material adds context_id. No plaintext address is stored in these tables.

- Address key purpose/id: email_address/email-address-1. Address digest is HMAC-SHA256
  with existing frame/domain helpers: domain `shadow.v00.email-address.v1`, ordered
  frames ENV=`v00-d03-07`, `email_send`, `ascii-email-v1`, normalized ASCII address.
- Cipher key purpose/id: email_cipher/email-cipher-1, distinct from address/other keys.
  XChaCha20-Poly1305 combined mode; nonce24, key32, ciphertext includes tag16; nonce
  and ciphertext canonical standard base64. Format `v00-test-email-xchacha20poly1305-v1`.
- AAD domain `shadow.v00.email.aad.v1`, then eight ordered length-prefixed frames:
  ENV, `user`, secret_id, `context`, context_id, `email_delivery`, cipher_format,
  reveal_until. Deadline exactly original context.expiresAt; metadata immutable.
- This is an explicitly isolated V00 cipher profile, not certification of the full
  production AC07 key lifecycle. Raw input comparison remains separate from address
  normalization. Current protected context_read provides expiry for encryption;
  seal rechecks current proof/state/deadline and the binding metadata. Early capture
  returns original context expiry before cipher preparation; it does not call a read
  that could silently confirm access.

## Admission/send — frozen interface

capture accepts exactly context_id,proof_digest,operation_id,action,fingerprint,
comparison_hmac,comparison_key_id,executor_id,executor_proof_digest,challenge_id,
locale,email_binding,request_started_at. The last field is original UTC milliseconds
from the trusted ingress at HTTP start, alongside its monotonic budget, never client
input. A future timestamp or already elapsed10s fails closed; no clock adjustment.
Action C01/C03/C02/AUTH_TOTP_VERIFY. C01 challenge_id=null and email_binding contains
only address_digest,address_key_id; other actions binding=null. C01/C03 locale ru/en; others null.
C03 challenge_id is expectedChallengeId; C02/TOTP current request challenge ID.
Returns exactly http,admission_id,created,context_expires_at;201 new,200 same immutable admission.
Ingress commits before giving the original capability to the handler. It never
restores capability or extends original10s budget on repeat.

seal_send accepts ExecutorRef + email_binding: full eight-field binding for C01,
null for C03. Initial C01 cipher and seal commit in the same T before network.
seal_send returns dispatch variant exactly http,dispatch_allowed,
dispatch_id,email_material,locale;http200, material present for both booleans.
True only for newly committed original seal; false never authorizes dispatch or
witness creation. Already resolved exact replay returns the replay variant below.
Email material is private transient adapter input, never HTTP/history/log output.

send_observed accepts exactly dispatch_id on the **separate trusted witness
connection**. Caller is the closed egress observer after an actual pinned provider
HTTP200/empty-object response to this dispatch. Never called for timeout/5xx/no-forward
or dispatch_allowed=false. DB correlates exactly one new recovery generation after
seal, before-generation mismatch, source user/family and live issued state. Response
exactly http,recorded (200,true on first observation;200,false on exact repeat).
No inferred SMTP delivery: the pinned send path's accepted response and committed
generation are required together; mailbox delivery remains separate evidence.
acceptedAt is the trusted DB registration time of sufficient acceptance evidence,
not provider token issue time or mailbox delivery time. The isolated provider has
no per-request locale selection: only EN is an implemented capability; valid RU
input returns503 after replay/access checks and before any send seal/network effect.
It is not malformed400 and is never silently sent as EN. Full RU remains open.

finalize_send(WriteRef) returns exactly http,replay,result,resolved_at,
historical_http_status. New accepted response202/replay=false/status202; exact replay
http200/replay=true with original status202. Result exactly email_dispatch_accepted,
acceptedAt,challengeId,resendNotBeforeAt. Unknown503 has no saved rejection.

All saved-result replay variants in this namespace have the same five keys:
http,replay,result,resolved_at,historical_http_status. Direct HTTP projection uses
historical_http_status; GET operation uses200 for any saved result including401.

## Verification and completion — frozen interface

seal_verify accepts ExecutorRef + code. It uses locked authoritative provider email
without returning or retaining plaintext/hash. The directory is initialized from
actual canonical provider email; provider email mutation disables the mapping via
a fail-closed hook. This is an isolated allowlist guard, not an email-change API.
That excluded provider email-change path locks provider row before the directory,
unlike ordinary verifier order. A concurrent email change can therefore abort on
deadlock and must remain a technical failure with no negative counter. The hook is
not evidence of complete global lock ordering or implemented email-change lifecycle.
Three variants:

1. Exact saved replay: five-key replay variant above.
2. Proven negative precheck committed in this T: five-key result variant with
   http401,replay=false,historical_http_status401 and verification_rejected result.
   Expired current code has no counter increment; live mismatch increments once.
3. Positive current-code candidate: exactly http,dispatch_allowed,dispatch_id,
   email_material;http200. True only for original fresh committed verify seal.
   No local success/login: provider must consume and emit exact same-transaction
   outcome. Generic provider403 after dispatch remains unknown.

The local negative proof uses pinned Auth2.197.0 GenerateTokenHash=SHA224(email+code),
raw/pkce_ expected forms and both confirmation/recovery branches. Under source locks,
wrong requires live current recovery generation plus mismatch against every live
supported branch; another family's match is unsupported503, never wrong or success.
Malformed/missing/banned/unsupported source, untrusted clock or storage failure does
not become401. No hash/token/code is persisted or returned. Negative calls do not
dispatch a provider verify; reports must distinguish this from external rejection.

plan_email accepts WriteRef + CompletionIds; same immutable sealed provider outcome,
current admission/guards and original context. Returns an intermediate five-key
result, replay, or existing dependency plan variant exactly http,replay,metadata,
completed_at,login_expires_at. Subject/session dependency context is created only
after proven provider identity. No retrospectively fabricated legacy provider seal.

plan_totp accepts ExecutorRef + code + CompletionIds; uses same intermediate/replay/
plan variants. In this isolated namespace it retains all-matching/actor-global factor
step guards and delegates completion to the existing v00_session dependency.

complete accepts WriteRef + cookie_digest,ciphertext,nonce,key_id,credential_key_id;
only same-T plan. Returns existing dependency shape http,result,login_expires_at.
Counter/steps/result/login/window/credential/secret/context/audit commit together.
Negative result requires COMMIT before returning401; an HTTP error status is not a
reason to roll back a successfully finalized rejection. Unknown COMMIT returns503.

read_operation(ReadRef): exactly http,status,result,resolved_at;200/resolved or
202/unresolved. recover(ReadRef) requires original full completion and delegates
unchanged dependency recovery shape; noncompletion409, unresolved503.
q01 and logout wrappers retain existing dependency payload/return shapes, gate/current
guards and selected-target semantics. No direct runtime grant to dependency methods.

## Current boundaries

Initial actor/provider directory is an operator allowlist, never an authenticated
context subject. Ready context has no address or actor; candidate lookup for sending
does not authenticate a user. Existing confirmed-user-only scope leaves signup open.

Address send exclusion must cover all contexts for an address. A sealed unresolved
send blocks a new send even after a timeout; no automatic reservation release or
replacement key. Business send windows and transport quota tokens are separate;
precise reservation/counting evidence is being reviewed with backend before enabling
the writer. No changed numbers or silent broad quota exemption is accepted here.

Implementation and independent test plan are in progress. This interface agreement
does not mean SQL was installed, provider paths tested or full V00/V01 approved.


## Additive008 input validation correction

The private DTO shapes above are unchanged. Installed001–007 incorrectly reused the
upstream scalar-only/C02-only validator for nested entries/email_binding, nullable
capture fields and C01/C03. Forward008 introduces a private owner-only typed validator
and replaces capture/read_operation/seal_send/finalize_send/seed_directory without
changing their grants, transaction boundaries, guards or saved-result rules. The old
upstream validator remains strict. Capture requires C01: null challenge + ru/en locale
+ address object; C03: challenge string + ru/en locale + null binding; C02/TOTP:
challenge string + null locale/binding. All fields remain required even when null.
The directory loader input has exactly actor_id/normalized_email; only its trusted
loader adds address_digest/address_key_id. See manifest for the two actual setup
failures and prepared (not yet run) SQL validator regression. No HTTP success is
inferred from source review or prior offline auditor tests.
