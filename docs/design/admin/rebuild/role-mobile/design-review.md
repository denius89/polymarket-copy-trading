# Shadow admin: responsive design record

Date: 2026-10-25. Mode: **Operate**. Disposition: retain the bounded local responsive/navigation refinement, consistent with [finish-review.md](finish-review.md).

This record compares the current local implementation and its captured runtime against the incumbent source at `6df15ef6ffe32405c22bd9739cfbf19cb8f154c7`. It documents the requested extension of Shadow, not a replacement identity or an approval of the entire admin interface. Figma work and the global admin plan remain ongoing.

## Authority and scope

The explicit direction is dark Shadow, Inter, purple action/selection emphasis, one role-filtered navigation tree, readable narrow controls and preservation of employee, object and draft context in RU/EN. No token change was approved. The existing implementation is the visual authority for this refinement.

Impeccable's document reference was applied to inspect and record the incumbent system. Missing root `PRODUCT.md` and `DESIGN.md` are pre-existing gaps, not permission to invent product or brand choices. This pass therefore creates only this scoped evidence record; it does not generate a global design document, token sidecar, new metaphor or renamed palette.

## Incumbent fidelity

| Property | Comparison with incumbent | Evidence |
| --- | --- | --- |
| Typography | Inter and its existing fallbacks, heading hierarchy, body rhythm and tabular-number treatment retained. No font substitution or new type scale. | The `:root` block in [style.css](../prototype/style.css) is byte-for-byte unchanged against the baseline; the supplied overview, reconciliation and profile captures retain the same hierarchy. |
| Color and surfaces | Existing dark background, raised navy panels, muted supporting copy, purple selected states and primary actions retained. | No root token changes in the stylesheet diff. Captured RU/EN profile and modal surfaces use the incumbent colors. |
| Material and shape | Existing bordered panels, restrained rounded controls and SVG icon language retained. The mobile disclosure uses the existing surface, border and focus tokens. | Source diff and mobile captures. The menu's shadow serves overlay separation; it does not introduce a different material direction. |
| Information hierarchy | Identity remains above the workspace; page title, filters, task content and explicit return actions preserve their order. | 390 px overview and 1280 px profiles. The account section navigation remains separate from the application's single primary navigation tree. |
| Monetary meaning | The responsive changes preserve explicit synthetic/unknown states and the existing amount presentation. | At 768 px, the reconciliation comparison still says “Unconfirmed” in all three cells and explains that virtual USD is not wallet balance or profit. This is a visual/source finding, not a financial logic audit. |

## Responsive decisions

| Surface | Incumbent behavior | Finished adaptation and purpose |
| --- | --- | --- |
| Primary navigation at 760 px and below | Primary navigation was displayed as wrapping links in the top area. | One labelled Menu control reveals the existing role-filtered tree. The toggle and disclosed navigation buttons have a 44 px minimum height. The expanded region has bounded vertical scrolling, keeping long role menus reachable without consuming the initial workspace. |
| Navigation interaction | Existing route/role conditions controlled the same navigation content. | The toggle exposes `aria-expanded` and `aria-controls`; Escape closes the menu and restores focus to the toggle. The common route action handler closes the disclosure. Source preserves the role conditions; the saved seven-context trace supports menu/Escape and profile-return behavior. |
| Filters at 760 px and below | Fields relied on a wrapping horizontal layout. | A single column uses the available width for labelled fields and the period control. Form text uses the implemented 16 px narrow-screen size. Labels, selected values and actions remain readable in the captured mobile state. |
| Period picker at 400 px and below | Date fields shared a row. | Dates become a single vertical column; presets and footer actions can wrap. The 320 px capture shows both dates, UTC context, Cancel and Apply within the picker. The overlay remains bounded by viewport width and height. |
| Wide tables | Incumbent tables already used horizontal overflow containers and retained useful column widths. | The container remains independently scrollable instead of forcing the page wider. It gains a localized region label, keyboard focusability, visible focus and contained horizontal overscroll. This preserves values and table structure rather than abbreviating financial data to fit. |
| Tablet and desktop | Sidebar and workbench layout already existed above the mobile breakpoint. | At 768 px the sidebar remains visible and the workbench fits its content column. At 761 px and above the sidebar can scroll vertically; the 1280 px RU profile capture visibly shows this independent sidebar scrollbar. Desktop content density and profile hierarchy stay intact. |
| Supporting forms | Existing account and support layouts already adapted across widths. | Narrow field sizing, wrapping actions and retained stacked support controls complement the shell change. The 390 px support detail preserves recipient, independent draft explanation, editable text and send action. The security modal preserves its explanation, synthetic outcome and language selector. |

The breakpoints above describe the implemented rules for this slice; they do not define a new global spacing or breakpoint system.

## Evidence reviewed

All seven current images were opened during this pass. Their first 60 pixels belong to the review harness; the embedded application uses the selected width. Dark space outside that iframe is not application overflow.

| Capture | Observed result |
| --- | --- |
| [320 px period picker](evidence/mobile-320-calendar.png) | Stacked dates and complete period actions; focused date control is visible. |
| [390 px overview, RU](evidence/mobile-390-overview-ru.png) | Compact header/menu control, employee identity, readable title and vertical venue/period controls. |
| [390 px support detail](evidence/mobile-390-support.png) | Stacked reply/note controls and readable draft composer. This is a scrolled detail, not a full-page capture. |
| [390 px security modal, EN](evidence/mobile-390-security-en.png) | Modal content, close control, synthetic identity-check action and locale field fit the viewport. |
| [768 px reconciliation, EN](evidence/tablet-768-reconciliation-en.png) | Sidebar plus readable comparison workbench; unknown amounts remain explicit. |
| [1280 px profile, RU](evidence/desktop-1280-profile-ru.png) | Existing primary/profile navigation hierarchy, return-to-work action and independent sidebar scrollbar. |
| [1280 px profile, EN](evidence/desktop-1280-profile-en.png) | Equivalent desktop hierarchy and visible focus on the account-protection action. |

[role-browser-trace.json](evidence/role-browser-trace.json) records seven employee/assignment contexts at 390 px with RU→EN, menu open/Escape and profile return. It is supporting recorded evidence, not a fresh interaction test by this documenter. [app.js](../prototype/app.js) and the stylesheet diff supply evidence for expanded-state, focus-return, breakpoint and overflow decisions.

## Limits and handoff

This pass directly inspected saved runtime images and source. It did not operate a live browser, repeat the role trace, rerun model assertions, measure contrast, use assistive technology or test physical mobile devices. Images do not prove every menu state, horizontal-scroll interaction or every route at every width. No complete accessibility, performance, backend, production or Figma verification is claimed.

No additional material design fix was identified within this bounded record. Preserve the existing tokens and role-conditioned navigation when extending the prototype. Keep future evidence explicit about captured states versus repeated interactions. Figma synchronization, global acceptance and the remaining admin plan retain their separate open status.
