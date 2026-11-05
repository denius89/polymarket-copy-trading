# Source reconstruction status · 2026-11-05

This draft preserves the **deployed** operator launcher and SPA adapter under `tools/v00-polygon/`. They are byte-exact copies of the inspected Oracle source, not new Auth behavior. The read-only 28-file source check is recorded in `docs/technical/first-session/evidence/polygon-2026-11-05/deployed-source-check.json`.

- 21 Auth/runtime Python files are byte-exact at PR251 commit `68f3254dddf5d8cfb5903a14e9c0c5b03b5fe3f4`, independently checked by the backend chat against frozen runtime.v2.
- Five `tools/v00-recovery-quota/` files are preserved in [PR263](https://github.com/denius89/polymarket-copy-trading/pull/263), commit `dc32b7212b7e12402719c687a510fed550d5b840`. The server chat independently fetched all five remote files and confirmed byte equality with runtime.v2, previously matched to actual Oracle source. The older local7eb commit is not used as a cloud locator.
- `tools/v00-polygon/polygon_serve.py` SHA256 `8c0a4e180b888a83081259d20d88ec067361e3973d8d1a4d34aed7c68d0f2fb2` and `spa_mount.py` SHA256 `38e5c154e79eae4a8f9c2c4d527445b6e191922b8d0e2c123699b9f8962143bc` are saved by this draft. The earlier auth-only launcher inside runtime.v2 is a different source; do not substitute it for the deployed SPA version.

A single checkout is not yet a complete launchable release. All 28 baseline Python source files now have verified cloud locators across the pinned drafts. Compose those exact files with the candidate gateway, frontend and API using a verified manifest; a draft pin does not mean merge or runtime readiness. Install no fixtures, keys or migrations at import/startup. No 008 or permanent activation is authorized by this source preservation.
