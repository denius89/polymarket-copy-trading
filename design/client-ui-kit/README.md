# Shadow client UI kit

Native source: [Figma Foundations](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=1977-2).

- [Development handoff](HANDOFF.md): source precedence, synchronization and checks before implementation.
- [Usage](USAGE.md): component instances, locale overrides and semantic boundaries.
- [Manifest](manifest.json): 1 page / 4 sections; original build 44 native families / 118 variants, now 45 / 136 after the content-width button addition; 9 reused families / 46 variants.
- [Tokens](tokens.json) and [CSS](tokens.css): 72 visual variables and 21 shared text styles. CSS is a design export, not application implementation.
- [QA](qa.json): structural and visual checks, corrections and acceptance limits.
- [Project report](../../docs/121_client_ui_kit_2026-10-12.md): scope and Figma links.
- [Client grid and button-width handoff](grid-and-button-width.json) and [review](../../docs/124_client_grid_button_width_handoff_2026-10-12.md): the current client-only sizing rules, Figma IDs and verification limits. These additions postdate the original manifest counts.

Native component definitions remain in Figma. Git stores the registry, design tokens, usage guidance and construction provenance. No .fig binary export or portable Figma restore is claimed. Construction scripts are historical records, not idempotent rebuild tools.

Current organization: **07 · Client UI kit** (page `1976:2`) contains four core sections (Foundations, Controls, Data, Patterns). Linked product-source masters (`2152:528`) live on **98 · Источники и архив компонентов** (page `2:79`), separate from five legacy archive nodes. Source and component IDs and instance links remain unchanged. The three former empty kit pages were removed; component and review-board IDs remain unchanged. Manifest `originalPage` records are historical provenance.
