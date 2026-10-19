"""Read-only mathematical audit; does not modify the frozen score experiment.

Run from repository root with PYTHONDONTWRITEBYTECODE=1. No venue/network calls.
All probabilities below are invented counterexamples, never estimated market risks.
"""
import hashlib
import json
import math
from pathlib import Path
import random
import runpy

ROOT = Path(__file__).resolve().parents[2]


def quantile(values, weights, alpha=.10):
    cumulative = 0.0
    for value, weight in sorted(zip(values, weights)):
        cumulative += weight
        if cumulative >= alpha:
            return value
    return max(values)


def ce2(values, weights=None):
    if min(values) <= 0:
        return -1.0
    weights = weights or [1 / len(values)] * len(values)
    return 1 / sum(w / x for w, x in zip(weights, values)) - 1


def main():
    results = {}
    # M01: rare adverse parameter state can be cut off by a posterior quantile.
    wealth = [1.10, .01]
    weights = [.95, .05]
    q = quantile([x - 1 for x in wealth], weights)
    integrated = ce2(wealth, weights)
    assert q > 0 > integrated
    results['posterior_quantile_vs_predictive_ce'] = {
        'q10_conditional_ce': q, 'posterior_predictive_ce': integrated,
        'not_market_estimates': True}

    # The same issue survives the minimum over individually assessed scenarios.
    posterior_weights = [.85, .05, .05, .05]
    scenario_ces = [[.10 if theta != bad else -.99 for theta in range(4)]
                    for bad in [1, 2, 3]]
    min_of_quantiles = min(quantile(v, posterior_weights) for v in scenario_ces)
    quantile_of_min = quantile([min(s[t] for s in scenario_ces) for t in range(4)],
                               posterior_weights)
    assert min_of_quantiles > 0 > quantile_of_min
    results['scenario_ordering'] = {'min_q10': min_of_quantiles,
                                    'q10_min': quantile_of_min}

    # M02: a random single copying user and a diversified five-slot account differ.
    # Five equally likely worlds; only the low slot rotates. Total wealth is fixed.
    basket_a = [[.5 if j == world else 1.125 for j in range(5)] for world in range(5)]
    basket_b = [[.99] * 5 for _ in range(5)]
    pooled_a = ce2([x for row in basket_a for x in row])
    pooled_b = ce2([x for row in basket_b for x in row])
    portfolio_a = ce2([sum(row) / 5 for row in basket_a])
    portfolio_b = ce2([sum(row) / 5 for row in basket_b])
    assert pooled_a < pooled_b and portfolio_a > portfolio_b
    results['estimand_ranking_reversal'] = {
        'single_slot_a': pooled_a, 'single_slot_b': pooled_b,
        'portfolio_a': portfolio_a, 'portfolio_b': portfolio_b}

    # M03: Dirichlet weights cannot add outcomes absent from its support.
    rng = random.Random(20261018)
    mus, ces = [], []
    for _ in range(2000):
        raw = [rng.expovariate(1) for _ in range(3)]
        p = [x / sum(raw) for x in raw]
        mus.append(sum(w * 1.01 for w in p) - 1)
        ces.append(ce2([1.01] * 3, p))
    assert max(mus) - min(mus) < 1e-12
    assert max(ces) - min(ces) < 1e-12
    true_ce = ce2([1.01, .01], [.99, .01])
    assert true_ce < 0
    results['bootstrap_support_counterexample'] = {
        'all_conditional_mu_and_ce_approx': .01, 'true_example_ce': true_ce,
        'chance_three_observations_miss_tail': .99 ** 3,
        'chance_ten_observations_miss_tail': .99 ** 10,
        'not_market_estimates': True}

    # Narrow, valid ordering: on identical weights CE <= arithmetic mean.
    for _ in range(2000):
        xs = [rng.uniform(.05, 2.0) for _ in range(10)]
        raw = [rng.expovariate(1) for _ in xs]
        p = [x / sum(raw) for x in raw]
        assert ce2(xs, p) <= sum(w*x for w, x in zip(p, xs)) - 1 + 1e-12
    results['ce_below_same_draw_mean'] = '2000 checks passed; no relation to integrated predictive CE claimed'

    # M05: the declared rule proves direction, not effect >= 1 percentage point.
    point, low, high, tail_upper = .0101, .0001, .0201, .019
    protocol_pass = point >= .01 and low > 0 and tail_upper <= .02
    assert protocol_pass and low < .01
    results['minimum_effect_rule'] = {'point': point, 'ci95': [low, high],
                                      'passes_written_rule': protocol_pass,
                                      'lower_bound_reaches_minimum_effect': low >= .01}

    # Not a bug: 150 days is a calendar minimum, not an evidentiary guarantee.
    results['calendar_preflight'] = {}
    for n in [150, 500]:
        a, ab = math.floor(.6 * n), math.floor(.8 * n)
        results['calendar_preflight'][str(n)] = {
            'days': [a, ab-a, n-ab],
            'complete_30d_windows': [a//30, (ab-a)//30, (n-ab)//30]}
    assert results['calendar_preflight']['150']['complete_30d_windows'] == [3, 1, 1]

    frozen = ROOT / 'research/trader-score-simulation-2026-10-16/compare_ce.py'
    before = hashlib.sha256(frozen.read_bytes()).hexdigest()
    old = runpy.run_path(str(frozen))
    results['existing_regression_assertions'] = old['regressions']()
    assert before == hashlib.sha256(frozen.read_bytes()).hexdigest()
    results['frozen_compare_ce_sha256_unchanged'] = before
    results['audit_check_groups'] = 8
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
