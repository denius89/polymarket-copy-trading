"""Synthetic score sensitivity experiment; no market/execution backtest."""
import csv
import json
import math
import random
import statistics
from pathlib import Path

OUT = Path(__file__).parent
PARAMS = dict(seed=20261016, days=90, repetitions=100, bootstrap=160,
              block=7, alpha=0.10, T_ref=90, N_ref=60, d_ref=0.10, r_ref=0.001)
PROFILES = [
    ('stable', .001, .003, .95, 90),
    ('losing', -.0006, .001, .95, 90),
    ('no_edge', 0, .008, .95, 90),
    ('illiquid', .001, .003, .25, 90),
    ('one_lucky_event', -.0002, .001, .95, 90),
    ('tail_loss', .0008, .002, .95, 90),
    ('one_market_many_fills', .001, .003, .95, 1),
]

def lower(values):
    return sorted(values)[int(PARAMS['alpha'] * (len(values)-1))]

def blocks(values, rng):
    # Paired circular moving blocks preserve local return/fill dependence.
    n = len(values)
    result = []
    while len(result) < n:
        start = rng.randrange(n)
        result.extend(values[(start+j) % n] for j in range(PARAMS['block']))
    return result[:n]

def score(returns, fills, groups, rng):
    if len(returns) < 30 or groups < 20:
        return None
    paired = list(zip(returns, fills))
    bootstrap = [blocks(paired, rng) for _ in range(PARAMS['bootstrap'])]
    L = lower([statistics.fmean(x[0] for x in sample) for sample in bootstrap])
    C = 100*lower([statistics.fmean(x[1] for x in sample) for sample in bootstrap])
    equity = peak = 1.0
    drawdown = 0.0
    for value in returns:
        equity *= 1+value
        peak = max(peak, equity)
        drawdown = max(drawdown, 1-equity/peak)
    # Fixed non-overlapping seven-day blocks, including a shorter final block.
    period_returns = [math.prod(1+r for r in returns[i:i+7])-1
                      for i in range(0, len(returns), 7)]
    b = statistics.fmean(x > 0 for x in period_returns)
    D = 100*math.sqrt(min(1, len(returns)/PARAMS['T_ref']))*math.sqrt(min(1, groups/PARAMS['N_ref']))
    R = 100*math.exp(-drawdown/PARAMS['d_ref'])
    P = 100*max(0, min(1, L/PARAMS['r_ref']))*b
    return dict(score=.30*D+.25*R+.25*C+.20*P, D=D, R=R, C=C, P=P,
                net_return=equity-1, max_drawdown=drawdown, lower_daily_return=L)

def main():
    rows = []
    for profile_index, (name, mu, sigma, fill_prob, groups) in enumerate(PROFILES):
        for repetition in range(PARAMS['repetitions']):
            rng = random.Random(PARAMS['seed']+10000*profile_index+repetition)
            # Net daily marked-to-market returns are synthetic inputs, not derived
            # from orders, fills, fees or real historical books.
            returns = [max(-.99, rng.gauss(mu, sigma)) for _ in range(PARAMS['days'])]
            fills = [float(rng.random() < fill_prob) for _ in returns]
            if name == 'one_lucky_event':
                returns[rng.randrange(len(returns))] += .20
            if name == 'tail_loss':
                returns[rng.randrange(len(returns))] -= .25
            metrics = score(returns, fills, groups, rng)
            rows.append(dict(profile=name, repetition=repetition, eligible=metrics is not None,
                             **(metrics or {})))
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT/'runs.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for name, *_ in PROFILES:
        subset = [r for r in rows if r['profile']==name and r['eligible']]
        summary.append(dict(profile=name, eligible_runs=len(subset),
            median_score=statistics.median(r['score'] for r in subset) if subset else None,
            median_return=statistics.median(r['net_return'] for r in subset) if subset else None,
            median_drawdown=statistics.median(r['max_drawdown'] for r in subset) if subset else None,
            median_P=statistics.median(r['P'] for r in subset) if subset else None,
            profitable_runs=sum(r['net_return']>0 for r in subset),
            losing_score_above_70=sum(r['score']>70 and r['net_return']<0 for r in subset)))
    (OUT/'summary.json').write_text(json.dumps(dict(parameters=PARAMS, summary=summary), indent=2))
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
