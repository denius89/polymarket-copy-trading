# Admin Apps Components · v0.4.1

Updated 12.10.2026. Design only. Native editable Figma component sets, variants and instances; no application implementation.

[Open the showcase](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2082-125).
Existing page: `1981:2`; showcase: `2082:125`, 1600 × 3318. Construction masters remain outside the review frame. No new file, branch or page was created.

## Inventory

| Family | Variants | Configurable content |
| --- | ---: | --- |
| Primary / Secondary / Quiet / Danger buttons | 24 | Label, Loading label, Icon, Show icon |
| Form field: Input / Select / Search / Amount / Address | 30 | Label, Value, Hint |
| Navigation item | 6 | Label, Icon |
| Status pill | 6 | Label, Tone |
| Chip: Choice / Filter / Tag / Count | 8 | Label, Selected; filter Show clear, Clear icon |
| Checkbox / Radio / Switch | 18 | Label, Checked, State |
| Segmented filter | 3 | All label, Active label, Pending label, Selected |
| Alert | 4 | Title, Body, Tone |
| Table row | 3 | ID, Venue, Amount |
| Confirmation | 2 | Standard: Title, Body, Hint; Money: Money title, Money body, Money hint |
| **Total** | **104** | **15 component sets** |

The exact component/property/variant IDs and scoped binding evidence are in [apps-components.json](apps-components.json). Existing metric composition is also shown, outside the 104-variant count.

## State contract

Buttons: Default, Hover, Focus, Pressed, Loading, Disabled. Height 44 px; hug label and icon; minimum width 96 px. Only one Primary per action group. Loading keeps a spinner and exposes a separate localized Loading label; it hides the action icon. Loading and Disabled must not submit in the eventual implementation.

Fields: Default, Focus, Filled, Error, Disabled, ReadOnly. Source control height and minimum height are 48 px; counter axis is fixed. Do not switch the control to vertical Hug when arranging specimens. Text, placeholder and helper/error content must be explicitly configured on each instance. Filled is a specimen state, not proof of saved data. Error requires readable text, not color alone. ReadOnly remains readable; Disabled cannot edit. Search and select retain icon/text spacing.

Navigation: Default, Selected, Hover, Focus, GroupOpen, Disabled. Selected means current route; GroupOpen only expands a group. Disabled has no destination. Controls: Checked False/True × Default/Focus/Disabled. Segmented: All/Active/Pending; labels are localizable.

Status semantics: Success = confirmed; Warning = pending or unknown; Danger = error; Neutral = inactive; Brand = VIP; Info = checking/information. Tone changes the visual treatment, not the text or business status automatically. Set Label explicitly to match the actual state. The showcase includes correct examples.

Choice chips select; filter chips clear through the trailing close affordance; Tag and Count are informational. Selected on Tag/Count is a presentation variant, not an implied interaction. Show clear applies only to filter variants.

## Admin constraints

Money confirmation must show venue, asset, verified network/route, full recipient address, amount, transfer fee and who pays the fee. Monetary and destructive actions always retain text labels. Confirmation action is “Выплатить”, not a generic save.

Owner-only execution and the agreed full available payout rule remain in the domain specification. Unknown result blocks another send until reconciliation. UI states do not establish API confirmation, transaction success or permission enforcement. The network, 125.00 USDT amount, 0.50 USDT fee and address in the review specimen are synthetic; they are not a verified provider route or a production payment.

Address fields use 8 columns in real forms and may wrap. Never substitute the abbreviated showcase field value for the full address in a payout confirmation.

## Foundations and adoption

Reuse existing Color, Spacing, Radius and Inter text styles. Dark mode is pinned for the review board. No new token collection was created; fill, stroke, radius and spacing bindings reuse shared semantics. Icons remain instances with swap properties where applicable.

Existing field and navigation component sets were expanded in place; their original Default/Selected IDs are preserved. Existing button masters `113:207`, `113:209`, `113:211` and their screen instances remain. New button state sets are for incremental adoption in future admin screens; this update does not claim migration of all 184 screens.

Use the same base component with content overrides for RU/EN. Do not detach instances to translate them. Before merging with the client kit, compare property APIs and token bindings; record exact old→new IDs and retain prototypes/overrides. The client merge is pending.

## Validation

The final review frame has no visible child bounds overflow, no IMAGE fills and no text without a shared style. The complete board and corrected confirmation/filter panels were visually reviewed. Native editable objects were preserved.

Hover/focus/pressed/loading are design variants. This deliverable does not implement component interactions, spinner animation, keyboard behavior, API enforcement, responsive layouts or a fully integrated table system. Those are separate design/prototype or development work.

## Screenshot defect correction · 12.10.2026

Reviewed the reported collapsed search fields and confirmation cards at 1x. Current specimens have fixed-height fields and transparent action rows. Added a durable minimum control height of 48 px to all 30 field variants. Standard and Money now have distinct text-property bindings/defaults, so changing Standard defaults cannot silently replace monetary headings or notices. Configure the separate Money properties when translating or placing that variant. The money specimen sizes vertically to content; the demo metric is localized to Russian. Existing IDs are retained. Final review frame bounds check passed without overflow.
