# Final mobile EN — product polish (15 October 2026)

Scope: Figma file `lxPP2um7FvIbt02K8eeH4T`, Final mobile EN page `2499:2`. Admin and other Figma pages were not edited. The approved Home and trader catalogue were left as they were.

## Changes

| Area | Screen / node | Result |
| --- | --- | --- |
| Positions | `2502:17587` | Six filter actions remain in two rows, now 36 px high with an 8 px inter-row gap. Replaced the fixed-height 48 px instances with token-matched auto-layout chips because resizing instances clipped them. Each chip retains its original `ON_CLICK` variable actions. New chips start at `2710:137317`. |
| Tickets | `2502:18359` | Three status filters now use the same compact chip treatment. Eight ticket cards have distinct readable topics/statuses and contextual records, without `ticket-##` or `event-###` in the visible copy. Their `SET_VARIABLE` title, status, context, description and displayed request number were updated to match the cards; navigation targets and other actions were preserved. |
| Help | `2502:18417` | Three category filters now use 36 px chips; the two rows and results list no longer collide. |
| Notifications | `2502:18291` | Removed `notification-##` from 20 visible cards. Read/unread state, event title, timestamp and actions remain. |
| Risk | `2502:21163`, `2502:21221` | Removed internal decision language from global and trader-specific rule explanations. Compressed the global form so `Save global rules` ends at content y=656 within the 672 px scroll viewport, above bottom navigation. |
| Support forms | `2502:18700`, `2528:4889` | Message fields use the existing input surface and border tokens, making the message area recognizable as a form field. |
| Empty states | `2502:21035`, `2502:21080`, `2502:21317` | Cards say “No positions yet”, “No activity yet” and “No orders yet” instead of repeating the page heading. |
| Conversation | `2502:19695` | Replaced the debug-like `Conversation D-01` heading with “Support conversation”. |
| Default filter state | `2710:137317`, `2710:137335`, `2710:137344`, `2502:18331`, `2502:17708`, `2502:17805`, `2502:18017`, `2502:20223` | The active All / All answers filter has the existing selected navigation's soft purple fill, purple border and lavender label across Positions, Tickets, Help, Notifications, Orders, Activity, Operations and Markets. All eight original reactions remain. |

The copy setup and review screens (`2502:19857`, `2502:19957`), email entry/error forms, feedback form, and selected empty/fresh screens were visually reviewed. Their existing hierarchy and actions were retained because no comparable issue was found.

## Verification and limits

- Re-rendered Positions, Tickets, Help, Notifications, support forms, risk rules, empty states, and conversation after editing. No visible clipping or overlap remains in these inspected states.
- All 12 new compact chips are 36 px high, have exactly one label and at least one reaction. Ticket card titles equal the titles assigned by their detail-navigation variable actions.
- A scan of visible EN text found no remaining internal `word-##` identifiers after these changes.
- The checked Positions, Tickets, Help, Notifications and global-risk prototype actions have no missing node destinations.
- Screenshots of Positions, Tickets, Help and Notifications were rechecked after the color change; the same token-bound style was applied to the other four list screens and all eight reactions were retained.
- This is a design and Figma-prototype check. It does not replace a complete interactive Present walkthrough or implementation testing in the web client.

