# Emergency recovery — implemented design record

Date: 2026-10-25. Fresh documenter: `/root/emergency_documenter`. Mode: **Operate**. Scope: the additive emergency recovery prototype, preserving the incumbent admin interface.

## Evidence and authority

Directly inspected `../prototype/emergency.js`, the relevant rules in `../prototype/style.css`, [finish-review.md](finish-review.md), and the rendered [RU desktop](evidence/desktop-ru.png) and [EN desktop](evidence/desktop-en.png) captures. Both captures show Technical mode, version 4, after STAFF-201's approval. The RU capture visibly includes focus on the recovery heading. This documentation pass did not repeat browser interactions or tests.

Root `DESIGN.md` and `PRODUCT.md` are absent. The existing implementation nevertheless supplies a coherent visual authority: this is a local extension, not a new identity. The Impeccable context command did not discover that authority automatically; direct source and screenshot inspection did. No root design document, token sidecar, shared component, or source file was created or changed by this pass. Missing global documentation is recorded without an unrequested system migration.

## Implemented direction and reuse

The extension retains the dark admin shell, Inter typography, purple navigation/primary-action treatment, rounded bordered panels, and existing control sizing. Shared CSS defines the page ground (`#0b0d14`), panel surface (`#141824`), raised surface (`#1b2030`), border (`#282e40`), primary text (`#f4f6fc`), secondary text (`#a3adc2`) and accent (`#7044e0`). These are observations of the incumbent source, not new token decisions.

The composition places scope, reason and evidence in the wider left column, with independent approvals and the related investigation alongside. It reuses the existing support two-column layout/context panel, feedback metadata/select patterns, trading check rows, status badges, buttons and disclosure controls. Panels retain 24 px padding and 12 px corners; ordinary buttons retain a 44 px minimum height and 9 px corners. Page headings retain the established 28 px/36 px hierarchy. Emergency-specific styling is limited to the status summary, approval list, wrapping and navigation selection.

The inspected desktop captures show readable RU/EN hierarchy, wrapped action labels and no visible clipping. Russian authored reason text remains Russian inside the EN interface. The status badge communicates the waiting state in words as well as color. History and synthetic failure controls sit behind disclosure elements below the primary task, keeping the immediate recovery decision prominent.

## Interaction contract represented by the prototype

The page identifies one selected restriction, its environment/scope, a reason, a numeric request version and the associated evidence. A separate confirmation panel identifies the two STAFF approvals. In the local model, changing scope/reason or evidence invalidates prior approvals; each approval needs a fresh synthetic identity proof, and one identity cannot approve twice. A separate synthetic sign-in supplies the second identity. The UI distinguishes a removed restriction from permission to execute a trade or payout.

Unknown application outcome prevents editing, repeat application and restart; the remaining reconciliation action checks the original result. Other restrictions and fresh checks for unsent money actions remain explicit in the explanatory copy. These are synthetic interaction semantics only.

After recovery actions rerender the page, the heading receives `tabindex="-1"` and focus. Scope changes restore focus to the select; reason edits restore the textarea caret. The focus correction is visible in source and the RU capture. Full keyboard and assistive-technology acceptance is not inferred from that evidence.

## Native Figma and validation limits

The parent handoff identifies native Figma roots `4143:371`–`4143:374`; their final verification belongs to the parent, and this documenter did not inspect them. Reported native simplifications remain explicit: fixed reason choices, no numeric version display and no history, compared with arbitrary reason input, numeric versions and history in HTML. Native and HTML interaction parity is therefore not claimed.

The independent finish review gives **SHIP** for the reviewed desktop composition and bounded synthetic prototype after the focus correction; it reports an independent rerun of **122 assertions**. The parent reports **1,316 aggregate checks including the baseline**. These counts are attributed reports, not checks rerun in this documentation pass.

Responsive CSS exists, but the attempted 390 px browser override did not actually resize the viewport. Mobile visual acceptance remains unverified. No mobile, intermediate or wide-screen acceptance, measured contrast/performance result, exhaustive accessibility result, real WebAuthn, backend authorization/security enforcement, production recovery or live-operation approval follows from this record.

The finished extension fits the incumbent visual system at the inspected desktop scope. Preserve that system; further evidence should resolve the stated coverage limits without prompting an unrelated redesign.
