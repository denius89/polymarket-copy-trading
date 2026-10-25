# Finance: incumbent design comparison

25 October 2026 · independent documenter after the listed HTML corrections · scope: the local synthetic finance prototype.

This is an ordinary extension of the established Shadow admin interface in Operate mode. The [brief](brief.md) retains the existing dark surfaces, one purple accent, Inter, tables, forms and workspace grid. The finished source and the inspected captures follow that direction. This record documents reuse and local additions; it does not establish a new global design system.

## Existing visual vocabulary reused

The normative values remain in [the shared stylesheet](../prototype/style.css). The values below are an observed snapshot, not a second token source.

| Existing role | Observed value | Use in finance |
| --- | --- | --- |
| Page background | `--bg: #0b0d14` | Workspace canvas |
| Surface / raised surface | `--surface: #141824`; `--raised: #1b2030` | Panels, controls, table headers and hover surfaces |
| Borders | `--line: #282e40` | Panel, table and row boundaries |
| Main / secondary text | `--text: #f4f6fc`; `--muted: #a3adc2` | Values and headings / labels and context |
| Primary accent / selected surface | `--accent: #7044e0`; `--selected: #282044` | Primary actions, receipt bars, active tabs and notices |
| Keyboard focus | `--focus: #a78bfa` | Shared 2px outline with 3px offset |
| Typeface | `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | Shared body and controls; CSS declares the stack, this pass does not verify downloaded font identity |

The shared body is 14px with line-height 1.5; headings use the existing 28px/36px page-title and 18px section-title sizes. Money values reuse tabular numerals. Finance summary values use a local `clamp(20px, 2.3vw, 30px)` to fit the established summary strip. The familiar control height is at least 44px, normal button/input corners are 9px, and panel/table containers have 12px corners. These are reused implementation values, not a newly imposed scale.

The desktop shell retains its 232px navigation column and shared workspace spacing. The finance content has a 24px grid gap. Four linked summary values lead into the receipts/expenses panel and the existing two-column detail layout. Detail screens keep the status first, then the money breakdown and full route, then owner confirmations. Tables preserve the common bordered scroll region and column hierarchy. The VIP comparison continues to distinguish previous and proposed values, now with translated choice labels instead of raw option codes.

Depth is predominantly conveyed by dark tonal layers and thin borders. Finance adds no new shadow language. Existing popover/dialog shadows and shared reduced-motion behavior remain owned by the shared stylesheet.

## Local composition and responsive behavior

Finance adds a daily receipts/expenses display within the incumbent panel: purple receipt bars, muted expense bars, adjacent numeric values, and a labelled button for each day. These use existing colors and controls. The chart text distinguishes funding from revenue and states its synthetic scale; color is not the sole carrier of the values.

Finance filters extend the existing labelled fields with an expandable period control. The settings layout uses two columns and becomes one at the existing 760px breakpoint. At that breakpoint, finance filters and date fields stack, the chart compresses its date/value columns, and the chart heading/actions stack. The shared summary strip becomes two columns, the shared detail split has already become one column below 1180px, and the existing mobile navigation disclosure is retained. Long recipient addresses wrap within their panel. Wide data tables retain intentional horizontal scrolling with a labelled, keyboard-focusable region.

These are local composition rules for this operational surface. They do not change the global palette, font family, component identity or navigation architecture.

## Evidence checked

Source inspection covered the shared stylesheet, the [finance implementation](../prototype/finance.js), the [direction contract](brief.md), and the [bounded finish verdict](finish-review.md). Finance source inspected includes the common table wrapper, overview, payout detail, content routing, access predicate, localized money formatter, and display-value mapping. This was a documentation comparison, not a new runtime test or defect hunt.

Opened and visually inspected:

- [Desktop finance overview](evidence/finance-overview-ru-full.png): established shell, four summary cells, daily chart, neutral panels and purple emphasis.
- [Corrected Russian VIP review](evidence/vip-review-ru-full.png): human-readable action/duration labels in the form and comparison table, with user ID, exact version/date references and values retained.
- [Corrected payout at a 390px browser review width](evidence/payout-prepared-ru-390-full.png): single-column amount, route and confirmation panels; 120 USDT liability, separate 0.50 USDT fee, 120.50 USDT reserve; the full wrapped address and saved `USDT / DEMO-CONTRACT` / `Demo network` route. This file includes the review harness surrounding the narrow app pane; it is not a physical-device capture.

The finish reviewer reports `disposition: ship` for the listed corrections. It records 137 synthetic finance assertions from the preceding review and four focused English display checks for the final fix. This documenter did not rerun those checks and does not promote the bounded verdict to a whole-surface certification.

Source SHA-256 at comparison time:

| File | SHA-256 |
| --- | --- |
| `prototype/style.css` | `d05b04ba61a07fe0edbac550e75bb61fb9fb6a06197f63430397ede31738973f` |
| `prototype/finance.js` | `104055879110cf11cf7fe6d60b9a6c43e5d2b054e14132701e3802161c4b6606` |
| `finance/finish-review.md` | `9293405fb4a2006f7ab5323734510680638f1654405a13c281c3264859b6d9f4` |

## Documentation boundary and limitations

Root `PRODUCT.md`, root `DESIGN.md`, and `.impeccable/design.json` were absent when inspected. Their absence is disclosed, not presented as a newly discovered visual identity or silently repaired. The incumbent authority for this slice is the saved brief and existing shared implementation. The brief's generic FINISH sentence names `DESIGN.md`; the applicable [new-work §7 ordinary-extension contract](../../../../../.agents/skills/impeccable/reference/new-work.md) specifically requires comparing the finished build with the incumbent system, preserving its files, and reporting evidence. Token-bearing `DESIGN.md` plus its sidecar are required for a new world or an approved system change; neither is introduced by this finance extension. New token files are therefore not required for this bounded documentation pass. Any later deliberate global design-system extraction is separate work.

This document does not verify native Figma nodes or interactions, public deployment, physical devices, backend authorization/accounting, real payments, complete accessibility, or runtime performance. Figma work was still underway and must have its own evidence and handoff. RU source and the three named captures were directly checked; English checks are attributed to the reviewer. No new detector, context run, global design-system edit, code edit, or Git mutation was performed in this pass. Later changes to the compared HTML/CSS or corrected evidence require a scoped recheck.
