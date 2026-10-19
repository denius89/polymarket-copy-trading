# Independent reference-ledger validation — 2026-10-18

**Result: controlled accounting checks pass. This is not a historical return, statistical score validation, venue execution certification, or approval to publish a score.**

## Evidence and reproduction

Run from repository root:

```bash
python3 research/trader-score-reference-2026-10-18/independent_reference_check.py
```

Observed result: **1,125 assertions passed, 0 failed**, covering all **23 events** in `reference-output.json` and **25 independently constructed adversarial cases**. The assertion count includes repeated conservation checks; it is not 1,125 independent scenarios or a statistical sample size. The primary run has no incidents. Adversarial invalid inputs deliberately produce quarantine incidents and are checked against their expected unchanged economic state.

The checker invokes `reference_replay.py` as a separate process with temporary fixture files. It does not import the engine to calculate expected values. It compares decimal values exactly, without floating-point tolerances.

Frozen manual expected ledger, before reading the first engine output:

- `expected-ledger.json`: `42bf8af63b97d8e81e6c6898f71095c1d4b408b285f3a8d97b82c9cb5c8c5974`

Reviewed artifacts at the passing run:

| Artifact | SHA-256 |
|---|---|
| `reference_replay.py` | `d971a833e3bcecc0ff8f9049ba397cffaf7dd1e2f139b0c90532caabd75452da` |
| `market_data.py` | `7c61a6db5c990d0a997d89e1b9c106fe2338598e72f5aedf1a55e58d106a8fe1` |
| `copier-standard.json` | `c3eeec577f26bf8a40b309e2de370674603a2e25c889aa1a57b4f31c1622d17a` |
| `reference-output.json` | `e3e2e12e77bcf147b779da191e1a11c442576d8fcd67c423930ef667ff26c752` |

The first-output artifact is preserved. A changed engine, fixture, market-data helper or passport needs a new versioned output and review; passing this report does not transfer automatically to another hash.

## Independence and scope

A separate evaluator calculated the primary ledger using manual arithmetic before reading the engine or its output. During fixture coordination the engine author also sent proposed endpoint amounts; the evaluator saw them. Accordingly this is **independent implementation and open engineering review, not a blind holdout**. The adversarial scenarios were then constructed by the evaluator after reading the implementation. They are open regression tests, not evidence of model generalization.

The expected known-valuation label is normalized from the engine's stricter `known_under_controlled_fixture` label to the oracle's `known`. No economic expectation was changed after inspecting actual output. The pre-output oracle hash is enforced by the checker.

Skills used: project market-domain (S03), copy-replay (S12), product-QA (S23) and AI-quality (S10), with the supplied scope and ADR0015–0028. The test evaluates the restricted reference implementation; it does not certify all those ADRs as implemented.

## Manually derived checkpoints

All figures below are synthetic fixture units, with $200 opening cash, no initial lots and no external cashflows. The $0.10 fee reserve and $0.05 terminal fee are explicit test assumptions, **not Polymarket tariffs**.

| Checkpoint | Cash | Cash reserved | Available | Tracked quantity / purchase cost |
|---|---:|---:|---:|---|
| BUY $5 admitted | 200.00 | 5.10 | 194.90 | 0 / 0 |
| First $2 fill, cancellation requested | 198.00 | 3.10 | 194.90 | A: 4 / 2.00 |
| Second $1 confirmed fill | 197.00 | 2.10 | 194.90 | A: 6 / 3.00 |
| Residual cancellation and $0.05 fee confirmed | 196.95 | 0 | 196.95 | A: 6 / 3.00 |
| Sell 25% of tracked shares, $0.90 proceeds, before terminal fee | 197.85 | 0.10 | 197.75 | A: 4.5 / 2.25 |
| SELL terminal confirmation | 197.80 | 0 | 197.80 | A: 4.5 / 2.25 |
| B $5 full fill, before terminal fee | 192.80 | 0.10 | 192.70 | A: 4.5 / 2.25; B: 10 / 5.00 |
| B terminal confirmation | 192.75 | 0 | 192.75 | Same lots |
| Known B settlement at $1/share | 202.75 | 0 | 202.75 | A: 4.5 / 2.25; B: 0 / 0 |

The late second A fill was executed before local midnight and received after it. Previous-day confirmed gross becomes $3; current-day confirmed gross stays $0 while pending gross falls from $3 to $2. A different test moves execution after midnight: previous-day gross stays $2, current-day gross becomes $1. Pending reservations carry across midnight in both cases.

