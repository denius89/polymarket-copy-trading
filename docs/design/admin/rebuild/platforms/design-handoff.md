# Platforms and data: incumbent design comparison

25 October 2026 · independent documenter · scope: the finished local synthetic HTML addition and six supplied browser captures.

The [brief](brief.md) defines an ordinary extension of the existing Shadow admin in Operate mode. The inspected implementation retains that system: dark layered surfaces, Inter typography, purple selection, labelled forms, operational tables and persistent desktop navigation. It continues the [finance implementation's documented vocabulary](../finance/design-documentation.md); no new visual world or global token source is introduced.

## Reused colors, typography and components

The authoritative implementation values remain in the [shared stylesheet](../prototype/style.css). This table records their observed use, rather than establishing a second normative token file.

| Incumbent role | Observed value | Platforms use |
| --- | --- | --- |
| Canvas | `--bg: #0b0d14` | Workspace background |
| Surface / raised surface | `--surface: #141824`; `--raised: #1b2030` | Panels, fields, table headers and hover treatment |
| Border | `--line: #282e40` | Rows, controls and panel outlines |
| Main / secondary text | `--text: #f4f6fc`; `--muted: #a3adc2` | Results and headings / labels and supporting context |
| Accent / selected surface | `--accent: #7044e0`; `--selected: #282044` | Selected tab underline, sidebar selection and notices |
| Focus | `--focus: #a78bfa` | Shared 2px outline with 3px offset |

The declared family is `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`. Body text remains 14px at line-height 1.5, page headings 28px/36px and section headings 18px. This pass verifies the CSS declaration, not which font file the browser resolved. Buttons and labelled fields retain the shared 44px minimum/field height and 9px corners; panels and table containers retain 12px corners. Depth comes from tonal layers and borders. Platforms introduces no shadow or motion vocabulary.

The addition reuses the shared page heading, breadcrumbs, profile entry, tab strip, fields, buttons, table wrapper, notices and panels. In [platforms.js](../prototype/platforms.js), the table helper gives wide tables a labelled, keyboard-focusable scrolling region. Command and history displays are compositions of those primitives, not new global component families. Methodology comparison uses explicit current/draft columns and written absence reasons, so color does not carry the distinction alone.

The [Admin UI kit documentation](../../ui-kit/README.md) describes shared Shadow colors, Inter, linked fields, buttons, panels, rows and navigation, with a documented Figma desktop grid of 12 columns, 16px gutters, 24px margins and 248px sidebar. The existing HTML rebuild uses its own 232px sidebar, narrowing to 208px below 1180px. That pre-existing representation difference is disclosed; this extension does not reconcile it or claim pixel parity with native Figma.

## Layout and local composition

The desktop shell and workspace spacing remain shared with finance. The six sections follow the operational route: connections, markets, collection, validation, methodology and results. Within the content area, platforms adds a 24px vertical grid gap, two-column forms with 20px gaps, wrapping actions with 8px gaps, and explicit full-address wrapping. These are local composition rules using the existing palette and controls.

Below 760px, those forms become one column and the established mobile navigation disclosure replaces the persistent sidebar. Shared filters stack. Tabs and wide tables retain bounded horizontal scrolling instead of compressing every column. In the supplied 390px and 320px collector states, labels, current settings, the newer unsent draft, unknown command and reconciliation action remain readable. Some form actions sit close together; the finish reviewer explicitly accepted their distinguishable boundaries in this bounded review.

## Evidence directly inspected

Source comparison covered the platforms brief, README, finish review, the shared stylesheet, platforms rendering/access helpers, finance implementation patterns and design documentation, and the Admin UI kit README. All six following PNGs were opened and visually inspected during this documentation pass:

- [Desktop connections](evidence/connections-ru-desktop.png): separate connection and rating-data columns, shared shell and table/panel hierarchy; Limitless coverage is unknown rather than zero.
- [Desktop methodology comparison](evidence/rating-comparison-ru-desktop.png): two-column form and current/draft comparison; profile C changes from a score to insufficient data while D retains no response.
- [Desktop restoration](evidence/rating-restore-ru-desktop.png): restored minimum of 20 actions, current R-2 context and preserved R-1/R-2 history; confirmation and draft are distinct.
- [Connections at 390px](evidence/connections-ru-390.png): collapsed menu, stacked filters and visibly bounded tab/table scrolling.
- [Unknown collector command at 390px](evidence/collector-unknown-ru-390.png) and [320px](evidence/collector-unknown-ru-320.png): single-column form; current P-1 remains 5 minutes / 90 days while the unsent draft is 12 / 90; the unknown command and its reconciliation action remain separate.

The narrow captures include a surrounding review harness and unused black area beside the app pane. They are browser-width evidence, not physical-device screenshots. No English screenshot, live browser session, native Figma node or deployed Site was inspected by this documenter.

The independent [finish review](finish-review.md) reports **SHIP for the bounded synthetic HTML addition**, with 155 passing assertions and the listed source findings resolved. Those test results are attributed to that reviewer; this documentation pass did not rerun them or expand their verdict to production or all possible states.

Source SHA-256 at comparison time:

| File | SHA-256 |
| --- | --- |
| `prototype/style.css` | `cb131f92e43c4ec7c5f4090c386b7d7da85bea10ff89cb46f119a0c8844c60ca` |
| `prototype/platforms.js` | `7c0df2895b65f08ad8a17321fa5acc0c03f8acc06536f1ba31cc63efffd3e0cb` |
| `platforms/finish-review.md` | `5156de760558454f2fb66a7b365902230a081f6600cb0d0e2c96b1ea7fd78ee8` |

## Implementation and documentation boundaries

The [README](README.md) remains the scoped behavior contract: HTML supports synthetic numeric input, filtering and drafts held in the current browser tab; publication and confirmed catalog readiness are separate. The 0–100 score is an index, not profit probability. Missing or insufficient source data does not become zero. Example timings, addresses, weights and thresholds are not verified venue API parameters. Prototype permission predicates and command state checks do not implement server authorization, concurrency or live integrations.

Native Figma has a separate prepared interaction model and requires its own evidence; its ongoing menu-width/reset work is outside this HTML comparison. Construction scripts are not exact Figma backups. This document does not certify Figma, deployment, complete accessibility, physical devices, runtime performance, real collection, financial outcomes or trading.

Root `PRODUCT.md`, root `DESIGN.md` and `.impeccable/design.json` were directly checked and remain absent. Their absence predates this extension. The applicable [Impeccable new-work §7](../../../../../.agents/skills/impeccable/reference/new-work.md) requires ordinary extensions to compare with the incumbent system and report evidence while preserving its files. The [document reference](../../../../../.agents/skills/impeccable/reference/document.md) informed the extraction; no global identity workshop, token file or sidecar was created to repair unrelated drift. Only this handoff was written. Later changes to the compared HTML/CSS require a scoped documentation recheck.
