# Admin Apps Components · v0.4.5

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

Fields: Default, Focus, Filled, Error, Disabled, ReadOnly. Default control height and minimum height are 48 px. Regular fields keep a fixed counter axis; Address is an explicit exception: its control grows vertically to fit character-preserving wrapped text. Text, placeholder and helper/error content must be explicitly configured on each instance. Filled is a specimen state, not proof of saved data. Error requires readable text, not color alone. ReadOnly remains readable; Disabled cannot edit. Search and select retain icon/text spacing.

Navigation: Default, Selected, Hover, Focus, GroupOpen, Disabled. Selected means current route; GroupOpen only expands a group. Disabled has no destination. Controls: Checked False/True × Default/Focus/Disabled. Segmented: All/Active/Pending; labels are localizable.

Status semantics: Success = confirmed; Warning = pending or unknown; Danger = error; Neutral = inactive; Brand = VIP; Info = checking/information. Tone changes the visual treatment, not the text or business status automatically. Set Label explicitly to match the actual state. The showcase includes correct examples.

Choice chips select; filter chips clear through the trailing close affordance; Tag and Count are informational. Selected on Tag/Count is a presentation variant, not an implied interaction. Show clear applies only to filter variants.

## Admin constraints

Money confirmation must show venue, asset, verified network/route, full recipient address, amount, transfer fee and who pays the fee. Monetary and destructive actions always retain text labels. Confirmation action is “Выплатить”, not a generic save.

Owner-only execution and the agreed full available payout rule remain in the domain specification. Unknown result blocks another send until reconciliation. UI states do not establish API confirmation, transaction success or permission enforcement. The network, 125.00 USDT amount, 0.50 USDT fee and address in the review specimen are synthetic; they are not a verified provider route or a production payment.

Address fields use 8 columns in real forms and may wrap. Addresses must be fully visible in the showcase and the real interface. Never abbreviate an address in a field, read-only view, recipient detail or payout confirmation.

## Foundations and adoption

Reuse existing Color, Spacing, Radius and Inter text styles. Dark mode is pinned for the review board. No new token collection was created; fill, stroke, radius and spacing bindings reuse shared semantics. Icons remain instances with swap properties where applicable.

Existing field and navigation component sets were expanded in place; their original Default/Selected IDs are preserved. Existing button masters `113:207`, `113:209`, `113:211` and their screen instances remain. New button state sets are for incremental adoption in future admin screens; this update does not claim migration of all 184 screens.

Use the same base component with content overrides for RU/EN. Do not detach instances to translate them. Before merging with the client kit, compare property APIs and token bindings; record exact old→new IDs and retain prototypes/overrides. The client merge is pending.

## Validation

The final review frame has no visible child bounds overflow, no IMAGE fills and no text without a shared style. The complete board and corrected confirmation/filter panels were visually reviewed. Native editable objects were preserved.

Hover/focus/pressed/loading are design variants. This deliverable does not implement component interactions, spinner animation, keyboard behavior, API enforcement, responsive layouts or a fully integrated table system. Those are separate design/prototype or development work.

## Screenshot defect correction · 12.10.2026

Reviewed the reported collapsed search fields and confirmation cards at 1x. Current specimens have fixed-height fields and transparent action rows. Added a durable minimum control height of 48 px to all 30 field variants. Standard and Money now have distinct text-property bindings/defaults, so changing Standard defaults cannot silently replace monetary headings or notices. Configure the separate Money properties when translating or placing that variant. The money specimen sizes vertically to content; the demo metric is localized to Russian. Existing IDs are retained. Final review frame bounds check passed without overflow.

## Radio and segmented polish · 12.10.2026

Radio uses a 20px outlined circle and centered 8px accent dot. Focus uses a distinct 3px focus stroke; Disabled uses muted semantic colors. The label names the option independently of Checked (specimen: «Маршрут A»). This prevents a disabled/unselected option from misleadingly saying «Выбран маршрут».

Segmented defaults to 360×44 with 4px padding and gaps. All three segments share available width equally (114.667px at the default width), have a 36px height and centered labels. The selected segment uses a solid accent background and on-accent text. Keep the parent width fixed and its children in horizontal Fill; do not collapse each segment to its label width. Both rows were reviewed at 1x and passed bounds validation. Existing node IDs retained; no new variants, pages or tokens.

## Full address visibility · 12.10.2026

Removed the abbreviated filled address specimen. Filled and ReadOnly now show the complete synthetic 42-character address, preserving every character and wrapping it across lines when needed. Address controls have a 48px minimum and grow vertically; width must not cause ellipsis, masking or hidden overflow. RU and EN admin-page text scans found no address text containing ellipsis. Full address visibility is a required visual verification aid; it supplements automated route/address checks rather than proving authenticity on its own.

Пакет 03, ревизия 0.4.4: Label/Value/Hint в 30 Form field вариантах привязаны к одноимённым text-properties (90 привязок; 84 восстановлены). Использовать setProperties и instances. Полные адреса Filled/ReadOnly проверены после исправления. Источник Sidebar теперь содержит 13 пунктов. [QA](../package-03/qa.json).


## Metadata row и responsive alerts · 0.4.5

Admin/Metadata row (2137:26727) — отдельный read-only composition master, а не замена двухколоночного Data row. Title/Detail/Meta, три равных текстовых колонки при 1144 px, 16 px gap, 20 px боковые и 16 px вертикальные поля, minHeight 64. HEIGHT и переносы сохраняют все данные. Instance text задаётся через setProperties; не detach для RU/EN. 15 sets / 104 variants сохранены. Alert Title/Body в четырёх исходных вариантах используют Fill по ширине и HEIGHT; безопасно работают в широкой админке и 560 px форме входа. [Пакет 04](../package-04/README.md).

## Личный кабинет · 0.4.6

Добавлены `Admin/Account button` (Default/Hover/Focus, 44×44) и `Admin/Profile settings row` (Default/Hover/Focus/Disabled, Title/Detail, одна стрелка, перенос текста). 17 семейств / 111 вариантов. Новые source sets находятся в прежней секции «02 · Исходные компоненты»; [витрина экземпляров](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=2167-567) — в «03 · Композиции». Иконка заимствована из клиентского header, цветовые токены и Inter общие. Кнопка открывает личный профиль напрямую; язык выбирается в нём. Новый основной sidebar item не добавлен. [Пакет 05](../package-05/README.md).
