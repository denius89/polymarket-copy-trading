# Focused UI surface and onboarding implementation · 04.10.2026

Implemented only the approved surface/copy subset of audit 81. Existing Inter fonts, shared component instances, colours, and financial content retained.

- 527 whole-screen FRAME roots checked across mobile RU/EN and desktop RU/EN. Canvas token `VariableID:2:28` resolves to RGB(11,13,20). 128 initial candidates had missing canvas bindings or incorrect fallback colours (57 mobile RU, 22 mobile EN, 27 desktop RU, 22 desktop EN). Root paints were normalized; final read-back has zero mismatches. Transparent overlay roots were excluded. No global variable values or component masters changed.
- Four duplicated onboarding card titles hidden; one visible page heading remains per locale/device. RU/EN desktop headers read «Как работает shadow» / «How shadow works».
- Existing RU desktop primary CTA moved below the explanation in the left reading area, matching EN desktop's role and position. Existing instance `955:3833` remains, 240×48, and its catalogue navigation reaction is unchanged. Mobile CTAs remain 350×48.
- Desktop RU Help's QA category button `909:11820` («Нет совпадений») hidden. Its underlying empty-result state and search/sort/filter states were not deleted. EN desktop had no equivalent visible QA category control.

Evidence: `ui-copy-surface-evidence.json`, `ui-copy-surface-root-paints.figmascript.js`, native representative screenshots `ui-copy-surface-*.png`. Screenshots visually inspected for RU/EN mobile onboarding, EN desktop onboarding and RU desktop Help; RU desktop onboarding also inspected inline.

Limits: this is not a manual pass of every screen or Present combination. No archive, API, finance, period selector, search overlay, navigation, notification labels, header balance, or financial text colour edits performed in this subtask. These belong to other approved package owners.
