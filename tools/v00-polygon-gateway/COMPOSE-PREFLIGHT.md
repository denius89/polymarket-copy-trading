# Disposable composition · preparation, not activation

`compose.disposable.template.json` is a six-service source template. It does not contain passwords, keys, login cookies, emails or SQL fixtures. No services were created from it. Existing Oracle image IDs were inspected read-only. Static assertions confirm no host ports, one internal network, no restart/pull, and no actual PGDATA mount for gateway/API/template services. The database explicitly runs as `postgres`; an operator must set ownership on the **owned disposable copy** before starting it, so root/gosu capabilities are unnecessary.

The installed Oracle Compose CLI accepted a schema-only probe with the two `env_file` paths replaced by `/dev/null` and `config --no-env-resolution --no-path-resolution --quiet`. This validates structure only. The original template correctly refused rendering without its required private auth.env. Private files, real DSNs, HBA, role passwords and service readiness are not validated by that probe.

## Exact preparation before any up

1. Allocate one unique run ID and canonical root under `/opt/shadow-polygon/.browser-e2e.<id>`. Refuse symlinks, preexisting paths and the permanent project's resources. Set SHADOW_E2E_ID and SHADOW_E2E_ROOT; never fall back to the permanent root.
2. Verify baseline28 source hashes, candidate6-file manifest, frontend3e3f3f3, API7d02 source/dependency lock and installed image IDs. Compose assembled sources under gateway/ and api/, test-mail templates under templates/, private files under private/, DB-only physical copy under base/. Verify backup before use. No private file goes to Git or Mac.
3. Prepare separate private auth.env and gateway.env. All DB/provider/SMTP URLs resolve only to the disposable network aliases db/auth/mail/otp-template. No external SMTP relay, webhook or restored external outbox execution. Use fresh clone-only DB LOGIN passwords and Auth JWT key; do not change the permanent profile. Confirm fresh C01/C02 login compatibility with those clone settings before claiming real Auth PASS.
4. Gateway private directory: existing synthetic V00 key/config needed by Auth, separate paper-ingress key, exact gateway config. Node private directory: credential-1 **subset only**, not the whole Auth/email keyset; same ingress key in its own UID1000 private file, fresh cursor keyset, exact API config. Permissions600; gateway UID65534 and API UID1000. Never mount auth.env, Auth DB credentials, Docker socket or PGDATA into Node. Gateway config requires the actual private Node IP and exact origin https://localhost:18444.
5. HBA rejects owner/postgres/all unspecified network LOGINs; permits only required existing Auth roles and the fresh paper runtime over SCRAM on the disposable network, plus the local peer operator. Review memberships and effective ACL before enabling paper. Runtime role starts with no memberships for008. The profile remains disabled until the separately reviewed activation step.

## Proposed start/observation sequence after explicit package approval

- Start only db/mail/otp-template, confirm their owned mounts/network/readiness and no relay.
- Install pinned paper001–007 in the disposable DB; create restricted fresh LOGIN and passwords. Record seed/profile disabled, actual scoped baseline and ACL.
- Run the pinned008 **only in this disposable DB** with role/tzdb arguments after its exact activation package is approved. It is not run by this template or at service startup. Permanent008 remains a separate gate.
- Start Auth and prove its DB/SMTP target belongs to this run. Start Node with gateway-monotonic-v1 and startEnabled only as approved. Measure Python/Node CLOCK_MONOTONIC and zero time namespace offsets in these actual services.
- Set gateway's exact Node private IP, then start gateway. Auth POST10s remains unchanged; Q01+identity and paper use the original5s. Create no fixture contexts or completion rows.
- Open localhost18444 using an SSH forward directly to the owned gateway's private IP:8443. Use fresh Playwright/browser contexts; ports alone do not isolate cookies. Do not reuse the permanent18443 context or import its storage.
- Execute E01–E08 in the linked E2E package, including both venues and independent SQL observation. Do not count component/stub proofs as this browser result.

## Cleanup/abort

Identify containers/network by the exact project/run labels and expected bind mounts; mismatch means stop cleanup and report, not broaden deletion. Stop/remove only owned services and network, close only this SSH forward, delete only the canonical owned root after mounts are absent. Do not use a broad Docker prune or delete permanent volumes. Confirm permanent Auth/UI still work and paper schema remains absent there. Preserve safe logs without secrets.

The five recovery files are now preserved at PR263 commit dc32b7212b7e12402719c687a510fed550d5b840 and independently byte-verified against the frozen/observed source. Outstanding before this is an executable, approvable run: exact private-config generator/operator script with preflight/cleanup guards, independent composition review and real rendering with prepared private files. This template is not a request to skip those dependencies or authorize the new test scope.
