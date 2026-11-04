# Shadow client web

React 18 + TypeScript + Vite + Tailwind. The visual base follows the approved Final Figma file `lxPP2um7FvIbt02K8eeH4T`, especially mobile landing `2529:19569`, first catalog `2532:20141`, fixed setup `2498:28817`, and matching RU/EN mobile/desktop variants from `docs/design/client/sitemap.json`. Shared controls and colors live in `packages/ui`.

## Run

From repository root:

```sh
npm ci
npm run dev:web
npm run typecheck:web
npm run build:web
VITE_PUBLIC_BASE=/app/ npm run build:web
```

The development server proxies `/api` to `https://localhost:18443`. This requires the existing authorized SSH tunnel to the closed Oracle polygon. For the closed polygon, build with `VITE_PUBLIC_BASE=/app/` and serve `apps/web/dist` at `/app/` on the same HTTPS origin as `/api`. The router uses that base automatically. No direct browser connection to Auth/provider services is used. `VITE_` flags do not grant privileges.

## Implemented client flow

- RU/EN responsive landing, catalog, trader profile, copy settings, review, login, first session summary and navigation.
- User Auth C01/C02/TOTP: context confirmation, request/verify, unknown-operation read, and Q01 confirmation with exact `X-Shadow-Login-Id` before personal access. Email, OTP, and authenticator codes stay in component memory. Only opaque progress IDs are stored in session storage for recovery after reload.
- Q02 catalog paging and explicit `CATALOG_CHANGED` restart. The UI never substitutes a synthetic trader when the API is unavailable.
- C04 saves all five raw fields and retains the inactive size field when switching fixed/percent. C05 validates a saved version. C06 submits the shown review; only a successful receipt navigates to the session. Q04 renders actual snapshot money and `copying_not_connected`/EMPTY from the server.
- The original C04/C06 command ID is kept on a lost response. A new command is blocked until its original result can be resolved. No automatic POST retry or false success state.

## Runtime readiness at first package

On 2026-11-04, the polygon backend confirmed only the narrow user Auth path. The Q02/C04/C05/C06/Q04 routes are accepted contracts but not yet active runtime endpoints. These screens show API errors or unavailable states until the backend is integrated. RU email dispatch is currently unavailable; EN is configured for existing synthetic provider users. TOTP enrollment/registration is not connected. Guest draft claim is disabled under current polygon authorization. Positions, Activity, Funds, and Help remain reachable but display an explicit unavailable state until their accepted API slices exist.

## Verification

`npm run typecheck:web`, `npm run build:web`, and repository `npm run check` passed on the first package. Browser visual smoke covered RU/EN at 320 and 390 px, desktop 1280 px, no horizontal overflow, landing, catalog unavailable state, and login form. This does not prove a completed Auth or paper session because the required API endpoints/test identities were not exercised in that browser pass.
