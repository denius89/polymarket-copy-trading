# Source reconstruction status · 2026-11-05

This draft preserves the **deployed** operator launcher and SPA adapter under `tools/v00-polygon/`. They are byte-exact copies of the inspected Oracle source, not new Auth behavior. The read-only 28-file source check is recorded in `docs/technical/first-session/evidence/polygon-2026-11-05/deployed-source-check.json`.

- 21 Auth/runtime Python files are byte-exact at PR251 commit `68f3254dddf5d8cfb5903a14e9c0c5b03b5fe3f4`, independently checked by the backend chat against frozen runtime.v2.
- Five `tools/v00-recovery-quota/` files are currently confirmed only at local commit `7eb10f3da877d948e5212d05933c3519ab0ec7c5`; the backend chat is preserving them in a separate source-only draft. The local commit is NOT a GitHub locator.
- `tools/v00-polygon/polygon_serve.py` SHA256 `8c0a4e180b888a83081259d20d88ec067361e3973d8d1a4d34aed7c68d0f2fb2` and `spa_mount.py` SHA256 `38e5c154e79eae4a8f9c2c4d527445b6e191922b8d0e2c123699b9f8962143bc` are saved by this draft. The earlier auth-only launcher inside runtime.v2 is a different source; do not substitute it for the deployed SPA version.

A single checkout is not yet a complete launchable release. Before preparation is called reproducible, close the five-file cloud locator and compose the exact 28-file baseline, candidate gateway, frontend and API source with a verified manifest. Install no fixtures, keys or migrations at import/startup. No 008 or permanent activation is authorized by this source preservation.
