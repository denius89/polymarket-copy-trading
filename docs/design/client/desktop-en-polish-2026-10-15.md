# Final desktop EN polish — 2026-10-15

Scope: Figma file `lxPP2um7FvIbt02K8eeH4T`, page `2499:3` (**Final desktop EN**) only. Admin and other pages were not changed. The current one-demo-account flow and all existing business values, statuses, and prototype reactions were retained.

## Screens changed

| Screen | Figma node | Change |
| --- | --- | --- |
| Positions | `2504:609` | Added a concise page subtitle and `Market / status` / `Value / result` labels above the 19-row list. Header `2710:137353` is inserted as the first child of auto-layout list `2504:765`; rows move down automatically by 32 px. |
| Orders | `2504:902` | Added a subtitle and replaced the visible `Partial-fill learning example` fixture label with `BTC above $80k · Buy` (`2504:1148`). Fill and reserve amounts remain unchanged. |
| Funds | `2504:2302` | Added a subtitle clarifying virtual demo funds and future venue accounts. |
| Copy settings | `2504:5521` | Added a subtitle. Moved existing Review settings action `2504:5551` beneath the right-hand settings summary at x=1000, y=398, 408×48. Its prototype reaction remains attached. |
| My requests | `2504:3127` | Added a subtitle. Eight records now have distinct, readable topics and contexts instead of repeated subjects and `ticket-##` / `event-###`. The eight topics match desktop RU by meaning and order: demo balance, uncertain copied-buy outcome, open positions, partial fill, reserved funds, result update, closed-position history, cancellation of the unfilled amount. Existing workflow statuses and row reactions remain. |
| Notification history | `2504:2840` | Removed 20 visible `notification-##` identifiers; the read/unread status and event dates remain. Added a subtitle. |
| Activity, demo account history, Help, Profile, support form and detail views | `2504:1444`, `2504:2405`, `2504:3286`, `2504:3574`, `2504:3663`, `2504:3703`, `2504:3741`, `2504:3828`, `2504:3898`, `2504:3955`, `2504:4016` | Filled empty header subtitles with context for each task. |
| Filtered list screens | Positions `2504:756`, Orders `2504:1137`, Activity `2504:1798`, demo history `2504:2599`, notifications `2504:2978`, requests `2504:3220`, Markets `2504:7481` | Set the visible `All` filter to the existing Primary button variant, making the current filter explicit. Each retains one prototype reaction. |

## Verification and limits

- Reviewed screenshots of Positions, Orders, Funds, Copy settings, My requests, Help, support form, position detail, notifications and simulation states. The edited screens show no text overlap or clipped controls at their 1440 px design width.
- Structural scan of 75 visible EN Final desktop screens found 3,010 visible text nodes, no remaining visible `ticket-##`, `event-###`, `notification-##` or `Partial-fill learning example` labels, and no missing fonts.
- The `Review settings` button was repositioned within the existing screen, rather than reparented into the right-column auto-layout. Its position is correct for the fixed 1440 px Final frame; implementation should place the action in layout flow for responsiveness.
- A full manual click-through of every prototype path was not repeated in this pass. Existing reactions were kept on changed interactive nodes; the new column labels are non-interactive.
