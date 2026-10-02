# Figma remediation, 02.10.2026

Scope: docs/57 plan, user mobile/desktop RU/EN; owner-finance separate proposed branch. Existing page and frame IDs retained. Sections reorganized into Current/Reference/Future without deleting frames. Source inventories and baseline route graphs captured before writes under /private/tmp/shadow-*; scripts in this directory are reproducible implementation helpers, not frontend or trading code.

Execution evidence is saved in final-review-evidence.json and docs/58_figma_implementation_and_review_2026-10-02.md. Do not infer completed checks from the existence of a helper. Runtime accessibility and trading capability checks remain separate.

## Provider limitations verified during execution

The Figma provider currently retains only two conditional blocks (IF and ELSE) per `CONDITIONAL` action. Sending three blocks silently drops the third stage on read-back; nested conditionals are rejected. `native-review-context.js` therefore emits **three flat, independent conditional actions** for `before`, `empty` and `active`. Each action has one equality condition and an empty ELSE. Read-back must show three actions with all three stage values and the expected destination IDs. Do not rerun an older helper that uses a single three-block conditional.

Variable bindings also need a real paint fallback. Binding a semantic COLOR alias to an all-black placeholder paint produced black generated states through this provider. Before applying a paint, resolve the semantic variable in the collection's default mode, follow `VARIABLE_ALIAS` links to a concrete RGB/RGBA value, and use that actual RGB as the paint's `color`; place alpha in paint `opacity`. Then attach the variable binding. A binding alone is not evidence of the rendered color: inspect a screenshot after applying it. Existing helpers with placeholder black fallbacks require this correction before generating further screens.
