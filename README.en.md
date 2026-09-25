# Controlled Copy Trading

[Русский](README.md) · **English**

Controlled Copy Trading is a mobile-first product concept for controlled copy trading on prediction markets. A user will be able to choose a trader, test whether that trader's activity can be reproduced with a specific budget, set clear limits, and understand why every action was executed, adjusted, or skipped.

The target product includes both **Polymarket** and **Limitless** as required venues. The service is being designed as an independent control layer: it will not accept customer payments, hold customer funds, or promise to reproduce a trader's results.

> **Current status: pre-MVP.** The team is defining the product, interfaces, economics, and architecture. The user application, trading integrations, and live trading are not available yet. This repository documents decisions, hypotheses, and the development plan; it is not documentation for a finished service.

## Why this product

Copying a trade only looks simple before execution. A follower may have a different budget, price, delay, liquidity, and available position size. The result can differ substantially from the trader's history, while existing tools often fail to explain why.

The project is built around five principles:

- **Test before live trading.** A backtest and a 72-hour shadow mode should show which trades can be reproduced with the selected budget.
- **Risk expressed in clear amounts.** Users set a budget per trader, a daily limit for new buys, a maximum trade size, and a free reserve.
- **Explainable actions.** Every execution, partial fill, skip, delay, and stop receives a human-readable reason.
- **Control after entry.** The planned controls include pause, manual close, detaching a position from a trader, and a global stop.
- **Transparent cost.** Fees are shown before activation and for every successfully executed automated action. Manual and protective closes carry no service fee.

Historical performance does not guarantee future results. The planned ranking describes history and copyability for a given budget; it is not an investment recommendation.

## Two required venues

| Venue | Role in the project | Status |
|---|---|---|
| **Polymarket** | a well-known prediction-market venue and an important audience entry point | public data and access options have been researched; the project has not yet validated its trading path |
| **Limitless** | a partner venue and the first candidate for integration experiments | documentation and the Programmatic API have been researched; partner capabilities and the live path remain unvalidated |

The shared product layer is planned to remain venue-neutral. Each venue requires its own validation of access, fees, GEO restrictions, trading permissions, recovery, and withdrawal. Live mode can only be enabled after the relevant venue passes those checks.

## Safety by design

Safe behavior is a core product requirement:

- the user retains control of the wallet and withdrawals;
- neither the service nor a partner receives the seed phrase;
- trading permission must not grant withdrawal rights;
- live execution is disabled by default;
- an unknown order state blocks conflicting actions until reconciliation;
- limits stop new risk while allowing safe position reduction;
- critical incidents and stops cannot be fully hidden through notification settings;
- each venue's GEO restrictions are enforced independently;
- guaranteed-profit claims and incentives for unnecessary turnover are excluded.

See [docs/13_trust_permissions_and_state_model.md](docs/13_trust_permissions_and_state_model.md) for the trust and state model.

## Planned product surfaces

### User application

A standalone mobile-first web app for people without experience using complex trading terminals. The primary journey is: understand the product → choose a trader or add an address → test copyability → set a budget and limits → monitor positions and the activity log → pause copying or close a position.

### Operations console

A minimal internal console for monitoring service state, handling exceptions, managing versioned fee settings, and recording sensitive actions in an audit log. The console is not intended to provide manual trading on behalf of users.

### Partner tools

The referral model is being considered as a distribution channel after the core user journey. A partner dashboard and agent operations are outside the interface MVP.

The source requirements are documented in the [UX audit and user journey](docs/06_ux_audit_and_user_flow.md) and the [trust and state model](docs/13_trust_permissions_and_state_model.md).

## Languages

The first frontend is planned with a multilingual foundation and a manual language selector. Text, numbers, dates, currencies, and event reasons must support localization; layouts will account for longer translations and RTL languages from the start.

Most project documentation is currently written in Russian. This overview is available in [Russian](README.md) and [English](README.en.md). The first product stage supports English and Russian; additional languages will be selected after the priority GEOs are chosen.

## Contributor quick start

1. Read the [current project state](docs/PROJECT_STATE.md).
2. Use the [documentation map](docs/README.md) to find the source of truth for your area.
3. Review the [current roadmap](docs/ROADMAP.md) and active [architecture decisions](docs/decisions/README.md).
4. Read the [contribution guide](CONTRIBUTING.md) and [security policy](SECURITY.md) before making changes.
5. Define one verifiable outcome, state its dependencies, and do not present a hypothesis as an accepted decision.
6. Run the repository check before submitting changes.

Node.js 22 or newer is required:

```bash
npm run check
```

The check verifies that key documents exist and that Markdown relative links are valid. Application code has not been created yet; `apps/`, `packages/`, and `infra/` currently describe future project boundaries.

## Key materials

- [Product and economics](docs/01_product_and_economics.md)
- [UX audit and user journey](docs/06_ux_audit_and_user_flow.md)
- [Target audience and personas](docs/15_target_audience_and_personas.md)
- [Positioning without profit promises](docs/18_first_validation_positioning.md)
- [Bilingual product language foundation](docs/29_bilingual_product_language.md)
- [Binance Copy Trading benchmark](docs/30_binance_copy_trading_ui_benchmark.md)
- [Dual-venue adapter contract](docs/23_dual_venue_adapter_contract.md)
- [Trust, permissions, and state model](docs/13_trust_permissions_and_state_model.md)
- [Full documentation map](docs/README.md)

## Presentation

Current concept deck: [Controlled Copy Trading Project RU v5](artifacts/Controlled_Copy_Trading_Project_RU_v5.pptx).

It reflects the current product hypothesis, both required venues, and separate gates for live execution. All economic scenarios in the deck are working assumptions, not forecasts or promises of returns.

## Repository structure

```text
apps/                   future user applications and background processes
packages/               future domain logic and venue adapters
docs/                   product, economics, UX, architecture, and decisions
docs/decisions/         accepted and proposed ADRs
research/               scoped research tasks
artifacts/              presentations and finished materials
infra/                  future infrastructure
scripts/                repository integrity checks
```

This repository has not been declared open source and does not include a license. External participation is coordinated with the project owner.
