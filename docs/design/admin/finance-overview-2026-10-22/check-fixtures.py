"""Consistency check for fictional finance design amounts; no external API access."""
import json
from decimal import Decimal as D
from pathlib import Path

f = json.loads(Path(__file__).with_name('fixtures.json').read_text())
rows = f['records']
assert f['synthetic'] and not f['realMoneyEnabled']
assert f['mode'] == 'Paper Alpha' and f['commissionPercent'] == 0 and f['usdtUSD'] == 1
assert len({r['id'] for r in rows}) == len(rows) == 6
assert all(r['id'].startswith('ALPHA-') for r in rows)
amount = lambda r: D(str(r['amountUSD']))
sum_rows = lambda rr: sum((amount(r) for r in rr), D('0'))
receipts = sum_rows([r for r in rows if r['direction'] == 'receipt'])
expenses = sum_rows([r for r in rows if r['direction'] == 'expense'])
funding = sum_rows([r for r in rows if r['classification'] == 'funding'])
unmatched = sum_rows([r for r in rows if not r['matched']])
assert (receipts, expenses, funding, unmatched) == (D('1520'), D('24.5'), D('1500'), D('20'))
assert D(str(f['totals']['observedBalanceUSD'])) == D(str(f['openingBalanceUSD'])) + receipts - expenses
assert D(str(f['totals']['matchedFundsUSD'])) == funding - expenses
assert f['incomeAccrualUSD'] == f['partnerLiabilityUSD'] == f['partnerPaidUSD'] == f['pendingPayoutCount'] == 0
for s in f['sources']:
    own = [r for r in rows if r['source'] == s['id']]
    observed = sum_rows([r for r in own if r['direction'] == 'receipt']) - sum_rows([r for r in own if r['direction'] == 'expense'])
    assert observed == D(str(s['observedBalanceUSD']))
    assert D(str(s['matchedUSD'])) + D(str(s['unmatchedUSD'])) == observed
assert sum(D(str(s['observedBalanceUSD'])) for s in f['sources']) == D('1495.5')
for period, days in [(7, f['days']), (3, [10, 11, 12])]:
    selected = [r for r in rows if r['day'] in days]
    expected = (D('1520'), D('24.5')) if period == 7 else (D('520'), D('10'))
    assert (sum_rows([r for r in selected if r['direction'] == 'receipt']), sum_rows([r for r in selected if r['direction'] == 'expense'])) == expected
    for day in days:
        for direction, axis_max in [('receipt', D('1000')), ('expense', D('15'))]:
            assert sum_rows([r for r in selected if r['day'] == day and r['direction'] == direction]) <= axis_max
print('Fictional finance ledger, two periods, source balances, zero Alpha fees and chart scales are consistent.')
