# Trading design-system review

25 October 2026 · scoped documenter pass after the Robin-only explanation correction.

**Outcome: the reviewed trading extension preserves the incumbent Operate interface.** The supplied HTML captures and inspected implementation support the narrow ship disposition in [finish-review.md](finish-review.md). This is a consistency record for this package, not acceptance of the whole admin or production behavior.

## Authority and scope

Read repository AGENTS, current roadmap/state introductions, Impeccable and its document reference, [foundation](../foundation.md), [package scope](README.md), [trading implementation](../prototype/trading.js), the integration in [app.js](../prototype/app.js), [shared stylesheet](../prototype/style.css), and [native construction source](native.js). The parent session had already run Impeccable context once: no PRODUCT.md, DESIGN.md or matching surface brief was found. The existing foundation, components and rendered interface supply the visual authority for this ordinary extension.

No new visual world, product interview, root DESIGN.md, token registry or sidecar was needed. This pass writes only this report; it does not change implementation, unrelated drift or the client kit. The parent reports a single detector warning for the incumbent Inter stack; replacing the agreed typeface would contradict this task.

## Consistency findings

| Area | Inspected evidence |
| --- | --- |
| Palette and depth | Trading inherits the existing dark canvas, surface and raised-surface colors, muted text, purple selection and amber notices. Its CSS adds no palette or global theme override. Existing borders and tonal separation continue to establish hierarchy. |
| Typography | The inherited Inter/system stack, 28px page heading, 18px panel heading and compact table text remain in use. Amounts retain right alignment and tabular numerals. Actual browser Inter availability was not measured. |
| Shell and layout | Existing employee context, profile, breadcrumb, sidebar selection and back-to-session action remain intact. The facts/events composition reuses the support workspace grid and its 24px gap. The existing 1050px breakpoint stacks those panels; the 760px shell adapts navigation for narrow widths. |
| Components | Snapshot selection, tabs, notice, panel, table, buttons and disclosure reuse existing controls. The route adds a bounded 640px selector, 75ch explanatory text, a two-column evidence table with its wide-table minimum removed, and a six-condition recovery list. Below 600px the recovery status and explanation stack. |
| Context and language | RU/EN strings use the existing locale helper. Entry remains on the existing order route for three selected users; no new top-level navigation was added. The reconciliation link identifies the original record separately from the alternative snapshot. |
| Financial legibility | Unknown values display as unconfirmed rather than zero. Purchase fill, possible remaining fill/reserve, cancelled amount and session cost are distinct rows. The sell example states actual remaining shares separately from its target. Robin's prior-cost explanation is now restricted to Robin and monetary access. |

One non-blocking source detail was reported to the parent: recovery row dividers reference `--border`, while the shared root defines `--line`; the supplied recovery capture therefore has no visible row rules. The labels and spacing still separate the conditions clearly. No missing divider is treated as a verified design-system feature, and no repair was made by this documenter.

## Rendered evidence

All four supplied files were opened and visually inspected:

- [Desktop RU](evidence/desktop-ru.png): Robin's late-fill example keeps the selected Sessions route, a visible selector focus ring, clear warning, aligned amounts and adjacent event context. The two-column composition follows the incumbent admin workbench.
- [Recovery EN](evidence/recovery-en.png): the same order, actor and selected snapshot remain visible. Six evidence-based conditions precede the check action and a clear negative result. Text labels distinguish confirmed and unmet conditions without relying on color alone.
- [Mobile EN](evidence/mobile-en.png): the narrow capture shows the existing wrapped navigation, stacked facts/events panels and readable evidence table. Long explanatory copy wraps inside the cards; unknown remaining cost remains explicit. The visible skip-to-content focus state is inherited from the existing shell.
- [Noor corrected RU](evidence/noor-fixed-ru.png): unknown outcome and retained reserve remain visible, while Robin's unrelated cost explanation is absent. The source condition and the screenshot agree with the corrected finish finding.

These are supplied captures, not interactions replayed by this documenter. The images support the displayed states and widths only. Code restores focus after snapshot selection, tab changes and checking; the result has a status region. Those observations do not certify screen-reader announcements, complete keyboard coverage or all responsive widths.

## Native Figma and execution boundaries

The native source builds two 1440px desktop screens and two 720px menus/results on the existing page. It clones incumbent persistent navigation, calls existing button/panel helpers, applies the established client desktop grid, and binds text to existing styles. Shared RU/EN variables drive the same roots. This is a fixed desktop native representation; HTML provides the responsive layout. Construction source establishes intended reuse, not proof of every saved live node or prototype reaction. No live Figma inspection or native rendered capture was performed in this documenter pass.

The implementation contains 12 synthetic snapshots: one for Noor, nine for Robin and two for Orion. Snapshot selection presents alternative evidence without replacing the original user or reconciliation snapshot. Recovery checks read the six conditions from that selected snapshot; users cannot manually mark them complete. Even the fully reconciled example only reports eligibility: it does not start a session, reset history, send an order, release real funds or lift an operational restriction. Monetary access checks in this prototype are presentation behavior, not server authorization. Paper Alpha remains virtual USD with Shadow fee 0%; venue expenses, sale proceeds and market revaluation are outside this package.

No tests or browser actions were rerun by the documenter. The finish review separately records 670 passing assertions and resolution of its single copy finding. Comprehensive role/state coverage, live native behavior, accessibility measurements, performance, publication and real execution remain outside this report.
