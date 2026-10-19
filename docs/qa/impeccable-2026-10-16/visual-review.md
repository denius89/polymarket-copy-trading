# Impeccable · independent Assessment A · 16 October 2026

Mode: Operate. Read-only review of a bounded Figma sample. Independent of detector output; no Figma, application, or business-rule edits. Existing Shadow dark/purple identity is preserved, not treated as a defect. Context launcher failed with Permission denied; existing AGENTS, current ROADMAP/STATE and client/admin handoff were read instead. No PRODUCT.md or DESIGN.md existed in the searched repository.

## Evidence and coverage

Fresh Figma screenshots visually inspected in this assessment:
| Surface | Node | Size | Evidence |
| --- | --- | --- | --- |
| Client RU mobile active home | 2498:26193 | 390×844 | client-mobile-home-ru.png |
| Client RU mobile trader 30d | 2498:28378 | 390×844 | client-mobile-trader-ru.png |
| Client RU desktop active home | 2499:53 | 1440×960 | client-desktop-home-ru.png |
| Admin RU overview | 1982:37690 | 1440×1000 | admin-overview-ru.png |
| Admin RU incident queue | 2414:117179 | 1440×1200 | admin-incidents-ru.png |
| Admin EN incident queue | 2414:120601 | 1440×1200 | admin-incidents-en.png |

Direct URL pattern: https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2498-26193 (substitute table node IDs with hyphen).

Current Final client pages only, not archived client variants. Admin current pages 1981:29 / 1981:30. Admin financial detail was not sampled; incident queue supplies the operational-risk sample. A client EN home capture was still pending when the review boundary was reached; it is not included in the visual verdict even if its capture later completes. English review is limited to admin incident queue. Other states, scrolling, transitions, keyboard/screen reader, responsive variants and real runtime were not exercised. This is not a full-file, whole-prototype, accessibility or browser audit.

## Design-specificity verdict

The product has a coherent operational identity and visible domain substance: account components separate available money, reserve and positions; the unknown purchase warning explains the pause in buying; trader public performance is separated from personal copying. Standard cards and tables are appropriate for Operate mode. No visual-world replacement is warranted.

## Strengths

1. Money structure is explicit on both homes: total 209.77, available 180.38, reserve 5.79 and positions 23.60 reconcile. A yellow warning gives a concrete next step while describing retained reserve.
2. One recognizable brand and control vocabulary spans client mobile, client desktop and admin: dark neutral surfaces, purple selection, semantic yellow warnings, repeated labeled navigation.
3. RU/EN incident tables show object identity, venue, severity, owner/status and UTC update time together; this supports investigation without memorizing context between screens. The visible layout does not clip either language.

## Priority issues (observed only)

### P1 · Incident filter block pushes the actual incidents too far down
Evidence: RU 2414:117179 and EN 2414:120601. Only two selects occupy a full-width block from roughly y268 to y626; the table header begins around y740 and first incident around y790. At a common 900px-high workspace, only a small amount of actual queue is initially visible. This matters to an operator arriving to inspect a high-severity unknown order.
Recommendation: on desktop put Venue and Status in a compact horizontal filter row with Apply/Reset nearby, freeing vertical space for the actual incident queue. Preserve all filter meanings and states; verify narrower desktop separately.

### P2 · Positive Active badge needs local qualification when new purchases are blocked
Evidence: mobile 2498:26193 and desktop 2499:53. Green Active appears in the copying card while a separate warning states that new purchases are stopped pending reconciliation. The rules are not contradictory (the session is active), but scanning only the card gives an incomplete operational picture, particularly when the warning scrolls out of view on mobile.
Recommendation: keep session status and add a nearby subordinate buying-state label, e.g. New purchases paused / Waiting for reconciliation. Do not rename the session Paused or change reserve behavior.

### P2 · Trader's primary action is not discoverable in the first mobile viewport
Evidence: 2498:28378, 390×844. Header, trader summary, period controls and the beginning of performance chart occupy the viewport; Configure copying is not visible. A prospective copier must scroll past the chart and metric block before discovering the action.
Recommendation: place a visible Configure copying action next to the initial trader summary or provide a properly reserved sticky action; retain the full statistics below and avoid colliding with the existing bottom navigation. The issue is action discovery, not that scrolling itself is broken; scrolling was not tested.

### P2 · Important desktop operational labels are too small relative to unused space
Evidence: 2499:53 text-node inspection plus screenshot. Realized/unrealized result and copying state use 11px and a 9px active chip; account component labels are 11px, while the card has substantial interior space. Small secondary text impedes quick reading of financially relevant distinctions.
Recommendation: bring essential status/financial labels into the existing readable 12–14px product scale, adjust wrapping, and check at actual size. This is a legibility concern; no contrast or WCAG failure is asserted without measurement.

## Cognitive load and emotional journey

Mobile home has a clear overview → warning → copying sequence. Trader profile puts five successive informational blocks before or around the primary copying action, increasing search cost for the novice. Admin queue prioritizes filter mechanics spatially over the incident that motivates the visit. Sidebar expansion yields more than four visible destinations, but those are persistent navigation grouped by domain; this alone is not a defect. The main emotional valley is seeing Active together with blocked purchases: the warning reassures, but the localized card status should carry the same nuance.

## Approximate Nielsen review (0–4, bounded visual evidence)

Numbers assess visible design only, not interaction implementation. n/a means not established by the sample and must not be read as passed.
| Heuristic | Score | Basis / limit |
| --- | --- | --- |
| System status | 3 | Account, reserve, warning and incident status visible; Active needs buying qualification |
| Match to real world | 3 | Concrete money breakdown and venue naming; PnL remains specialist shorthand |
| User control/freedom | n/a | Cancel, undo and recovery behavior not exercised |
| Consistency/standards | 3 | Shared vocabulary and style across sample; no full consistency audit |
| Error prevention | n/a | Limits, submit guards and destructive confirmation not sampled |
| Recognition over recall | 3 | Labeled navigation and linked object context; trader CTA discovery weak |
| Efficiency/flexibility | n/a | Keyboard, bulk operations and actual filter behavior untested |
| Aesthetic/minimalist | 3 | Restrained useful composition; excess filter block height hurts density |
| Error recognition/recovery | n/a | Warning visible but recovery flow not followed |
| Help/documentation | 2 | Visible client help icon and explanatory copy; no help flow inspection |

Subtotal 17/24 for six visually assessable heuristics; no whole-product quality grade should be inferred.

## Persona red flags

- Jordan, first-time client: primary copying action requires scrolling to discover, and Active can be misread as all purchases continuing.
- Alex, operations staff: valuable queue rows compete with an oversized filter form.
- Sam, low-vision user: 9–11px desktop statuses and financial labels merit actual-size/zoom verification. Keyboard and assistive technology remain unknown.

## Questions for the synthesis

Would the operator's first screen show the urgent incident before optional filtering? Can the trader summary expose the next step while preserving performance context? Which same-card wording can distinguish active session from stopped buying without changing agreed business logic?

Questions skipped: this is an internal independent Assessment A handed to the parent for the combined review; final user questions belong to the synthesis.
