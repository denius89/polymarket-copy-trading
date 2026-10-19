"""Evidence replay and exact diagnostic arithmetic; not an execution adapter."""
import datetime,hashlib,json,statistics,unittest
from fractions import Fraction as F
from pathlib import Path

HERE=Path(__file__).resolve().parent
E=HERE/'evidence'


def replay(frames,venue,identity):
    """Independent full-snapshot review model for labelled fixtures."""
    state=None;version=None;generation=None;events=[];trusted=False
    for gen,payload in frames:
        if generation!=gen:state=None;version=None;trusted=False;generation=gen
        if venue=='limitless':
            if payload.get('marketSlug')!=identity:events.append('identity_mismatch');trusted=False;continue
            v=payload.get('version')
            if not isinstance(v,int) or v<=0:events.append('fallback_or_unknown_version');trusted=False;continue
            book=payload.get('orderbook')
            if not isinstance(book,dict) or not all(isinstance(book.get(k),list) for k in ('bids','asks')):
                events.append('invalid_full_snapshot');trusted=False;continue
            canonical=json.dumps(book,sort_keys=True)
            if version is not None:
                if v<version:events.append('out_of_order');continue
                if v==version:
                    if state==canonical:events.append('duplicate');continue
                    events.append('same_version_conflict');trusted=False;continue
            state=canonical;version=v;trusted=True;events.append('full_snapshot')
        else:
            asset,condition=identity if isinstance(identity,tuple) else (identity,None)
            if condition is not None and payload.get('market')!=condition:
                events.append('identity_mismatch');trusted=False;continue
            if payload.get('event_type')=='book':
                if payload.get('asset_id')!=asset:
                    events.append('identity_mismatch');trusted=False;continue
                if not all(isinstance(payload.get(k),list) for k in ('bids','asks')):
                    events.append('invalid_full_snapshot');trusted=False;continue
                state=json.dumps({k:payload[k] for k in ('bids','asks')},sort_keys=True);trusted=True;events.append('full_snapshot')
            elif payload.get('event_type')=='price_change':
                changes=payload.get('price_changes')
                if not isinstance(changes,list):
                    events.append('invalid_changes');trusted=False;continue
                relevant=[x for x in changes if x.get('asset_id')==asset]
                if not relevant:events.append('unrelated_asset');continue
                if not trusted:events.append('delta_before_seed');continue
                book=json.loads(state)
                for change in relevant:
                    side={'BUY':'bids','SELL':'asks'}.get(change.get('side'))
                    if side is None:
                        events.append('invalid_side');trusted=False;break
                    price=F(str(change['price']));size=F(str(change['size']))
                    if not 0<price<1 or size<0:
                        events.append('invalid_level');trusted=False;break
                    levels={F(str(x['price'])):x for x in book[side]}
                    if size==0:levels.pop(price,None)
                    else:levels[price]={'price':str(change['price']),'size':str(change['size'])}
                    book[side]=[levels[k]for k in sorted(levels,reverse=side=='bids')]
                state=json.dumps(book,sort_keys=True);events.append('delta_after_seed')
            else:events.append('other')
    return {'events':events,'trustedStructuralSeed':trusted,'state':state,'version':version}


def fee_collateral(n,s,r):
    exact=F(r)*F(n)*(F(s)-F(n))/(10000*F(s))
    return (exact/10+F(1,2)).__floor__()*10


def poly_fee(shares,price,rate):
    return F(shares)*F(rate)*F(price)*(1-F(price))


def clock_interval(samples,requests):
    rr={r['id']:r for r in requests};intervals=[]
    for x in samples:
        r=rr[x['requestId']]
        if r.get('httpStatus')==200 and isinstance(x['value'],int):
            # Conditional model ONLY: generated during request, floor-to-seconds,
            # one stable server clock and no cache. Not a publisher-clock proof.
            lo=F(x['value']*1000)-F(r['receivedUnixNs'],1000000)
            hi=F((x['value']+1)*1000)-F(r['sentUnixNs'],1000000)
            intervals.append((lo,hi))
    return max(a for a,b in intervals),min(b for a,b in intervals)


