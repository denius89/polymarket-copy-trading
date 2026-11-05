# Shadow client web

React 19 + TypeScript + Vite 8 + Tailwind 4. The visual base follows the approved Final Figma file `lxPP2um7FvIbt02K8eeH4T`, especially mobile landing `2529:19569`, first catalog `2532:20141`, fixed setup `2498:28817`, empty home `2532:21021`/`2499:3827`, positions `2865:3224`/`2884:49632`, and activity `2867:153346`/`2884:49688`. Matching RU/EN mobile/desktop variants are indexed in `docs/design/client/sitemap.json`. Shared controls and colors live in `packages/ui`.

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
- C04 saves all five raw fields and retains the inactive size field when switching fixed/percent. C05 validates a saved version. C06 submits the shown review; only a successful receipt navigates to the session. Q04 renders actual snapshot money and `copying_not_connected`/EMPTY from the server. Home, Positions and Activity share the Q04 read state. Positions shows zero only when the server confirms an EMPTY snapshot with zero positions; Activity does not invent events without a history API.
- The original C04/C06 command ID is kept on a lost response. A new command is blocked until its original result can be resolved. No automatic POST retry or false success state.

## Runtime readiness at first package

On 2026-11-05, the installed polygon frontend has passed C01/C02/Q01 smoke in RU/EN; the backend Q02/C04/C05/C06/Q04 runtime is still awaiting database/API integration. These screens show API errors or unavailable states until that integration passes. The closed test mail adapter sends English email for both interface languages, with a visible explanation in the sign-in form. TOTP enrollment/registration is not connected. Guest draft claim is disabled under current polygon authorization. Positions and Activity render real Q04 loading/error/no-session/EMPTY states but no position/event rows; dedicated list/history APIs do not exist yet. Funds and Help remain explicit unavailable states.

## Verification

`npm run typecheck:web`, `VITE_PUBLIC_BASE=/app/ npm run build:web`, repository `npm run check`, and `npm run test:repository` passed on the 2026-11-05 empty-session package. Browser visual smoke used a temporary local EMPTY fixture for RU/EN at 320/390 px and desktop 1280 px, including Home, Positions and Activity; the fixture was removed before the build. This proves layout and copy, not a completed paper API session. The server operator independently confirmed installed Auth C01/C02/Q01 smoke for the previous pinned client build.
