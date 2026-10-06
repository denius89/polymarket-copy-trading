# Audit 81: admin interface changes · 6 October 2026

Scope: Figma admin page `51:2`. Interface work only; illustrative paper data and disconnected finance sources. No backend persistence, live execution, role enforcement or real accounting is asserted.

## Changed screens

| Finding | Interface result | Evidence / remaining work |
|---|---|---|
| BL-06 | A04 distinguishes active lifecycle from blocked new buys. The $25 allocation remainder is explicitly before unverified expenses and does not assert spendable funds or permission to buy. A06 explains uncertainty, held reserve and recovery. | A04 `51:222`; A06 `1879:25495`. Exact block scope and resume policy still require the business/technical contract; the sample shows the affected session. |
| BL-07 | A05 identifies the same operation `int_8f21`, separates rereading from resending, explains late fills and linked cancellation/replacement. | `121:1513`. It remains an explicitly marked preview. Durable operation/idempotency behavior is not implemented by Figma. |
| BL-08 | A06 shows unavailable ownership evidence and lists tracked/manual/other-session distinctions. Detach is not presented as a sale; late fills retain the operation link. | `1879:25495`. Virtual-lot accounting and repeated-entry rules remain technical work. |
| BL-09 | A06 states protection thresholds and valuation freshness are unapproved; stale valuation is not zero and pause does not imply liquidation. | No invented threshold or enabled financial-autopause control. |
| BL-10 | A06 separates system ceiling, template, session override, effective version and Before/After. Unrecorded sample values are honest; view is read-only. | No claim that the sample $30 daily limit proves a mandatory system ceiling. Reserve remains held. |
| BL-14 | A06 uses the agreed support labels Sent / Waiting for support / Waiting for your reply / Resolved / Closed; Draft / Sending / Result unknown is separate. Assignment does not change lifecycle. | This is operator explanation, not a new ticket-management backend or a tested send operation. |
| BL-04 / section 8 | Old A04 hardcoded maker/taker schedule removed: confirmed costs unavailable, unknown cost is not zero. Existing bilingual finance journal extended with operation/basis, rate/effective date, asset/network/recipient, received/outstanding and FX provenance. | RU basis `801:472`, EN `801:1552`. Accrual, receipt, correction/refund, expenses and liabilities remain separate. Partial receipt does not settle the full accrual; internal transfers are not revenue. Source remains disconnected. |
| BL-15 | RU/EN liabilities distinguish our program from venue programs and use received service fees as the basis. | `801:752`, `801:1832`; program eligibility still requires a decision. No real payouts. |

Existing finance screens were extended, not duplicated. A06 is linked from the A04 “Session controls and evidence” card; its return action goes back to A04 and is labelled “Back to user session”. Original A01–A05 IDs and existing finance paths are preserved.

## Verification

- Read back changed roots: A04 content height 981 within 1000; A06 content 884 within 1000; A05 expanded to 560 × 566. RU/EN finance basis content ends at y=922 within 1280.
- Every inspected text uses Inter, matching the current admin product font. No full-UI raster or image-filled nodes in those roots.
- 37 destination links inspected across changed session/reconciliation/journal/basis roots; zero missing targets. A04 → A06 → A04 verified structurally.
- Visual compositions reviewed: A04, A05, A06, RU/EN finance basis, RU journal, RU liabilities and RU reconciliation. Text wraps and no overlapping content were observed. A06 return copy was corrected after the first visual pass. A04 allocation helper was then clarified as before unverified expenses; its two-line text fits the card and the updated visual pass passed.
- Saved final composition evidence: [session](audit81-admin-session.png), [reconciliation](audit81-admin-reconcile.png), [controls](audit81-admin-controls.png), [finance basis](audit81-owner-basis-ru.png). The controls image includes the corrected return label, factual effective-rule wording and factual sellable-share evidence wording; the final visual pass passed.
- This is Figma visual/structural validation, not a browser Present pass, permissions test, payment reconciliation or implementation acceptance.

## Direct review links

- [User session](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=51-222)
- [Session controls and evidence](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1879-25495)
- [Reconciliation preview](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=121-1513)
- [Owner entry basis RU](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=801-472)
- [Owner entry basis EN](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=801-1552)
