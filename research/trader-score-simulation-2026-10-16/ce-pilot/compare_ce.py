"""Frozen synthetic experiment; Python standard library only, no network or trading.

Run: PYTHONDONTWRITEBYTECODE=1 python3 compare_ce.py
Specification and limitations: CE_REVIEW.md. Outputs are deliberately local research.
"""
import csv
import json
import math
import random
import statistics as st
from pathlib import Path

OUT = Path(__file__).resolve().parent
CFG = dict(seeds=list(range(202610160, 202610166)), wallets_per_type=16,
           history_days=270, horizon=30, future_windows=6, draws=600,
           block=7, budget=200, buy=5, daily_cap=30, position_cap=20,
           fee=.002, min_fill=.60, max_history_drawdown=.25, top_k=10,
           stress_probability=.005, stress_daily_loss=20, ui_scale=.05)
KINDS = ['steady', 'no_edge', 'loser', 'rare_crash', 'rare_upside',
         'illiquid', 'delay_sensitive', 'lucky_history']


def ce(xs, gamma=2):
    if min(xs) <= 0:
        return -1.0  # log/CRRA >= 1: a positive ruin mass implies zero CE wealth.
    if gamma == 1:
        return math.expm1(st.fmean(math.log(x) for x in xs))
    return st.fmean(x ** (1 - gamma) for x in xs) ** (1 / (1 - gamma)) - 1


def drawdown(pnls):
    wealth = peak = CFG['budget']
    worst = 0
    for x in pnls:
        wealth += x
        peak = max(peak, wealth)
        worst = max(worst, 1 - wealth / peak)
    return worst


def costed_pnl(spend, ask, win):
    return spend / ask * (1 - CFG['fee']) * int(win) - spend


