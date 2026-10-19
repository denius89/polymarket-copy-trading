"""Isolated exact arithmetic and gate fixtures, not a trading adapter."""
import hashlib
import json
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent / 'evidence'
POLICY = json.loads((ROOT / 'policies/paper-clob-market-profiles-v1.json').read_text())


def floor_grid(x, step):
    return (F(x) // F(step)) * F(step)


def ceil_grid(x, step):
    return -((-F(x)) // F(step)) * F(step)


def fresh(source_at_receive_ms, uncertainty_ms, elapsed_ms=0,
          acquisition_ms=100, trusted=True, identity=True):
    if source_at_receive_ms is None or uncertainty_ms is None:
        return False
    rule = POLICY['freshness']
    return (trusted and identity and 0 <= elapsed_ms and 0 <= acquisition_ms <= rule['maxSnapshotAcquisitionMs']
            and 0 <= uncertainty_ms <= rule['maxClockUncertaintyMs']
            and source_at_receive_ms >= -uncertainty_ms
            and source_at_receive_ms + elapsed_ms + uncertainty_ms <= rule['maxBookAgeMs'])


def limit_price(best, step, side):
    move = F(POLICY['priceEnvelope']['maxAdverseRelativeMove'])
    return (floor_grid(F(best)*(1+move), step) if side == 'BUY'
            else ceil_grid(F(best)*(1-move), step))


def full_buy(book, notional, cap):
    remaining = F(notional)
    for price, shares in sorted((F(p), F(q)) for p, q in book):
        if price <= F(cap):
            remaining -= min(remaining, price*shares)
    return remaining == 0


def limitless_order_ok(price, raw_shares, side):
    p = F(price)
    qty = F(raw_shares)
    if not (F('.001') <= p <= F('.999') and (p*1000).denominator == 1
            and qty > 0 and qty.denominator == 1):
        return False
    raw_collateral = qty*p
    maker = raw_collateral if side == 'BUY' else qty
    return raw_collateral.denominator == 1 and maker >= 100


def collateral_fee_raw(raw_notional, raw_shares, rate_bps):
    n, s = F(raw_notional), F(raw_shares)
    if not 0 < n < s or not 0 <= rate_bps <= 500:
        raise ValueError('invalid fixture match totals/rate')
    exact = F(rate_bps)*n*(s-n)/(10000*s)
    return ((exact/F(10) + F(1, 2)).__floor__())*10


def explicit_poly_fee(raw):
    fd = raw.get('fd')
    if not isinstance(fd, dict) or not all(k in fd for k in ('r','e')):
        return None
    # Scope of this fixture: documented exponent-1 calculator only.
    if fd['e'] != 1 or F(str(fd['r'])) < 0:
        return None
    return F(str(fd['r'])), fd['e']


def reserve_raw(raw_notional, rate_bps, max_charge_events):
    if max_charge_events is None:
        return None
    # Conservative one quantum per independently rounded charge, not an actual fee.
    return ceil_grid(F(raw_notional)*rate_bps/10000, 1)+10*max_charge_events


class ProfileContract(unittest.TestCase):
    def test_accepted_thresholds_do_not_enable_runtime(self):
        self.assertEqual(POLICY['status'], 'accepted_contract_pending_activation')
        self.assertFalse(POLICY['runtimeEnabled'])
        source_ids={x['id'] for x in json.loads((EVIDENCE.parent/'sources.json').read_text())['claims']}
        for p in POLICY['profiles']:
            self.assertFalse(p['concreteMarketInstanceReady'])
            self.assertTrue(set(p['documentedSources']) <= source_ids)
        r = POLICY['freshness']
        self.assertEqual((r['maxBookAgeMs'], r['maxSnapshotAcquisitionMs'], r['maxClockUncertaintyMs']), (2000,1000,250))
        self.assertFalse(r['clockBoundVerified'])
        self.assertFalse(r['streamAcceptanceVerified'])
        self.assertTrue(all(p['activation'] == 'blocked' for p in POLICY['profiles'] if p['mechanism']=='CLOB'))

    def test_age_upper_bound_at_boundary(self):
        self.assertTrue(fresh(1500,250,250))
        self.assertFalse(fresh(1501,250,250))

    def test_receive_delay_does_not_refresh_old_snapshot(self):
        self.assertFalse(fresh(7477,0,acquisition_ms=190))
        self.assertFalse(fresh(100,20,1900))

    def test_unknown_or_future_time_is_not_fresh(self):
        self.assertFalse(fresh(None,20))
        self.assertFalse(fresh(20,None))
        self.assertFalse(fresh(-251,250))
        self.assertTrue(fresh(-100,250))
        self.assertFalse(fresh(100,251))

    def test_acquisition_and_generation(self):
        self.assertTrue(fresh(100,250,acquisition_ms=1000))
        self.assertFalse(fresh(100,250,acquisition_ms=1001))
        self.assertFalse(fresh(100,250,trusted=False))
        self.assertFalse(fresh(100,250,identity=False))
        self.assertFalse(POLICY['freshness']['heartbeatRefreshesBookAge'])
        self.assertFalse(POLICY['freshness']['limitlessRestOnlyAllowed'])
        self.assertFalse(POLICY['freshness']['limitlessDatabaseFallbackVersionZeroAllowed'])

    def test_relative_price_bound_both_sides(self):
        self.assertEqual(limit_price('.50','.01','BUY'),F('.51'))
        self.assertEqual(limit_price('.50','.01','SELL'),F('.49'))
        self.assertEqual(limit_price('.01','.01','BUY'),F('.01'))
        self.assertFalse(POLICY['priceEnvelope']['reanchorExistingOrder'])

    def test_all_supported_ticks_never_weaken_price_bound(self):
        for tick in ['.1','.01','.005','.0025','.001','.0001']:
            for i in range(1,100):
                best=F(i,100)
                buy=limit_price(best,tick,'BUY');sell=limit_price(best,tick,'SELL')
                self.assertLessEqual(buy,best*F('1.02'))
                self.assertGreaterEqual(sell,best*F('.98'))
                self.assertEqual((buy/F(tick)).denominator,1)
                self.assertEqual((sell/F(tick)).denominator,1)

    def test_full_depth_before_technical_rounding(self):
        book=[('.52','100'),('.50','10'),('.51','10')]
        self.assertTrue(full_buy(book,'10.10','.51'))
        self.assertFalse(full_buy(book,'10.11','.51'))
        self.assertTrue(full_buy(book,'10.10','.51'))  # no amount resized to 10.10

    def test_reward_minimum_not_a_trading_floor(self):
        for p in POLICY['profiles']:
            if p['venue']=='limitless' and p['mechanism']=='CLOB':
                self.assertFalse(p['rewardMinSizeIsTradingMinimum'])
        self.assertTrue(limitless_order_ok('.5',200,'BUY'))  # far below reward minSize

    def test_limitless_grid_uses_exact_collateral_equation(self):
        self.assertTrue(limitless_order_ok('.333',1000,'BUY'))
        self.assertFalse(limitless_order_ok('.333',1001,'BUY'))
        self.assertFalse(limitless_order_ok('.3333',10000,'BUY'))
        self.assertFalse(limitless_order_ok('1',1000,'BUY'))
        self.assertFalse(limitless_order_ok('0',1000,'BUY'))

    def test_maker_floor_is_side_specific(self):
        self.assertTrue(limitless_order_ok('.5',100,'SELL'))
        self.assertFalse(limitless_order_ok('.5',100,'BUY'))
        self.assertFalse(limitless_order_ok('.5',99,'SELL'))
        self.assertTrue(limitless_order_ok('.5',200,'BUY'))

    def test_no_book_complements_and_preserves_quantity(self):
        yes_bids=[(F('.4'),F(12))];yes_asks=[(F('.6'),F(15))]
        no_asks=[(1-p,q) for p,q in yes_bids];no_bids=[(1-p,q) for p,q in yes_asks]
        self.assertEqual(no_asks,[(F('.6'),F(12))])
        self.assertEqual(no_bids,[(F('.4'),F(15))])

    def test_collateral_fee_official_example(self):
        fee=collateral_fee_raw(40000000,100000000,500)
        self.assertEqual(fee,1200000)
        self.assertEqual(40000000+fee,41200000)
        self.assertEqual(40000000-fee,38800000)

    def test_fee_matches_aggregate_before_rounding(self):
        self.assertEqual(collateral_fee_raw(100000000,200000000,500),2500000)
        wrong_level_sum=(collateral_fee_raw(40000000,100000000,500)
                         +collateral_fee_raw(60000000,100000000,500))
        self.assertEqual(wrong_level_sum,2400000)
        self.assertNotEqual(wrong_level_sum,2500000)

    def test_fee_half_up_at_raw_quantum(self):
        # p=.5, exact fee = .025*N; N=200 yields 5 raw => 10 raw.
        self.assertEqual(collateral_fee_raw(200,400,500),10)
        self.assertEqual(collateral_fee_raw(199,398,500),0)
        self.assertEqual(collateral_fee_raw(200,400,0),0)

    def test_reserve_is_not_expected_fee_and_needs_event_bound(self):
        self.assertEqual(reserve_raw(40000000,500,1),2000010)
        self.assertGreater(reserve_raw(40000000,500,1),1200000)
        self.assertIsNone(reserve_raw(40000000,500,None))
        for n in range(100,200):
            for s in [n+1,n*2,n*10]:
                self.assertLessEqual(collateral_fee_raw(n,s,500),reserve_raw(n,500,1))

    def test_gross_net_are_not_double_debited(self):
        gross=F(40);fee=F('1.2');buy_usd_net=gross;sell_usd_net=gross-fee
        self.assertEqual(buy_usd_net+fee,F('41.2'))
        self.assertEqual(sell_usd_net,F('38.8'))
        self.assertNotEqual(sell_usd_net-fee,F('38.8'))
        # Legacy token fee: received amount used once for Q0, no second subtraction.
        net_shares=F(100)-F(3)
        self.assertEqual(net_shares,97)
        self.assertNotEqual(net_shares-F(3),97)

    def test_different_protocol_identity_not_selected_by_presence(self):
        row=json.loads((EVIDENCE/'polymarket-markets.json').read_text())
        self.assertEqual(row['version'],'v1')
        self.assertTrue(row['clobTokenIds'])
        self.assertTrue(row['positionIds'])
        p={x['marketVersion']:x for x in POLICY['profiles'] if x['venue']=='polymarket'}
        self.assertEqual(p['v1']['assetSelector'],'clobTokenIds')
        self.assertEqual(p['v2']['assetSelector'],'positionIds')

    def test_explicit_poly_fee_source_not_legacy_base_or_zero_default(self):
        raw=json.loads((EVIDENCE/'polymarket-clob-market.json').read_text())
        self.assertEqual(explicit_poly_fee(raw),(F('.04'),1))
        self.assertEqual(raw['tbf'],1000)
        self.assertIsNone(explicit_poly_fee({'tbf':1000}))
        self.assertIsNone(explicit_poly_fee({'fd':{}}))
        self.assertIsNone(explicit_poly_fee({'fd':{'r':0}}))
        self.assertEqual(explicit_poly_fee({'fd':{'r':0,'e':1}}),(0,1))

    def test_budget_including_fee_does_not_resize_desired_copy(self):
        desired=F(20);fee_bound=F(1);available=F(20)
        self.assertGreater(desired+fee_bound,available)
        self.assertEqual(desired,20)
        # A smaller result from a convenience SDK helper is a different intent.
        helper_amount=available/(1+F('.05'))
        self.assertLess(helper_amount,desired)
        self.assertNotEqual(helper_amount,desired)

    def test_rest_and_stream_evidence_hashes(self):
        for manifest in ['public-get-manifest.json','stream-manifest.json']:
            for rec in json.loads((EVIDENCE/manifest).read_text())['records']:
                name=rec.get('savedAs',rec.get('artifact'))
                if name:
                    self.assertEqual(hashlib.sha256((EVIDENCE/name).read_bytes()).hexdigest(),rec['artifactSHA256'])

    def test_amm_is_explicitly_unsupported(self):
        amm=next(x for x in POLICY['profiles'] if x['mechanism']=='AMM')
        self.assertEqual(amm['activation'],'unsupported_in_first_profile')


if __name__=='__main__':
    unittest.main(verbosity=2)
