# Emergency recovery — independent finish review

Reviewer: fresh `impeccable_finish_reviewer` agent `/root/emergency_finish_review`. Date: 2026-10-25. Mode: Operate. Review is independent of the implementation author.

## 1. Scope and evidence

Reviewed the local synthetic extension in `../prototype/emergency.js`, its sign-in integration in `../prototype/account.js`, and rendering/navigation in `../prototype/app.js`. Inspected shared CSS and identity fixtures only as supporting evidence. Read repository instructions, the Impeccable craft floor, and ADR-0043, ADR-0045 and ADR-0046.

Visually inspected `evidence/desktop-ru.png` and `evidence/desktop-en.png`, both captured at an actual width of 1265 px with the final CSS. These show Technical mode, version 4, after STAFF-201's first approval. Independently reran `check-emergency.cjs`: **122 assertions passed**. The implementer's reported manual Owner A → Owner B → EN → unknown → reconciliation path and 90 saved native Figma reaction assertions are supporting reports, not interactions independently repeated by this reviewer. Native Figma review belongs to the parent review.

Scoped recheck: inspected the corrected action/change handlers and the recaptured RU screenshot, which visibly shows focus on the recovery heading. Independently reran all 122 assertions successfully after the fix. The parent reports that keyboard Enter on evidence, identity proof and approval resulted in `activeElement === H1` with `tabindex="-1"`; this browser check was not repeated by this reviewer.

## 2. Direction fidelity

The code-led narrow extension preserves the incumbent dark surfaces, Inter, purple selection/focus treatment, sidebar, spacing and control patterns. The two-column layout gives scope and evidence the larger area and keeps independent approvals adjacent. This is consistent with Operate; no replacement visual direction or approved comparison comp was supplied.

The desktop RU/EN captures have clear heading hierarchy, readable groups and deliberate wrapping; no clipped controls or horizontal overflow is visible. Source and the EN capture show that authored Russian reason text is preserved when the surrounding interface switches to English. The final recaptured RU image uses another synthetic reason; the two final images are not presented as a matched before/after localization trace. The detector's sole Inter warning is an intentional exception: changing the approved incumbent font would be inappropriate.

## 3. Craft and behavior

The request identifies environment, selected restriction, scope, exact version, evidence package and the approving STAFF identity. Owner A and Owner B are distinct STAFF-201/STAFF-202 fixtures. The same identity cannot confirm twice; explicit sign-out and a separate synthetic sign-in retain the request and clear identity proof. Each approval requires a fresh synthetic key check. Scope/reason/evidence changes invalidate approvals; stale evidence prevents readiness and revocation clears approvals and removes the affected confirmation permission.

Unknown application locks edits, repeat application and restart. The remaining action checks the original result. Success copy distinguishes restriction removal from authorization of a trade or payout; other restrictions and fresh checks/initiator approval for unsent money actions are preserved. Technical mode copy covers the whole environment, both venues, app, public API and product background jobs. These are synthetic UI semantics, not implemented enforcement.

The initial review found that recovery actions replaced the active button and tried to focus a non-focusable heading. The corrected `emergencyAction()` now assigns `tabindex="-1"` to the newly rendered h1 before `focus({preventScroll:true})`, matching the established navigation pattern. Scope changes restore focus to the scope select. Source inspection and the recaptured focused-heading image confirm the narrow correction; the parent's keyboard trace supports the intended runtime behavior.

## 4. Material fixes

**P2 — restore focus after recovery actions: CLOSED.** The correction described above resolves the source-level cause. The parent verified the evidence → identity check → approval path by keyboard, and the independent state-model rerun remains green. No open material fix remains within this review's scope.

No other material defect was found in the reviewed desktop captures and bounded local state model. Do not replace Inter based on the generic detector warning.

## 5. Disposition and limits

**Disposition: SHIP**, for the reviewed desktop composition and bounded synthetic prototype extension. The focus correction closes the only material finding. This is not whole-product or mobile acceptance.

Mobile/intermediate/wide responsive coverage is unverified. The requested 390 px browser override did not take effect; neither provided capture constitutes mobile evidence. Full keyboard/screen-reader operation, measured contrast, performance and every browser/state combination were not independently exercised. This review does not approve backend authorization, real WebAuthn, execution controls, production recovery, native Figma interaction correctness or live operation. A fresh mobile capture is needed before claiming mobile visual acceptance; it does not require redesigning the evidenced desktop composition.
