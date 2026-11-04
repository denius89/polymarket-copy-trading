# Upstream Auth V00: compatibility findings

04.11.2026. Baseline `41123ecb0586679facbd036dca43b3747e7f4b80`.
User authorization: management chat message
`01a1a6a7-d0fc-7f00-8fda-baf79ebc3d93`, following the specific proposal to connect
email OTP, an enabled TOTP factor, Shadow completion, recovery and logout.
Server chat is the sole Oracle operator; backend owns this directory, DB owns
`scripts/v00-upstream-db/`. Existing tested adapters stay unchanged.

This is a working compatibility record, not an implemented bridge or a PASS.
Runtime component preflight is reported separately by the server. No production
guarantee is changed by selecting a test implementation.

## Pinned source and observed components

Supabase Auth2.197.0, PostgreSQL17.11 and internal Mailpit1.32.0. The operator
reported actual `/otp` → six-digit email → `/verify` with type=email → TOTP
enroll/challenge/verify → AAL2 in a separate internal environment. That confirms
provider primitives only, not their relation to a Shadow operation/session.
Existing-user OTP, failure recovery and the Shadow bridge require independent
evidence. SMTP templates expose only test codes inside the closed mail service.

| Fact from pinned source | Consequence for the bridge |
| --- | --- |
| [Otp](https://github.com/supabase/auth/blob/v2.197.0/internal/api/otp.go#L63) calls MagicLink for email | Use actual email-code flow; do not reinterpret the prior signup URL probe as this flow |
| [MagicLink](https://github.com/supabase/auth/blob/v2.197.0/internal/api/magic_link.go#L69) uses signup for new/unconfirmed users and recovery-token delivery for confirmed users | Prior confirmation-only witness does not cover an existing user's login |
| [verifyUserAndToken](https://github.com/supabase/auth/blob/v2.197.0/internal/api/verify.go#L700) type=email checks confirmation or recovery token | Witness must identify the exact token family/generation; user ID/count alone is insufficient |
| [verifyPost](https://github.com/supabase/auth/blob/v2.197.0/internal/api/verify.go#L229) consumes/updates the user and issues the session in one provider transaction | Bind original operation/seal/token evidence, exact session and provider transaction before accepting the outcome |
| [TOTP verify](https://github.com/supabase/auth/blob/v2.197.0/internal/api/mfa.go#L594) uses SHA1, six digits,30s,±1, then updates challenge/factor/session/claims | Provider success does not supply all matched steps or global one-use protection; Shadow must enforce the accepted rule |
| The same TOTP transaction invalidates other provider sessions below AAL2 | Do not silently map this to revocation of independent Shadow logins; examine this boundary explicitly |
| [Refresh token model](https://github.com/supabase/auth/blob/v2.197.0/internal/models/refresh_token.go) and [session model](https://github.com/supabase/auth/blob/v2.197.0/internal/models/sessions.go) hold provider credentials/state | A proved session ID is not an access bearer. Reading or refreshing a credential is not a harmless substitute for replaying an unknown Auth operation |

## Decisions checked against accepted contracts

1. Email outcome observer must cover confirmation and recovery-token consumption
   and exact same-transaction session issuance. Durable dispatch permits cannot
   be transferred after a timeout. A missing response does not allow a new OTP
   consumption or another operation ID.
2. AC09 allows a local-adapter challenge; AC10 keeps active factor seed at the
   provider. Backend/DB source review selected a narrowly scoped trusted
   all-matching verifier over that active provider factor, without a second
   upstream MFA effect. This is NOT provider AAL2 verification on each login.
   No persistent active-seed copy may be introduced into Shadow history.
3. If each login requires an actual provider MFA dispatch, it needs a durable
   factor/step fence before dispatch and exact challenge/session/AMR outcome
   evidence before local finalization. A lost email response can lose the bearer
   required for that next provider call; no ad-hoc JWT minting or hidden new
   refresh/verification action is allowed to mask this dependency.
4. Completion must atomically bind the original permitted operation and full
   session bundle. The new executor must not inherit direct access to synthetic
   `v00_session.plan_completion/complete` or fixture completion routes. A second
   independent success is not proof of the first operation's outcome.

The chosen private interface and test matrix are in
[PR239's contract](../../docs/technical/first-session/v00-oci/upstream-db-verification/private-contract.md).
Executable adapters are in this directory; real bridge integration is still NOT RUN.
Provider/network faults, local COMMIT uncertainty and browser
response loss remain distinct observations. V01, full78 and complete D03/BR08
are not admitted by this working record.
