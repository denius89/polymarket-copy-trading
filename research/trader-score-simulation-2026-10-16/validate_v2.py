"""Locked-parameter synthetic validation of recommendation vetoes, not production code."""
import csv
import importlib.util
import json
import math
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location('baseline', ROOT/'run.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
SETTINGS = dict(seed=2026101602, repetitions=100, train_days=60, check_days=30,
                copy_lower_min=.80, drawdown_max=.15)
# These two thresholds are experiment assumptions, not approved product defaults.

def evaluate(returns, fills, groups, rng, data_ok=True):
    if not data_ok or groups < 20:
        return dict(status='insufficient_data', reason='missing_source_or_independent_groups',
                    recommended=False, public_score=None, diagnostic_score=None)
    all_metrics = base.score(returns, fills, groups, rng)
    cut = SETTINGS['train_days']
    # Each synthetic day is one independent event group. A real implementation
    # must use market/event IDs, never remove just one fill of a shared event.
    train = base.score(returns[:cut], fills[:cut], cut, rng)
    check = base.score(returns[cut:], fills[cut:], len(returns)-cut, rng)
    reasons = []
    if all_metrics['C']/100 < SETTINGS['copy_lower_min']:
        reasons.append('low_copyability')
    if all_metrics['max_drawdown'] > SETTINGS['drawdown_max']:
        reasons.append('drawdown_outside_research_limit')
    if train['lower_daily_return'] <= 0:
        reasons.append('training_edge_not_confirmed')
    if check['lower_daily_return'] <= 0:
        reasons.append('later_period_edge_not_confirmed')
    if all_metrics['net_return'] <= 0:
        reasons.append('negative_net_result')
    for label, segment in [('train', returns[:cut]), ('check', returns[cut:])]:
        without_best = list(segment)
        without_best.pop(max(range(len(without_best)), key=without_best.__getitem__))
        if math.prod(1+x for x in without_best) <= 1:
            reasons.append(label+'_depends_on_best_event')
    passed = not reasons
    return dict(status='research_candidate' if passed else 'not_confirmed',
                reason=';'.join(reasons), recommended=passed,
                public_score=round(all_metrics['score'], 1) if passed else None,
                diagnostic_score=all_metrics['score'], net_return=all_metrics['net_return'])

def sample(name, repetition):
    # Seed namespace was chosen before inspecting validation outcomes.
    rng = random.Random(SETTINGS['seed'] + repetition)
    profile = next(p for p in base.PROFILES if p[0]==name)
    _, mu, sigma, prob, groups = profile
    returns = [max(-.99, rng.gauss(mu, sigma)) for _ in range(90)]
    fills = [float(rng.random() < prob) for _ in returns]
    if name == 'one_lucky_event':
        returns[rng.randrange(90)] += .20
    if name == 'tail_loss':
        returns[rng.randrange(90)] -= .25
    return returns, fills, groups, rng

def main():
    rows = []
    names = [p[0] for p in base.PROFILES]
    for name in names:
        for repetition in range(SETTINGS['repetitions']):
            returns, fills, groups, rng = sample(name, repetition)
            rows.append(dict(profile=name, repetition=repetition,
                             **evaluate(returns, fills, groups, rng)))
    # Deterministic regressions: a positive score alone must not recommend.
    case_rng = random.Random(19)
    losing = evaluate([-.0001]*90, [1.0]*90, 90, case_rng)
    assert losing['diagnostic_score'] > 70 and not losing['recommended']
    assert losing['public_score'] is None
    lucky_returns = [-.0001]*90
    lucky_returns[20] = .20
    assert not evaluate(lucky_returns, [1.0]*90, 90, case_rng)['recommended']
    assert not evaluate([.001]*90, [1.0]*90, 1, case_rng)['recommended']
    assert not evaluate([.001]*90, [1.0]*90, 90, case_rng, data_ok=False)['recommended']
    assert not evaluate([.001]*90, [.2]*90, 90, case_rng)['recommended']
    assert evaluate([.001]*90, [1.0]*90, 90, case_rng)['recommended']
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (ROOT/'v2-runs.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for name in names:
        subset = [r for r in rows if r['profile']==name]
        valid = [r for r in subset if r['diagnostic_score'] is not None]
        summary.append(dict(profile=name, runs=len(subset),
                            candidates=sum(r['recommended'] for r in subset),
                            median_diagnostic_score=statistics.median(r['diagnostic_score'] for r in valid) if valid else None,
                            negative_candidates=sum(r['recommended'] and r.get('net_return', 0)<0 for r in subset)))
    result = dict(settings=SETTINGS, unchanged_component_parameters=base.PARAMS,
                  regression_checks=6, summary=summary)
    (ROOT/'v2-summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
