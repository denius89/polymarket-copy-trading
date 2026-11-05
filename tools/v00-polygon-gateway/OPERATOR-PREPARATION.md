# Private configuration and resource guards · proposed preparation

These helpers are draft source only. They have not created real private files, changed keys/passwords, executed SQL, activated008 or started a new profile. `private_config.py` has no CLI/default execution; `operator_guards.py` is read-only. The full operator driver is now prepared alongside these helpers; exact package review and execution approval remain required.

## Clone-only key proposal

Create fresh context, credential and cipher material for one new immutable installation ID. Preserve hardcoded purpose IDs only within this distinct installation; do not treat this as production key rotation. Old three key values never appear in the generated gateway/API files or a fallback list. Node receives only the same fresh credential used by gateway. Old context/login rows and ciphertext are not rewritten or described as migrated.

Keep email_address for directory lookup. Retained email_cipher/comparison material is a chosen history compatibility measure and residual sensitivity, not anonymization or a prerequisite for fresh C01. The three-key change does not invalidate every copied provider refresh token/OTP/MFA secret. Copied quotas, pending operations, bans, provider state and MFA are preserved; readiness must inspect them and never clear/disable them to force a passing test. This proposal requires review and approval as part of the single disposable E2E package before execution.

The exact purpose→ID map and distinct source material are checked before outputs. A clone-key-profile manifest binds run ID and scope, explicitly records retained purposes, rejects old fallback and states that historical rows were not reencrypted. Independent backend and DB source review identified and justified the three-key boundary; that review is not runtime proof.

## Files and phases

- Builder validates the current closed Auth environment, database options and internal mail/template targets. New passwords, Auth JWT, ingress and cursor material are generated; no original DB password is reused. Nothing is sent to a remote service.
- Closed immutable13-file plan is checked before the private directory is created: names/UID/bytes plus actual semantic contents, original Auth policy, disabled API start gate, exact internal destinations, matching gateway/API credential and ingress, fresh3 versus the original keyset, retained purposes, scoped password/role SQL and cursor format. Source directory/ancestor symlinks, an unrelated run/root, group-readable root and overwrite are refused.
- Writer uses exclusive no-follow0600 files, separate UID65534/UID1000 directories and publishes PRIVATE-PREPARED.json atomically without overwrite only after every planned file and pending marker metadata are written successfully. Final marker ownership failure leaves no valid completion marker. Missing inspect security fields are refusals, never safe defaults. Partial failure cannot be resumed by silently generating different credentials over existing files. Local ownership tests use an explicit mocked chown and do not prove Linux UID enforcement.
- Paper start remains false. TLS and gateway IP config are absent until separate verified binding; a partially prepared profile cannot be called a usable browser environment.
- SQL file is private preparation only: rotate clone-only role passwords and create a restricted paper LOGIN with no memberships. It includes no grants, schema install,008 or profile changes. The future operator must validate existing role privileges and source eligibility before executing it, then inspect effective ACL and negative LOGIN proofs.

## Resource guards

Immutable Docker IDs are returned only after exact project/run/service/name, bind source/destination/RW, network, capabilities, no public ports and no-new-privileges match. An owner label alone cannot make a permanent volume, Docker socket or unrelated mount eligible. Runtime image, UID, read-only mode and restart are a separate check. Network cleanup requires ownership, internal bridge and no endpoints; preflight refuses unknown endpoints even on an owned network. The future driver must validate actual network membership, not merely accept an IP inside a CIDR, and recheck all canonical mount paths.

The helpers themselves do not remove resources. The prepared browser operator removes by the proven immutable ID, refuse uncertain inspection, prove all references absent before root removal and independently confirm permanent Auth/UI/schema state.

## Evidence and limits

80 local tests:26 gateway,22 private-plan/writer,11 resource guards,9 eligibility decoder and12 operator boundary tests. Synthetic material and temporary files only; no Mac stand/listener/database. Source codec probe inherits the actual fixed crypto.py framing and confirms old/new context/login HMAC differ. Native libsodium is unavailable on the Mac, explicitly not run there. `clone_codec_probe.py` requires native support by default for a future separately approved test; it uses only deterministic public synthetic material and never reads real keys, cookies, database or provider state. No negative/positive DB/Auth/browser result follows from these component tests.