def simulate(kind, rng, n, common, history=False):
    """Four distinct binary positions/day, one shared outcome cluster/day.

    Each accepted buy consumes $5 cash, reserves it until end-of-day settlement.
    Synthetic depth is full-or-skip before admission. No sells or partial fills.
    """
    cash = CFG['budget']
    pnls, fills = [], []
    skipped_cash = 0
    for d in range(n):
        # Persistent weekly regimes are shared across wallets of the same world.
        p = {'steady': .57, 'no_edge': .50, 'loser': .46,
             'rare_crash': .97, 'rare_upside': .035,
             'illiquid': .57, 'delay_sensitive': .57,
             'lucky_history': .49}[kind]
        p = min(.999, max(.001, p + .025 * common[d // 7]))
        crash = kind == 'rare_crash' and rng.random() < .018
        win = False if crash else rng.random() < p
        if kind == 'lucky_history' and history and d == 140:
            win = True
        # Delay is adverse movement from leader price into actual synthetic ask.
        leader_price = .90 if kind == 'rare_crash' else (.02 if kind == 'rare_upside' else .50)
        if kind == 'lucky_history' and history and d == 140:
            leader_price = .025
        delay = .09 if kind == 'delay_sensitive' else .002
        ask = min(.999, leader_price + delay)
        spent = payoff = accepted = 0
        for _ in range(4):
            enough_depth = rng.random() < (.25 if kind == 'illiquid' else .96)
            if not enough_depth:
                continue
            if cash < CFG['buy']:
                skipped_cash += 1
                continue
            if spent + CFG['buy'] > CFG['daily_cap'] or CFG['buy'] > CFG['position_cap']:
                continue
            cash -= CFG['buy']
            spent += CFG['buy']
            accepted += 1
            payoff += CFG['buy'] / ask * (1 - CFG['fee']) * int(win)
        cash += payoff
        pnls.append(payoff - spent)
        fills.append(accepted / 4)
    return pnls, fills, skipped_cash


def predict(pnls, rng):
    # Non-overlapping seven-day blocks preserve within-block dependence;
    # omit final incomplete block explicitly. Bayesian bootstrap weights over blocks.
    b = CFG['block']
    blocks = [pnls[i:i+b] for i in range(0, len(pnls)-b+1, b)]
    means = [st.fmean(x) for x in blocks]
    ws, stressed, posterior_means = [], [], []
    for _ in range(CFG['draws']):
        weights = [rng.expovariate(1) for _ in blocks]
        total = sum(weights)
        posterior_means.append(sum(w*m for w, m in zip(weights, means))/total)
        selected = rng.choices(blocks, weights=weights, k=math.ceil(CFG['horizon']/b))
        path = [x for block in selected for x in block][:CFG['horizon']]
        ws.append(max(0, 1 + sum(path) / CFG['budget']))
        stressed_path = [-CFG['stress_daily_loss'] if rng.random() < CFG['stress_probability'] else x
                         for x in path]
        stressed.append(max(0, 1 + sum(stressed_path) / CFG['budget']))
    return dict(lcb=sorted(posterior_means)[int(.1*len(posterior_means))],
                ce2=ce(ws), ce1=ce(ws, 1), probability=st.fmean(x > 1 for x in ws),
                ce2_stress=ce(stressed), predicted_mean=st.fmean(ws)-1,
                low=sorted(ws)[int(.05*len(ws))], high=sorted(ws)[int(.95*len(ws))])


def regressions():
    assert abs(ce([1.1]*50)-.1) < 1e-12
    assert abs(ce([1.1]*50, 1)-.1) < 1e-12
    assert ce([1, 0]) == -1
    a = [1.001]*99+[.10]
    b = [1.05]*80+[.98]*20
    assert st.fmean(x > 1 for x in a) > st.fmean(x > 1 for x in b)
    assert ce(a) < 0 < ce(b)
    assert abs(ce(a) - (-.08173562058526751)) < 1e-12
    assert costed_pnl(5, .502, True) < costed_pnl(5, .5, True)
    assert costed_pnl(5, .502, False) == -5
    # Four perfectly correlated fills are one outcome: averaging does not diversify it.
    assert st.pvariance([4*x for x in [-5, 5]]) == 16*st.pvariance([-5, 5])
    assert abs(drawdown([10, -21]) - .1) < 1e-12
    assert ce([1]*20) == 0
    return 10


def main():
    tests = regressions()
    rows, picks, worlds = [], [], []
    for seed in CFG['seeds']:
        env = random.Random(seed)
        hc = [env.choice([-1, 1]) for _ in range(math.ceil(CFG['history_days']/7))]
        # Future random streams are disjoint and never used for selection.
        fc = [[env.choice([-1, 1]) for _ in range(math.ceil(CFG['horizon']/7))]
              for _ in range(CFG['future_windows'])]
        cohort = []
        for ki, kind in enumerate(KINDS):
            for j in range(CFG['wallets_per_type']):
                wid = ki*CFG['wallets_per_type']+j
                hist, fill, skips = simulate(kind, random.Random(seed*10000+wid),
                                            CFG['history_days'], hc, True)
                pred = predict(hist, random.Random(seed*100000+wid))
                gate = st.fmean(fill) >= CFG['min_fill'] and drawdown(hist) <= CFG['max_history_drawdown']
                cohort.append(dict(seed=seed, wallet=wid, kind=kind, gate=gate,
                                   history_return=sum(hist)/200, history_drawdown=drawdown(hist),
                                   fill=st.fmean(fill), history_cash_skips=skips, **pred))
        # Freeze all lists before generating any future trades.
        frozen = {}
        for method in ['lcb', 'ce2', 'ce1', 'probability', 'ce2_stress']:
            threshold = .5 if method == 'probability' else 0
            eligible = [x for x in cohort if x['gate'] and x[method] > threshold]
            frozen[method] = [x['wallet'] for x in sorted(eligible, key=lambda x: (-x[method], x['wallet']))[:CFG['top_k']]]
        worlds.append(dict(seed=seed, frozen=frozen))
        for row in cohort:
            actual = []
            for window in range(CFG['future_windows']):
                pnl, fill, skips = simulate(row['kind'], random.Random(seed*1000000+row['wallet']*10+window),
                                            CFG['horizon'], fc[window])
                actual.append(dict(wealth=max(0, 1+sum(pnl)/200), drawdown=drawdown(pnl),
                                   fill=st.fmean(fill), cash_skips=skips))
            row['future_mean_return'] = st.fmean(x['wealth']-1 for x in actual)
            row['future_ce2'] = ce([x['wealth'] for x in actual])
            row['interval_coverage'] = st.fmean(row['low'] <= x['wealth'] <= row['high'] for x in actual)
            row['future_mean_drawdown'] = st.fmean(x['drawdown'] for x in actual)
            row['score_ce2_illustrative'] = 100/(1+math.exp(-row['ce2']/CFG['ui_scale']))
            rows.append(row)
            for method, selected in frozen.items():
                if row['wallet'] in selected:
                    for window, x in enumerate(actual):
                        picks.append(dict(seed=seed, method=method, wallet=row['wallet'], kind=row['kind'],
                                          window=window, **x))
        print('Completed world', seed, flush=True)
    summary = dict(config=CFG, regression_checks=tests, wallets=len(rows), methods={})
    for method in ['lcb', 'ce2', 'ce1', 'probability', 'ce2_stress']:
        selected = [x for x in picks if x['method'] == method]
        xs = [x['wealth'] for x in selected]
        counts = {k:sum(x['kind']==k for x in selected)//CFG['future_windows'] for k in KINDS}
        per_world = []
        for seed in CFG['seeds']:
            group = [x['wealth'] for x in selected if x['seed']==seed]
            per_world.append(dict(seed=seed, ce2=ce(group) if group else None,
                                  mean_return=st.fmean(group)-1 if group else None))
        summary['methods'][method] = dict(selected_wallets=len(selected)//CFG['future_windows'],
             type_counts=counts, future_mean_return=st.fmean(xs)-1, future_ce2=ce(xs),
             future_loss_frequency=st.fmean(x<1 for x in xs),
             future_loss_over_20pct=st.fmean(x<.8 for x in xs),
             future_mean_drawdown=st.fmean(x['drawdown'] for x in selected),
             future_worst_return=min(xs)-1, per_world=per_world)
    summary['prediction_90pct_interval_coverage'] = st.fmean(x['interval_coverage'] for x in rows)
    summary['type_diagnostics'] = {kind:dict(
        admitted=sum(x['gate'] for x in rows if x['kind']==kind),
        future_mean_return=st.fmean(x['future_mean_return'] for x in rows if x['kind']==kind),
        interval_coverage=st.fmean(x['interval_coverage'] for x in rows if x['kind']==kind)) for kind in KINDS}
    for name, data in [('ce-wallets.csv', rows), ('ce-selections.csv', picks)]:
        with (OUT/name).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    (OUT/'ce-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (OUT/'ce-frozen-selections.json').write_text(json.dumps(worlds, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
