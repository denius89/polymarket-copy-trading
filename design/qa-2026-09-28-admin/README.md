# Admin design rebuild — 28 September 2026

Scope: current operational admin in [Figma](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=51-3). This is a visual and interaction prototype using illustrative paper data, not an operational service.

## Baseline findings

- Each screen had roughly 70 loose, absolute-positioned elements and no component instances.
- Table headings and cells used different column offsets; dense labels were 11–13px with tight line heights.
- The overview graph had no units, period, or explanation of its second series.
- The venue summary claimed three health states although only two venues were listed.
- An unconfirmed incident conflicted with an executed event in the linked user session.
- Some sidebar entries looked actionable but had no destination.

## Changes

The four original top-level frame IDs are preserved at 1440 × 1000px:

| Frame | ID | Purpose |
|---|---|---|
| A01 Operations overview | `51:3` | Priority issues, sample processing delay and two venue states |
| A02 Incident queue | `51:89` | Seven aligned incident rows; INC-204 opens its detail |
| A03 Incident INC-204 | `51:159` | Consistent event timeline, recorded evidence and safe reconciliation preview |
| A04 User session | `51:222` | Protection, allocation, copy settings, events and support explanation |
| A05 Reconciliation preview | `121:1513` | Explicit demo-only feedback; no request or data mutation |

Layout uses a 224px sidebar, 32px main gutters and 1152px content width. Related content is grouped with auto layout. Cards use 16/24px spacing, readable 14px body text with 20px line height, 12px secondary labels, 28px page headings and 44px action controls. Navigation is 48px tall; incident rows are 64px tall. Table headers and rows share exactly the same column widths.

Eleven reusable main components live in container `113:203` (the root task may move this container to the shared component page): primary/secondary/quiet button, four semantic status labels, default/selected navigation, metric card and incident row. They bind to existing semantic color, spacing and radius variables. Current screens contain actual linked instances.

The chart shows Polymarket event-processing delay in seconds over the last hour. It has one named series, explicit time labels, zero baseline, monotone interpolation that does not overshoot the observations, a 2px line and an 8% area fill. The previous decorative comparison and glow were removed.

All screens identify illustrative data and paper mode. The example reconciles an unknown **simulated** result, not a real order. The user allocation is internally consistent: $80 = $42.60 confirmed exposure + $12.40 reserved for checking + $25 available after reconciliation. The latest user event stays unconfirmed in both views. Virtual fee copy follows the first paid schedule: 0.50% taker / 0.25% maker; alpha charges remain $0.

## Validation

- Each desktop screen was inspected separately at 1440px; the confirmation was inspected at natural size.
- Table border inset overflow found by structural inspection was corrected through `strokesIncludedInLayout = false`.
- Session content height is 981px within the 1000px frame; buttons and text are within bounds.
- All 18 destination links resolve to existing frames. Navigation, incident inspection, user-session access, reconciliation preview and return paths are connected.
- 44px buttons and 48/64px navigation/table targets are preserved.
- The text-only Inspect link uses the light purple token; noninteractive sample rows show a muted dash.
- No external assets, customer information, production API calls or live trading controls were added.

## Sources informing the layout

- [IBM Carbon: data tables](https://carbondesignsystem.com/components/data-table/usage/) — title, toolbar, consistent columns, generous table width and explicit row actions.
- [IBM Carbon: chart anatomy](https://carbondesignsystem.com/data-visualization/chart-anatomy/) — chart context, axes, labels and legible data encoding.
- Project ADR-0011 — safe operator scope and paper-only workflow.

This QA covers the desktop design prototype. It does not claim browser rendering, keyboard or screen-reader testing, backend behavior, or production readiness. Economics/tariff and feedback requirements remain in the full product scope; the current four-screen modern flow demonstrates operations and support, with tariff context and feedback explanation included in the session view.
