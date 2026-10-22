"""Validate fictional financial examples; no API or real money is involved."""
import json
from decimal import Decimal
from pathlib import Path

PACKAGE = Path(__file__).parent
fixture = json.loads((PACKAGE / 'fixtures.json').read_text(), parse_float=Decimal)
alpha = json.loads((PACKAGE / fixture['alphaFixture']).read_text(), parse_float=Decimal)
assert alpha['commissionPercent'] == 0
assert not alpha['realMoneyEnabled'] and not fixture['realMoneyEnabled']
expected_counts = {
    7: {'all': [6, 4, 2], 'receipt': [3, 2, 1], 'expense': [3, 2, 1], 'unmatched': [1, 1, 0]},
    3: {'all': [3, 1, 2], 'receipt': [2, 1, 1], 'expense': [1, 0, 1], 'unmatched': [1, 1, 0]},
}
for period, kinds in expected_counts.items():
    for kind, expected in kinds.items():
        for venue, count in zip(['all', 'Polymarket', 'Limitless'], expected):
            rows = [r for r in alpha['records']
                    if (period == 7 or r['day'] >= 10)
                    and (kind == 'all' or r['direction'] == kind
                         or (kind == 'unmatched' and r['classification'] == 'unmatched'))
                    and (venue == 'all' or r['venue'] == venue)]
            assert len(rows) == count, (period, kind, venue)
            assert len({r['id'] for r in rows}) == count
scenario = fixture['futureExample']
assert Decimal(scenario['principalUSD']) + scenario['transferFeeUSD'] == scenario['calculatedSourceDebitUSD']
assert scenario['otherReserves'] is None
for state, amounts in scenario['states'].items():
    assert sum(amounts.values()) == 120
    assert amounts['availableForNewUSD'] == (120 if state == 'ready' else 0)
    assert amounts['heldPrincipalUSD'] == (120 if state in ['accepted', 'submitted', 'unknown'] else 0)
    assert amounts['settledPrincipalUSD'] == (120 if state == 'paid' else 0)
assert scenario['otherVenueAvailableUSD'] == 40
assert scenario['unconfirmedPolymarketUSD'] == 18
assert fixture['incompletePartner']['knownReservedUSD'] == 25
assert fixture['incompletePartner']['availableUSD'] is None
assert fixture['incompletePartner']['unconfirmedUSD'] is None
times = list(scenario['fictionalTimesUTC'].values())
assert times == sorted(times) and len(set(times)) == 5
print('24 expected filter counts, five conserving PAY-021 snapshots, fees, unknowns and fictional chronology pass.')