Missing B liquidation data yields **unknown equity and PnL**, not zero. After the explicit B settlement, the known fixture A bid gives $4.5 × 0.60 − 0.05 = $2.65 liquidation value. Equity is $205.40 and PnL is $5.40. These are arithmetic results from constructed confirmations and books, not investment performance. A future-known resolution is rejected before its knowledge timestamp.

## Adversarial cases passed

1. Four repeated $5 buys reach the same-token $20 cost cap; the fifth is skipped wholly. Cash is $179.80 after four terminal $0.05 fees.
2. Four unresolved same-token intents reserve $20.40; a fifth is skipped, with no synthetic fills.
3. Six $5 buys across tokens consume the $30 daily gross limit; fees do not consume that gross limit. A seventh is skipped. Cash is $169.70.
4. An unknown order and a cancellation request retain $5.10 across midnight.
5. A nonterminal full gross fill retains the $0.10 fee bound.
6–7. Identical fill redeliveries before and after terminal confirmation do not debit again.
8. A changed payload under the same ID makes no second economic mutation, blocks new risk, and still permits valid terminal reconciliation.
9–14. Missing fee, missing price bound, future book, stale source time, ambiguous exact-time book and empty depth each create no order, fill or reserve.
15. A confirmed full remainder during the cancellation race is retained; complete execution plus terminal fee yields the same $194.95 cash and 10 shares.
16–20. Overfill, future execution, pre-intent execution, inconsistent quantity/price/gross and a price-cap breach are quarantined atomically with the initial reserve held.
21. A terminal cumulative-fill mismatch cannot release the remainder or charge fees.
22. Missing terminal fee evidence retains the fee reserve after full gross execution.
23. Late receipt with execution in the new local day is charged to that new day.
24. Europe/Warsaw autumn repeated hour does not reset the day; the 25-hour day resets at the actual next midnight. The primary trace separately checks the spring 23-hour reset.
25. A SELL with unknown leader inventory creates no guessed position reduction or fee reserve.

Each trace also checks available cash equals cash minus reserves, gross plus expense reserve components, daily gross bookkeeping and nonnegative balances, and sums of per-lot quantity and purchase cost.

## Passport review and boundaries

`copier-standard.json` correctly separates the frozen research standard from production risk acceptance; declares historical 30-day outcomes as zero; labels quantum and fee assumptions as controlled; uses remaining tracked purchase cost plus pending gross for the position cap; and keeps unknown pre-intent data from creating a reservation. The owner's approval of this research standard does not set an acceptable loss probability, minimum model improvement or permission to publish.

**Additional real-data gate:** external deposits, withdrawals, transfers, opening inventory and relevant fees must be known and reconciled for a wallet-wealth result, or proven outside the specific virtual-account estimand. Missing cashflow records are unknown, never automatically zero. A synthetic no-external-cashflow opening does not establish the starting state of a real wallet. This clarification is recorded here without mutating the frozen passport.

Not exercised or not implemented by this review:

- Real venue authentication, signing, order placement, network concurrency, crashes, retries, transaction isolation, durable idempotency and reconciliation against actual venue records.
- Authoritative economic signal identity across different IDs, same-time event order without producer sequencing, reorganizations, revisions, malicious producer evidence or authenticated settlement provenance. Fixture evidence labels are assertions in controlled input.
- Native venue quantum discovery, fee schedules, fees charged in tokens or another asset, fee rounding integration, rebates, variable fees, platform/version migration, actual slippage or execution latency distributions.
- Manual/detached lots, multiple traders/sessions, percentage sizing, detached/residual policy, queued sells while buys remain unresolved, extreme proportional-allocation rounding and very large histories. A single proportional sell and per-lot sums are checked; the full product lot lifecycle is not.
- Every possible fee/budget boundary, malformed external schema and clock conflict. Covered malformed-confirmation cases are listed above; helper-specific coverage is documented separately by its owner.
- Historical full-book continuity, hidden liquidity, queue priority, depth consumption by competing users, actual fills, real settlement completeness or cashflows.
- Terminal marks for the target 30-day horizon, independent temporal/group holdouts, model calibration, comparison against baselines, acceptable-loss thresholds or user-facing score readiness.

**Release conclusion:** suitable as a bounded engineering regression reference at the listed hashes. Real-data qualification and score/model comparison remain blocked until their separate evidence gates are met. No production score or live financial action was performed.
