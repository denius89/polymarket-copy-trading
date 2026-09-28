# Mobile design rebuild · 28 September 2026

Scope: active EN/RU mobile flows in Figma file `lxPP2um7FvIbt02K8eeH4T`. This is an editable design prototype, not production UI or a working trading application.

## What was wrong

- All ten previous screen roots per locale used flat absolute-positioned text and rectangles.
- Narrow fixed-width status labels, detached switch geometry, 38px chips and 28px Back targets had no content-driven layout.
- Old rotated rectangle segments remained below replacement chart vectors. The earlier chart cleanup did not remove the complete old chart subtree.
- Chart periods, percentage/dollar examples and virtual-fee examples were inconsistent.
- Session management routed back into onboarding, and the active flow lacked separate management, report and profile destinations.

## Rebuild

- Preserved all original child nodes in reversible backup containers. No original screen content was deleted. Stable main frame IDs retained.
- Rebuilt 20 main screens with 24px gutters, structural auto-layout, consistently spaced cards, readable Inter typography and token-bound colors.
- Added six explicit destinations per locale: session management, paused state, disconnect confirmation, close confirmation, example result and profile. Total: **16 screens per locale / 32 mobile screens**.
- Repeated buttons, content-hugging statuses and on/off switches use true component instances. Buttons are 48px high; switches have 48×44 interactive containers around 48×32 tracks.
- Graphs use one continuous native vector series, quiet grid and subtle area, with labels matching 30-day examples, the active 3-day session, or a 7-day example report.
- Discover's 12.8% example corresponds to $25.60 on a $200 budget. Future first-paid example uses 0.50% taker / 0.25% maker; an illustrative 0.40625% blended rate gives $3.25 on $800 turnover. Demo charges remain zero.
- Russian visible monetary/percentage decimals use commas; EN strings keep decimal points.
- Input boundaries bind to the separate strong-control border token; card dividers remain subtle.
- Unknown state refers to the simulator/session ledger, stops new risk and offers no blind retry.

## Prototype interactions

Budget presets update prototype-only budget, turnover and virtual-fee text variables. The review budget uses the same variable. Switches have on/off component interactions. Main flows, Back controls, activity details, management branches and report/profile destinations are linked.

Language changes use Figma prototype URLs because native NAVIGATE cannot cross pages. The selected language control intentionally has no navigation action.

The account screen explicitly submits no credentials. Profile/Telegram settings are illustrative. The demo report and dashboard are curated sample states, not outputs of an execution engine. Switch state is not a complete persistent risk configuration. Confirming a demo branch opens an explicitly identified example report. These limitations must be retained in reviews; no backend, real order, authentication or messaging integration is implied.

## QA evidence

- All 32 mobile screens inspected at readable screen scale across the build and independent QA pass.
- Final native geometry audit: **0 children outside auto-layout parents** across both locales; **44 nodes with prototype reactions per locale** (includes switch and preset actions, not a count of unique routes).
- 48px action targets and 44px switch targets; previous 28px Back controls removed from active pages.
- Inspected native graph scaling, full RU labels, input boundaries, wrapping, baseline alignment and safe bottom action area.
- Selected PNG exports are included. The screenshot connector intermittently omits repeated header/label content in batch renders; individual exports and underlying geometry were used to check this discrepancy. `EN-session.png` and `RU-risk.png` are individual exports.
- Not yet verified: frontend reflow at 320/360px, 200% browser zoom, screen-reader behavior, actual keyboard focus, real touch interaction, persistence or full state-machine behavior. No production-ready or stakeholder-approved claim is made.

## Stable identities

| Screen | EN | RU |
|---|---|---|
| Welcome |29:3|33:3|
| Discover |29:31|33:31|
| Trader |29:90|33:90|
| Budget |29:127|33:127|
| Risk |29:158|33:158|
| Account |29:187|33:187|
| Review |29:210|33:210|
| Active |29:236|33:236|
| Activity |29:289|33:289|
| Event |29:328|33:328|
| Manage |133:44|133:575|
| Paused |133:45|133:576|
| Disconnect |133:46|133:577|
| Close |133:47|133:578|
| Result example |133:48|133:579|
| Profile |133:49|133:580|

Shared mobile control container: `113:239` (moved to shared component page by project coordinator).
Recovery containers: EN `121:981`, RU `121:1526`, now in recovery page `121:1943`.
Prototype-only state collection: `VariableCollectionId:134:180`; shared text variables `134:181`–`134:183` (Figma VariableID prefix), plus a separate `Demo/FeeRU` variable so Russian decimal commas do not alter English strings.

## Construction snippets

The JavaScript files in this folder are historical construction snippets retained for audit. **They are not idempotent migrations and do not reproduce the full final canvas.** Follow-up corrections, variable wiring and component refinements were separate tool operations. Do not rerun them on the working file. Use the Figma file and identity table above as the current source of truth.
