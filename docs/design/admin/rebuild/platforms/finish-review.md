## verdict

**SHIP for the bounded synthetic HTML addition reviewed here.** Independent finish review · 25 October 2026. All listed source findings are resolved. The six supplied desktop/mobile captures show no blocking overlap, clipped form value or inaccessible-looking primary action in the inspected states. This disposition does not certify native Figma, deployment, physical devices or production behavior.

### Scored fixes

| Finding | Result | Evidence |
| --- | --- | --- |
| Rating minimum-days field lost initial/retained value | Resolved | Correct `rating-days` key with draft/current fallback; regression covers 30 initially and retained 45 in EN. |
| Auditor could run comparison | Resolved | Both button and handler require draft authority; auditor read-only regression passes. |
| Completion of an old command discarded a newer draft | Resolved | Completion clears only its matching draft. Collector regression preserves newer 12-minute draft and rejects its stale revision. Reviewer also checked validator and rating variants in the prior bounded pass. |
| Connections summary contradicted confirmed catalog | Resolved | Eligibility is derived from the confirmed catalog version; R-2 excludes C. Validator now names the methodology version used for its independent result. |
| Restore retained stale raw form fields | Resolved | Explicit restore clears the rating raw form. Regression verifies restored 20 actions, and `rating-restore-ru-desktop.png` visibly shows 20 while current method/history remain R-2. |
| Retained diagnostic/error/notice text after language change | Resolved in inspected source | Messages retain RU/EN pairs and render for the current locale. Error regression passes. This is source evidence, not a separate screenshot of every English state. |
| Failed catalog calculation had no distinct recovery | Resolved | Confirmed failure/conflict can start a new calculation attempt without a new methodology version. Unknown cannot restart, old catalog remains, owner/technical-mode gates remain. |

### Verification

`node docs/design/admin/rebuild/prototype/check-platforms.cjs` passes **155 assertions** in this final pass. Source review confirms immutable submitted source/payload, no duplicate command while pending/unknown, one-time application, owner-only numerical application, versioned restoration, confirmed whole-catalog switch, and null rather than zero for unknown/insufficient rating data. These are synthetic runtime checks, not server authorization or API tests.

Inspected images in `evidence/`:

- `connections-ru-desktop.png`: connection readiness and rating-data status are separate columns; Limitless absence is not rendered as zero coverage.
- `rating-comparison-ru-desktop.png`: current versus draft outcomes distinguish C's prior score from insufficient data; unknown D is not given a score.
- `rating-restore-ru-desktop.png`: restored field values, preserved R-1/R-2 history and confirmed catalog state are legible.
- `connections-ru-390.png`: menu is collapsed; tabs/table use bounded horizontal scrolling, with visible scrollbars. The black space beside the 390px preview belongs to the review harness.
- `collector-unknown-ru-390.png` and `collector-unknown-ru-320.png`: form, saved draft, unknown command and next reconciliation action remain legible. Long labels wrap without overlapping their controls. The existing active P-1 and unsent draft are visibly distinct.

No additional visual blocker was found in these supplied states. Buttons beneath the form are visually close together, but their labels and boundaries remain distinct; this does not reopen the approved layout in this bounded verdict.

### Boundaries

Authority: `platforms/brief.md`, ADR-0044/0046 and `package-09/data-rating-contract.md`. The original four findings plus the restore follow-up are closed by the scoped checks above. No implementation or Git edits were made by this reviewer; only this report was updated.

Native Figma is being checked separately by the build agent and is **not certified here**. The mobile evidence is browser-width evidence, not physical-device testing. Public deployment, full role journey acceptance, final handoff completeness, real API capabilities, backend concurrency and production commands are outside this verdict. Numerical/source examples remain explicitly synthetic.