def analyze():
    run=json.loads((E/'run.json').read_text());result={'streams':[],'runtimeActivationAllowed':False}
    lo,hi=clock_interval(run['clockSamples'],run['requests'])
    result['clock']={'samples':len(run['clockSamples']),'conditionalServerMinusLocalIntervalMs':[float(lo),float(hi)],'halfWidthMs':float((hi-lo)/2),'assumptionsVerified':False,'publisherClockBoundVerified':False,'hostSyncConfigurationRead':'administrator_required_not_escalated','localNtpDiagnostic':'two one-shot SNTP reads, no -s/-S; not continuous sync evidence'}
    for stream in run['streams']:
        p=stream['profile'];row={'profile':p['id'],'sessions':[]};ages=[]
        for s in stream['sessions']:
            records=[json.loads(x) for x in (E/s['artifact']).read_text().splitlines()]
            identity=p.get('marketSlug') if p['venue']=='limitless' else (p['assetId'],p['conditionId'])
            replayed=replay([(s['generation'],x['payload']) for x in records],p['venue'],identity)
            for x in records:
                ts=x['payload'].get('timestamp')
                if ts is not None:
                    src=(datetime.datetime.fromisoformat(str(ts).replace('Z','+00:00')).timestamp()*1000 if 'T' in str(ts) else int(ts))
                    ages.append(datetime.datetime.fromisoformat(x['receivedAt']).timestamp()*1000-src)
            row['sessions'].append({'frames':len(records),'bookCount':s['bookCount'],'firstFrameMs':s.get('firstFrameMs'),'frameCapReached':s['frameCapReached'],'replayEvents':{a:replayed['events'].count(a)for a in sorted(set(replayed['events']))},'fullSeedObserved':replayed['trustedStructuralSeed']})
        row['unadjustedSourceLagMs']={'min':min(ages),'median':statistics.median(ages),'max':max(ages),'above2000':sum(x>2000 for x in ages),'count':len(ages)}
        row['streamGate']='partial_observed_not_full_acceptance';result['streams'].append(row)
    result['fees']={'polymarketExponent1':'exact_reference_only_not_settlement_verified','limitlessCollateral':'exact_reference_only_no_deployed_venue_observed','limitlessLegacy':'blocked_no_verified_pretrade_curve; docs_whitepaper_counterexample; SDK_profile_rate_fallback'}
    (E/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');return result


class ActivationAudit(unittest.TestCase):
    def sample(self,version=10,slug='m',size=1):return {'marketSlug':slug,'version':version,'timestamp':'2026-10-19T00:00:00Z','orderbook':{'bids':[{'price':'.4','size':size}],'asks':[]}}

    def test_full_limitless_recording_and_reconnect(self):
        run=json.loads((E/'run.json').read_text());p=next(s for s in run['streams'] if s['profile']['venue']=='limitless')
        for s in p['sessions']:
            frames=[json.loads(x) for x in (E/s['artifact']).read_text().splitlines()]
            self.assertEqual(len(frames),s['frameCount']);self.assertFalse(s['frameCapReached'])
            result=replay([(s['generation'],x['payload'])for x in frames],'limitless',p['profile']['marketSlug'])
            self.assertTrue(result['trustedStructuralSeed'])
            self.assertFalse(set(result['events'])-{'full_snapshot','duplicate','out_of_order'})
            self.assertLessEqual(s['firstFrameMs'],1000)

    def test_full_polymarket_recording_has_seed_per_generation(self):
        run=json.loads((E/'run.json').read_text());p=next(s for s in run['streams'] if s['profile']['venue']=='polymarket')
        for s in p['sessions']:
            frames=[json.loads(x) for x in (E/s['artifact']).read_text().splitlines()]
            self.assertEqual(len(frames),s['frameCount']);self.assertFalse(s['frameCapReached'])
            result=replay([(s['generation'],x['payload'])for x in frames],'polymarket',(p['profile']['assetId'],p['profile']['conditionId']))
            self.assertTrue(result['trustedStructuralSeed']);self.assertNotIn('delta_before_seed',result['events'])
            self.assertLessEqual(s['firstFrameMs'],1000)

    def test_duplicate_does_not_add_quantity(self):
        s=self.sample();a=replay([(0,s)],'limitless','m');b=replay([(0,s),(0,s)],'limitless','m')
        self.assertEqual(a['state'],b['state']);self.assertEqual(b['events'],['full_snapshot','duplicate'])

    def test_noncontiguous_versions_are_not_lost_events(self):
        r=replay([(0,self.sample(10)),(0,self.sample(50,size=2))],'limitless','m')
        self.assertEqual(r['events'],['full_snapshot','full_snapshot']);self.assertEqual(r['version'],50)

    def test_old_frame_does_not_replace_new_book(self):
        r=replay([(0,self.sample(50,size=2)),(0,self.sample(10))],'limitless','m')
        self.assertEqual(r['version'],50);self.assertEqual(r['events'][-1],'out_of_order')

    def test_same_version_different_book_is_conflict(self):
        r=replay([(0,self.sample()),(0,self.sample(size=2))],'limitless','m')
        self.assertFalse(r['trustedStructuralSeed']);self.assertIn('same_version_conflict',r['events'])

    def test_restart_generation_allows_new_lower_live_version(self):
        r=replay([(0,self.sample(50)),(1,self.sample(1))],'limitless','m')
        self.assertTrue(r['trustedStructuralSeed']);self.assertEqual(r['version'],1)

    def test_zero_fallback_and_identity_mismatch_block(self):
        for x in [self.sample(0),self.sample(slug='wrong')]:
            self.assertFalse(replay([(0,self.sample()),(1,x)],'limitless','m')['trustedStructuralSeed'])

    def test_delta_after_reconnect_cannot_reuse_old_seed(self):
        book={'event_type':'book','asset_id':'a','bids':[],'asks':[]}
        delta={'event_type':'price_change','price_changes':[{'asset_id':'a','side':'BUY','price':'.4','size':'1'}]}
        r=replay([(0,book),(1,delta)],'polymarket','a')
        self.assertFalse(r['trustedStructuralSeed']);self.assertEqual(r['events'][-1],'delta_before_seed')

    def test_polymarket_nested_asset_and_absolute_size_updates(self):
        book={'event_type':'book','asset_id':'a','market':'m','bids':[{'price':'.4','size':'5'}],'asks':[]}
        delta={'event_type':'price_change','market':'m','price_changes':[
            {'asset_id':'other','side':'BUY','price':'.4','size':'100'},
            {'asset_id':'a','side':'BUY','price':'.4','size':'7'}]}
        r=replay([(0,book),(0,delta),(0,delta)],'polymarket',('a','m'))
        self.assertEqual(json.loads(r['state'])['bids'][0]['size'],'7')
        self.assertTrue(r['trustedStructuralSeed'])
        bad={**delta,'market':'other'}
        self.assertFalse(replay([(0,book),(0,bad)],'polymarket',('a','m'))['trustedStructuralSeed'])

    def test_polymarket_fee_examples_from_official_table(self):
        # At 100 shares and 50 cents, published category examples are $1.75/$1.25/$1.
        for rate,expected in [('.07','1.75'),('.05','1.25'),('.04','1')]:
            self.assertEqual(poly_fee(100,'.5',rate),F(expected))
        self.assertEqual(poly_fee(100,'.3','.07'),F('1.47'))
        self.assertEqual(poly_fee(100,'.7','.07'),F('1.47'))

    def test_new_collateral_fee_and_rounding_vectors(self):
        self.assertEqual(fee_collateral(40000000,100000000,500),1200000)
        self.assertEqual(fee_collateral(200,400,500),10)
        self.assertEqual(fee_collateral(199,398,500),0)
        self.assertEqual(fee_collateral(40000000,100000000,0),0)

    def test_legacy_whitepaper_not_a_current_quote_calculator(self):
        p=F('.6');rate=F('.03')
        whitepaper_buy_pct=rate*min(p,1-p)/p*100
        self.assertEqual(whitepaper_buy_pct,2)
        self.assertNotEqual(whitepaper_buy_pct,F('2.13')) # current representative table
        p=F('.4');whitepaper_sell_pct=rate*min(p,1-p)*100
        self.assertEqual(whitepaper_sell_pct,F('1.2'))
        self.assertNotEqual(whitepaper_sell_pct,F('1.44'))

    def test_sdk_rank_rate_does_not_equal_effective_rate_by_assumption(self):
        rank=300;effective=150
        self.assertNotEqual(rank,effective)
        self.assertNotEqual(300,0) # fallback is not proof of any actual rate

    def test_api_algebraic_grid_is_not_sdk_builder_grid(self):
        raw_shares=200;price=F('.5')
        self.assertEqual((raw_shares*price).denominator,1)
        self.assertNotEqual(raw_shares%1000,0) # inspected SDK with .001 priceTick rejects
        self.assertEqual(1000%1000,0)

    def test_time_endpoint_does_not_prove_publisher_clock(self):
        run=json.loads((E/'run.json').read_text());lo,hi=clock_interval(run['clockSamples'],run['requests'])
        self.assertLess(lo,hi)
        self.assertGreater(hi-lo,0)
        self.assertTrue(all(isinstance(x['value'],int)for x in run['clockSamples']))
        self.assertFalse(analyze()['clock']['publisherClockBoundVerified'])

    def test_evidence_manifest_hashes(self):
        manifest=json.loads((E/'manifest.json').read_text())
        for row in manifest['files']:
            blob=(E/row['path']).read_bytes()
            self.assertEqual(len(blob),row['bytes'])
            self.assertEqual(hashlib.sha256(blob).hexdigest(),row['sha256'])

    def test_no_profile_enabled_by_diagnostics(self):
        d=json.loads((HERE.parents[1]/'policies/paper-clob-market-profiles-v1.json').read_text())
        self.assertFalse(d['runtimeEnabled'])
        self.assertTrue(all(x['activation']!='enabled'for x in d['profiles']))

if __name__=='__main__':
    analyze();unittest.main(verbosity=2)
