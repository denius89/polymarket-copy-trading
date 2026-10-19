# Controlled Copy Trading

[Русский](README.md) · **English**

[![Repository check](https://github.com/denius89/polymarket-copy-trading/actions/workflows/repository-check.yml/badge.svg)](https://github.com/denius89/polymarket-copy-trading/actions/workflows/repository-check.yml)

A mobile-first product for controlled copy trading on **Polymarket** and **Limitless**: choose a trader, try a virtual-money demo, set clear limits, and understand each action.

**Status on 19 October 2026: design and documentation, pre-MVP.** Client and admin RU/EN designs are prepared and remain under review. The user application, trading adapters, and real transactions are not implemented. Follow [ROADMAP](docs/ROADMAP.md) for the current queue and each handoff for verification limits.

Current Final anchors, manual settings, and desktop introduction: [client sitemap](docs/design/client/sitemap.md). [Landing v2](docs/design/landing/hero-2026-10-19/v2/README.md) is awaiting review. [ADR-0048](docs/decisions/0048_unified_registration_and_first_entry.md) records the agreed first entry, with prototype alignment still open. The links and images below retain the original 6 October snapshot.

## Open a prototype

**[Start here in Figma →](https://www.figma.com/design/lxPP2um7FvIbt02K8eeH4T?node-id=3-2)** — one entry point for every version.

| Version | Russian | English |
| --- | --- | --- |
| Mobile | [Mobile RU](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1839-57824&starting-point-node-id=1839%3A57824&page-id=33%3A2&scaling=scale-down) | [Mobile EN](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=1839-57862&starting-point-node-id=1839%3A57862&page-id=29%3A2&scaling=scale-down) |
| Desktop | [Desktop RU](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=584-265&starting-point-node-id=584%3A265&page-id=205%3A2&scaling=scale-down) | [Desktop EN](https://www.figma.com/proto/lxPP2um7FvIbt02K8eeH4T?node-id=584-225&starting-point-node-id=584%3A225&page-id=186%3A2&scaling=scale-down) |

Each entry offers a **first launch** and a separate **prepared active demo**. Use Restart to change scenarios. The mobile first-launch path is introduction → choose a trader → copy size and limits → review → start → an empty home screen.

Recent corrections include consistent headers and bottom navigation, restored trader selection, explicit PnL labels, a general support question, short venue account names, and profile titles without a repeated period. [Latest results and review route — 109 (RU)](docs/109_latest_design_review_2026-10-06.md).

Images and links for the latest corrections have been checked. **A new manual Present walkthrough has not yet been completed:** browser access was blocked by policy. Walkthroughs in [report 106 (RU)](docs/106_four_prototypes_acceptance_2026-10-06.md) refer to the previous version; final visual acceptance remains open.

## Current preview

Figma layouts captured on 6 October 2026. The data is illustrative; these are not screenshots of a working trading application.

<table>
<tr><th>New demo</th><th>Trader profile</th></tr>
<tr>
<td><img src="docs/preview/2026-10-06/fresh-home-ru.png" width="260" alt="New demo: shared header, budget, and empty history"></td>
<td><img src="docs/preview/2026-10-06/trader-profile-ru.png" width="260" alt="Trader profile: selected period and performance"></td>
</tr>
</table>

The preview uses Russian screens; English prototypes are linked above.

## Find the right material

| Task | Material |
| --- | --- |
| Review the latest interfaces with a colleague | [Latest result and review route](docs/109_latest_design_review_2026-10-06.md) |
| Understand the current queue | [Roadmap](docs/ROADMAP.md) |
| Read accepted rules and open questions | [MVP business logic](docs/MVP_BUSINESS_LOGIC.md) · [ADRs](docs/decisions/README.md) |
| Find documents by topic | [Documentation map](docs/README.md) |
| Read decisions and project history | [Project state](docs/PROJECT_STATE.md) · [Full document index](docs/DOCUMENT_INDEX.md) |
| Understand GitHub organization | [Cleanup result and PR status](docs/REPOSITORY_MAINTENANCE_2026-10-19.md) |

If an old report disagrees with the current state, use ROADMAP for the work queue, the latest report for interfaces, and MVP_BUSINESS_LOGIC plus ADRs for rules. A document number or the word “current” in an old entry does not make it today's status.

## Venue APIs

| Venue | Reference | Status |
| --- | --- | --- |
| Polymarket | [Reference](docs/api/polymarket/README.md) | Evidence dated 6 October 2026; see documented limits |
| Limitless | [Reference](docs/api/limitless/README.md) | Evidence dated 6 October 2026; see documented limits |

These references document official APIs and evidence from public reads on 6 October 2026. Partner permissions, execution, account-specific fees, and trading connection recovery require separate validation. A reference and a passing Markdown check do not constitute a working integration.

## Repository layout and checks

```text
docs/               current navigation, product documents, and history
docs/decisions/     accepted and proposed ADRs
docs/preview/       current overview images
design/            Figma materials and evidence from earlier checks
apps/, packages/   boundaries for the future application and adapters
research/          research
artifacts/         presentations and other materials
scripts/           structure and link checks
```

Use Node.js 22 or later:

```bash
npm run check
git diff --check
```

These check the repository; they do not launch an application. Contribution guidance: [CONTRIBUTING](CONTRIBUTING.md), [SECURITY](SECURITY.md), [AGENTS](AGENTS.md). Presentations and earlier concepts are in [artifacts](artifacts/README.md); they do not replace the current status or prototypes.
